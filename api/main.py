import httpx
from fastapi import FastAPI, HTTPException, Response
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    relay_url: str = "http://127.0.0.1:5000"


settings = Settings()
app = FastAPI()


@app.get("/hls/{name}/{path}")
async def get_hls_stream(name: str, path: str) -> Response:
    device_url = f"{settings.relay_url}/hls/{name}/{path}"
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
