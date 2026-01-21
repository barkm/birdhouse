import enum
import uuid
from datetime import datetime, timezone
from sqlmodel import ARRAY, Enum, SQLModel, Field
from sqlalchemy import Column, DateTime


class Role(enum.StrEnum):
    USER = "user"
    ADMIN = "admin"


role_enum = Enum(
    Role,
    name="role_enum",
    create_constraint=True,
    values_callable=lambda enum_cls: [e.value for e in enum_cls],
)


class User(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    uid: str = Field(index=True, unique=True)
    email: str | None = Field(default=None, index=True, unique=True)
    role: Role | None = Field(
        default=None,
        sa_column=Column(role_enum, nullable=True),
    )


class Device(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(index=True, unique=True)
    allowed_roles: list[Role] = Field(
        sa_column=Column(
            ARRAY(role_enum),
            nullable=False,
            server_default="{admin}",
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


class Registration(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    device_id: uuid.UUID = Field(foreign_key="device.id", index=True)
    url: str
