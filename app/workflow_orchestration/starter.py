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
        handle = await client.start_workflow(
            workflow_class.run,
            *args,
            id=workflow_id,
            task_queue=self._config.task_queue,
        )
        return handle.id
