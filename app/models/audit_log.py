"""Audit log entries for traceability."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin
from app.models.types import GUID, JSONType


class AuditLog(TimestampMixin, Base):
    """Immutable audit log entries persisted for chain verification."""

    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_actor", "actor_id"),
        Index("ix_audit_logs_entity", "entity_id"),
        Index("ix_audit_logs_action", "action"),
        Index("ix_audit_logs_sequence", "sequence", unique=True),
        UniqueConstraint("event_id", name="uq_audit_logs_event_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    sequence: Mapped[int] = mapped_column(BigInteger, nullable=False)
    previous_hash: Mapped[str] = mapped_column(String(length=128), nullable=False)
    entry_hash: Mapped[str] = mapped_column(String(length=128), nullable=False)
    hash_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    event_id: Mapped[str | None] = mapped_column(String(length=128), nullable=True)
    source: Mapped[str] = mapped_column(String(length=128), nullable=False, default="entity_permissions_core")
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    actor_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), nullable=True)
    actor_type: Mapped[str] = mapped_column(String(length=64), nullable=False, default="user")
    entity_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), nullable=True)
    entity_type: Mapped[str | None] = mapped_column(String(length=64), nullable=True)
    action: Mapped[str] = mapped_column(String(length=120), nullable=False)
    correlation_id: Mapped[str | None] = mapped_column(String(length=120), nullable=True)
    details: Mapped[dict] = mapped_column(JSONType, default=dict, nullable=False)
