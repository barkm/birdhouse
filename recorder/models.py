import uuid
from datetime import datetime, timezone
from common.auth.firebase import Role
from sqlmodel import ARRAY, Enum, SQLModel, Field
from sqlalchemy import Column, DateTime

role_enum = Enum(
    Role,
    name="role_enum",
    create_constraint=True,
    values_callable=lambda enum_cls: [e.value for e in enum_cls],
)


class Device(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(index=True, unique=True)
    allowed_roles: list[Role] = Field(
        sa_column=Column(
            ARRAY(role_enum),
            nullable=False,
            server_default="{user}",
        )
    )


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
