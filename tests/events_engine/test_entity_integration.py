from __future__ import annotations

from sqlalchemy import select

from app.core.database import session_scope
from app.models.entity import EntityStatus, EntityType
from app.models.platform_event import PlatformEvent
from app.schemas.entity import EntityCreate
from app.services.entities import EntityService


def test_entity_archive_emits_platform_event(event_dispatcher_stub) -> None:
    dispatcher = event_dispatcher_stub

    with session_scope() as session:
        service = EntityService(session, event_dispatcher=dispatcher)
        entity = service.create_entity(
            EntityCreate(
                name="Eventful Issuer",
                type=EntityType.ISSUER,
                attributes={"region": "NA"},
                status=EntityStatus.ACTIVE,
            ),
            actor_id=None,
        )

        service.archive(entity.id, actor_id=None)

        events = session.execute(select(PlatformEvent)).scalars().all()
        assert len(events) == 1
        event = events[0]
        assert event.event_type == "entity.archived"
        assert event.payload["entity_id"] == str(entity.id)
        assert event.payload["entity_type"] == entity.type.value

    published = dispatcher.stub_publisher.envelopes  # type: ignore[attr-defined]
    assert len(published) == 1
    assert published[0].event_type == "entity.archived"
