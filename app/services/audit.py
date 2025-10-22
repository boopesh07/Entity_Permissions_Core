"""Audit logging service."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.schemas.audit import AuditEvent


class AuditService:
    """Persists audit entries and mirrors them to structured logs."""

    _HASH_VERSION = 1
    _GENESIS_HASH = "0" * 64

    def __init__(self, session: Session) -> None:
        self._session = session
        self._logger = logging.getLogger("app.audit")

    def record(
        self,
        *,
        action: str,
        actor_id: Optional[UUID],
        entity_id: Optional[UUID],
        entity_type: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
        actor_type: str = "user",
        source: str = "entity_permissions_core",
        occurred_at: Optional[datetime] = None,
        event_id: Optional[UUID] = None,
    ) -> AuditLog:
        """Write an audit log entry anchored into the hash chain."""

        event = AuditEvent(
            event_id=event_id,
            source=source,
            action=action,
            actor_id=actor_id,
            actor_type=actor_type,
            entity_id=entity_id,
            entity_type=entity_type,
            details=details or {},
            correlation_id=correlation_id,
            occurred_at=occurred_at or datetime.now(timezone.utc),
        )
        return self.record_event(event)

    def record_event(self, event: AuditEvent) -> AuditLog:
        """Persist an audit entry derived from an externally supplied event."""

        event_id_str = str(event.event_id) if event.event_id else None
        if event_id_str:
            existing = self._session.scalar(select(AuditLog).where(AuditLog.event_id == event_id_str))
            if existing:
                return existing

        previous_sequence, previous_hash = self._lock_chain_tip()
        next_sequence = previous_sequence + 1

        canonical_payload = self._serialize_for_hash(
            {
                "sequence": next_sequence,
                "hash_version": self._HASH_VERSION,
                "event_id": event_id_str,
                "source": event.source,
                "action": event.action,
                "actor_id": self._optional_str(event.actor_id),
                "actor_type": event.actor_type,
                "entity_id": self._optional_str(event.entity_id),
                "entity_type": event.entity_type,
                "correlation_id": event.correlation_id,
                "details": event.details,
                "occurred_at": event.occurred_at.astimezone(timezone.utc).isoformat(),
                "previous_hash": previous_hash,
            }
        )

        entry_hash = self._compute_entry_hash(previous_hash, canonical_payload)

        audit_entry = AuditLog(
            sequence=next_sequence,
            previous_hash=previous_hash,
            entry_hash=entry_hash,
            hash_version=self._HASH_VERSION,
            event_id=event_id_str,
            source=event.source,
            occurred_at=event.occurred_at,
            actor_id=event.actor_id,
            actor_type=event.actor_type,
            entity_id=event.entity_id,
            entity_type=event.entity_type,
            action=event.action,
            correlation_id=event.correlation_id,
            details=event.details,
        )

        self._session.add(audit_entry)
        self._session.flush()

        self._logger.info(
            "audit_event",
            extra={
                "sequence": next_sequence,
                "entry_hash": entry_hash,
                "previous_hash": previous_hash,
                "action": event.action,
                "actor_id": self._optional_str(event.actor_id),
                "entity_id": self._optional_str(event.entity_id),
                "entity_type": event.entity_type,
                "source": event.source,
                "event_id": event_id_str,
            },
        )
        return audit_entry

    def _lock_chain_tip(self) -> tuple[int, str]:
        stmt = select(AuditLog.sequence, AuditLog.entry_hash).order_by(AuditLog.sequence.desc()).limit(1)
        dialect_name = self._session.get_bind().dialect.name
        if dialect_name != "sqlite":
            stmt = stmt.with_for_update(nowait=False)
        result = self._session.execute(stmt).first()
        if result is None:
            return 0, self._GENESIS_HASH
        sequence, entry_hash = result
        return int(sequence), str(entry_hash)

    @staticmethod
    def _serialize_for_hash(payload: Dict[str, Any]) -> str:
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)

    @staticmethod
    def _compute_entry_hash(previous_hash: str, canonical_payload: str) -> str:
        return hashlib.sha256((previous_hash + canonical_payload).encode("utf-8")).hexdigest()

    @staticmethod
    def _optional_str(value: Optional[UUID]) -> Optional[str]:
        return str(value) if value is not None else None
