"""Temporal workflow for entity cascade archival."""

from __future__ import annotations

from datetime import timedelta
from typing import Any, Dict

from temporalio import workflow

from app.workflow_orchestration import activities


@workflow.defn(name="entity_cascade_archive")
class EntityCascadeArchiveWorkflow:
    """Archive downstream systems when an entity is archived."""

    @workflow.run
    async def run(self, payload: Dict[str, Any]) -> str:  # noqa: D401
        await workflow.execute_activity(
            activities.archive_documents_activity,
            payload,
            schedule_to_close_timeout=timedelta(seconds=60),
        )
        await workflow.execute_activity(
            activities.invalidate_permissions_activity,
            payload,
            schedule_to_close_timeout=timedelta(seconds=60),
        )
        return "entity.archive.completed"
