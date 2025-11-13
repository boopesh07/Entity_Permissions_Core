"""Property management service."""

from __future__ import annotations

import logging
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entity import Entity, EntityStatus, EntityType
from app.schemas.property import PropertyCreate, PropertyUpdate
from app.services.audit import AuditService

logger = logging.getLogger("app.services.properties")


class PropertyNotFoundError(ValueError):
    """Raised when property is not found."""


class PropertyService:
    """Service for property management operations."""
    
    def __init__(
        self,
        session: Session,
        audit_service: Optional[AuditService] = None,
    ) -> None:
        """Initialize property service."""
        self._session = session
        self._audit = audit_service or AuditService(session)
        self._logger = logging.getLogger("app.services.properties")
    
    def create_property(
        self,
        payload: PropertyCreate,
        *,
        actor_id: Optional[UUID],
    ) -> Entity:
        """
        Create a new property entity.
        
        Args:
            payload: Property creation data
            actor_id: ID of the actor creating the property
        
        Returns:
            Created property entity
        """
        # Verify owner exists
        owner = self._session.get(Entity, payload.owner_id)
        if not owner or owner.type != EntityType.ISSUER:
            raise ValueError(f"Owner {payload.owner_id} not found or not an issuer")
        
        # Create property entity
        property_entity = Entity(
            name=payload.name,
            type=EntityType.OFFERING,
            status=EntityStatus.ACTIVE,
            parent_id=payload.owner_id,
            attributes={
                "property_type": payload.property_type,
                "address": payload.address,
                "valuation": payload.valuation,
                "total_tokens": payload.total_tokens,
                "token_price": payload.token_price,
                "available_tokens": payload.total_tokens,
                "property_status": "pending",  # pending → active after tokenization
                "minimum_investment": payload.minimum_investment,
                "description": payload.description or "",
                **payload.attributes,
            },
        )
        
        self._session.add(property_entity)
        self._session.flush()
        
        self._audit.record(
            action="property.create",
            actor_id=actor_id,
            entity_id=property_entity.id,
            entity_type=property_entity.type.value,
            details={
                "name": property_entity.name,
                "owner_id": str(payload.owner_id),
                "valuation": payload.valuation,
            },
        )
        
        logger.info(
            "property_created",
            extra={
                "property_id": str(property_entity.id),
                "owner_id": str(payload.owner_id),
                "actor_id": str(actor_id) if actor_id else None,
            },
        )
        
        return property_entity
    
    def get_property(self, property_id: UUID) -> Entity:
        """
        Get property by ID.
        
        Args:
            property_id: Property entity ID
        
        Returns:
            Property entity
        
        Raises:
            PropertyNotFoundError: If property not found
        """
        property_entity = self._session.get(Entity, property_id)
        if not property_entity or property_entity.type != EntityType.OFFERING:
            raise PropertyNotFoundError(f"Property {property_id} not found")
        return property_entity
    
    def list_properties(
        self,
        *,
        status: Optional[str] = None,
        property_type: Optional[str] = None,
        owner_id: Optional[UUID] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Entity]:
        """
        List properties with optional filters.
        
        Args:
            status: Filter by property status (pending, active, sold_out)
            property_type: Filter by property type (residential, commercial, industrial)
            owner_id: Filter by owner entity ID
            limit: Maximum number of results
            offset: Offset for pagination
        
        Returns:
            List of property entities
        """
        stmt = select(Entity).where(Entity.type == EntityType.OFFERING)
        stmt = stmt.where(Entity.status != EntityStatus.ARCHIVED)
        
        if owner_id:
            stmt = stmt.where(Entity.parent_id == owner_id)
        
        stmt = stmt.order_by(Entity.created_at.desc()).limit(limit).offset(offset)
        
        results = self._session.scalars(stmt).all()
        
        # Filter by attributes in Python (database-agnostic approach)
        filtered_results = []
        for entity in results:
            if status and entity.attributes.get("property_status") != status:
                continue
            if property_type and entity.attributes.get("property_type") != property_type:
                continue
            filtered_results.append(entity)
        
        return filtered_results
    
    def update_property(
        self,
        property_id: UUID,
        payload: PropertyUpdate,
        *,
        actor_id: Optional[UUID],
    ) -> Entity:
        """
        Update property details.
        
        Args:
            property_id: Property entity ID
            payload: Update data
            actor_id: ID of the actor updating the property
        
        Returns:
            Updated property entity
        """
        from sqlalchemy.orm.attributes import flag_modified
        
        property_entity = self.get_property(property_id)
        
        updates = payload.model_dump(exclude_unset=True)
        
        if "name" in updates:
            property_entity.name = updates["name"]
        
        # Update attributes
        attributes_changed = False
        for key in ["property_type", "address", "valuation", "token_price",
                    "minimum_investment", "description"]:
            if key in updates and updates[key] is not None:
                property_entity.attributes[key] = updates[key]
                attributes_changed = True
        
        if "attributes" in updates and updates["attributes"]:
            property_entity.attributes.update(updates["attributes"])
            attributes_changed = True
        
        # Mark attributes as modified for SQLAlchemy to detect changes
        if attributes_changed:
            flag_modified(property_entity, "attributes")
        
        self._session.add(property_entity)
        self._session.flush()
        
        self._audit.record(
            action="property.update",
            actor_id=actor_id,
            entity_id=property_entity.id,
            entity_type=property_entity.type.value,
            details={"changes": updates},
        )
        
        logger.info(
            "property_updated",
            extra={
                "property_id": str(property_id),
                "actor_id": str(actor_id) if actor_id else None,
            },
        )
        
        return property_entity
    
    def get_property_count(self, **filters) -> int:
        """
        Get total count of properties matching filters.
        
        Args:
            **filters: Same filters as list_properties
        
        Returns:
            Total count
        """
        stmt = select(Entity).where(Entity.type == EntityType.OFFERING)
        stmt = stmt.where(Entity.status != EntityStatus.ARCHIVED)
        
        if "owner_id" in filters and filters["owner_id"]:
            stmt = stmt.where(Entity.parent_id == filters["owner_id"])
        
        results = self._session.scalars(stmt).all()
        
        # Filter by attributes in Python (database-agnostic approach)
        count = 0
        for entity in results:
            if "status" in filters and filters["status"]:
                if entity.attributes.get("property_status") != filters["status"]:
                    continue
            if "property_type" in filters and filters["property_type"]:
                if entity.attributes.get("property_type") != filters["property_type"]:
                    continue
            count += 1
        
        return count

