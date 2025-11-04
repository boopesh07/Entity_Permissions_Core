from __future__ import annotations

from sqlalchemy import select

from app.core.database import session_scope
from app.events_engine.dispatcher import EventDispatcher
from app.models.platform_event import PlatformEvent


class StubPublisher:
    def __init__(self) -> None:
        self.envelopes = []

    def publish(self, envelope):
        self.envelopes.append(envelope)


def test_dispatcher_persists_and_publishes() -> None:
    publisher = StubPublisher()
    dispatcher = EventDispatcher(publisher=publisher, default_source="test-service")

    with session_scope() as session:
        dispatcher.publish_event(
            session,
            event_type="entity.archived",
            payload={"entity_id": "123", "entity_type": "issuer"},
            schema_version="v1",
            metadata={"origin": "unit-test"},
        )

        records = session.execute(select(PlatformEvent)).scalars().all()
        assert len(records) == 1
        record = records[0]
        assert record.event_type == "entity.archived"
        assert record.payload["entity_id"] == "123"
        assert record.context["origin"] == "unit-test"

    assert len(publisher.envelopes) == 1
    published = publisher.envelopes[0]
    assert published.event_type == "entity.archived"
    assert published.payload["entity_id"] == "123"
