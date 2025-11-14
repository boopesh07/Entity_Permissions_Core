"""User onboarding API endpoints."""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_session
from app.models.entity import Entity, EntityStatus, EntityType
from app.models.role import Role
from app.models.role_assignment import RoleAssignment
from app.schemas.onboarding import (
    OnboardInvestorRequest,
    OnboardingResponse,
    OnboardPropertyOwnerRequest,
)
from app.services.audit import AuditService
from app.workflow_orchestration.config import get_temporal_config
from app.workflow_orchestration.starter import WorkflowStarter

router = APIRouter()


@router.post(
    "/property-owner",
    response_model=OnboardingResponse,
    status_code=status.HTTP_201_CREATED,
)
def onboard_property_owner(
    payload: OnboardPropertyOwnerRequest,
    session: Session = Depends(get_session),
    x_actor_id: Optional[UUID] = Header(default=None, alias="X-Actor-Id"),
) -> OnboardingResponse:
    """
    Onboard a new property owner.
    
    Creates an issuer entity and assigns PropertyOwner role.
    """
    audit = AuditService(session)
    
    # Create issuer entity
    owner_entity = Entity(
        name=payload.name,
        type=EntityType.ISSUER,
        status=EntityStatus.ACTIVE,
        attributes={
            "company_name": payload.company_name,
            "contact_email": payload.contact_email,
            "phone": payload.phone or "",
            "address": payload.address or "",
            "onboarding_status": "completed",
            "kyc_status": "approved",  # Simplified for demo
            **payload.attributes,
        },
    )
    
    session.add(owner_entity)
    session.flush()
    
    # Assign PropertyOwner role
    property_owner_role = session.scalar(
        select(Role).where(Role.name == "PropertyOwner")
    )
    
    role_assigned = False
    role_id = None
    
    if property_owner_role:
        assignment = RoleAssignment(
            principal_id=owner_entity.id,
            principal_type="user",
            role_id=property_owner_role.id,
            entity_id=owner_entity.id,  # Scoped to their own entity
        )
        session.add(assignment)
        role_assigned = True
        role_id = property_owner_role.id
    
    # Record audit log
    audit.record(
        action="user.onboard",
        actor_id=x_actor_id,
        entity_id=owner_entity.id,
        entity_type=owner_entity.type.value,
        details={
            "user_type": "property_owner",
            "company_name": payload.company_name,
        },
    )
    
    session.commit()
    
    return OnboardingResponse(
        entity_id=owner_entity.id,
        name=owner_entity.name,
        entity_type=owner_entity.type.value,
        role_assigned=role_assigned,
        role_id=role_id,
        onboarding_status="completed",
        message="Property owner onboarded successfully",
    )


@router.post(
    "/investor",
    response_model=OnboardingResponse,
    status_code=status.HTTP_201_CREATED,
)
async def onboard_investor(
    payload: OnboardInvestorRequest,
    session: Session = Depends(get_session),
    x_actor_id: Optional[UUID] = Header(default=None, alias="X-Actor-Id"),
) -> OnboardingResponse:
    """
    Onboard a new investor.
    
    Creates an investor entity and assigns InvestorPending role.
    Investor must complete KYC verification before being upgraded to InvestorActive.
    
    To activate investor, start InvestorOnboardingWorkflow after KYC documents are uploaded.
    """
    audit = AuditService(session)
    
    # Create investor entity
    investor_entity = Entity(
        name=payload.name,
        type=EntityType.INVESTOR,
        status=EntityStatus.ACTIVE,
        attributes={
            "email": payload.email,
            "phone": payload.phone or "",
            "investor_type": payload.investor_type,
            "kyc_status": "pending",
            "onboarding_status": "pending",
            "token_holdings": {},
            **payload.attributes,
        },
    )
    
    session.add(investor_entity)
    session.flush()
    
    # Assign InvestorPending role
    investor_pending_role = session.scalar(
        select(Role).where(Role.name == "InvestorPending")
    )
    
    role_assigned = False
    role_id = None
    
    if investor_pending_role:
        assignment = RoleAssignment(
            principal_id=investor_entity.id,
            principal_type="user",
            role_id=investor_pending_role.id,
            entity_id=None,  # Global assignment
        )
        session.add(assignment)
        role_assigned = True
        role_id = investor_pending_role.id
    
    # Record audit log
    audit.record(
        action="user.onboard",
        actor_id=x_actor_id,
        entity_id=investor_entity.id,
        entity_type=investor_entity.type.value,
        details={
            "user_type": "investor",
            "investor_type": payload.investor_type,
        },
    )
    
    session.commit()
    
    return OnboardingResponse(
        entity_id=investor_entity.id,
        name=investor_entity.name,
        entity_type=investor_entity.type.value,
        role_assigned=role_assigned,
        role_id=role_id,
        onboarding_status="pending",
        message="Investor onboarded. Complete KYC verification to activate.",
    )


@router.post(
    "/investor/{investor_id}/activate",
    response_model=dict,
    status_code=status.HTTP_202_ACCEPTED,
)
async def activate_investor(
    investor_id: UUID,
    session: Session = Depends(get_session),
    x_actor_id: Optional[UUID] = Header(default=None, alias="X-Actor-Id"),
) -> dict:
    """
    Activate investor after KYC verification.
    
    Starts InvestorOnboardingWorkflow which verifies KYC documents,
    creates blockchain wallet, and upgrades permissions.
    """
    from app.workflow_orchestration.workflows.investor_onboarding import InvestorOnboardingWorkflow
    
    # Verify investor exists
    investor = session.get(Entity, investor_id)
    if not investor or investor.type != EntityType.INVESTOR:
        return {
            "status": "failed",
            "message": "Investor not found",
        }
    
    # Check if Temporal is configured
    temporal_config = get_temporal_config()
    if not temporal_config.enabled:
        return {
            "workflow_id": "N/A",
            "investor_id": str(investor_id),
            "status": "skipped",
            "message": "Temporal workflows are disabled. Configure EPR_TEMPORAL_* variables.",
        }
    
    # Start workflow
    workflow_id = f"investor-onboarding-{investor_id}"
    starter = WorkflowStarter(config=temporal_config)
    
    try:
        await starter.start_workflow(
            workflow_class=InvestorOnboardingWorkflow,
            workflow_id=workflow_id,
            args=(str(investor_id),),
        )
        
        return {
            "workflow_id": workflow_id,
            "investor_id": str(investor_id),
            "status": "started",
            "message": "Investor activation workflow started successfully",
        }
    except Exception as exc:
        return {
            "workflow_id": workflow_id,
            "investor_id": str(investor_id),
            "status": "failed",
            "message": f"Failed to start workflow: {str(exc)}",
        }



