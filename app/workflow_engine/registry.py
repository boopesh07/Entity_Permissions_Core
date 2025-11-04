"""Minimal workflow registry placeholder for upcoming Temporal integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class WorkflowDefinition:
    """Describes a workflow entry point."""

    name: str
    description: str


class WorkflowRegistry:
    """In-memory catalog for registered workflows (stub implementation)."""

    def __init__(self) -> None:
        self._workflows: Dict[str, WorkflowDefinition] = {}

    def register(self, workflow: WorkflowDefinition) -> None:
        self._workflows[workflow.name] = workflow

    def get(self, name: str) -> Optional[WorkflowDefinition]:
        return self._workflows.get(name)

    def all(self) -> Dict[str, WorkflowDefinition]:
        return dict(self._workflows)
