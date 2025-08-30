from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic_settings import BaseSettings

from stream import Stream


PLAYLIST_FILENAME = "playlist.m3u8"


class Settings(BaseSettings):
    test_stream: bool = False


settings = Settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.stream = Stream(PLAYLIST_FILENAME, settings.test_stream)
    yield
    app.state.stream.stop()


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

app = FastAPI(lifespan=lifespan)


@app.get("/hls/{filename:path}")
async def serve_hls_files(request: Request, filename: str):
    stream: Stream = request.app.state.stream
    stream_path = stream.get_file(filename)
    if not stream_path:
        raise HTTPException(status_code=404, detail="File not found")
    headers = (
        {"Cache-Control": "no-store", "Pragma": "no-cache", "Expires": "0"}
        if "m3u8" in filename
        else {}
    )
    return FileResponse(stream_path, headers=headers)


@app.get("/start")
async def start_stream(request: Request):
    stream: Stream = request.app.state.stream
    stream.start()
    return {"playlist": f"/hls/{PLAYLIST_FILENAME}"}
