"""Event ingestion schemas."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.platform_event import DeliveryState


class EventIngestRequest(BaseModel):
    """Inbound payload for the event ingestion API."""

    event_type: str = Field(..., min_length=3, max_length=128)
    source: str = Field(..., min_length=3, max_length=128)
    payload: Dict[str, Any] = Field(default_factory=dict)
    context: Dict[str, Any] = Field(default_factory=dict)
    correlation_id: Optional[str] = Field(default=None, max_length=128)
    occurred_at: Optional[datetime] = Field(
        default=None,
        description="Optional UTC timestamp provided by the producer.",
    )
    schema_version: str = Field(default="v1", max_length=16)

    @field_validator("occurred_at")
    @classmethod
    def _ensure_utc(cls, value: Optional[datetime]) -> Optional[datetime]:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


class EventResponse(BaseModel):
    """API response describing a stored platform event."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_id: str
    event_type: str
    source: str
    occurred_at: datetime
    correlation_id: Optional[str]
    schema_version: str
    payload: Dict[str, Any]
    context: Dict[str, Any]
    delivery_state: DeliveryState
    delivery_attempts: int
    last_error: Optional[str]
    created_at: datetime
    updated_at: datetime
