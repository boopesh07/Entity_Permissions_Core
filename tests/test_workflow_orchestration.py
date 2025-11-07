from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.models.platform_event import DeliveryState, PlatformEvent
from app.workflow_orchestration.config import TemporalConfig
from app.workflow_orchestration.orchestrator import WorkflowOrchestrator
from app.workflow_orchestration.workflows import EntityCascadeArchiveWorkflow


class StubStarter:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def start_workflow(self, *, workflow_class, workflow_id, args):
        self.calls.append({"workflow_class": workflow_class, "workflow_id": workflow_id, "args": args})
        return workflow_id


def _build_event(event_type: str) -> PlatformEvent:
    return PlatformEvent(
        id=uuid4(),
        event_id=str(uuid4()),
        event_type=event_type,
        source="test-suite",
        occurred_at=datetime.now(timezone.utc),
        correlation_id=None,
        schema_version="v1",
        payload={"entity_id": "123"},
        context={},
        delivery_state=DeliveryState.SUCCEEDED,
        delivery_attempts=1,
        last_error=None,
    )


def test_orchestrator_starts_workflow_when_enabled(monkeypatch) -> None:
    starter = StubStarter()
    config = TemporalConfig(
        host="localhost:7233",
        namespace="test",
        api_key="dummy",
        task_queue="unit-tests",
        tls_enabled=False,
    )
    orchestrator = WorkflowOrchestrator(starter=starter, config=config)

    orchestrator.handle_event(_build_event("entity.archived"))

    assert len(starter.calls) == 1
    call = starter.calls[0]
    assert call["workflow_class"] is EntityCascadeArchiveWorkflow
    assert call["args"] == ({"entity_id": "123"},)


def test_orchestrator_skips_when_temporal_disabled() -> None:
    starter = StubStarter()
    disabled_config = TemporalConfig(
        host=None,
        namespace=None,
        api_key=None,
        task_queue="unused",
        tls_enabled=True,
    )
    orchestrator = WorkflowOrchestrator(starter=starter, config=disabled_config)
    orchestrator.handle_event(_build_event("entity.archived"))
    assert starter.calls == []
