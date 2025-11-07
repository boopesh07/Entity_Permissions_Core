"""Service layer for event ingestion and querying."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.events_engine import EventDispatcher, get_event_dispatcher
from app.models.platform_event import PlatformEvent
from app.schemas.event import EventIngestRequest


class EventServiceError(RuntimeError):
    """Base class for event ingestion errors."""


class EventNotFoundError(EventServiceError):
    """Raised when a requested event does not exist."""


class EventService:
    """Coordinates event ingestion, deduplication, and querying."""

    def __init__(self, session: Session, dispatcher: Optional[EventDispatcher] = None) -> None:
        self._session = session
        self._dispatcher = dispatcher or get_event_dispatcher()
        self._logger = logging.getLogger("app.events_engine.service")

    def ingest(self, request: EventIngestRequest) -> PlatformEvent:
        """Persist and publish an event, enforcing deduplication."""

        if request.correlation_id:
            existing = self._session.scalar(
                select(PlatformEvent)
                .where(PlatformEvent.source == request.source)
                .where(PlatformEvent.correlation_id == request.correlation_id)
            )
            if existing:
                self._logger.info(
                    "event_ingest_deduplicated",
                    extra={
                        "source": request.source,
                        "event_type": request.event_type,
                        "correlation_id": request.correlation_id,
                        "event_id": existing.event_id,
                    },
                )
                return existing

        occurred_at = request.occurred_at or datetime.now(timezone.utc)
        try:
            record = self._dispatcher.publish_event(
                self._session,
                event_type=request.event_type,
                payload=request.payload,
                source=request.source,
                correlation_id=request.correlation_id,
                occurred_at=occurred_at,
                schema_version=request.schema_version,
                metadata=request.context,
            )
        except Exception as exc:  # noqa: BLE001
            self._logger.exception(
                "event_ingest_failed",
                extra={"event_type": request.event_type, "source": request.source},
            )
            raise EventServiceError("Failed to publish event") from exc

        self._logger.info(
            "event_ingest_success",
            extra={
                "event_id": record.event_id,
                "event_type": record.event_type,
                "source": record.source,
            },
        )

        try:
            from app.workflow_orchestration import get_workflow_orchestrator

            orchestrator = get_workflow_orchestrator()
            orchestrator.handle_event(record)
        except Exception:  # noqa: BLE001
            self._logger.exception(
                "event_workflow_dispatch_failed",
                extra={"event_id": record.event_id, "event_type": record.event_type},
            )

        return record

    def list_events(
        self,
        *,
        event_type: Optional[str] = None,
        source: Optional[str] = None,
        limit: int = 50,
    ) -> List[PlatformEvent]:
        stmt = select(PlatformEvent).order_by(PlatformEvent.occurred_at.desc()).limit(limit)
        if event_type:
            stmt = stmt.where(PlatformEvent.event_type == event_type)
        if source:
            stmt = stmt.where(PlatformEvent.source == source)
        return list(self._session.scalars(stmt))

    def get_event(self, event_id: str) -> PlatformEvent:
        record = self._session.scalar(select(PlatformEvent).where(PlatformEvent.event_id == event_id))
        if not record:
            raise EventNotFoundError(f"Event {event_id} not found")
        return record
