import uuid
from common.auth.firebase import Role
from sqlmodel import ARRAY, Enum, SQLModel, Field
from sqlalchemy import Column

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
            server_default="{admin}",
        )
    )
