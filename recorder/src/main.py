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
from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic_settings import BaseSettings, SettingsConfigDict
import ffmpeg
from pydantic import BaseModel

from common.auth import firebase
from common.auth import google
from sqlalchemy import create_engine
from sqlmodel import Session, select, text

from gcs import upload_to_gcs
from recorder.src.db import queries
from timelapse import make_timelapse
import recorder.src.db.models as models

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


class Settings(BaseSettings):
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
    if request.url.path == "/healthz":
        return await call_next(request)

    headers = dict(request.headers)

    verifiers = [
        firebase.verify,
        lambda headers: google.verify(headers, settings.allowed_emails),
    ]

    responses = [get_auth_response(headers, verify) for verify in verifiers]

    roles = [response for response in responses if isinstance(response, firebase.Role)]
    sorted_roles = sorted(roles, key=firebase.role_order, reverse=True)

    if sorted_roles:
        request.state.role = sorted_roles[0]
        return await call_next(request)

    return next(
        response for response in responses if isinstance(response, JSONResponse)
    )


def get_auth_response(
    headers: dict[str, str],
    verify: Callable[[dict[str, str]], firebase.Role],
) -> JSONResponse | firebase.Role:
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


class RegisterRequest(BaseModel):
    name: str
    url: str


@app.get("/healthz", include_in_schema=False)
def healthz(session: Session = Depends(get_session)) -> dict[str, str]:
    try:
        session.exec(text("SELECT 1")).first()  # type: ignore
    except Exception:
        raise HTTPException(status_code=503, detail="unhealthy")
    return {"status": "ok"}


@app.post("/register")
def register_device(
    request: Request,
    register_request: RegisterRequest,
    session: Session = Depends(get_session),
) -> dict[str, str]:
    if request.state.role != firebase.Role.ADMIN:
        raise HTTPException(status_code=403, detail="Unauthorized")
    logging.info(
        f"Registering device {register_request.name} with url {register_request.url}"
    )
    device = queries.get_device(register_request.name, session) or queries.add_device(
        register_request.name, session
    )
    queries.register_device(device, register_request.url, session)
    return {"status": "OK"}


@app.get("/get/{name}/{path:path}")
def forward(
    request: Request, name: str, path: str, session: Session = Depends(get_session)
) -> Response:
    device = queries.get_device(name, session)
    if not device:
        raise HTTPException(status_code=404, detail="Name not registered")
    if request.state.role not in device.allowed_roles:
        raise HTTPException(status_code=403, detail="Forbidden")
    base_url = queries.get_url(name, session)
    if not base_url:
        raise HTTPException(status_code=404, detail="Device not registered")
    url = f"{base_url}/{path}"
    response = httpx.get(url, timeout=20.0, params=request.query_params)
    return Response(
        content=response.content,
        status_code=response.status_code,
        headers=dict(response.headers),
    )


def _is_active(url: str) -> bool:
    try:
        response = httpx.get(f"{url}/status", timeout=5.0)
        return response.status_code == 200
    except httpx.RequestError:
        return False


@app.get("/list_devices")
def list_devices(
    request: Request, session: Session = Depends(get_session)
) -> list[dict[str, str | bool]]:
    return [
        {
            "name": device.name,
            "active": _is_active(url)
            if (url := queries.get_url(device.name, session))
            else False,
        }
        for device in queries.get_devices(request.state.role, session)
    ]


@app.get("/record_sensors")
def record_sensors(request: Request, session: Session = Depends(get_session)) -> dict:
    devices = [
        (d, url)
        for d in queries.get_devices(request.state.role, session)
        if (url := queries.get_url(d.name, session)) and _is_active(url)
    ]
    for device, url in devices:
        try:
            response = httpx.get(f"{url}/sensor")
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
def get_sensors(
    request: Request,
    device_name: str,
    from_: Annotated[datetime | None, Query(alias="from")] = None,
    to: datetime | None = None,
    session: Session = Depends(get_session),
) -> Sequence[models.Sensor]:
    return queries.get_sensors(request.state.role, device_name, from_, to, session)


@app.get("/record")
def record(
    request: Request, duration: int = 10, session: Session = Depends(get_session)
) -> dict:
    devices = [
        (d, url)
        for d in queries.get_devices(request.state.role, session)
        if (url := queries.get_url(d.name, session)) and _is_active(url)
    ]
    for device, url in devices:
        try:
            _record_and_save(
                str(request.base_url),
                url,
                device,
                settings.recording_dir,
                duration,
                session,
            )
        except RuntimeError as e:
            logging.error(f"Failed to record for device {device.name}: {e}")
    return {}


def _record_and_save(
    base_url: str,
    device_url: str,
    device: models.Device,
    recording_dir: str,
    duration: int,
    session: Session,
) -> None:
    output_path = f"{recording_dir}/{device.name}/{datetime.now().isoformat()}.mp4"
    if recording_dir.startswith("gs://"):
        with NamedTemporaryFile(suffix=".mp4") as temp_file:
            _record(device_url, device.name, temp_file.name, duration)
            url = upload_to_gcs(temp_file.name, output_path)
    else:
        _record(device_url, device.name, output_path, duration)
        url = _get_local_recording_url(base_url, recording_dir, Path(output_path))
    logging.info(f"Saved recording for {device.name} to {url}")
    recording = models.Recording(
        device_id=device.id,
        url=url,
    )
    session.add(recording)
    session.commit()
    session.refresh(recording)


def _record(device_url: str, device: str, output_path: str, duration: int) -> None:
    logging.info(f"Saving recording for {device}")
    start_url = f"{device_url}/start"
    start_response = httpx.get(
        start_url, params={"bitrate": 10000000, "framerate": 30}, timeout=60.0
    )
    try:
        start_response.raise_for_status()
    except httpx.HTTPStatusError as e:
        logging.error(f"Failed to start recording for {device}: {e}")
        raise RuntimeError(f"Failed to start recording for {device}: {e}") from e
    playlist_path = start_response.json()["playlist"]
    playlist_url = f"{device_url}{playlist_path}"
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
    request: Request,
    device: str,
    from_: Annotated[datetime | None, Query(alias="from")] = None,
    to: datetime | None = None,
    session: Session = Depends(get_session),
) -> Sequence[models.Recording]:
    device_obj = session.exec(
        select(models.Device)
        .where(models.Device.name == device)
        .where(
            models.Device.allowed_roles.any(request.state.role)  # type: ignore
        )
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
    request: Request,
    start: datetime,
    end: datetime,
    duration: int | None = None,
    fade_duration: float | None = None,
    batch_size: int | None = None,
    session: Session = Depends(get_session),
) -> None:
    devices = queries.get_devices(request.state.role, session)
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
        recordings = queries.get_recordings(device.name, session)
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
