"""Permission schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PermissionCreate(BaseModel):
    action: str = Field(..., min_length=3, max_length=255)
    description: Optional[str] = Field(default=None, max_length=1024)


class PermissionResponse(PermissionCreate):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
