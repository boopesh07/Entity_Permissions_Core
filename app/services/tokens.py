"""Token operations service."""

from __future__ import annotations

import logging
from typing import Dict, Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.entity import Entity, EntityType
from app.services.token_registry import get_token_registry_service

logger = logging.getLogger("app.services.tokens")


class TokenNotFoundError(ValueError):
    """Raised when token information is not found."""


class InsufficientTokensError(ValueError):
    """Raised when insufficient tokens are available."""


class TokenService:
    """Service for token operations."""
    
    def __init__(self, session: Session) -> None:
        """Initialize token service."""
        self._session = session
        self._token_registry = get_token_registry_service(session)
    
    async def get_token_details(self, property_id: UUID) -> Dict[str, Any]:
        """
        Get token details for a property.
        
        Args:
            property_id: Property entity ID
        
        Returns:
            Token details dictionary
        
        Raises:
            TokenNotFoundError: If property not found
        """
        property_entity = self._session.get(Entity, property_id)
        if not property_entity or property_entity.type != EntityType.OFFERING:
            raise TokenNotFoundError(f"Property {property_id} not found")
        
        attrs = property_entity.attributes
        
        return {
            "property_id": str(property_entity.id),
            "property_name": property_entity.name,
            "total_tokens": attrs.get("total_tokens", 0),
            "token_price": attrs.get("token_price", 0),
            "available_tokens": attrs.get("available_tokens", 0),
            "smart_contract_address": attrs.get("smart_contract_address"),
            "property_type": attrs.get("property_type", ""),
            "address": attrs.get("address", ""),
            "valuation": attrs.get("valuation", 0),
        }
    
    async def validate_purchase(
        self,
        investor_id: UUID,
        property_id: UUID,
        quantity: int,
    ) -> Dict[str, Any]:
        """
        Validate if a token purchase is possible.
        
        Args:
            investor_id: Investor entity ID
            property_id: Property entity ID
            quantity: Number of tokens to purchase
        
        Returns:
            Validation result with details
        """
        # Check investor exists and is verified
        investor_entity = self._session.get(Entity, investor_id)
        if not investor_entity or investor_entity.type != EntityType.INVESTOR:
            return {
                "valid": False,
                "reason": "Investor not found",
            }
        
        kyc_status = investor_entity.attributes.get("kyc_status", "pending")
        if kyc_status != "verified":
            return {
                "valid": False,
                "reason": "Investor KYC not verified",
            }
        
        # Check property exists and is active
        property_entity = self._session.get(Entity, property_id)
        if not property_entity or property_entity.type != EntityType.OFFERING:
            return {
                "valid": False,
                "reason": "Property not found",
            }
        
        property_status = property_entity.attributes.get("property_status", "")
        if property_status != "active":
            return {
                "valid": False,
                "reason": f"Property not active (status: {property_status})",
            }
        
        # Check token availability
        available_tokens = property_entity.attributes.get("available_tokens", 0)
        if quantity > available_tokens:
            return {
                "valid": False,
                "reason": f"Only {available_tokens} tokens available",
            }
        
        # Check minimum investment
        token_price = property_entity.attributes.get("token_price", 0)
        total_amount = quantity * token_price
        minimum_investment = property_entity.attributes.get("minimum_investment", 0)
        
        if total_amount < minimum_investment:
            return {
                "valid": False,
                "reason": f"Minimum investment is ${minimum_investment}",
            }
        
        return {
            "valid": True,
            "token_price": token_price,
            "total_amount": total_amount,
            "available_tokens": available_tokens,
        }
    
    async def get_investor_portfolio(self, investor_id: UUID) -> Dict[str, Any]:
        """
        Get investor's token portfolio.
        
        Args:
            investor_id: Investor entity ID
        
        Returns:
            Portfolio details
        """
        return await self._token_registry.get_investor_portfolio(str(investor_id))
    
    async def get_available_tokens(self, property_id: UUID) -> int:
        """
        Get number of available tokens for a property.
        
        Args:
            property_id: Property entity ID
        
        Returns:
            Available token count
        """
        return await self._token_registry.get_available_tokens(str(property_id))


