import httpx
from fastapi import FastAPI, HTTPException, Response

RELAY_URL = "http://127.0.0.1:5000"

app = FastAPI()


@app.get("/hls/{name}/{path}")
async def get_hls_stream(name: str, path: str) -> Response:
    device_url = f"{RELAY_URL}/hls/{name}/{path}"
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
