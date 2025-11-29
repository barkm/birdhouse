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
from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic_settings import BaseSettings, SettingsConfigDict

from common.auth import firebase
from common.auth import google
from common.db import models
from sqlalchemy import create_engine
from sqlmodel import Session, select

from gcs import Recording, list_gcs_recordings, upload_to_gcs
from timelapse import create_and_upload_timelapse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


class Settings(BaseSettings):
    relay_url: str | None = None
    recording_dir: str = "/recordings"
    allowed_emails: list[str] | None = None
    database_url: str = "postgresql+psycopg://moja:moja@localhost/moja"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@asynccontextmanager
async def lifespan(_: FastAPI):
    firebase.initialize()
    yield


settings = Settings()
app = FastAPI(lifespan=lifespan)

engine = create_engine(settings.database_url)


def get_session():
    with Session(engine) as session:
        yield session


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


@app.get("/record_sensors")
async def record_sensors(session: Session = Depends(get_session)) -> dict:
    if settings.relay_url is None:
        logging.error("Relay url not set")
        return {"error": "Relay url not set"}
    devices = _get_devices(settings.relay_url)
    for device_name in devices:
        try:
            sensor_data = httpx.get(f"{settings.relay_url}/{device_name}/sensor").json()
        except httpx.HTTPError as e:
            logging.error(f"Failed to get sensor data for {device_name}: {e}")
            continue

        statement = select(models.Device).where(models.Device.name == device_name)
        device = session.exec(statement).first()
        if not device:
            logging.error(f"Device {device_name} not found in database")
            continue
        sensor = models.Sensor(
            device_id=device.id,
            temperature=sensor_data["temperature"],
            humidity=sensor_data["humidity"],
            cpu_temperature=sensor_data["cpu_temperature"],
        )
        session.add(sensor)
        session.commit()
        session.refresh(sensor)
    return {}


@app.get("/record")
async def record(duration: int = 10) -> dict:
    if settings.relay_url is None:
        logging.error("Relay url not set")
        return {"error": "Relay url not set"}
    devices = _get_devices(settings.relay_url)
    for device in devices:
        if "birdhouse" in device:
            _record_and_save(
                settings.relay_url, device, settings.recording_dir, duration
            )
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
            upload_to_gcs(temp_file.name, output_path)
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


@app.get("/recording/{path:path}")
def get_recording(path: str) -> FileResponse:
    return FileResponse(f"{settings.recording_dir}/{path}")


@app.get("/recordings/{device}")
def list_recordings(request: Request, device: str) -> list[Recording]:
    if settings.recording_dir.startswith("gs://"):
        return list_gcs_recordings(f"{settings.recording_dir}/{device}")
    return _list_local_recordings(str(request.base_url), settings.recording_dir, device)


@app.get("/timelapse")
def create_timelapse(start: datetime, end: datetime, duration: int) -> None:
    devices = _get_devices(settings.relay_url or "")
    for device in devices:
        create_and_upload_timelapse(
            start, end, device, duration, Path(settings.recording_dir)
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
