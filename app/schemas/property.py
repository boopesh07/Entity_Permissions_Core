"""Property API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PropertyCreate(BaseModel):
    """Schema for creating a new property."""
    
    name: str = Field(..., max_length=255, description="Property name")
    owner_id: UUID = Field(..., description="Property owner entity ID")
    property_type: str = Field(..., description="Property type (residential, commercial, industrial)")
    address: str = Field(..., description="Property address")
    valuation: float = Field(..., gt=0, description="Property valuation in USD")
    total_tokens: int = Field(..., gt=0, description="Total number of tokens to mint")
    token_price: float = Field(..., gt=0, description="Price per token in USD")
    minimum_investment: float = Field(default=1000, gt=0, description="Minimum investment amount")
    description: Optional[str] = Field(default=None, description="Property description")
    attributes: Dict[str, Any] = Field(default_factory=dict, description="Additional property attributes")


class PropertyUpdate(BaseModel):
    """Schema for updating property details."""
    
    name: Optional[str] = Field(default=None, max_length=255)
    property_type: Optional[str] = None
    address: Optional[str] = None
    valuation: Optional[float] = Field(default=None, gt=0)
    token_price: Optional[float] = Field(default=None, gt=0)
    minimum_investment: Optional[float] = Field(default=None, gt=0)
    description: Optional[str] = None
    attributes: Optional[Dict[str, Any]] = None
    
    model_config = ConfigDict(extra="forbid")


class PropertyResponse(BaseModel):
    """Schema for property response."""
    
    id: UUID
    name: str
    owner_id: UUID
    property_type: str
    address: str
    valuation: float
    total_tokens: int
    token_price: float
    available_tokens: int
    property_status: str
    smart_contract_address: Optional[str] = None
    tokenization_date: Optional[str] = None
    minimum_investment: float
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class PropertyListResponse(BaseModel):
    """Schema for property list response."""
    
    properties: list[PropertyResponse]
    total: int
    page: int
    page_size: int


class TokenizePropertyRequest(BaseModel):
    """Schema for initiating property tokenization."""
    
    property_id: UUID
    owner_id: UUID


class TokenizePropertyResponse(BaseModel):
    """Schema for tokenization response."""
    
    property_id: UUID
    workflow_id: str
    status: str
    message: str


