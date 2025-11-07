"""Workflow orchestration entrypoints."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Callable, Dict, Optional, Sequence, Type

from app.models.platform_event import PlatformEvent
from app.workflow_orchestration.config import TemporalConfig, get_temporal_config
from app.workflow_orchestration.starter import WorkflowStarter
from app.workflow_orchestration.workflows import (
    DocumentVerifiedWorkflow,
    EntityCascadeArchiveWorkflow,
    PermissionChangeWorkflow,
)

LOGGER = logging.getLogger("app.workflow.orchestrator")


@dataclass(frozen=True)
class WorkflowRoute:
    event_type: str
    workflow_class: Type
    args_builder: Callable[[PlatformEvent], Sequence[object]]


class WorkflowOrchestrator:
    """Map events to Temporal workflows and launch them."""

    def __init__(
        self,
        *,
        starter: Optional[WorkflowStarter] = None,
        config: Optional[TemporalConfig] = None,
    ) -> None:
        self._config = config or get_temporal_config()
        self._starter = starter or WorkflowStarter(config=self._config)
        self._routes: Dict[str, WorkflowRoute] = {
            "entity.archived": WorkflowRoute(
                event_type="entity.archived",
                workflow_class=EntityCascadeArchiveWorkflow,
                args_builder=lambda event: (event.payload,),
            ),
            "document.verified": WorkflowRoute(
                event_type="document.verified",
                workflow_class=DocumentVerifiedWorkflow,
                args_builder=lambda event: (event.payload,),
            ),
            "role.assignment.changed": WorkflowRoute(
                event_type="role.assignment.changed",
                workflow_class=PermissionChangeWorkflow,
                args_builder=lambda event: (event.payload,),
            ),
            "role.updated": WorkflowRoute(
                event_type="role.updated",
                workflow_class=PermissionChangeWorkflow,
                args_builder=lambda event: (event.payload,),
            ),
        }

    def handle_event(self, event: PlatformEvent) -> None:
        """Start workflows mapped to the supplied event."""

        route = self._routes.get(event.event_type)
        if not route:
            return

        if not self._config.enabled:
            LOGGER.debug(
                "workflow_skipped_temporal_disabled",
                extra={"event_type": event.event_type, "event_id": event.event_id},
            )
            return

        workflow_id = self._build_workflow_id(event, route.workflow_class)
        args = route.args_builder(event)

        try:
            asyncio.run(
                self._starter.start_workflow(
                    workflow_class=route.workflow_class,
                    workflow_id=workflow_id,
                    args=args,
                )
            )
            LOGGER.info(
                "workflow_started",
                extra={"workflow_id": workflow_id, "event_type": event.event_type},
            )
        except RuntimeError as exc:
            LOGGER.warning(
                "workflow_start_skipped",
                extra={"reason": str(exc), "event_type": event.event_type},
            )
        except Exception:  # noqa: BLE001
            LOGGER.exception(
                "workflow_start_failed",
                extra={"workflow_id": workflow_id, "event_type": event.event_type},
            )

    @staticmethod
    def _build_workflow_id(event: PlatformEvent, workflow_class: Type) -> str:
        return f"{workflow_class.__name__}-{event.event_id}"


_orchestrator: Optional[WorkflowOrchestrator] = None


def get_workflow_orchestrator() -> WorkflowOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = WorkflowOrchestrator()
    return _orchestrator
