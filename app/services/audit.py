"""Audit logging service."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog, AuditStatus


class AuditService:
    """Persists audit entries and mirrors them to structured logs."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._logger = logging.getLogger("app.audit")

    def record(
        self,
        *,
        action: str,
        actor_id: Optional[UUID],
        entity_id: Optional[UUID],
        status: str = AuditStatus.SUCCESS,
        details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
        actor_type: str = "user",
    ) -> AuditLog:
        entry = AuditLog(
            actor_id=actor_id,
            actor_type=actor_type,
            entity_id=entity_id,
            action=action,
            status=status,
            details=details or {},
            correlation_id=correlation_id,
        )
        self._session.add(entry)
        self._session.flush()

        self._logger.info(
            "audit_event",
            extra={
                "action": action,
                "actor_id": str(actor_id) if actor_id else None,
                "entity_id": str(entity_id) if entity_id else None,
                "status": status,
                "correlation_id": correlation_id,
            },
        )
        return entry
