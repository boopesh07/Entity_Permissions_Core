"""Schemas for external audit ingestion events."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class AuditEvent(BaseModel):
    """Canonical audit event published by upstream services."""

    event_id: Optional[UUID] = Field(
        default=None,
        description="Idempotency key supplied by the producer; UUID strongly encouraged.",
    )
    source: str = Field(..., max_length=128, description="Logical service name that produced the event.")
    action: str = Field(..., max_length=120)
    actor_id: Optional[UUID] = Field(default=None)
    actor_type: str = Field(default="user", max_length=64)
    entity_id: Optional[UUID] = Field(default=None)
    entity_type: Optional[str] = Field(default=None, max_length=64)
    correlation_id: Optional[str] = Field(default=None, max_length=120)
    details: Dict[str, Any] = Field(default_factory=dict)
    occurred_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp (UTC) the action occurred.",
    )

    @model_validator(mode="after")
    def _enforce_timezone(self) -> "AuditEvent":
        timestamp = self.occurred_at
        if timestamp.tzinfo is None:
            self.occurred_at = timestamp.replace(tzinfo=timezone.utc)
        else:
            self.occurred_at = timestamp.astimezone(timezone.utc)
        return self
