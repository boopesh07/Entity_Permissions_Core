"""Stub for workflow starter integration."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class WorkflowStarter:
    """Placeholder Temporal workflow starter."""

    registry_name: str = "default"

    def start(self, workflow_name: str, *, payload: dict) -> None:
        raise NotImplementedError(
            "Workflow engine integration is not yet implemented."
        )
