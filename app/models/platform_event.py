"""Normalized platform event model stored by the events engine."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Enum as SqlEnum
from sqlalchemy import Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin
from app.models.types import GUID, JSONType


class DeliveryState(str, Enum):
    """Outbox delivery state."""

    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class PlatformEvent(TimestampMixin, Base):
    """Immutable record describing a normalized platform event."""

    __tablename__ = "platform_events"
    __table_args__ = (
        Index("ix_platform_events_event_type", "event_type"),
        Index("ix_platform_events_occurred_at", "occurred_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    event_id: Mapped[str] = mapped_column(String(length=128), unique=True, nullable=False)
    event_type: Mapped[str] = mapped_column(String(length=128), nullable=False)
    source: Mapped[str] = mapped_column(String(length=128), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(nullable=False)
    correlation_id: Mapped[Optional[str]] = mapped_column(String(length=128), nullable=True)
    schema_version: Mapped[str] = mapped_column(String(length=16), nullable=False, default="v1")
    payload: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)
    context: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)
    delivery_state: Mapped[DeliveryState] = mapped_column(
        SqlEnum(DeliveryState, name="platform_event_delivery_state", native_enum=False),
        nullable=False,
        default=DeliveryState.PENDING,
    )
    delivery_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[Optional[str]] = mapped_column(String(length=1024), nullable=True)
