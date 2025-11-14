"""Token registry service for tracking token ownership (MOCKED for MVP)."""

from __future__ import annotations

import logging
from typing import Any, Dict
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entity import Entity

logger = logging.getLogger("app.services.token_registry")


class TokenRegistryService:
    """
    Token registry for off-chain token balance tracking.
    
    For MVP, this stores token holdings in the entities.attributes JSON field.
    In production, this should use dedicated database tables for better
    performance, indexing, and data integrity.
    
    Future Implementation Requirements:
    - Create dedicated token_holdings table
    - Add token_transfers table for complete history
    - Implement real-time balance calculations
    - Add aggregation queries for portfolio analytics
    - Implement atomic transaction updates
    - Add event sourcing for audit trail
    """
    
    def __init__(self, session: Session) -> None:
        """Initialize token registry service."""
        self._session = session
    
    async def create_token_entry(
        self,
        property_id: str,
        total_tokens: int,
        token_price: float,
        contract_address: str,
    ) -> Dict[str, Any]:
        """
        Register a new tokenized property.
        
        Args:
            property_id: Property entity ID
            total_tokens: Total supply of tokens
            token_price: Price per token
            contract_address: Blockchain smart contract address
        
        Returns:
            Token registry entry
        
        MOCKED: Stores in property entity attributes.
        PRODUCTION: Should insert into dedicated tokens table.
        """
        logger.info(
            "token_registry_create_entry",
            extra={
                "property_id": property_id,
                "total_tokens": total_tokens,
                "token_price": token_price,
            },
        )
        
        property_entity = self._session.get(Entity, UUID(property_id))
        if not property_entity:
            raise ValueError(f"Property {property_id} not found")
        
        # Store token metadata in property attributes
        property_entity.attributes["total_tokens"] = total_tokens
        property_entity.attributes["token_price"] = token_price
        property_entity.attributes["available_tokens"] = total_tokens
        property_entity.attributes["smart_contract_address"] = contract_address
        property_entity.attributes["token_holders"] = {}
        
        self._session.add(property_entity)
        self._session.flush()
        
        return {
            "property_id": property_id,
            "total_tokens": total_tokens,
            "token_price": token_price,
            "available_tokens": total_tokens,
            "contract_address": contract_address,
        }
    
    async def get_token_balance(
        self,
        investor_id: str,
        property_id: str,
    ) -> int:
        """
        Get investor's token balance for a property.
        
        Args:
            investor_id: Investor entity ID
            property_id: Property entity ID
        
        Returns:
            Token quantity owned
        
        MOCKED: Retrieves from investor entity attributes.
        PRODUCTION: Should query token_holdings table.
        """
        investor_entity = self._session.get(Entity, UUID(investor_id))
        if not investor_entity:
            return 0
        
        token_holdings = investor_entity.attributes.get("token_holdings", {})
        return token_holdings.get(property_id, 0)
    
    async def record_transfer(
        self,
        from_investor_id: str | None,
        to_investor_id: str,
        property_id: str,
        quantity: int,
        transaction_hash: str,
    ) -> Dict[str, Any]:
        """
        Record a token transfer.
        
        Args:
            from_investor_id: Sender investor ID (None for initial mint)
            to_investor_id: Recipient investor ID
            property_id: Property entity ID
            quantity: Number of tokens transferred
            transaction_hash: Blockchain transaction hash
        
        Returns:
            Transfer record
        
        MOCKED: Updates in-memory balances in entity attributes.
        PRODUCTION: Should perform atomic database transaction:
        - Deduct from sender balance
        - Add to recipient balance
        - Insert into token_transfers table
        - Validate constraints (non-negative balances)
        """
        logger.info(
            "token_registry_record_transfer",
            extra={
                "from_investor_id": from_investor_id,
                "to_investor_id": to_investor_id,
                "property_id": property_id,
                "quantity": quantity,
            },
        )
        
        # Update property's available tokens
        property_entity = self._session.get(Entity, UUID(property_id))
        if not property_entity:
            raise ValueError(f"Property {property_id} not found")
        
        if from_investor_id is None:
            # Initial mint - reduce available tokens
            available = property_entity.attributes.get("available_tokens", 0)
            property_entity.attributes["available_tokens"] = available - quantity
        
        # Update recipient's token holdings
        investor_entity = self._session.get(Entity, UUID(to_investor_id))
        if not investor_entity:
            raise ValueError(f"Investor {to_investor_id} not found")
        
        if "token_holdings" not in investor_entity.attributes:
            investor_entity.attributes["token_holdings"] = {}
        
        current_balance = investor_entity.attributes["token_holdings"].get(property_id, 0)
        investor_entity.attributes["token_holdings"][property_id] = current_balance + quantity
        
        # Update property's token holders mapping
        if "token_holders" not in property_entity.attributes:
            property_entity.attributes["token_holders"] = {}
        
        holder_balance = property_entity.attributes["token_holders"].get(to_investor_id, 0)
        property_entity.attributes["token_holders"][to_investor_id] = holder_balance + quantity
        
        self._session.add(property_entity)
        self._session.add(investor_entity)
        self._session.flush()
        
        return {
            "from_investor_id": from_investor_id,
            "to_investor_id": to_investor_id,
            "property_id": property_id,
            "quantity": quantity,
            "transaction_hash": transaction_hash,
            "new_balance": current_balance + quantity,
        }
    
    async def get_available_tokens(self, property_id: str) -> int:
        """
        Get number of tokens available for purchase.
        
        Args:
            property_id: Property entity ID
        
        Returns:
            Available token quantity
        
        MOCKED: Returns from property attributes.
        PRODUCTION: Should calculate from token_holdings aggregation:
        SELECT total_supply - SUM(quantity) FROM token_holdings
        WHERE property_id = ?
        """
        property_entity = self._session.get(Entity, UUID(property_id))
        if not property_entity:
            raise ValueError(f"Property {property_id} not found")
        
        return property_entity.attributes.get("available_tokens", 0)
    
    async def get_investor_portfolio(self, investor_id: str) -> Dict[str, Any]:
        """
        Get investor's complete token portfolio.
        
        Args:
            investor_id: Investor entity ID
        
        Returns:
            Portfolio details with holdings across all properties
        
        MOCKED: Reads from investor attributes.
        PRODUCTION: Should query token_holdings with property joins.
        """
        investor_entity = self._session.get(Entity, UUID(investor_id))
        if not investor_entity:
            raise ValueError(f"Investor {investor_id} not found")
        
        token_holdings = investor_entity.attributes.get("token_holdings", {})
        
        portfolio = []
        total_value = 0.0
        
        for property_id, quantity in token_holdings.items():
            property_entity = self._session.get(Entity, UUID(property_id))
            if property_entity:
                token_price = property_entity.attributes.get("token_price", 0)
                value = quantity * token_price
                total_value += value
                
                portfolio.append({
                    "property_id": property_id,
                    "property_name": property_entity.name,
                    "quantity": quantity,
                    "token_price": token_price,
                    "value": value,
                })
        
        return {
            "investor_id": investor_id,
            "holdings": portfolio,
            "total_value": total_value,
            "properties_count": len(portfolio),
        }


def get_token_registry_service(session: Session) -> TokenRegistryService:
    """Create token registry service instance."""
    return TokenRegistryService(session)



