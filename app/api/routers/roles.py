"""Role management endpoints."""

from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, status

from app.api.dependencies import get_role_service
from app.models.role import Role
from app.schemas.role import RoleCreate, RoleResponse, RoleUpdate
from app.services.roles import RoleService

router = APIRouter()


@router.post(
    "",
    response_model=RoleResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_role(
    payload: RoleCreate,
    service: RoleService = Depends(get_role_service),
    x_actor_id: Optional[UUID] = Header(default=None, alias="X-Actor-Id"),
) -> RoleResponse:
    role = service.create_role(payload, actor_id=x_actor_id)
    return _to_role_response(role)


@router.get(
    "",
    response_model=List[RoleResponse],
)
def list_roles(
    service: RoleService = Depends(get_role_service),
) -> List[RoleResponse]:
    roles = service.list_roles()
    return [_to_role_response(role) for role in roles]


@router.patch(
    "/{role_id}",
    response_model=RoleResponse,
)
def update_role(
    role_id: UUID,
    payload: RoleUpdate,
    service: RoleService = Depends(get_role_service),
    x_actor_id: Optional[UUID] = Header(default=None, alias="X-Actor-Id"),
) -> RoleResponse:
    role = service.update_role(role_id, payload, actor_id=x_actor_id)
    return _to_role_response(role)


def _to_role_response(role: Role) -> RoleResponse:
    return RoleResponse(
        id=role.id,
        name=role.name,
        description=role.description,
        scope_types=role.scope_types,
        is_system=role.is_system,
        permissions=[permission.action for permission in role.permissions],
        created_at=role.created_at,
        updated_at=role.updated_at,
    )
