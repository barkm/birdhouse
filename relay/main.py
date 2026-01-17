from contextlib import asynccontextmanager
from dataclasses import dataclass
from threading import Timer
import logging

from common.auth.exception import AuthException
from common.auth.google import get_id_token
from fastapi.responses import JSONResponse
import httpx
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import create_engine
from sqlmodel import Session, select
from pydantic import BaseModel

from common.auth import firebase

import models


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://relay_user:relay@localhost/relay"
    register_url: str = "http://localhost:8003/register"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    firebase.initialize()
    yield


app = FastAPI(lifespan=lifespan)

engine = create_engine(settings.database_url)


def get_session():
    with Session(engine) as session:
        yield session


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    headers = dict(request.headers)
    if "x-external" not in headers:
        request.state.role = firebase.Role.ADMIN
        return await call_next(request)
    try:
        request.state.role = firebase.verify(headers)
    except AuthException as e:
        return JSONResponse({"detail": e.detail}, status_code=e.status_code)
    return await call_next(request)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@dataclass
class Device:
    url: str
    removalTimer: Timer


class RegisterRequest(BaseModel):
    name: str
    url: str


@app.post("/register")
def register_device(
    request: Request,
    register_request: RegisterRequest,
    session: Session = Depends(get_session),
) -> str:
    if request.state.role != firebase.Role.ADMIN:
        raise HTTPException(status_code=403, detail="Forbidden")
    logging.info(
        f"Registering device {register_request.name} with url {register_request.url}"
    )
    device = _get_device(register_request.name, session) or _add_device(
        register_request.name, session
    )
    _register_device(device, register_request.url, session)

    token = get_id_token(settings.register_url)
    httpx.post(
        settings.register_url,
        headers={"Authorization": f"Bearer {token}"},
        json={"name": register_request.name, "url": register_request.url},
    )

    return "OK"


def _get_device(name: str, session: Session) -> models.Device | None:
    statement = select(models.Device).where(models.Device.name == name)
    return session.exec(statement).first()


def _add_device(name: str, session: Session) -> models.Device:
    device = models.Device(name=name, allowed_roles=[firebase.Role.ADMIN])
    session.add(device)
    session.commit()
    session.refresh(device)
    return device


def _register_device(device: models.Device, url: str, session: Session):
    register = models.Register(device_id=device.id, url=url)
    session.add(register)
    session.commit()
    session.refresh(register)
