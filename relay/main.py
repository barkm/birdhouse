from contextlib import asynccontextmanager
from dataclasses import dataclass
from threading import Timer
import logging

from common.auth.exception import AuthException
from common.auth.google import get_id_token
from fastapi.datastructures import QueryParams
from fastapi.responses import JSONResponse
import httpx
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import create_engine
from sqlalchemy.orm import aliased
from sqlmodel import Session, func, select
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


@app.get("/list")
def list_devices(request: Request, session: Session = Depends(get_session)):
    devices = _get_active_devices(session)
    return [
        {"name": device.name}
        for device in devices
        if request.state.role in device.allowed_roles
    ]


@app.get("/{name}/{path:path}")
def forward(
    request: Request, name: str, path: str, session: Session = Depends(get_session)
) -> Response:
    device = _get_device(name, session)
    if not device:
        raise HTTPException(status_code=404, detail="Name not registered")
    if request.state.role not in device.allowed_roles:
        raise HTTPException(status_code=403, detail="Forbidden")
    forward_func = _cached_forward if ".ts" in path else _forward
    url = f"{_get_url(name, session)}/{path}"
    return forward_func(url, request.query_params)


@cached(max_size=100)
def _cached_forward(url: str, query_params: QueryParams) -> Response:
    return _forward(url, query_params)


def _forward(url: str, query_params: QueryParams) -> Response:
    response = httpx.get(url, timeout=20.0, params=query_params)
    return Response(
        content=response.content,
        status_code=response.status_code,
        headers=dict(response.headers),
    )


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
    if not _is_active(register.url):
        raise HTTPException(status_code=503, detail="Device is not active")
    return register.url


def _get_active_devices(session: Session) -> list[models.Device]:
    r = aliased(models.Register)
    ranked = select(
        r.id,
        r.device_id,
        func.row_number()
        .over(partition_by=r.device_id, order_by=r.created_at.desc())  # type: ignore
        .label("rn"),
    ).subquery()
    device_registers = (
        select(models.Device, models.Register)
        .join(models.Register, models.Register.device_id == models.Device.id)  # type: ignore
        .join(ranked, ranked.c.id == models.Register.id)
        .where(ranked.c.rn == 1)
    )
    return [d for d, r in session.exec(device_registers).all() if _is_active(r.url)]


def _is_active(url: str) -> bool:
    try:
        response = httpx.get(f"{url}/status", timeout=5.0)
        return response.status_code == 200
    except httpx.RequestError:
        return False
