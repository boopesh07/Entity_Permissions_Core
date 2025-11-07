"""Router registrations."""

from fastapi import APIRouter

from app.api.routers import assignments, authorization, entities, events, health, roles


def get_api_router() -> APIRouter:
    router = APIRouter()
    router.include_router(health.router, tags=["health"])
    router.include_router(entities.router, prefix="/api/v1/entities", tags=["entities"])
    router.include_router(roles.router, prefix="/api/v1/roles", tags=["roles"])
    router.include_router(assignments.router, prefix="/api/v1/assignments", tags=["assignments"])
    router.include_router(authorization.router, prefix="/api/v1", tags=["authorization"])
    router.include_router(events.router, prefix="/api/v1/events", tags=["events"])
    return router
