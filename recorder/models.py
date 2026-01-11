import uuid
from datetime import datetime, timezone
from common.auth.firebase import Role
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, DateTime, JSON


class Device(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(index=True, unique=True)
    allowed_roles: list[str] = Field(
        sa_column=Column(JSON, nullable=False),
        default_factory=lambda: [Role.USER.value],
    )

    @property
    def allowed_role_enums(self) -> list[Role]:
        return [Role(r) for r in self.allowed_roles]

    def set_allowed_roles(self, roles: list[Role]) -> None:
        self.allowed_roles = [r.value for r in roles]


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
