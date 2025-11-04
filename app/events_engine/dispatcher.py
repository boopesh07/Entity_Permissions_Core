"""Event dispatcher that normalizes, stores, and publishes events."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Dict, Optional

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.events_engine.config import get_event_engine_config
from app.events_engine.publisher import EventPublisher, NullEventPublisher, SnsEventPublisher
from app.events_engine.schemas import EventEnvelope
from app.models.platform_event import PlatformEvent

_dispatcher: Optional["EventDispatcher"] = None

LOGGER = logging.getLogger("app.events_engine.dispatcher")


class EventDispatcher:
    """Coordinates persistence and delivery of platform events."""

    def __init__(
        self,
        *,
        publisher: EventPublisher,
        default_source: str,
    ) -> None:
        self._publisher = publisher
        self._default_source = default_source

    def publish_event(
        self,
        session: Session,
        *,
        event_type: str,
        payload: Dict[str, object],
        source: Optional[str] = None,
        correlation_id: Optional[str] = None,
        occurred_at: Optional[datetime] = None,
        schema_version: str = "v1",
        metadata: Optional[Dict[str, object]] = None,
    ) -> PlatformEvent:
        """Persist an event record and emit it through the configured publisher."""

        envelope = EventEnvelope(
            event_type=event_type,
            payload=payload,
            source=source or self._default_source,
            correlation_id=correlation_id,
            occurred_at=occurred_at or datetime.now(timezone.utc),
            schema_version=schema_version,
            metadata=metadata or {},
        )

        record = PlatformEvent(
            event_id=str(envelope.event_id),
            event_type=envelope.event_type,
            source=envelope.source,
            occurred_at=envelope.occurred_at,
            correlation_id=envelope.correlation_id,
            schema_version=envelope.schema_version,
            payload=envelope.payload,
            context=envelope.metadata,
        )
        session.add(record)
        session.flush()

        self._publisher.publish(envelope)

        LOGGER.info(
            "events_engine_published",
            extra={
                "event_id": str(envelope.event_id),
                "event_type": envelope.event_type,
                "source": envelope.source,
            },
        )
        return record


def get_event_dispatcher() -> EventDispatcher:
    """Return the singleton event dispatcher for the application."""

    global _dispatcher
    if _dispatcher is not None:
        return _dispatcher

    settings = get_settings()
    config = get_event_engine_config(settings)

    if config.topic_arn:
        import os

        region = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "us-east-1"
        publisher: EventPublisher = SnsEventPublisher(topic_arn=config.topic_arn, region_name=region)
    else:
        publisher = NullEventPublisher()

    _dispatcher = EventDispatcher(publisher=publisher, default_source=config.source)
    return _dispatcher


def set_event_dispatcher(dispatcher: Optional[EventDispatcher]) -> None:
    """Override the cached dispatcher (primarily for tests)."""

    global _dispatcher
    _dispatcher = dispatcher
