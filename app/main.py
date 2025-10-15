"""FastAPI application factory."""

from __future__ import annotations

import sys
from contextlib import asynccontextmanager

try:
    import python_multipart  # type: ignore
except ImportError:  # pragma: no cover
    python_multipart = None  # type: ignore
else:
    sys.modules.setdefault("multipart", python_multipart)

from fastapi import FastAPI

from app.api.error_handlers import register_exception_handlers
from app.api.routers import get_api_router
from app.core.config import AppSettings, get_settings
from app.core.database import engine, session_scope
from app.core.logging import configure_logging
from app.models import Base
from app.services.roles import RoleService


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: D401
    """Application lifespan context for startup/shutdown hooks."""

    settings = get_settings()
    if settings.environment in {"local", "test"}:
        Base.metadata.create_all(bind=engine)

    with session_scope() as session:
        RoleService(session).ensure_baseline_permissions(settings.default_permissions)

    yield


def create_app(settings: AppSettings | None = None) -> FastAPI:
    """Application factory."""

    settings = settings or get_settings()
    configure_logging(settings)

    app = FastAPI(
        title="Omen Entity & Permissions Core",
        version="1.0.0",
        lifespan=lifespan,
    )

    register_exception_handlers(app)
    app.include_router(get_api_router())
    return app


app = create_app()
