"""make registration unique per device

Revision ID: 5f72aae70125
Revises: 8f646f01712b
Create Date: 2026-08-29 14:01:37.338371

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "5f72aae70125"
down_revision: Union[str, Sequence[str], None] = "8f646f01712b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        """
        DELETE FROM registration
        WHERE id NOT IN (
            SELECT DISTINCT ON (device_id) id
            FROM registration
            ORDER BY device_id, created_at DESC
        )
        """
    )
    op.drop_index(op.f("ix_registration_device_id"), table_name="registration")
    op.create_index(
        op.f("ix_registration_device_id"), "registration", ["device_id"], unique=True
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_registration_device_id"), table_name="registration")
    op.create_index(
        op.f("ix_registration_device_id"), "registration", ["device_id"], unique=False
    )
