"""FastAPI application factory."""

from __future__ import annotations

from contextlib import asynccontextmanager
import sys

import python_multipart

from fastapi import FastAPI

from app.api.error_handlers import register_exception_handlers
from app.api.routers import get_api_router
from app.core.config import AppSettings, get_settings
from app.core.database import session_scope
from app.core.logging import configure_logging
from app.services.roles import RoleService

# Starlette <0.39 still imports `multipart`; map it to python-multipart to avoid warnings.
sys.modules.setdefault("multipart", python_multipart)


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: D401
    """Application lifespan context for startup/shutdown hooks."""

    settings = get_settings()
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
