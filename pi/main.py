from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
import platform
import subprocess
import tempfile
import uuid
import time
from threading import Lock, Timer
import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic_settings import BaseSettings


PLAYLIST_FILENAME = "playlist.m3u8"


class Settings(BaseSettings):
    test_stream: bool = False


settings = Settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.stream = Stream(settings.test_stream)
    yield
    app.state.stream.stop()


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

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


@dataclass
class Video:
    process: subprocess.Popen
    directory: Path
    timer: Timer


class Stream:
    def __init__(self, test_stream: bool):
        self.test_stream = test_stream
        self.video = None
        self.video_lock = Lock()

    def get_file(self, filename: str) -> Path | None:
        if Path(filename).suffix not in {".m3u8", ".ts"}:
            return None
        path = self.start() / filename
        return path if path.exists() else None

    def start(self) -> Path:
        with self.video_lock:
            if self.video:
                self.video.timer.cancel()
                self.video.timer = self._get_video_timer()
            else:
                logger.info("Starting video stream")
                directory = Path(tempfile.mkdtemp())
                self.video = Video(
                    process=_start_hls_video_stream(directory, self.test_stream),
                    directory=directory,
                    timer=self._get_video_timer(),
                )
            self.video.timer.start()
        return self.video.directory

    def _get_video_timer(self) -> Timer:
        return Timer(20.0, self.stop)

    def stop(self) -> None:
        with self.video_lock:
            if self.video:
                logger.info("Stopping video stream")
                self.video.process.terminate()
                _remove_directory(self.video.directory)
                self.video.timer.cancel()
                self.video = None


def _remove_directory(dirpath: Path) -> None:
    for child in dirpath.iterdir():
        if child.is_dir():
            _remove_directory(child)
        else:
            child.unlink()
    dirpath.rmdir()


def _start_hls_video_stream(stream_dir: Path, test_stream: bool) -> subprocess.Popen:
    stream_dir.mkdir(parents=True, exist_ok=True)
    stream_file_path = stream_dir / PLAYLIST_FILENAME
    segment_filename = stream_dir / (uuid.uuid4().hex + "_%04d.ts")
    process = _start_stream_process(stream_file_path, segment_filename, test_stream)
    _wait_until_exists(stream_file_path)
    return process


def _start_stream_process(
    stream_filepath: Path, segment_filepath: Path, test_stream: bool
) -> subprocess.Popen:
    if test_stream:
        return _start_test_stream(segment_filepath, stream_filepath)
    if is_raspberry_pi():
        return _start_hls_video_stream_raspberry_pi(segment_filepath, stream_filepath)
    if is_mac():
        return _start_hls_video_stream_mac(segment_filepath, stream_filepath)
    raise RuntimeError("Unsupported platform for HLS streaming")


def _wait_until_exists(path: Path) -> None:
    while not path.exists():
        time.sleep(0.1)


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
