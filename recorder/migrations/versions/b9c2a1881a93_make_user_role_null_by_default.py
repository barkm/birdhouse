"""make user role null by default

Revision ID: b9c2a1881a93
Revises: a373bdd516ef
Create Date: 2026-02-01 12:05:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "b9c2a1881a93"
down_revision: Union[str, Sequence[str], None] = "a373bdd516ef"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        "user",
        "role",
        existing_type=postgresql.ENUM("user", "admin", name="role_enum"),
        nullable=True,
        server_default=None,
        existing_server_default=sa.text("'user'::role_enum"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        "user",
        "role",
        existing_type=postgresql.ENUM("user", "admin", name="role_enum"),
        nullable=True,
        server_default=sa.text("'user'::role_enum"),
    )
