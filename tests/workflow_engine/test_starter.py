from __future__ import annotations

import pytest

from app.workflow_engine.starter import WorkflowStarter


def test_workflow_starter_not_implemented() -> None:
    starter = WorkflowStarter()
    with pytest.raises(NotImplementedError):
        starter.start("entity.archive.cascade", payload={})
