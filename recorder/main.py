from contextlib import asynccontextmanager
from datetime import datetime
import logging
from typing import Annotated, Callable, Sequence

from common.auth.exception import AuthException
from fastapi.responses import FileResponse, JSONResponse
import httpx
from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import BaseModel

from common.auth import firebase
from common.auth import google
from sqlalchemy import create_engine
from sqlmodel import Session

from src.record import record_and_save
from src.timelapse.create_save import create_and_save_timelapse
import src.db.models as models
import src.db.queries as queries

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
    if not queries.session_is_alive(session):
        raise HTTPException(status_code=503, detail="Database connection not alive")
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
    device = queries.get_device(session, register_request.name) or queries.add_device(
        session, register_request.name
    )
    queries.register_device(session, device, register_request.url)
    return {"status": "OK"}


@app.get("/get/{name}/{path:path}")
def forward(
    request: Request, name: str, path: str, session: Session = Depends(get_session)
) -> Response:
    device = queries.get_device(session, name)
    if not device:
        raise HTTPException(status_code=404, detail="Name not registered")
    if request.state.role not in device.allowed_roles:
        raise HTTPException(status_code=403, detail="Forbidden")
    base_url = queries.get_url(session, name)
    if not base_url:
        raise HTTPException(status_code=404, detail="Device not registered")
    url = f"{base_url}/{path}"
    response = httpx.get(url, timeout=20.0, params=request.query_params)
    return Response(
        content=response.content,
        status_code=response.status_code,
        headers=dict(response.headers),
    )


@app.get("/list_devices")
def list_devices(
    request: Request, session: Session = Depends(get_session)
) -> list[dict[str, str | bool | list[str]]]:
    return [
        {
            "name": device.name,
            "allowed_roles": [role.value for role in device.allowed_roles],
            "active": _is_active(url)
            if (url := queries.get_url(session, device.name))
            else False,
        }
        for device in queries.get_devices(session, request.state.role)
    ]


@app.post("/set_roles/{device_name}")
def set_device_roles(
    request: Request,
    device_name: str,
    roles: list[firebase.Role],
    session: Session = Depends(get_session),
) -> dict[str, str]:
    if request.state.role != firebase.Role.ADMIN:
        raise HTTPException(status_code=403, detail="Unauthorized")
    device = queries.get_device(session, device_name)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    queries.set_device_roles(session, device, roles)
    return {"status": "OK"}


@app.get("/record_sensors")
def record_sensors(request: Request, session: Session = Depends(get_session)) -> dict:
    devices = [
        (d, url)
        for d in queries.get_devices(session, request.state.role)
        if (url := queries.get_url(session, d.name)) and _is_active(url)
    ]
    for device, url in devices:
        try:
            response = httpx.get(f"{url}/sensor")
            response.raise_for_status()
        except (httpx.HTTPError, httpx.HTTPStatusError) as e:
            logging.error(f"Failed to get sensor data for {device.name}: {e}")
            continue
        sensor_data = response.json()
        queries.add_sensor(
            session,
            device,
            sensor_data["temperature"],
            sensor_data["humidity"],
            sensor_data["cpu_temperature"],
        )
    return {}


@app.get("/sensors/{device_name}")
def get_sensors(
    request: Request,
    device_name: str,
    from_: Annotated[datetime | None, Query(alias="from")] = None,
    to: datetime | None = None,
    session: Session = Depends(get_session),
) -> Sequence[models.Sensor]:
    return queries.get_sensors(session, request.state.role, device_name, from_, to)


@app.get("/record")
def record(
    request: Request, duration: int = 10, session: Session = Depends(get_session)
) -> dict:
    devices = [
        (d, url)
        for d in queries.get_devices(session, request.state.role)
        if (url := queries.get_url(session, d.name)) and _is_active(url)
    ]
    for device, url in devices:
        try:
            record_and_save(
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
    device_obj = queries.get_device(session, device, request.state.role)
    if not device_obj:
        logging.error(f"Device {device} not found in database")
        return []
    return queries.get_recordings(session, device_obj.name, from_, to)


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
    devices = queries.get_devices(session, request.state.role)
    for device in devices:
        logging.info(f"Creating timelapse for device {device}")
        create_and_save_timelapse(
            start,
            end,
            device,
            duration,
            fade_duration,
            batch_size,
            settings.recording_dir,
            session,
        )


def _is_active(url: str) -> bool:
    try:
        response = httpx.get(f"{url}/status", timeout=5.0)
        return response.status_code == 200
    except httpx.RequestError:
        return False
