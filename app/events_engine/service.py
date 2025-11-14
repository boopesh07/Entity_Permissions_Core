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
        
        # Send signal to waiting workflows for document.verified events
        if record.event_type == "document.verified":
            try:
                import asyncio
                from app.workflow_orchestration.signal_sender import get_signal_sender
                
                entity_id = record.payload.get("entity_id")
                entity_type = record.payload.get("entity_type")
                
                if entity_id and entity_type:
                    signal_sender = get_signal_sender()
                    
                    verification_data = {
                        "approved": True,
                        "property_details": record.payload.get("property_details", {}),
                        "documents": record.payload.get("documents", []),
                    }
                    
                    # Run async signal sending synchronously
                    loop = None
                    try:
                        loop = asyncio.get_event_loop()
                    except RuntimeError:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                    
                    # Execute signal sending and wait for completion
                    success = loop.run_until_complete(
                        signal_sender.send_document_verified_signal(
                            entity_id=entity_id,
                            entity_type=entity_type,
                            verification_data=verification_data,
                        )
                    )
                    
                    if success:
                        self._logger.info(
                            "document_verified_signal_sent_success",
                            extra={
                                "entity_id": entity_id,
                                "entity_type": entity_type,
                                "event_id": record.event_id,
                            },
                        )
                    else:
                        self._logger.warning(
                            "document_verified_signal_send_failed",
                            extra={
                                "entity_id": entity_id,
                                "entity_type": entity_type,
                                "event_id": record.event_id,
                            },
                        )
            except Exception:  # noqa: BLE001
                self._logger.exception(
                    "document_verified_signal_dispatch_failed",
                    extra={"event_id": record.event_id},
                )
        
        # Handle property.activated events to update entity status
        if record.event_type == "property.activated":
            try:
                from app.services.entities import EntityService
                from app.services.audit import AuditService
                from uuid import UUID
                
                property_id = record.payload.get("property_id")
                
                if property_id:
                    # Update property status to tokenized
                    entity_service = EntityService(self._session)
                    entity = entity_service.get_entity(UUID(property_id))
                    
                    if entity:
                        # Update attributes
                        entity.attributes["property_status"] = "tokenized"
                        entity.attributes["tokenized_at"] = record.occurred_at.isoformat()
                        entity.attributes["contract_address"] = record.payload.get("contract_address")
                        entity.attributes["total_tokens"] = record.payload.get("total_tokens")
                        
                        self._session.add(entity)
                        self._session.flush()
                        
                        # Create audit log
                        audit_service = AuditService(self._session)
                        audit_service.create_audit_log(
                            action="property.tokenized",
                            entity_id=UUID(property_id),
                            entity_type="property",
                            actor_id=record.payload.get("owner_id"),
                            changes={
                                "property_status": {"old": "pending", "new": "tokenized"},
                                "contract_address": record.payload.get("contract_address"),
                                "total_tokens": record.payload.get("total_tokens"),
                            },
                            metadata={
                                "workflow_event_id": record.event_id,
                                "tokenized_at": record.occurred_at.isoformat(),
                            },
                        )
                        
                        self._session.commit()
                        
                        self._logger.info(
                            "property_status_updated_to_tokenized",
                            extra={
                                "property_id": property_id,
                                "event_id": record.event_id,
                            },
                        )
            except Exception:  # noqa: BLE001
                self._logger.exception(
                    "property_activated_handler_failed",
                    extra={"event_id": record.event_id},
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
