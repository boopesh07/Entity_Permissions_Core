"""Role assignment endpoints."""

from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Response, status

from app.api.dependencies import get_role_service
from app.models.role_assignment import RoleAssignment
from app.schemas.assignment import RoleAssignmentCreate, RoleAssignmentResponse
from app.services.roles import RoleService

router = APIRouter()


@router.post(
    "",
    response_model=RoleAssignmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def assign_role(
    payload: RoleAssignmentCreate,
    service: RoleService = Depends(get_role_service),
    x_actor_id: Optional[UUID] = Header(default=None, alias="X-Actor-Id"),
) -> RoleAssignmentResponse:
    assignment = service.assign_role(payload, actor_id=x_actor_id)
    return _to_assignment_response(assignment)


@router.get(
    "",
    response_model=List[RoleAssignmentResponse],
)
def list_assignments(
    principal_id: Optional[UUID] = Query(default=None),
    entity_id: Optional[UUID] = Query(default=None),
    service: RoleService = Depends(get_role_service),
) -> List[RoleAssignmentResponse]:
    assignments = service.list_assignments(principal_id=principal_id, entity_id=entity_id)
    return [_to_assignment_response(assignment) for assignment in assignments]


@router.delete(
    "/{assignment_id}",
    status_code=status.HTTP_200_OK,
)
def revoke_assignment(
    assignment_id: UUID,
    service: RoleService = Depends(get_role_service),
    x_actor_id: Optional[UUID] = Header(default=None, alias="X-Actor-Id"),
) -> dict[str, str]:
    service.revoke_assignment(assignment_id, actor_id=x_actor_id)
    return {"status": "revoked", "assignment_id": str(assignment_id)}


def _to_assignment_response(assignment: RoleAssignment) -> RoleAssignmentResponse:
    return RoleAssignmentResponse(
        id=assignment.id,
        principal_id=assignment.principal_id,
        principal_type=assignment.principal_type,
        role_id=assignment.role_id,
        entity_id=assignment.entity_id,
        effective_at=assignment.effective_at,
        expires_at=assignment.expires_at,
        created_at=assignment.created_at,
        updated_at=assignment.updated_at,
    )
