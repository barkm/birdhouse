from sqlmodel import Session, select

from common.auth import firebase

import models


def get_device(name: str, session: Session) -> models.Device | None:
    statement = select(models.Device).where(models.Device.name == name)
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
