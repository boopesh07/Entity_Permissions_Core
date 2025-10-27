"""Add processed_events table to track ingested event ids."""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.models.types import GUID

# revision identifiers, used by Alembic.
revision: str = "0007_add_processed_events_table"
down_revision: Union[str, None] = "0006_audit_hash_chain"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "processed_events",
        sa.Column("id", GUID(), primary_key=True, nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("event_id", sa.String(length=255), nullable=False, unique=True),
        sa.Column("source", sa.String(length=128), nullable=False),
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.Column("entity_id", sa.String(length=255), nullable=True),
        sa.Column("entity_type", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("processed_events")
