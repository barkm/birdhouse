import httpx
from fastapi import FastAPI, Response
from pydantic_settings import BaseSettings
from fastapi.middleware.cors import CORSMiddleware


class Settings(BaseSettings):
    relay_url: str = "http://127.0.0.1:5000"


settings = Settings()
app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/{name}/hls/{path}")
async def get_hls_stream(name: str, path: str) -> Response:
    device_url = f"{settings.relay_url}/{name}/hls/{path}"
    response = httpx.get(device_url)
    return Response(
        content=response.content,
        status_code=response.status_code,
        headers=dict(response.headers),
    )
