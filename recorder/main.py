from contextlib import asynccontextmanager
from datetime import datetime
import logging
from typing import Annotated, Sequence

from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordBearer
import httpx
from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import BaseModel

from sqlalchemy import create_engine
from sqlmodel import Session

from src.auth.decode import Decoder
from src.auth import firebase
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
    database_url: str = "postgresql+psycopg://moja:moja@localhost/moja"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@asynccontextmanager
async def lifespan(_: FastAPI):
    firebase.initialize()
    yield


settings = Settings()
app = FastAPI(lifespan=lifespan)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


engine = create_engine(settings.database_url)


def get_session():
    with Session(engine) as session:
        yield session


def get_role(
    token: str = Depends(oauth2_scheme), session: Session = Depends(get_session)
) -> models.Role:
    decoded_token = Decoder().decode(token)
    user = queries.get_user(session, decoded_token.uid) or models.User(
        uid=decoded_token.uid, email=decoded_token.email, role=None
    )
    queries.add_user(session, user)
    if not user or not user.role:
        raise HTTPException(status_code=403, detail="User not authorized")
    return user.role


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


@app.get("/me")
def me(role: models.Role = Depends(get_role)) -> dict[str, str]:
    return {"role": role.value}


@app.post("/register")
def register_device(
    register_request: RegisterRequest,
    session: Session = Depends(get_session),
    role: models.Role = Depends(get_role),
) -> dict[str, str]:
    if role != models.Role.ADMIN:
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
    request: Request,
    name: str,
    path: str,
    session: Session = Depends(get_session),
    role: models.Role = Depends(get_role),
) -> Response:
    device = queries.get_device(session, name)
    if not device:
        raise HTTPException(status_code=404, detail="Name not registered")
    if role not in device.allowed_roles:
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
    session: Session = Depends(get_session),
    role: models.Role = Depends(get_role),
) -> list[dict[str, str | bool | list[str]]]:
    return [
        {
            "name": device.name,
            "allowed_roles": [role.value for role in device.allowed_roles],
            "active": _is_active(url)
            if (url := queries.get_url(session, device.name))
            else False,
        }
        for device in queries.get_devices(session, role)
    ]


@app.post("/set_roles/{device_name}")
def set_device_roles(
    device_name: str,
    roles: list[models.Role],
    session: Session = Depends(get_session),
    role: models.Role = Depends(get_role),
) -> dict[str, str]:
    if role != models.Role.ADMIN:
        raise HTTPException(status_code=403, detail="Unauthorized")
    device = queries.get_device(session, device_name)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    queries.set_device_roles(session, device, roles)
    return {"status": "OK"}


@app.get("/record_sensors")
def record_sensors(
    session: Session = Depends(get_session),
    role: models.Role = Depends(get_role),
) -> dict:
    devices = [
        (d, url)
        for d in queries.get_devices(session, role)
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
    device_name: str,
    from_: Annotated[datetime | None, Query(alias="from")] = None,
    to: datetime | None = None,
    session: Session = Depends(get_session),
    role: models.Role = Depends(get_role),
) -> Sequence[models.Sensor]:
    return queries.get_sensors(session, role, device_name, from_, to)


@app.get("/record")
def record(
    request: Request,
    duration: int = 10,
    session: Session = Depends(get_session),
    role: models.Role = Depends(get_role),
) -> dict:
    devices = [
        (d, url)
        for d in queries.get_devices(session, role)
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
def get_recording(path: str, _: models.Role = Depends(get_role)) -> FileResponse:
    return FileResponse(f"{settings.recording_dir}/{path}")


@app.get("/recordings/{device}")
def list_recordings(
    device: str,
    from_: Annotated[datetime | None, Query(alias="from")] = None,
    to: datetime | None = None,
    session: Session = Depends(get_session),
    role: models.Role = Depends(get_role),
) -> Sequence[models.Recording]:
    device_obj = queries.get_device(session, device, role)
    if not device_obj:
        logging.error(f"Device {device} not found in database")
        return []
    return queries.get_recordings(session, device_obj.name, from_, to)


@app.get("/timelapse")
def create_timelapse(
    start: datetime,
    end: datetime,
    duration: int | None = None,
    fade_duration: float | None = None,
    batch_size: int | None = None,
    session: Session = Depends(get_session),
    role: models.Role = Depends(get_role),
) -> None:
    devices = queries.get_devices(session, role)
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
