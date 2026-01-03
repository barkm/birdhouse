import uuid
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, DateTime


class Device(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(index=True, unique=True)


class Sensor(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    device_id: uuid.UUID = Field(foreign_key="device.id")
    temperature: float | None
    humidity: float | None
    cpu_temperature: float | None


class Recording(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    device_id: uuid.UUID = Field(foreign_key="device.id")
    url: str
