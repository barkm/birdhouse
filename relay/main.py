from contextlib import asynccontextmanager
from dataclasses import dataclass
from threading import Timer
import logging

from common.auth.exception import AuthException
from common.auth.google import get_id_token
from fastapi.responses import JSONResponse
import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import create_engine
from pydantic import BaseModel

from common.auth import firebase


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
) -> str:
    if request.state.role != firebase.Role.ADMIN:
        raise HTTPException(status_code=403, detail="Forbidden")
    logging.info(
        f"Registering device {register_request.name} with url {register_request.url}"
    )
    token = get_id_token(settings.register_url)
    httpx.post(
        settings.register_url,
        headers={"Authorization": f"Bearer {token}"},
        json={"name": register_request.name, "url": register_request.url},
    )
    return "OK"
