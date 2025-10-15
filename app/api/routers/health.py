"""Health check endpoints."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/healthz", summary="Liveness probe")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
