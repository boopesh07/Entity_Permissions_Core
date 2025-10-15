"""Entity HTTP endpoints."""

from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, status

from app.api.dependencies import get_entity_service
from app.models.entity import EntityType
from app.schemas.entity import EntityCreate, EntityResponse, EntityUpdate
from app.services.entities import EntityService

router = APIRouter()


@router.post(
    "",
    response_model=EntityResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_entity(
    payload: EntityCreate,
    service: EntityService = Depends(get_entity_service),
    x_actor_id: Optional[UUID] = Header(default=None, alias="X-Actor-Id"),
) -> EntityResponse:
    entity = service.create_entity(payload, actor_id=x_actor_id)
    return EntityResponse.model_validate(entity, from_attributes=True)


@router.get(
    "/{entity_id}",
    response_model=EntityResponse,
)
def get_entity(
    entity_id: UUID,
    service: EntityService = Depends(get_entity_service),
) -> EntityResponse:
    entity = service.get(entity_id)
    return EntityResponse.model_validate(entity, from_attributes=True)


@router.get(
    "",
    response_model=List[EntityResponse],
)
def list_entities(
    entity_types: Optional[List[EntityType]] = Query(default=None, alias="type"),
    parent_id: Optional[UUID] = Query(default=None),
    service: EntityService = Depends(get_entity_service),
) -> List[EntityResponse]:
    entities = service.list(
        types=[entity_type.value for entity_type in entity_types] if entity_types else None,
        parent_id=parent_id,
    )
    return [EntityResponse.model_validate(entity, from_attributes=True) for entity in entities]


@router.patch(
    "/{entity_id}",
    response_model=EntityResponse,
)
def update_entity(
    entity_id: UUID,
    payload: EntityUpdate,
    service: EntityService = Depends(get_entity_service),
    x_actor_id: Optional[UUID] = Header(default=None, alias="X-Actor-Id"),
) -> EntityResponse:
    entity = service.update(entity_id, payload, actor_id=x_actor_id)
    return EntityResponse.model_validate(entity, from_attributes=True)


@router.post(
    "/{entity_id}/archive",
    response_model=EntityResponse,
)
def archive_entity(
    entity_id: UUID,
    service: EntityService = Depends(get_entity_service),
    x_actor_id: Optional[UUID] = Header(default=None, alias="X-Actor-Id"),
) -> EntityResponse:
    entity = service.archive(entity_id, actor_id=x_actor_id)
    return EntityResponse.model_validate(entity, from_attributes=True)
