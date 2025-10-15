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


class AuthorizationService:
    """Evaluates whether a principal has permission for a resource."""

    def __init__(self, session: Session, audit_service: Optional[AuditService] = None) -> None:
        self._session = session
        self._audit = audit_service or AuditService(session)
        self._logger = logging.getLogger("app.services.authorization")

    def authorize(self, payload: AuthorizationRequest) -> bool:
        entity = self._session.get(Entity, payload.resource_id)
        if not entity:
            self._logger.warning(
                "authorization_denied_missing_entity",
                extra={"resource_id": str(payload.resource_id)},
            )
            return False

        lineage_ids = self._collect_entity_lineage_ids(entity.id)
        now = datetime.now(tz=timezone.utc)

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
            status="success" if authorized else "failure",
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
