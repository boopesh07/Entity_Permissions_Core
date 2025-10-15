"""Authorization endpoint schemas."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class AuthorizationRequest(BaseModel):
    user_id: UUID = Field(..., alias="user_id")
    action: str
    resource_id: UUID
    principal_type: str = Field(default="user", max_length=64)


class AuthorizationResponse(BaseModel):
    authorized: bool
