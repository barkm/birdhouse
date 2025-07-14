from contextlib import asynccontextmanager
from pathlib import Path
import platform
import subprocess
import tempfile

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse


PLAYLIST_FILENAME = "playlist.m3u8"


@asynccontextmanager
async def lifespan(app: FastAPI):
    with tempfile.TemporaryDirectory() as temp_dir_str:
        hls_dir = Path(temp_dir_str)
        app.state.hls_dir = hls_dir
        video = _start_hls_video_stream(hls_dir)
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


@app.get("/")
async def index():
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
      <head>
        <title>HLS Stream</title>
        <script src="https://cdn.jsdelivr.net/npm/hls.js@latest"></script>
      </head>
      <body>
        <h1>Live HLS Stream (On-Demand)</h1>
        <video id="video" width="640" height="360" controls autoplay muted></video>
        <script>
          const video = document.getElementById('video');
          const src = "/hls/playlist.m3u8";

          if (video.canPlayType('application/vnd.apple.mpegurl')) {
            video.src = src;
          } else if (Hls.isSupported()) {
            const hls = new Hls();
            hls.loadSource(src);
            hls.attachMedia(video);
            hls.on(Hls.Events.MANIFEST_PARSED, () => video.play());
          } else {
            alert("HLS is not supported in this browser.");
          }
        </script>
      </body>
    </html>
    """)


def _start_hls_video_stream(stream_dir: Path) -> subprocess.Popen:
    stream_dir.mkdir(parents=True, exist_ok=True)
    stream_file_path = stream_dir / PLAYLIST_FILENAME
    if is_mac():
        return _start_hls_video_stream_mac(stream_file_path)
    elif is_raspberry_pi():
        return _start_hls_video_stream_raspberry_pi(stream_file_path)
    raise RuntimeError("Unsupported platform for video input")


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
        ]
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
