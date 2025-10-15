"""Role assignment schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RoleAssignmentCreate(BaseModel):
    principal_id: UUID
    role_id: UUID
    entity_id: Optional[UUID] = None
    principal_type: str = Field(default="user", max_length=64)
    effective_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None


class RoleAssignmentResponse(RoleAssignmentCreate):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
