"""Role schemas."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RoleBase(BaseModel):
    name: str = Field(..., min_length=3, max_length=120)
    description: Optional[str] = Field(default=None, max_length=512)
    scope_types: List[str] = Field(default_factory=list)


class RoleCreate(RoleBase):
    permissions: List[str] = Field(default_factory=list, description="List of permission action strings.")


class RoleUpdate(BaseModel):
    description: Optional[str] = Field(default=None, max_length=512)
    scope_types: Optional[List[str]] = None
    permissions: Optional[List[str]] = None


class RoleResponse(RoleBase):
    id: UUID
    is_system: bool
    permissions: List[str]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
