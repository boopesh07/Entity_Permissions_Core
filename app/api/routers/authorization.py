"""Authorization API endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.dependencies import get_authorization_service
from app.schemas.authorization import AuthorizationRequest, AuthorizationResponse
from app.services.authorization import AuthorizationService

router = APIRouter()


@router.post(
    "/authorize",
    response_model=AuthorizationResponse,
)
def authorize(
    payload: AuthorizationRequest,
    service: AuthorizationService = Depends(get_authorization_service),
) -> AuthorizationResponse:
    authorized = service.authorize(payload)
    return AuthorizationResponse(authorized=authorized)
