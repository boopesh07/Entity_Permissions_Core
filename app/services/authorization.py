"""Authorization evaluation service."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.entity import Entity
from app.models.permission import Permission
from app.models.role_assignment import RoleAssignment
from app.models.role import Role
from app.schemas.authorization import AuthorizationRequest
from app.services.audit import AuditService
from app.services.cache import PermissionCache, PermissionCacheKey, get_permission_cache


class AuthorizationError(Exception):
    """Base class for authorization service errors."""


class EntityNotFoundError(AuthorizationError):
    """Raised when the target entity does not exist for authorization."""


class AuthorizationService:
    """Evaluates whether a principal has permission for a resource."""

    def __init__(
        self,
        session: Session,
        audit_service: Optional[AuditService] = None,
        cache: Optional[PermissionCache] = None,
    ) -> None:
        self._session = session
        self._audit = audit_service or AuditService(session)
        self._logger = logging.getLogger("app.services.authorization")
        self._cache = cache or get_permission_cache()

    def authorize(self, payload: AuthorizationRequest) -> bool:
        entity = self._session.get(Entity, payload.resource_id)
        if not entity:
            self._logger.warning(
                "authorization_entity_not_found",
                extra={"resource_id": str(payload.resource_id)},
            )
            raise EntityNotFoundError(f"Entity {payload.resource_id} not found")

        lineage_ids = self._collect_entity_lineage_ids(entity.id)
        now = datetime.now(tz=timezone.utc)

        cache_key: PermissionCacheKey = (
            str(payload.user_id),
            payload.principal_type,
            str(payload.resource_id),
            payload.action,
        )
        cached = self._cache.get(cache_key)
        if cached is not None:
            self._logger.info(
                "authorization_cache_hit",
                extra={
                    "user_id": str(payload.user_id),
                    "resource_id": str(payload.resource_id),
                    "action": payload.action,
                    "authorized": cached,
                },
            )
            return cached

        stmt = (
            select(RoleAssignment, Role)
            .join(Role, RoleAssignment.role_id == Role.id)
            .join(Permission, Role.permissions)
            .where(RoleAssignment.principal_id == payload.user_id)
            .where(RoleAssignment.principal_type == payload.principal_type)
            .where(RoleAssignment.effective_at <= now)
            .where(or_(RoleAssignment.expires_at.is_(None), RoleAssignment.expires_at > now))
            .where(
                or_(
                    RoleAssignment.entity_id.is_(None),
                    RoleAssignment.entity_id.in_(lineage_ids),
                )
            )
            .where(Permission.action == payload.action)
        )

        assignments = self._session.execute(stmt).all()
        authorized = False
        for assignment, role in assignments:
            if role.scope_types and entity.type.value not in role.scope_types:
                continue
            authorized = True
            break

        self._audit.record(
            action="authorization.evaluate",
            actor_id=payload.user_id,
            entity_id=entity.id,
            entity_type=entity.type.value,
            details={
                "action": payload.action,
                "principal_type": payload.principal_type,
                "authorized": authorized,
            },
        )

        if authorized:
            self._logger.info(
                "authorization_granted",
                extra={
                    "user_id": str(payload.user_id),
                    "resource_id": str(payload.resource_id),
                    "action": payload.action,
                },
            )
        else:
            self._logger.info(
                "authorization_denied",
                extra={
                    "user_id": str(payload.user_id),
                    "resource_id": str(payload.resource_id),
                    "action": payload.action,
                },
            )

        self._cache.set(cache_key, authorized, principal_id=str(payload.user_id))
        return authorized

    def _collect_entity_lineage_ids(self, entity_id: UUID) -> List[UUID]:
        lineage: List[UUID] = [entity_id]
        visited = {entity_id}
        current_id = entity_id
        while True:
            parent_id = self._session.scalar(
                select(Entity.parent_id).where(Entity.id == current_id)
            )
            if not parent_id or parent_id in visited:
                break
            lineage.append(parent_id)
            visited.add(parent_id)
            current_id = parent_id
        return lineage
