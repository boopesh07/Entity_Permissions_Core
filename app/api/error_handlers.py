"""Exception handlers for the FastAPI app."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.services.entities import EntityConflictError, EntityNotFoundError
from app.services.roles import (
    PermissionScopeError,
    RoleConflictError,
    RoleNotFoundError,
    RoleServiceError,
)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(EntityNotFoundError)
    async def entity_not_found_handler(request: Request, exc: EntityNotFoundError) -> JSONResponse:  # noqa: WPS430
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(RoleNotFoundError)
    async def role_not_found_handler(request: Request, exc: RoleNotFoundError) -> JSONResponse:  # noqa: WPS430
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(EntityConflictError)
    async def entity_conflict_handler(request: Request, exc: EntityConflictError) -> JSONResponse:  # noqa: WPS430
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    @app.exception_handler(RoleConflictError)
    async def role_conflict_handler(request: Request, exc: RoleConflictError) -> JSONResponse:  # noqa: WPS430
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    @app.exception_handler(PermissionScopeError)
    async def permission_scope_handler(request: Request, exc: PermissionScopeError) -> JSONResponse:  # noqa: WPS430
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    @app.exception_handler(RoleServiceError)
    async def role_service_handler(request: Request, exc: RoleServiceError) -> JSONResponse:  # noqa: WPS430
        return JSONResponse(status_code=400, content={"detail": str(exc)})
