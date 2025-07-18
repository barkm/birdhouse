from contextlib import asynccontextmanager
from pathlib import Path
import platform
import subprocess
import tempfile

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic_settings import BaseSettings


PLAYLIST_FILENAME = "playlist.m3u8"


class Settings(BaseSettings):
    test_stream: bool = False


settings = Settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    with tempfile.TemporaryDirectory() as temp_dir_str:
        hls_dir = Path(temp_dir_str)
        app.state.hls_dir = hls_dir
        video = _start_hls_video_stream(hls_dir, settings.test_stream)
        yield
        video.terminate()


app = FastAPI(lifespan=lifespan)


@app.get("/hls/{path:path}")
async def serve_hls_files(request: Request, path: str):
    hls_dir: Path = request.app.state.hls_dir
    file_path = hls_dir / path
    if not file_path.resolve().is_relative_to(hls_dir.resolve()):
        raise HTTPException(status_code=403, detail="Forbidden")
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path)


def _start_hls_video_stream(stream_dir: Path, test_stream: bool) -> subprocess.Popen:
    stream_dir.mkdir(parents=True, exist_ok=True)
    stream_file_path = stream_dir / PLAYLIST_FILENAME
    if test_stream:
        return _start_test_stream(stream_file_path)
    if is_raspberry_pi():
        return _start_hls_video_stream_raspberry_pi(stream_file_path)
    if is_mac():
        return _start_hls_video_stream_mac(stream_file_path)
    raise RuntimeError("Unsupported platform for HLS streaming")


def _start_test_stream(stream_file_path: Path) -> subprocess.Popen:
    return subprocess.Popen(
        [
            "ffmpeg",
            "-f",
            "lavfi",
            "-i",
            "testsrc=size=1280x720:rate=30",
            "-f",
            "hls",
            "-hls_time",
            "2",
            "-hls_list_size",
            "5",
            "-hls_flags",
            "delete_segments",
            str(stream_file_path),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _start_hls_video_stream_mac(stream_file_path: Path) -> subprocess.Popen:
    return subprocess.Popen(
        [
            "ffmpeg",
            "-framerate",
            "30",
            "-f",
            "avfoundation",
            "-i",
            "0",
            "-f",
            "hls",
            "-hls_time",
            "2",
            "-hls_list_size",
            "5",
            "-hls_flags",
            "delete_segments",
            str(stream_file_path),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _start_hls_video_stream_raspberry_pi(stream_file_path: Path) -> subprocess.Popen:
    rpicam = subprocess.Popen(
        [
            "rpicam-vid",
            "-t",
            "0",
            "--width",
            "1920",
            "--height",
            "1080",
            "--framerate",
            "30",
            "-o",
            "-",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    ffmpeg = subprocess.Popen(
        [
            "ffmpeg",
            "-i",
            "-",
            "-c:v",
            "copy",
            "-f",
            "hls",
            "-hls_time",
            "2",
            "-hls_list_size",
            "5",
            "-hls_flags",
            "delete_segments",
            str(stream_file_path),
        ],
        stdin=rpicam.stdout,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return ffmpeg


def is_mac():
    """Checks if the code is running on a macOS machine."""
    return platform.system() == "Darwin"


def is_raspberry_pi():
    """Checks if the code is running on a Raspberry Pi."""
    if not platform.system() == "Linux":
        return False

    model_file = Path("/sys/firmware/devicetree/base/model")
    return model_file.exists() and "raspberry pi" in model_file.read_text().lower()
