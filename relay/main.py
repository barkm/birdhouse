from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from threading import Timer
import logging

from common.auth.exception import AuthException
from fastapi.datastructures import QueryParams
from fastapi.responses import JSONResponse
import httpx
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import create_engine
from sqlmodel import Session, select
from memoization import cached
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
        return await call_next(request)
    try:
        firebase.verify(headers)
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
async def register_device(
    request: RegisterRequest, session: Session = Depends(get_session)
) -> str:
    logging.info(f"Registering device {request.name} with url {request.url}")

    device = _get_device(request.name, session)
    _register_to_db(device, request.url, session)

    return "OK"


def _get_device(name: str, session: Session) -> models.Device:
    statement = select(models.Device).where(models.Device.name == name)
    device = session.exec(statement).first()
    if not device:
        device = models.Device(name=name, allowed_roles=[firebase.Role.ADMIN])
        session.add(device)
        session.commit()
        session.refresh(device)
    return device


def _register_to_db(device: models.Device, url: str, session: Session):
    register = models.Register(device_id=device.id, url=url)
    session.add(register)
    session.commit()
    session.refresh(register)


@app.get("/list")
async def list_devices(session: Session = Depends(get_session)):
    devices = _get_active_devices(session)
    return [{"name": device.name} for device in devices]


@app.get("/{name}/{path:path}")
async def forward(
    request: Request, name: str, path: str, session: Session = Depends(get_session)
) -> Response:
    forward_func = _cached_forward if ".ts" in path else _forward
    return forward_func(name, path, request.query_params, session)


@cached(
    max_size=100,
    custom_key_maker=lambda name, path, query_params, _: (name, path, query_params),
)
def _cached_forward(
    name: str, path: str, query_params: QueryParams, session: Session
) -> Response:
    return _forward(name, path, query_params, session)


def _forward(
    name: str, path: str, query_params: QueryParams, session: Session
) -> Response:
    url = _get_url(name, session)
    device_url = f"{url}/{path}"
    response = httpx.get(device_url, timeout=20.0, params=query_params)
    return Response(
        content=response.content,
        status_code=response.status_code,
        headers=dict(response.headers),
    )


def _get_url(name: str, session: Session) -> str:
    statement = (
        select(models.Register)
        .join(models.Device)
        .where(models.Device.name == name)
        .order_by(models.Register.created_at.desc())  # type: ignore
    )
    register = session.exec(statement).first()
    if not register:
        raise HTTPException(status_code=404, detail="Name not registered")
    if register.created_at < datetime.now() - timedelta(minutes=5):
        raise HTTPException(status_code=404, detail="Device registration expired")
    return register.url


def _get_active_devices(session: Session) -> list[models.Device]:
    statement = (
        select(models.Device)
        .join(models.Register)
        .where(models.Register.created_at >= datetime.now() - timedelta(minutes=5))
        .distinct()
    )
    return list(session.exec(statement).all())
