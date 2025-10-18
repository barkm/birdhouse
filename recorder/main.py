from contextlib import asynccontextmanager
from pathlib import Path
from datetime import datetime
from subprocess import CalledProcessError, run
from tempfile import NamedTemporaryFile
import logging
from typing import Callable

from common.auth.exception import AuthException
from fastapi.responses import FileResponse, JSONResponse
import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import BaseModel
from google.cloud import storage
from moviepy import VideoFileClip, concatenate_videoclips
from moviepy.video.fx import CrossFadeIn

from common.auth import firebase
from common.auth import google

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

DOWNLOAD_DIR = "./.downloads"


class Settings(BaseSettings):
    relay_url: str | None = None
    recording_dir: str = "/recordings"
    allowed_emails: list[str] | None = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@asynccontextmanager
async def lifespan(_: FastAPI):
    firebase.initialize()
    yield


settings = Settings()
app = FastAPI(lifespan=lifespan)


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    headers = dict(request.headers)

    verifiers = [
        firebase.verify,
        lambda headers: google.verify(headers, settings.allowed_emails),
    ]

    responses = [get_auth_response(headers, verify) for verify in verifiers]

    if any(response is None for response in responses):
        return await call_next(request)

    return next(response for response in responses if response is not None)


def get_auth_response(
    headers: dict[str, str],
    verify: Callable[[dict[str, str]], JSONResponse | None],
) -> JSONResponse | None:
    try:
        return verify(headers)
    except AuthException as e:
        return JSONResponse({"detail": e.detail}, status_code=e.status_code)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/record")
async def record(duration: int = 10) -> dict:
    if settings.relay_url is None:
        logging.error("Relay url not set")
        return {"error": "Relay url not set"}
    devices = _get_devices(settings.relay_url)
    for device in devices:
        _record_and_save(settings.relay_url, device, settings.recording_dir, duration)
    return {}


def _get_devices(relay_url: str) -> list[str]:
    list_url = f"{relay_url}/list"
    try:
        response = httpx.get(list_url)
        response.raise_for_status()
        return [device["name"] for device in response.json()]
    except httpx.HTTPError as e:
        logging.warning(f"Failed to get devices from {list_url}: {e}")
        return []


def _record_and_save(
    relay_url: str, device: str, recording_dir: str, duration: int
) -> None:
    output_path = f"{recording_dir}/{device}/{datetime.now().isoformat()}.mp4"
    if recording_dir.startswith("gs://"):
        with NamedTemporaryFile(suffix=".mp4") as temp_file:
            _record(relay_url, device, temp_file.name, duration)
            _upload_to_gcs(temp_file.name, output_path)
    else:
        _record(relay_url, device, output_path, duration)


def _record(relay_url: str, device: str, output_path: str, duration: int) -> None:
    logging.info(f"Saving recording for {device}")
    start_url = f"{relay_url}/{device}/start"
    start_response = httpx.get(
        start_url, params={"bitrate": 10000000, "framerate": 30}, timeout=20.0
    )
    start_response.raise_for_status()
    playlist_path = start_response.json()["playlist"]
    playlist_url = f"{relay_url}/{device}{playlist_path}"
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    # fmt: off
    command = [
        "ffmpeg", "-y",
        "-i", playlist_url,
        "-t", str(duration),
        "-c:v", "libx264",
        "-c:a", "aac",
        "-movflags", "+faststart",
        "-profile:v", "main",
        "-pix_fmt", "yuv420p",
        output_path
    ]
    # fmt: on
    try:
        run(command, check=True, capture_output=True, text=True)
        logging.info(f"Finished recording video for {device} to {output_path}")
    except CalledProcessError as e:
        logging.error(
            f"Failed to record video for {device}: {e}\n"
            f"stderr: {e.stderr}\n"
            f"stdout: {e.stdout}"
        )


def _upload_to_gcs(source: str, gcs_path: str) -> None:
    bucket_name, dest = _get_bucket_and_blob_name(gcs_path)
    logging.info(f"Uploading {source} to {dest} in {bucket_name}.")
    client = storage.Client(project="birdhouse-464804")
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(dest)
    blob.upload_from_filename(source)
    logging.info(f"File {source} uploaded to {dest} in {bucket_name}.")


class Recording(BaseModel):
    time: str
    url: str


@app.get("/recording/{path:path}")
def get_recording(path: str) -> FileResponse:
    return FileResponse(f"{settings.recording_dir}/{path}")


@app.get("/recordings/{device}")
def list_recordings(request: Request, device: str) -> list[Recording]:
    if settings.recording_dir.startswith("gs://"):
        return _list_gcs_recordings(f"{settings.recording_dir}/{device}")
    return _list_local_recordings(str(request.base_url), settings.recording_dir, device)


@app.get("/timelapse/{device}")
def create_timelapse(device: str, start: datetime, end: datetime) -> None:
    with NamedTemporaryFile(suffix=".mp4") as temp_file:
        _make_timelapse(start, end, device, Path(temp_file.name))
        _upload_to_gcs(
            temp_file.name,
            f"{settings.recording_dir}/timelapses/{device}/{start.isoformat()}_{end.isoformat()}.mp4",
        )


def _list_local_recordings(
    url: str, recording_dir: str, device: str
) -> list[Recording]:
    return [
        Recording(
            time=path.stem, url=f"{url}recording/{path.relative_to(recording_dir)}"
        )
        for path in Path(recording_dir, device).iterdir()
    ]


def _list_gcs_recordings(gcs_dirpath: str) -> list[Recording]:
    bucket_name, prefix = _get_bucket_and_blob_name(gcs_dirpath)
    client = storage.Client(project="birdhouse-464804")
    bucket = client.bucket(bucket_name)
    blobs = bucket.list_blobs(prefix=prefix)
    return [
        Recording(
            time=Path(blob.name).stem,
            url=f"https://storage.googleapis.com/{bucket_name}/{blob.name}",
        )
        for blob in blobs
    ]


def _get_bucket_and_blob_name(gcs_path: str) -> tuple[str, str]:
    *_, bucket_name, blob_name = gcs_path.split("/", maxsplit=3)
    return bucket_name, blob_name


def _make_timelapse(start: datetime, end: datetime, device: str, dest: Path) -> None:
    recordings = _list_gcs_recordings(f"{settings.recording_dir}/{device}")
    recordings_in_range = [
        r for r in recordings if start <= datetime.fromisoformat(r.time) <= end
    ]
    downloaded_files = [_download_recording(r.url) for r in recordings_in_range]
    clips = [VideoFileClip(str(f)).with_speed_scaled(2) for f in downloaded_files]
    clips_cf = [clips[0]] + [c.with_effects([CrossFadeIn(1)]) for c in clips[1:]]
    timelapse = concatenate_videoclips(clips_cf, method="compose", padding=-1)
    timelapse.write_videofile(dest)


def _download_recording(url: str) -> Path:
    name = url.split("/")[-1]
    dest = Path(DOWNLOAD_DIR) / name
    if dest.exists():
        return dest
    response = httpx.get(url)
    response.raise_for_status()
    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "wb") as f:
        f.write(response.content)
    return dest
