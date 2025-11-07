"""Add delivery state metadata to platform events."""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0009_platform_event_delivery_fields"
down_revision: Union[str, None] = "0008_enforce_audit_hash_length"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DELIVERY_STATE_ENUM = sa.Enum(
    "pending",
    "succeeded",
    "failed",
    name="platform_event_delivery_state",
    native_enum=False,
)


def upgrade() -> None:
    op.add_column(
        "platform_events",
        sa.Column(
            "delivery_state",
            DELIVERY_STATE_ENUM,
            nullable=False,
            server_default="pending",
        ),
    )
    op.add_column(
        "platform_events",
        sa.Column("delivery_attempts", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "platform_events",
        sa.Column("last_error", sa.String(length=1024), nullable=True),
    )

    op.alter_column("platform_events", "delivery_state", server_default=None)
    op.alter_column("platform_events", "delivery_attempts", server_default=None)


def downgrade() -> None:
    op.drop_column("platform_events", "last_error")
    op.drop_column("platform_events", "delivery_attempts")
    op.drop_column("platform_events", "delivery_state")
