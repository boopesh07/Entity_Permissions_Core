"""Role and permission service logic."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Iterable, List, Optional
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.entity import Entity
from app.models.permission import Permission
from app.models.role import Role
from app.models.role_assignment import RoleAssignment
from app.schemas.assignment import RoleAssignmentCreate
from app.schemas.role import RoleCreate, RoleUpdate
from app.services.audit import AuditService
from app.services.cache import PermissionCache, get_permission_cache


class RoleServiceError(Exception):
    """Base class for role service errors."""


class RoleNotFoundError(RoleServiceError):
    """Raised when a role cannot be found."""


class PermissionScopeError(RoleServiceError):
    """Raised when assignment violates scope constraints."""


class RoleConflictError(RoleServiceError):
    """Raised when attempting to create a role that already exists."""


class RoleService:
    """Coordinates permission management and role assignments."""

    def __init__(
        self,
        session: Session,
        audit_service: Optional[AuditService] = None,
        cache: Optional[PermissionCache] = None,
    ) -> None:
        self._session = session
        self._audit = audit_service or AuditService(session)
        self._logger = logging.getLogger("app.services.roles")
        self._cache = cache or get_permission_cache()

    def create_role(self, payload: RoleCreate, *, actor_id: Optional[UUID]) -> Role:
        role = Role(
            name=payload.name,
            description=payload.description,
            scope_types=payload.scope_types,
            is_system=False,
        )
        role.permissions = list(self._ensure_permissions(payload.permissions))
        self._session.add(role)
        try:
            self._session.flush()
        except IntegrityError as exc:
            self._session.rollback()
            raise RoleConflictError(f"Role '{payload.name}' already exists") from exc

        self._audit.record(
            action="role.create",
            actor_id=actor_id,
            entity_id=None,
            entity_type=None,
            details={"role_id": str(role.id), "permissions": payload.permissions},
        )
        self._logger.info(
            "role_created",
            extra={"role_id": str(role.id), "actor_id": str(actor_id) if actor_id else None},
        )
        self._cache.invalidate()
        return role

    def update_role(self, role_id: UUID, payload: RoleUpdate, *, actor_id: Optional[UUID]) -> Role:
        role = self._get_role(role_id)
        updates = payload.model_dump(exclude_unset=True)

        if "description" in updates:
            role.description = updates["description"]
        if "scope_types" in updates:
            role.scope_types = updates["scope_types"] or []
        if "permissions" in updates and updates["permissions"] is not None:
            role.permissions = list(self._ensure_permissions(updates["permissions"]))

        self._session.add(role)
        self._session.flush()

        self._audit.record(
            action="role.update",
            actor_id=actor_id,
            entity_id=None,
            entity_type=None,
            details={"role_id": str(role.id), "changes": updates},
        )
        self._logger.info(
            "role_updated",
            extra={"role_id": str(role.id), "actor_id": str(actor_id) if actor_id else None},
        )
        self._cache.invalidate()
        return role

    def list_roles(self) -> List[Role]:
        stmt = select(Role).order_by(Role.created_at.desc())
        return list(self._session.scalars(stmt))

    def assign_role(self, payload: RoleAssignmentCreate, *, actor_id: Optional[UUID]) -> RoleAssignment:
        role = self._get_role(payload.role_id)

        entity: Optional[Entity] = None
        if payload.entity_id:
            entity = self._session.get(Entity, payload.entity_id)
            if not entity:
                raise PermissionScopeError(f"Entity {payload.entity_id} not found for assignment")
            if role.scope_types and entity.type.value not in role.scope_types:
                raise PermissionScopeError(f"Role {role.name} cannot be assigned to entity type {entity.type.value}")

        existing = self._session.scalar(
            select(RoleAssignment).where(
                and_(
                    RoleAssignment.principal_id == payload.principal_id,
                    RoleAssignment.principal_type == payload.principal_type,
                    RoleAssignment.role_id == payload.role_id,
                    RoleAssignment.entity_id == payload.entity_id,
                )
            )
        )
        if existing:
            return existing

        assignment = RoleAssignment(
            principal_id=payload.principal_id,
            principal_type=payload.principal_type,
            entity_id=payload.entity_id,
            role_id=payload.role_id,
            effective_at=self._normalize_datetime(payload.effective_at),
            expires_at=self._normalize_datetime(payload.expires_at, allow_none=True),
        )
        self._session.add(assignment)
        try:
            self._session.flush()
        except IntegrityError as exc:
            raise RoleServiceError("Failed to create assignment") from exc

        self._audit.record(
            action="role_assignment.create",
            actor_id=actor_id,
            entity_id=payload.entity_id,
            entity_type=entity.type.value if entity else None,
            details={
                "role_id": str(payload.role_id),
                "principal_id": str(payload.principal_id),
                "principal_type": payload.principal_type,
            },
        )
        self._logger.info(
            "role_assigned",
            extra={
                "role_id": str(payload.role_id),
                "principal_id": str(payload.principal_id),
                "entity_id": str(payload.entity_id) if payload.entity_id else None,
            },
        )
        self._cache.invalidate_for_principal(str(payload.principal_id))
        return assignment

    def list_assignments(
        self,
        *,
        principal_id: Optional[UUID] = None,
        entity_id: Optional[UUID] = None,
    ) -> List[RoleAssignment]:
        stmt = select(RoleAssignment)
        if principal_id:
            stmt = stmt.filter(RoleAssignment.principal_id == principal_id)
        if entity_id:
            stmt = stmt.filter(RoleAssignment.entity_id == entity_id)
        stmt = stmt.order_by(RoleAssignment.created_at.desc())
        return list(self._session.scalars(stmt))

    def revoke_assignment(self, assignment_id: UUID, *, actor_id: Optional[UUID]) -> None:
        assignment = self._session.get(RoleAssignment, assignment_id)
        if not assignment:
            raise RoleServiceError(f"Assignment {assignment_id} not found")

        entity_type = assignment.entity.type.value if assignment.entity else None
        entity_id = assignment.entity_id

        self._session.delete(assignment)
        self._session.flush()

        self._audit.record(
            action="role_assignment.delete",
            actor_id=actor_id,
            entity_id=entity_id,
            entity_type=entity_type,
            details={"assignment_id": str(assignment_id)},
        )
        self._logger.info(
            "role_assignment_revoked",
            extra={"assignment_id": str(assignment_id), "actor_id": str(actor_id) if actor_id else None},
        )
        if assignment:
            self._cache.invalidate_for_principal(str(assignment.principal_id))

    def ensure_baseline_permissions(self, actions: Iterable[str]) -> None:
        """Idempotently create baseline permission records."""

        actions = list({action for action in actions})
        if not actions:
            return

        existing_actions = set(
            self._session.scalars(select(Permission.action).where(Permission.action.in_(actions))).all()
        )
        for action in actions:
            if action not in existing_actions:
                permission = Permission(action=action)
                self._session.add(permission)
        self._session.flush()

    def _ensure_permissions(self, actions: Iterable[str]) -> Iterable[Permission]:
        if not actions:
            return []

        actions = list({action for action in actions})
        self.ensure_baseline_permissions(actions)

        stmt = select(Permission).where(Permission.action.in_(actions))
        return self._session.scalars(stmt).all()

    def _get_role(self, role_id: UUID) -> Role:
        role = self._session.get(Role, role_id)
        if not role:
            raise RoleNotFoundError(f"Role {role_id} not found")
        return role

    @staticmethod
    def _normalize_datetime(value: Optional[datetime], allow_none: bool = False) -> Optional[datetime]:
        if value is None:
            return None if allow_none else datetime.now(timezone.utc)
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
