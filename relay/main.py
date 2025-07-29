import httpx
from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from memoization import cached

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

URL_FROM_NAME: dict[str, str] = {}


class RegisterRequest(BaseModel):
    name: str
    url: str


@app.post("/register")
async def register_device(request: RegisterRequest) -> str:
    URL_FROM_NAME[request.name] = request.url
    return "OK"


@app.get("/{name}/{path:path}")
async def forward(name: str, path: str) -> Response:
    return _forward(name, path) if "m3u8" in path else _cached_forward(name, path)


@cached
def _cached_forward(name: str, path: str) -> Response:
    return _forward(name, path)


def _forward(name: str, path: str) -> Response:
    if name not in URL_FROM_NAME:
        raise HTTPException(status_code=404, detail="Name not registered")
    url = URL_FROM_NAME[name]
    device_url = f"{url}/{path}"
    response = httpx.get(device_url)
    return Response(
        content=response.content,
        status_code=response.status_code,
        headers=dict(response.headers),
    )
