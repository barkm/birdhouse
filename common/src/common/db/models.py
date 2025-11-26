import uuid
from sqlmodel import SQLModel, Field
from datetime import datetime, timezone


class Device(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str


class Register(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), nullable=False
    )
    device_id: uuid.UUID = Field(foreign_key="device.id")
    url: str
