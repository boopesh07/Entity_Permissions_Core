"""Utilities for starting Temporal workflows."""

from __future__ import annotations

from typing import Any, Sequence, Type

from temporalio import workflow as workflow_api

from app.workflow_orchestration.client import get_temporal_client
from app.workflow_orchestration.config import TemporalConfig, get_temporal_config


class WorkflowStarter:
    """Starts workflows using the Temporal Python SDK."""

    def __init__(self, *, config: TemporalConfig | None = None) -> None:
        self._config = config or get_temporal_config()

    async def start_workflow(
        self,
        *,
        workflow_class: Type,
        workflow_id: str,
        args: Sequence[Any],
    ) -> str:
        if not self._config.enabled:
            raise RuntimeError("Temporal service is not configured")

        client = await get_temporal_client(self._config)
        workflow_def = getattr(workflow_class, '__temporal_workflow_definition', None)
        if workflow_def and hasattr(workflow_def, 'name'):
            workflow_name = workflow_def.name
        else:
            workflow_name = workflow_class.__name__
        
        # Use start_workflow (not execute_workflow) to return immediately without waiting for result
        handle = await client.start_workflow(
            workflow_name,
            args=list(args),
            id=workflow_id,
            task_queue=self._config.task_queue,
        )
        return handle.id
