"""Audit event ingestion wired through the events engine."""

from __future__ import annotations

import logging
import os
from typing import Any, Dict

from app.core.database import session_scope
from app.events_engine.consumers.base import SQSEventConsumer
from app.schemas.audit import AuditEvent
from app.services.audit import AuditService

LOGGER = logging.getLogger("app.events_engine.consumers.audit")


def _handle_audit_message(payload: Dict[str, Any]) -> None:
    event = AuditEvent.model_validate(payload)
    with session_scope() as session:
        audit_service = AuditService(session)
        entry = audit_service.record_event(event)
        LOGGER.info(
            "audit_event_ingested",
            extra={
                "sequence": entry.sequence,
                "event_id": event.event_id,
                "source": event.source,
            },
        )


class AuditSQSEventConsumer(SQSEventConsumer):
    """SQS consumer specialized for audit events."""

    def __init__(
        self,
        *,
        queue_url: str,
        region_name: str | None = None,
        wait_time_seconds: int = 20,
        visibility_timeout: int | None = None,
        max_messages: int = 5,
    ) -> None:
        super().__init__(
            queue_url=queue_url,
            handler=_handle_audit_message,
            region_name=region_name,
            wait_time_seconds=wait_time_seconds,
            visibility_timeout=visibility_timeout,
            max_messages=max_messages,
        )


def build_audit_consumer_from_env() -> AuditSQSEventConsumer:
    """Construct an audit consumer using standard environment variables."""

    queue_url = os.environ["EPR_AUDIT_SQS_URL"]
    region = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION")
    max_messages = int(os.getenv("EPR_AUDIT_SQS_MAX_MESSAGES", "5"))
    wait_time = int(os.getenv("EPR_AUDIT_SQS_WAIT_TIME", "20"))
    visibility_timeout = os.getenv("EPR_AUDIT_SQS_VISIBILITY_TIMEOUT")
    visibility = int(visibility_timeout) if visibility_timeout else None

    return AuditSQSEventConsumer(
        queue_url=queue_url,
        region_name=region,
        max_messages=max_messages,
        wait_time_seconds=wait_time,
        visibility_timeout=visibility,
    )
