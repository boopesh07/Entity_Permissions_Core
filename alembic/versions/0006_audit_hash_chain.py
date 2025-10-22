"""Add hash chain columns to audit log."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import select

# revision identifiers, used by Alembic.
revision = "0006_audit_hash_chain"
down_revision = "0005_remove_audit_status"
branch_labels = None
depends_on = None

GENESIS_HASH = "0" * 64
HASH_VERSION = 1


def upgrade() -> None:
    op.add_column("audit_logs", sa.Column("sequence", sa.BigInteger(), nullable=True))
    op.add_column("audit_logs", sa.Column("previous_hash", sa.String(length=128), nullable=True))
    op.add_column("audit_logs", sa.Column("entry_hash", sa.String(length=128), nullable=True))
    op.add_column("audit_logs", sa.Column("hash_version", sa.Integer(), nullable=True, server_default="1"))
    op.add_column("audit_logs", sa.Column("event_id", sa.String(length=128), nullable=True))
    op.add_column("audit_logs", sa.Column("source", sa.String(length=128), nullable=True))
    op.add_column(
        "audit_logs",
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=True),
    )

    _backfill_audit_chain()

    op.create_unique_constraint("uq_audit_logs_event_id", "audit_logs", ["event_id"])
    op.create_index("ix_audit_logs_sequence", "audit_logs", ["sequence"], unique=True)

    op.alter_column("audit_logs", "sequence", nullable=False)
    op.alter_column("audit_logs", "previous_hash", nullable=False)
    op.alter_column("audit_logs", "entry_hash", nullable=False)
    op.alter_column("audit_logs", "hash_version", nullable=False, server_default=None)
    op.alter_column("audit_logs", "source", nullable=False)
    op.alter_column("audit_logs", "occurred_at", nullable=False)


def downgrade() -> None:
    op.drop_index("ix_audit_logs_sequence", table_name="audit_logs")
    op.drop_constraint("uq_audit_logs_event_id", "audit_logs", type_="unique")
    op.drop_column("audit_logs", "occurred_at")
    op.drop_column("audit_logs", "source")
    op.drop_column("audit_logs", "event_id")
    op.drop_column("audit_logs", "hash_version")
    op.drop_column("audit_logs", "entry_hash")
    op.drop_column("audit_logs", "previous_hash")
    op.drop_column("audit_logs", "sequence")


def _backfill_audit_chain() -> None:
    bind = op.get_bind()
    metadata = sa.MetaData()

    audit_logs = sa.Table(
        "audit_logs",
        metadata,
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=False)),
        sa.Column("sequence", sa.BigInteger()),
        sa.Column("previous_hash", sa.String(length=128)),
        sa.Column("entry_hash", sa.String(length=128)),
        sa.Column("hash_version", sa.Integer()),
        sa.Column("event_id", sa.String(length=128)),
        sa.Column("source", sa.String(length=128)),
        sa.Column("occurred_at", sa.DateTime(timezone=True)),
        sa.Column("actor_id", sa.String(length=36)),
        sa.Column("actor_type", sa.String(length=64)),
        sa.Column("entity_id", sa.String(length=36)),
        sa.Column("entity_type", sa.String(length=64)),
        sa.Column("action", sa.String(length=120)),
        sa.Column("correlation_id", sa.String(length=120)),
        sa.Column("details", sa.JSON()),
    )

    rows = bind.execute(
        select(audit_logs.c.id, audit_logs.c.created_at, audit_logs.c.actor_id, audit_logs.c.actor_type,
               audit_logs.c.entity_id, audit_logs.c.entity_type, audit_logs.c.action,
               audit_logs.c.correlation_id, audit_logs.c.details)
        .order_by(audit_logs.c.created_at.asc(), audit_logs.c.id.asc())
    ).fetchall()

    previous_hash = GENESIS_HASH
    sequence = 0

    for row in rows:
        sequence += 1
        occurred_at = _coerce_to_utc(row.created_at)
        payload = _serialize_for_hash(
            {
                "sequence": sequence,
                "hash_version": HASH_VERSION,
                "event_id": None,
                "source": "entity_permissions_core",
                "action": row.action,
                "actor_id": row.actor_id,
                "actor_type": row.actor_type,
                "entity_id": row.entity_id,
                "entity_type": row.entity_type,
                "correlation_id": row.correlation_id,
                "details": row.details or {},
                "occurred_at": occurred_at.isoformat(),
                "previous_hash": previous_hash,
            }
        )
        entry_hash = hashlib.sha256((previous_hash + payload).encode("utf-8")).hexdigest()

        bind.execute(
            audit_logs.update()
            .where(audit_logs.c.id == row.id)
            .values(
                sequence=sequence,
                previous_hash=previous_hash,
                entry_hash=entry_hash,
                hash_version=HASH_VERSION,
                event_id=None,
                source="entity_permissions_core",
                occurred_at=occurred_at,
            )
        )

        previous_hash = entry_hash


def _serialize_for_hash(payload: Dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def _coerce_to_utc(value) -> Any:
    if value is None:
        return datetime.now(timezone.utc)
    if getattr(value, "tzinfo", None) is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
