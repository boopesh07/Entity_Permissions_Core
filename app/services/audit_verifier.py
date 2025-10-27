"""Utilities for verifying the audit log hash chain."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.services.audit import (
    GENESIS_HASH,
    canonicalize_audit_entry_payload,
    compute_audit_entry_hash,
)


class AuditVerificationError(RuntimeError):
    """Raised when audit chain verification fails."""


@dataclass
class VerificationResult:
    """Result metadata returned after verification."""

    checked: int
    start_sequence: int
    end_sequence: int


class AuditVerifier:
    """Recomputes audit hashes to detect tampering or reordering."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def verify(
        self,
        *,
        start_sequence: int | None = None,
        end_sequence: int | None = None,
    ) -> VerificationResult:
        query = select(AuditLog).order_by(AuditLog.sequence.asc())
        if start_sequence is not None:
            query = query.where(AuditLog.sequence >= start_sequence)
        if end_sequence is not None:
            query = query.where(AuditLog.sequence <= end_sequence)

        entries = list(self._session.execute(query).scalars())
        if not entries:
            return VerificationResult(checked=0, start_sequence=start_sequence or 0, end_sequence=end_sequence or 0)

        previous_hash = GENESIS_HASH
        previous_sequence = entries[0].sequence - 1

        if start_sequence and start_sequence > 1:
            previous_entry = self._session.scalar(
                select(AuditLog).where(AuditLog.sequence == start_sequence - 1)
            )
            if not previous_entry:
                raise AuditVerificationError(f"Missing audit entry for sequence {start_sequence - 1}")
            previous_hash = previous_entry.entry_hash
            previous_sequence = start_sequence - 1

        checked = 0
        for entry in entries:
            expected = previous_sequence + 1
            if entry.sequence != expected:
                raise AuditVerificationError(
                    f"Sequence gap detected. Expected {expected}, found {entry.sequence}"
                )

            canonical_payload = canonicalize_audit_entry_payload(
                sequence=entry.sequence,
                hash_version=entry.hash_version,
                event_id=entry.event_id,
                source=entry.source,
                action=entry.action,
                actor_id=entry.actor_id,
                actor_type=entry.actor_type,
                entity_id=entry.entity_id,
                entity_type=entry.entity_type,
                correlation_id=entry.correlation_id,
                details=entry.details,
                occurred_at=entry.occurred_at,
                previous_hash=previous_hash,
            )

            expected_hash = compute_audit_entry_hash(previous_hash, canonical_payload)

            if entry.previous_hash != previous_hash or entry.entry_hash != expected_hash:
                raise AuditVerificationError(
                    f"Hash mismatch at sequence {entry.sequence}: expected {expected_hash}, stored {entry.entry_hash}"
                )

            previous_hash = entry.entry_hash
            previous_sequence = entry.sequence
            checked += 1

        return VerificationResult(
            checked=checked,
            start_sequence=entries[0].sequence,
            end_sequence=entries[-1].sequence,
        )
