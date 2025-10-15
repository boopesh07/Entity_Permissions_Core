"""Entity API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.entity import EntityStatus, EntityType


class EntityBase(BaseModel):
    name: str = Field(..., max_length=255)
    type: EntityType
    parent_id: Optional[UUID] = None
    attributes: Dict[str, Any] = Field(default_factory=dict)


class EntityCreate(EntityBase):
    status: EntityStatus = EntityStatus.ACTIVE


class EntityUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=255)
    status: Optional[EntityStatus] = None
    parent_id: Optional[UUID] = None
    attributes: Optional[Dict[str, Any]] = None


class EntityResponse(EntityBase):
    id: UUID
    status: EntityStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
