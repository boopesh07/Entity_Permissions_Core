from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select

from app.events_engine.consumers.audit import _handle_audit_message
from app.models.audit_log import AuditLog


def test_audit_consumer_handler_persists_events() -> None:
    event_payload = {
        "event_id": str(uuid4()),
        "source": "issuer-service",
        "action": "issuer.created",
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "details": {"issuer": "ACME"},
    }

    _handle_audit_message(event_payload)

    from app.core.database import session_scope

    with session_scope() as session:
        entries = session.execute(select(AuditLog)).scalars().all()
        assert entries
        assert entries[-1].action == "issuer.created"
