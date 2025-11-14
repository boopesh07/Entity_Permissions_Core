"""User onboarding API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, EmailStr


class OnboardPropertyOwnerRequest(BaseModel):
    """Schema for onboarding a property owner."""
    
    name: str = Field(..., max_length=255, description="Owner name or company name")
    company_name: str = Field(..., description="Company/legal name")
    contact_email: EmailStr = Field(..., description="Contact email")
    phone: Optional[str] = Field(default=None, description="Phone number")
    address: Optional[str] = Field(default=None, description="Business address")
    attributes: Dict[str, Any] = Field(default_factory=dict, description="Additional attributes")


class OnboardInvestorRequest(BaseModel):
    """Schema for onboarding an investor."""
    
    name: str = Field(..., max_length=255, description="Investor name")
    email: EmailStr = Field(..., description="Email address")
    phone: Optional[str] = Field(default=None, description="Phone number")
    investor_type: str = Field(default="individual", description="Investor type (individual, institutional)")
    attributes: Dict[str, Any] = Field(default_factory=dict, description="Additional attributes")


class OnboardingResponse(BaseModel):
    """Schema for onboarding response."""
    
    entity_id: UUID
    name: str
    entity_type: str
    role_assigned: bool
    role_id: Optional[UUID] = None
    onboarding_status: str
    message: str


class StartWorkflowRequest(BaseModel):
    """Schema for starting a workflow."""
    
    workflow_type: str = Field(..., description="Workflow type (property_onboarding, investor_onboarding, token_purchase)")
    payload: Dict[str, Any] = Field(..., description="Workflow payload")


class WorkflowStatusResponse(BaseModel):
    """Schema for workflow status response."""
    
    workflow_id: str
    workflow_type: str
    status: str
    result: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None



