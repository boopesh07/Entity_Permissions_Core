"""Property management API endpoints."""

from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, status

from app.api.dependencies import get_session
from app.schemas.property import (
    PropertyCreate,
    PropertyListResponse,
    PropertyResponse,
    PropertyUpdate,
    TokenizePropertyRequest,
    TokenizePropertyResponse,
)
from app.services.properties import PropertyService
from app.workflow_orchestration.starter import WorkflowStarter
from sqlalchemy.orm import Session

router = APIRouter()


def _to_property_response(entity) -> PropertyResponse:
    """Convert entity to property response."""
    attrs = entity.attributes
    return PropertyResponse(
        id=entity.id,
        name=entity.name,
        owner_id=entity.parent_id,
        property_type=attrs.get("property_type", ""),
        address=attrs.get("address", ""),
        valuation=attrs.get("valuation", 0),
        total_tokens=attrs.get("total_tokens", 0),
        token_price=attrs.get("token_price", 0),
        available_tokens=attrs.get("available_tokens", 0),
        property_status=attrs.get("property_status", "pending"),
        smart_contract_address=attrs.get("smart_contract_address"),
        tokenization_date=attrs.get("tokenization_date"),
        minimum_investment=attrs.get("minimum_investment", 0),
        description=attrs.get("description"),
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )


@router.post(
    "",
    response_model=PropertyResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_property(
    payload: PropertyCreate,
    session: Session = Depends(get_session),
    x_actor_id: Optional[UUID] = Header(default=None, alias="X-Actor-Id"),
) -> PropertyResponse:
    """
    Create a new property listing.
    
    Creates a property entity in 'pending' status. The property becomes 'active'
    after successful tokenization via the PropertyOnboardingWorkflow.
    """
    service = PropertyService(session)
    property_entity = service.create_property(payload, actor_id=x_actor_id)
    session.commit()
    return _to_property_response(property_entity)


@router.get(
    "/{property_id}",
    response_model=PropertyResponse,
)
def get_property(
    property_id: UUID,
    session: Session = Depends(get_session),
) -> PropertyResponse:
    """Get property details by ID."""
    service = PropertyService(session)
    property_entity = service.get_property(property_id)
    return _to_property_response(property_entity)


@router.get(
    "",
    response_model=PropertyListResponse,
)
def list_properties(
    status: Optional[str] = Query(default=None, description="Filter by property status"),
    property_type: Optional[str] = Query(default=None, description="Filter by property type"),
    owner_id: Optional[UUID] = Query(default=None, description="Filter by owner ID"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=50, ge=1, le=100, description="Page size"),
    session: Session = Depends(get_session),
) -> PropertyListResponse:
    """
    List properties with optional filters.
    
    Filters:
    - status: pending, active, sold_out
    - property_type: residential, commercial, industrial
    - owner_id: Filter by property owner
    """
    service = PropertyService(session)
    
    offset = (page - 1) * page_size
    properties = service.list_properties(
        status=status,
        property_type=property_type,
        owner_id=owner_id,
        limit=page_size,
        offset=offset,
    )
    
    total = service.get_property_count(
        status=status,
        property_type=property_type,
        owner_id=owner_id,
    )
    
    return PropertyListResponse(
        properties=[_to_property_response(p) for p in properties],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.patch(
    "/{property_id}",
    response_model=PropertyResponse,
)
def update_property(
    property_id: UUID,
    payload: PropertyUpdate,
    session: Session = Depends(get_session),
    x_actor_id: Optional[UUID] = Header(default=None, alias="X-Actor-Id"),
) -> PropertyResponse:
    """Update property details."""
    service = PropertyService(session)
    property_entity = service.update_property(property_id, payload, actor_id=x_actor_id)
    session.commit()
    return _to_property_response(property_entity)


@router.post(
    "/tokenize",
    response_model=TokenizePropertyResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def tokenize_property(
    payload: TokenizePropertyRequest,
    session: Session = Depends(get_session),
    x_actor_id: Optional[UUID] = Header(default=None, alias="X-Actor-Id"),
) -> TokenizePropertyResponse:
    """
    Initiate property tokenization workflow.
    
    This starts the PropertyOnboardingWorkflow which:
    1. Verifies property documents
    2. Creates smart contract
    3. Mints tokens
    4. Activates property for investor trading
    """
    from app.workflow_orchestration.workflows.property_onboarding import PropertyOnboardingWorkflow
    from app.workflow_orchestration.config import get_temporal_config
    
    # Verify property exists
    service = PropertyService(session)
    property_entity = service.get_property(payload.property_id)
    
    # Check if Temporal is configured
    temporal_config = get_temporal_config()
    if not temporal_config.enabled:
        return TokenizePropertyResponse(
            property_id=payload.property_id,
            workflow_id="N/A",
            status="skipped",
            message="Temporal workflows are disabled. Configure EPR_TEMPORAL_* variables.",
        )
    
    # Start workflow
    workflow_id = f"property-onboarding-{payload.property_id}"
    starter = WorkflowStarter(config=temporal_config)
    
    try:
        await starter.start_workflow(
            workflow_class=PropertyOnboardingWorkflow,
            workflow_id=workflow_id,
            args=(str(payload.property_id), str(payload.owner_id)),
        )
        
        return TokenizePropertyResponse(
            property_id=payload.property_id,
            workflow_id=workflow_id,
            status="started",
            message="Property tokenization workflow started successfully",
        )
    except Exception as exc:
        return TokenizePropertyResponse(
            property_id=payload.property_id,
            workflow_id=workflow_id,
            status="failed",
            message=f"Failed to start workflow: {str(exc)}",
        )


