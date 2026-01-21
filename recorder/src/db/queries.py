from datetime import datetime
from sqlmodel import Session, select

from common.auth import firebase

import src.db.models as models


def session_is_alive(session: Session) -> bool:
    try:
        session.exec(select(1)).first()
        return True
    except Exception:
        return False


def get_device(
    session: Session, name: str, role: firebase.Role | None = None
) -> models.Device | None:
    statement = select(models.Device).where(models.Device.name == name)
    if role:
        statement = statement.where(models.Device.allowed_roles.any(role))  # type: ignore
    return session.exec(statement).first()


def get_devices(session: Session, role: firebase.Role) -> list[models.Device]:
    statement = select(models.Device).where(models.Device.allowed_roles.any(role))  # type: ignore
    return list(session.exec(statement).all())


def add_device(session: Session, name: str) -> models.Device:
    device = models.Device(name=name, allowed_roles=[firebase.Role.ADMIN])
    session.add(device)
    session.commit()
    session.refresh(device)
    return device


def set_device_roles(
    session: Session, device: models.Device, roles: list[firebase.Role]
):
    device.allowed_roles = roles
    session.add(device)
    session.commit()
    session.refresh(device)


def register_device(session: Session, device: models.Device, url: str):
    register = models.Registration(device_id=device.id, url=url)
    session.add(register)
    session.commit()
    session.refresh(register)


def get_url(session: Session, name: str) -> str | None:
    statement = (
        select(models.Registration)
        .join(models.Device)
        .where(models.Device.name == name)
        .order_by(models.Registration.created_at.desc())  # type: ignore
    )
    register = session.exec(statement).first()
    return register.url if register else None


def get_recordings(
    session: Session,
    device_name: str,
    start: datetime | None = None,
    end: datetime | None = None,
) -> list[models.Recording]:
    statement = (
        select(models.Recording)
        .join(models.Device)
        .where(models.Device.name == device_name)
    )
    if start:
        statement = statement.where(models.Recording.created_at >= start)
    if end:
        statement = statement.where(models.Recording.created_at <= end)
    return list(session.exec(statement).all())


def get_sensors(
    session: Session,
    role: firebase.Role,
    device_name: str,
    start: datetime | None = None,
    end: datetime | None = None,
) -> list[models.Sensor]:
    statement = (
        select(models.Sensor)
        .join(models.Device)
        .order_by(models.Sensor.created_at.desc())  # type: ignore
        .where(models.Device.name == device_name)
        .where(models.Sensor.temperature is None or models.Sensor.temperature > -30)
        .where(models.Device.allowed_roles.any(role))  # type: ignore
    )
    if start:
        statement = statement.where(models.Sensor.created_at >= start)
    if end:
        statement = statement.where(models.Sensor.created_at <= end)
    return list(session.exec(statement).all())


def add_sensor(
    session: Session,
    device: models.Device,
    temperature: float | None,
    humidity: float | None,
    cpu_temperature: float | None,
) -> models.Sensor:
    sensor = models.Sensor(
        device_id=device.id,
        temperature=temperature,
        humidity=humidity,
        cpu_temperature=cpu_temperature,
    )
    session.add(sensor)
    session.commit()
    session.refresh(sensor)
    return sensor


def get_user(session: Session, uid: str) -> models.User | None:
    statement = select(models.User).where(models.User.uid == uid)
    return session.exec(statement).first()
