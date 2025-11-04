from __future__ import annotations

from app.workflow_engine.registry import WorkflowDefinition, WorkflowRegistry


def test_workflow_registry_registers_and_fetches() -> None:
    registry = WorkflowRegistry()
    workflow = WorkflowDefinition(name="entity.archive.cascade", description="Archive cascade workflow")
    registry.register(workflow)

    retrieved = registry.get("entity.archive.cascade")
    assert retrieved == workflow
    assert "entity.archive.cascade" in registry.all()
