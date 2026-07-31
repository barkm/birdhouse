"""add recording_enabled to device

Revision ID: 8f646f01712b
Revises: c7da84a8a214
Create Date: 2026-07-31 13:24:25.459588

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "8f646f01712b"
down_revision: Union[str, Sequence[str], None] = "c7da84a8a214"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "device",
        sa.Column(
            "recording_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("device", "recording_enabled")
