import httpx
from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

PORT_FROM_NAME: dict[str, int] = {}


class RegisterRequest(BaseModel):
    name: str
    port: int


@app.post("/register")
async def register_device(request: RegisterRequest) -> str:
    PORT_FROM_NAME[request.name] = request.port
    return "OK"


@app.get("/hls/{name}/{path}")
async def get_hls_stream(name: str, path: str) -> Response:
    if name not in PORT_FROM_NAME:
        raise HTTPException(status_code=404, detail="Name not registered")
    port = PORT_FROM_NAME[name]
    device_url = f"http://localhost:{port}/hls/{path}"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(device_url)
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers),
            )
    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=str(e))
