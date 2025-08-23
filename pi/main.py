from contextlib import asynccontextmanager, contextmanager
from pathlib import Path
import platform
import subprocess
import tempfile
import uuid
from typing import Generator
import time

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic_settings import BaseSettings


PLAYLIST_FILENAME = "playlist.m3u8"


class Settings(BaseSettings):
    test_stream: bool = False


settings = Settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    with _get_stream(settings.test_stream) as stream:
        app.state.stream = stream
        yield


app = FastAPI(lifespan=lifespan)


@app.get("/hls/{filename:path}")
async def serve_hls_files(request: Request, filename: str):
    headers = {"Cache-Control": "no-store", "Pragma": "no-cache", "Expires": "0"}
    stream: Stream = request.app.state.stream
    stream_path = stream.get_file(filename)
    if not stream_path:
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(stream_path, headers=headers)


class Stream:
    def __init__(self, directory: Path, test_stream: bool):
        self.directory = directory
        self.test_stream = test_stream
        self.video = None

    def get_file(self, filename: str) -> Path | None:
        path = self.directory / filename
        if path.suffix not in {".m3u8", ".ts"}:
            return None
        self.start()
        if path.name == PLAYLIST_FILENAME:
            _wait_until_exists(path)
        return path if path.exists() else None

    def start(self) -> None:
        if not self.video:
            self.video = _start_hls_video_stream(self.directory, self.test_stream)

    def stop(self) -> None:
        if self.video:
            self.video.terminate()


def _wait_until_exists(path: Path) -> None:
    while not path.exists():
        time.sleep(0.1)


@contextmanager
def _get_stream(test_stream: bool) -> Generator[Stream, None, None]:
    with tempfile.TemporaryDirectory() as temp_dir_str:
        stream = Stream(Path(temp_dir_str), test_stream)
        try:
            yield stream
        finally:
            stream.stop()


def _start_hls_video_stream(stream_dir: Path, test_stream: bool) -> subprocess.Popen:
    stream_dir.mkdir(parents=True, exist_ok=True)
    stream_file_path = stream_dir / PLAYLIST_FILENAME
    segment_filename = stream_dir / (uuid.uuid4().hex + "_%04d.ts")
    if test_stream:
        return _start_test_stream(segment_filename, stream_file_path)
    if is_raspberry_pi():
        return _start_hls_video_stream_raspberry_pi(segment_filename, stream_file_path)
    if is_mac():
        return _start_hls_video_stream_mac(segment_filename, stream_file_path)
    raise RuntimeError("Unsupported platform for HLS streaming")


def _start_test_stream(
    segment_filename: Path, stream_file_path: Path
) -> subprocess.Popen:
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
            "-hls_segment_filename",
            str(segment_filename),
            str(stream_file_path),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _start_hls_video_stream_mac(
    segment_filename: Path, stream_file_path: Path
) -> subprocess.Popen:
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
            "-hls_segment_filename",
            str(segment_filename),
            str(stream_file_path),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _start_hls_video_stream_raspberry_pi(
    segment_filename: Path, stream_file_path: Path
) -> subprocess.Popen:
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
            "-hls_segment_filename",
            str(segment_filename),
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
