from contextlib import asynccontextmanager
import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic_settings import BaseSettings

from stream import Stream
from sensor import read_sensor_data


PLAYLIST_FILENAME = "playlist.m3u8"


class Settings(BaseSettings):
    test_stream: bool = False
    test_sensor: bool = False


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
    if not _is_filename(filename):
        raise HTTPException(status_code=400, detail="Invalid filename")
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
async def start_stream(request: Request, bitrate: int = 500000, framerate: int = 24):
    stream: Stream = request.app.state.stream
    stream.start(bitrate, framerate)
    return {"playlist": f"/hls/{PLAYLIST_FILENAME}"}


def _is_filename(filename: str) -> bool:
    path = Path(filename)
    return (
        len(path.parts) == 1 and not path.is_absolute() and filename not in {"..", "."}
    )


@app.get("/sensor")
async def get_sensor_data():
    try:
        return read_sensor_data(settings.test_sensor)
    except RuntimeError as e:
        raise HTTPException(status_code=501, detail="Sensor not available") from e
