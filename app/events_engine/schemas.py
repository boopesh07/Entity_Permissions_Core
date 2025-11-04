"""Pydantic models describing normalized events."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class EventEnvelope(BaseModel):
    """Canonical platform event payload used for SNS fan-out and storage."""

    event_id: UUID = Field(default_factory=uuid4)
    event_type: str = Field(..., min_length=3, max_length=128)
    source: str = Field(..., min_length=3, max_length=128)
    occurred_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp for when the originating action occurred.",
    )
    correlation_id: Optional[str] = Field(default=None, max_length=128)
    schema_version: str = Field(default="v1", max_length=16)
    payload: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("occurred_at")
    @classmethod
    def _ensure_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
