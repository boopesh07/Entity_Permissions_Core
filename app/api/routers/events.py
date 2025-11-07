"""Event ingestion and query endpoints."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import get_event_service
from app.events_engine.service import EventService
from app.schemas.event import EventIngestRequest, EventResponse

router = APIRouter()


@router.post(
    "",
    response_model=EventResponse,
    status_code=status.HTTP_201_CREATED,
)
def ingest_event(
    payload: EventIngestRequest,
    service: EventService = Depends(get_event_service),
) -> EventResponse:
    record = service.ingest(payload)
    return EventResponse.model_validate(record, from_attributes=True)


@router.get(
    "",
    response_model=List[EventResponse],
)
def list_events(
    event_type: Optional[str] = Query(default=None, max_length=128),
    source: Optional[str] = Query(default=None, max_length=128),
    limit: int = Query(default=50, ge=1, le=200),
    service: EventService = Depends(get_event_service),
) -> List[EventResponse]:
    records = service.list_events(event_type=event_type, source=source, limit=limit)
    return [EventResponse.model_validate(record, from_attributes=True) for record in records]


@router.get(
    "/{event_id}",
    response_model=EventResponse,
)
def get_event(
    event_id: str,
    service: EventService = Depends(get_event_service),
) -> EventResponse:
    record = service.get_event(event_id)
    return EventResponse.model_validate(record, from_attributes=True)
