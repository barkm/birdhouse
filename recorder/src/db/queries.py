from datetime import datetime
from sqlmodel import Session, select

from common.auth import firebase

import models


def session_is_alive(session: Session) -> bool:
    try:
        session.exec(select(1)).first()
        return True
    except Exception:
        return False


def get_device(
    name: str, session: Session, role: firebase.Role | None = None
) -> models.Device | None:
    statement = select(models.Device).where(models.Device.name == name)
    if role:
        statement = statement.where(models.Device.allowed_roles.any(role))  # type: ignore
    return session.exec(statement).first()


def get_devices(role: firebase.Role, session: Session) -> list[models.Device]:
    statement = select(models.Device).where(models.Device.allowed_roles.any(role))  # type: ignore
    return list(session.exec(statement).all())


def add_device(name: str, session: Session) -> models.Device:
    device = models.Device(name=name, allowed_roles=[firebase.Role.ADMIN])
    session.add(device)
    session.commit()
    session.refresh(device)
    return device


def register_device(device: models.Device, url: str, session: Session):
    register = models.Registration(device_id=device.id, url=url)
    session.add(register)
    session.commit()
    session.refresh(register)


def get_url(name: str, session: Session) -> str | None:
    statement = (
        select(models.Registration)
        .join(models.Device)
        .where(models.Device.name == name)
        .order_by(models.Registration.created_at.desc())  # type: ignore
    )
    register = session.exec(statement).first()
    return register.url if register else None


def get_recordings(
    device_name: str, start: datetime | None, end: datetime | None, session: Session
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
    role: firebase.Role,
    device_name: str,
    start: datetime | None,
    end: datetime | None,
    session: Session,
) -> list[models.Sensor]:
    statement = (
        select(models.Sensor)
        .join(models.Device)
        .where(models.Device.name == device_name)
        .where(models.Sensor.temperature is None or models.Sensor.temperature > -30)
        .where(models.Device.allowed_roles.any(role))  # type: ignore
    )
    if start:
        statement = statement.where(models.Sensor.created_at >= start)
    if end:
        statement = statement.where(models.Sensor.created_at <= end)
    return list(session.exec(statement).all())
