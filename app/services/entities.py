"""Entity domain service."""

from __future__ import annotations

import logging
from typing import Iterable, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.entity import Entity, EntityStatus
from app.schemas.entity import EntityCreate, EntityUpdate
from app.services.audit import AuditService


class EntityNotFoundError(ValueError):
    """Raised when the target entity does not exist."""


class EntityConflictError(ValueError):
    """Raised when attempting to create an entity that already exists."""


class EntityService:
    """Encapsulates entity CRUD operations with auditing."""

    def __init__(self, session: Session, audit_service: Optional[AuditService] = None) -> None:
        self._session = session
        self._audit = audit_service or AuditService(session)
        self._logger = logging.getLogger("app.services.entities")

    def create_entity(self, payload: EntityCreate, *, actor_id: Optional[UUID]) -> Entity:
        entity = Entity(
            name=payload.name,
            type=payload.type,
            status=payload.status,
            parent_id=payload.parent_id,
            attributes=payload.attributes,
        )
        self._session.add(entity)
        try:
            self._session.flush()
        except IntegrityError as exc:
            self._session.rollback()
            raise EntityConflictError(f"Entity '{payload.name}' of type '{payload.type.value}' already exists") from exc

        self._audit.record(
            action="entity.create",
            actor_id=actor_id,
            entity_id=entity.id,
            details={"type": entity.type, "name": entity.name},
        )
        self._logger.info(
            "entity_created",
            extra={"entity_id": str(entity.id), "entity_type": entity.type, "actor_id": str(actor_id) if actor_id else None},
        )
        return entity

    def get(self, entity_id: UUID) -> Entity:
        entity = self._session.get(Entity, entity_id)
        if not entity:
            raise EntityNotFoundError(f"Entity {entity_id} not found")
        return entity

    def list(self, *, types: Optional[Iterable[str]] = None, parent_id: Optional[UUID] = None) -> list[Entity]:
        stmt = select(Entity)
        if types:
            stmt = stmt.filter(Entity.type.in_(types))
        if parent_id:
            stmt = stmt.filter(Entity.parent_id == parent_id)
        results = self._session.scalars(stmt.order_by(Entity.created_at.desc())).all()
        return list(results)

    def update(self, entity_id: UUID, payload: EntityUpdate, *, actor_id: Optional[UUID]) -> Entity:
        entity = self.get(entity_id)

        updates = payload.model_dump(exclude_unset=True)
        if "name" in updates:
            entity.name = updates["name"]
        if "status" in updates:
            entity.status = updates["status"]
        if "parent_id" in updates:
            entity.parent_id = updates["parent_id"]
        if "attributes" in updates:
            entity.attributes = updates["attributes"]

        self._session.add(entity)
        self._session.flush()

        self._audit.record(
            action="entity.update",
            actor_id=actor_id,
            entity_id=entity.id,
            details={"changes": updates},
        )
        self._logger.info(
            "entity_updated",
            extra={"entity_id": str(entity.id), "actor_id": str(actor_id) if actor_id else None},
        )
        return entity

    def archive(self, entity_id: UUID, *, actor_id: Optional[UUID]) -> Entity:
        entity = self.get(entity_id)
        entity.status = EntityStatus.ARCHIVED
        self._session.add(entity)
        self._session.flush()

        self._audit.record(
            action="entity.archive",
            actor_id=actor_id,
            entity_id=entity.id,
            details={},
        )
        self._logger.info(
            "entity_archived",
            extra={"entity_id": str(entity.id), "actor_id": str(actor_id) if actor_id else None},
        )
        return entity
