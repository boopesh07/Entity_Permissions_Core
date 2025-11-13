"""Token API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TokenDetails(BaseModel):
    """Schema for token details."""
    
    property_id: UUID
    property_name: str
    total_tokens: int
    token_price: float
    available_tokens: int
    smart_contract_address: Optional[str] = None
    property_type: str
    address: str
    valuation: float


class TokenPurchaseRequest(BaseModel):
    """Schema for token purchase request."""
    
    investor_id: UUID = Field(..., description="Investor entity ID")
    property_id: UUID = Field(..., description="Property entity ID")
    token_quantity: int = Field(..., gt=0, description="Number of tokens to purchase")
    payment_method: str = Field(default="card", description="Payment method (card, bank_transfer, crypto)")


class TokenPurchaseResponse(BaseModel):
    """Schema for token purchase response."""
    
    workflow_id: str
    investor_id: UUID
    property_id: UUID
    token_quantity: int
    payment_amount: float
    status: str
    message: str


class TokenHolding(BaseModel):
    """Schema for token holding details."""
    
    property_id: UUID
    property_name: str
    quantity: int
    token_price: float
    value: float


class InvestorPortfolioResponse(BaseModel):
    """Schema for investor portfolio response."""
    
    investor_id: UUID
    holdings: List[TokenHolding]
    total_value: float
    properties_count: int


class TokenTransferRequest(BaseModel):
    """Schema for token transfer request (future feature)."""
    
    from_investor_id: UUID
    to_investor_id: UUID
    property_id: UUID
    quantity: int


class TokenTransferResponse(BaseModel):
    """Schema for token transfer response."""
    
    from_investor_id: UUID
    to_investor_id: UUID
    property_id: UUID
    quantity: int
    transaction_hash: str
    status: str


