from dataclasses import dataclass
from threading import Timer
import logging

from fastapi.datastructures import QueryParams
import httpx
from fastapi import FastAPI, HTTPException, Request, Response
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from memoization import cached

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

app = FastAPI()

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


URL_FROM_NAME: dict[str, Device] = {}


class RegisterRequest(BaseModel):
    name: str
    url: str


@app.post("/register")
async def register_device(request: RegisterRequest) -> str:
    logging.info(f"Registering device {request.name} with url {request.url}")

    def remove_device():
        logging.info(f"Removing device {request.name}")
        URL_FROM_NAME.pop(request.name, None)

    timer = Timer(60 * 5, remove_device)
    if request.name in URL_FROM_NAME:
        URL_FROM_NAME[request.name].removalTimer.cancel()
    URL_FROM_NAME[request.name] = Device(
        request.url,
        timer,
    )
    timer.start()
    return "OK"


@app.get("/list")
async def list_devices():
    return [{"name": name} for name in URL_FROM_NAME.keys()]


@app.get("/{name}/{path:path}")
async def forward(request: Request, name: str, path: str) -> Response:
    forward_func = _cached_forward if ".ts" in path else _forward
    return forward_func(name, path, request.query_params)


@cached(max_size=100)
def _cached_forward(name: str, path: str, query_params: QueryParams) -> Response:
    return _forward(name, path, query_params)


def _forward(name: str, path: str, query_params: QueryParams) -> Response:
    if name not in URL_FROM_NAME:
        raise HTTPException(status_code=404, detail="Name not registered")
    url = URL_FROM_NAME[name].url
    device_url = f"{url}/{path}"
    response = httpx.get(device_url, timeout=20.0, params=query_params)
    return Response(
        content=response.content,
        status_code=response.status_code,
        headers=dict(response.headers),
    )
