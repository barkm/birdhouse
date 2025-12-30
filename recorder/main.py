from contextlib import asynccontextmanager
import os
from pathlib import Path
from datetime import datetime
import shutil
from subprocess import CalledProcessError
from tempfile import NamedTemporaryFile
import logging
from typing import Annotated, Callable, Sequence

from common.auth.exception import AuthException
from fastapi.responses import FileResponse, JSONResponse
import httpx
from fastapi import Depends, FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic_settings import BaseSettings, SettingsConfigDict
import ffmpeg

from common.auth import firebase
from common.auth import google
from sqlalchemy import create_engine
from sqlmodel import Session, select

from gcs import upload_to_gcs
from timelapse import make_timelapse
import models

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
    devices = _get_active_devices(settings.relay_url, session)
    for device in devices:
        try:
            response = httpx.get(f"{settings.relay_url}/{device.name}/sensor")
        except httpx.HTTPError as e:
            logging.error(f"Failed to get sensor data for {device.name}: {e}")
            continue

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            logging.error(f"Failed to get sensor data for {device.name}: {e}")
            continue

        sensor_data = response.json()

        if not device:
            logging.error(f"Device {device} not found in database")
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


@app.get("/sensors/{device_name}")
async def get_sensors(
    device_name: str, session: Session = Depends(get_session)
) -> Sequence[models.Sensor]:
    statement = (
        select(models.Sensor)
        .join(models.Device)
        .where(models.Device.name == device_name)
    )
    sensors = session.exec(statement).all()
    return sensors


@app.get("/record")
async def record(
    request: Request, duration: int = 10, session: Session = Depends(get_session)
) -> dict:
    if settings.relay_url is None:
        logging.error("Relay url not set")
        return {"error": "Relay url not set"}
    devices = _get_active_devices(settings.relay_url, session)
    for device in devices:
        try:
            _record_and_save(
                str(request.base_url),
                settings.relay_url,
                device,
                settings.recording_dir,
                duration,
                session,
            )
        except RuntimeError as e:
            logging.error(f"Failed to record for device {device.name}: {e}")
    return {}


def _get_active_devices(relay_url: str, session: Session) -> list[models.Device]:
    list_url = f"{relay_url}/list"
    try:
        response = httpx.get(list_url)
        response.raise_for_status()
        device_names = [device["name"] for device in response.json()]
    except httpx.HTTPError as e:
        logging.warning(f"Failed to get devices from {list_url}: {e}")
        return []

    devices = []
    for device_name in device_names:
        statement = select(models.Device).where(models.Device.name == device_name)
        device = session.exec(statement).first()
        if not device:
            device = models.Device(name=device_name)
            session.add(device)
            session.commit()
            session.refresh(device)
        devices.append(device)
    return devices


def _get_devices(session: Session) -> list[models.Device]:
    statement = select(models.Device)
    return list(session.exec(statement).all())


def _record_and_save(
    base_url: str,
    relay_url: str,
    device: models.Device,
    recording_dir: str,
    duration: int,
    session: Session,
) -> None:
    output_path = f"{recording_dir}/{device.name}/{datetime.now().isoformat()}.mp4"
    if recording_dir.startswith("gs://"):
        with NamedTemporaryFile(suffix=".mp4") as temp_file:
            _record(relay_url, device.name, temp_file.name, duration)
            url = upload_to_gcs(temp_file.name, output_path)
    else:
        _record(relay_url, device.name, output_path, duration)
        url = _get_local_recording_url(base_url, recording_dir, Path(output_path))
    logging.info(f"Saved recording for {device.name} to {url}")
    recording = models.Recording(
        device_id=device.id,
        url=url,
    )
    session.add(recording)
    session.commit()
    session.refresh(recording)


def _record(relay_url: str, device: str, output_path: str, duration: int) -> None:
    logging.info(f"Saving recording for {device}")
    start_url = f"{relay_url}/{device}/start"
    start_response = httpx.get(
        start_url, params={"bitrate": 10000000, "framerate": 30}, timeout=20.0
    )
    try:
        start_response.raise_for_status()
    except httpx.HTTPStatusError as e:
        logging.error(f"Failed to start recording for {device}: {e}")
        raise RuntimeError(f"Failed to start recording for {device}: {e}") from e
    playlist_path = start_response.json()["playlist"]
    playlist_url = f"{relay_url}/{device}{playlist_path}"
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    input_ = ffmpeg.input(playlist_url, t=duration)
    output = ffmpeg.output(
        input_,
        output_path,
        vcodec="libx264",
        acodec="aac",
        movflags="+faststart",
        profile="main",
        pix_fmt="yuv420p",
    )
    try:
        ffmpeg.run(output, overwrite_output=True, quiet=True)
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
def list_recordings(
    device: str,
    from_: Annotated[datetime | None, Query(alias="from")],
    to: datetime | None,
    session: Session = Depends(get_session),
) -> Sequence[models.Recording]:
    device_obj = session.exec(
        select(models.Device).where(models.Device.name == device)
    ).first()
    if not device_obj:
        logging.error(f"Device {device} not found in database")
        return []
    statement = select(models.Recording).where(
        models.Recording.device_id == device_obj.id
    )
    if from_:
        statement = statement.where(models.Recording.created_at >= from_)
    if to:
        statement = statement.where(models.Recording.created_at <= to)
    return session.exec(statement).all()


@app.get("/timelapse")
def create_timelapse(
    start: datetime,
    end: datetime,
    duration: int | None = None,
    fade_duration: float | None = None,
    batch_size: int | None = None,
    session: Session = Depends(get_session),
) -> None:
    devices = _get_devices(session)
    for device in devices:
        logging.info(f"Creating timelapse for device {device}")
        _create_and_upload_timelapse(
            start,
            end,
            device,
            duration,
            fade_duration,
            batch_size,
            settings.recording_dir,
            session,
        )


def _get_local_recording_url(url: str, recording_dir: str, path: Path) -> str:
    return f"{url}recording/{path.relative_to(recording_dir)}"


def _create_and_upload_timelapse(
    start: datetime,
    end: datetime,
    device: models.Device,
    duration: int | None,
    fade_duration: float | None,
    batch_size: int | None,
    recording_dir: str,
    session: Session,
) -> None:
    with NamedTemporaryFile(suffix=".mp4") as temp_file:
        recordings = session.exec(
            select(models.Recording)
            .join(models.Device)
            .where(models.Device.name == device)
        ).all()
        if not recordings:
            logging.info(f"No recordings found for device {device}, skipping timelapse")
            return
        else:
            logging.info(f"Found {len(recordings)} recordings for device {device}")
        recordings_in_range = [r for r in recordings if start <= r.created_at <= end]
        logging.info(
            f"Found {len(recordings_in_range)} recordings for device {device} in range {start} - {end}"
        )
        urls = [r.url for r in recordings_in_range]
        times = [r.created_at for r in recordings_in_range]
        make_timelapse(
            urls,
            times,
            Path(temp_file.name),
            total_time=duration,
            fade_duration=fade_duration,
            batch_size=batch_size,
        )
        save_path = os.path.join(
            recording_dir,
            "timelapses",
            device.name,
            f"{start.isoformat()}_{end.isoformat()}.mp4",
        )
        if recording_dir.startswith("gs://"):
            upload_to_gcs(temp_file.name, str(save_path))
        else:
            shutil.move(temp_file.name, save_path)
