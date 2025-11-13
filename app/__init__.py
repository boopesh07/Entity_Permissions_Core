"""Omen Entity & Permissions Core service package."""

import warnings

warnings.filterwarnings("ignore", category=PendingDeprecationWarning)

# Note: Don't import create_app at module level to avoid pulling FastAPI
# into Temporal workflow sandbox. Import it explicitly when needed.
# from .main import create_app  # noqa: F401


def __getattr__(name):
    """Lazy import to avoid loading FastAPI in Temporal workflows."""
    if name == "create_app":
        from .main import create_app
        return create_app
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
