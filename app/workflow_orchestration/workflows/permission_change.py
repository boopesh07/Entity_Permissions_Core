"""Workflow for permission change cache invalidation."""

from __future__ import annotations

from datetime import timedelta
from typing import Any, Dict

from temporalio import workflow

from app.workflow_orchestration import activities


@workflow.defn(name="permission_change_cache_invalidation")
class PermissionChangeWorkflow:
    """Invalidate caches after permission mutations."""

    @workflow.run
    async def run(self, payload: Dict[str, Any]) -> str:  # noqa: D401
        await workflow.execute_activity(
            activities.invalidate_permissions_activity,
            payload,
            schedule_to_close_timeout=timedelta(seconds=30),
        )
        return "permission.cache.invalidated"
