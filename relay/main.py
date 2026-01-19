import logging

from common.auth.google import get_id_token
import httpx
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import BaseModel


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


class Settings(BaseSettings):
    recorder_url: str = "http://localhost:8003"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()


app = FastAPI()


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
def register_device(register_request: RegisterRequest) -> Response:
    logging.info(
        f"Registering device {register_request.name} with url {register_request.url}"
    )
    token = get_id_token(settings.recorder_url)
    response = httpx.post(
        f"{settings.recorder_url}/register",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": register_request.name, "url": register_request.url},
    )
    return Response(
        content=response.content,
        status_code=response.status_code,
        headers=response.headers,
    )
