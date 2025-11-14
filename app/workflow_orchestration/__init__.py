"""Workflow orchestration module."""

# Note: Don't import orchestrator at module level to avoid pulling SQLAlchemy
# models into Temporal workflow sandbox. Import it explicitly when needed.


def __getattr__(name):
    """Lazy import to avoid loading SQLAlchemy in Temporal workflows."""
    if name == "get_workflow_orchestrator":
        from app.workflow_orchestration.orchestrator import get_workflow_orchestrator
        return get_workflow_orchestrator
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["get_workflow_orchestrator"]
