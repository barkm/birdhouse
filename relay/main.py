import logging

from common.auth.google import get_id_token
from fastapi.responses import JSONResponse
import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import create_engine
from pydantic import BaseModel


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


app = FastAPI()

engine = create_engine(settings.database_url)


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    headers = dict(request.headers)
    if "x-external" in headers:
        return JSONResponse({"detail": "Forbidden"}, status_code=403)
    return await call_next(request)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class RegisterRequest(BaseModel):
    name: str
    url: str


@app.post("/register")
def register_device(register_request: RegisterRequest) -> str:
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
