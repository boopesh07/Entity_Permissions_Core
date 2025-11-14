"""Token operations API endpoints."""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, status

from app.api.dependencies import get_session
from app.schemas.token import (
    InvestorPortfolioResponse,
    TokenDetails,
    TokenPurchaseRequest,
    TokenPurchaseResponse,
)
from app.services.tokens import TokenService
from app.workflow_orchestration.starter import WorkflowStarter
from sqlalchemy.orm import Session

router = APIRouter()


@router.get(
    "/{property_id}",
    response_model=TokenDetails,
)
async def get_token_details(
    property_id: UUID,
    session: Session = Depends(get_session),
) -> TokenDetails:
    """
    Get token details for a property.
    
    Returns information about total supply, available tokens, price, etc.
    """
    service = TokenService(session)
    token_data = await service.get_token_details(property_id)
    return TokenDetails(**token_data)


@router.post(
    "/purchase",
    response_model=TokenPurchaseResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def purchase_tokens(
    payload: TokenPurchaseRequest,
    session: Session = Depends(get_session),
    x_actor_id: Optional[UUID] = Header(default=None, alias="X-Actor-Id"),
) -> TokenPurchaseResponse:
    """
    Purchase property tokens.
    
    This starts the TokenPurchaseWorkflow which:
    1. Validates purchase eligibility
    2. Processes payment
    3. Transfers tokens on blockchain
    4. Records transaction
    5. Updates token registry
    """
    from app.workflow_orchestration.workflows.token_purchase import TokenPurchaseWorkflow
    from app.workflow_orchestration.config import get_temporal_config
    
    service = TokenService(session)
    
    # Validate purchase
    validation = await service.validate_purchase(
        payload.investor_id,
        payload.property_id,
        payload.token_quantity,
    )
    
    if not validation["valid"]:
        return TokenPurchaseResponse(
            workflow_id="N/A",
            investor_id=payload.investor_id,
            property_id=payload.property_id,
            token_quantity=payload.token_quantity,
            payment_amount=0,
            status="failed",
            message=f"Validation failed: {validation['reason']}",
        )
    
    payment_amount = validation["total_amount"]
    
    # Check if Temporal is configured
    temporal_config = get_temporal_config()
    if not temporal_config.enabled:
        return TokenPurchaseResponse(
            workflow_id="N/A",
            investor_id=payload.investor_id,
            property_id=payload.property_id,
            token_quantity=payload.token_quantity,
            payment_amount=payment_amount,
            status="skipped",
            message="Temporal workflows are disabled. Configure EPR_TEMPORAL_* variables.",
        )
    
    # Start workflow
    workflow_id = f"token-purchase-{payload.investor_id}-{payload.property_id}"
    starter = WorkflowStarter(config=temporal_config)
    
    try:
        await starter.start_workflow(
            workflow_class=TokenPurchaseWorkflow,
            workflow_id=workflow_id,
            args=(
                str(payload.investor_id),
                str(payload.property_id),
                payload.token_quantity,
                payment_amount,
                payload.payment_method,
            ),
        )
        
        return TokenPurchaseResponse(
            workflow_id=workflow_id,
            investor_id=payload.investor_id,
            property_id=payload.property_id,
            token_quantity=payload.token_quantity,
            payment_amount=payment_amount,
            status="started",
            message="Token purchase workflow started successfully",
        )
    except Exception as exc:
        return TokenPurchaseResponse(
            workflow_id=workflow_id,
            investor_id=payload.investor_id,
            property_id=payload.property_id,
            token_quantity=payload.token_quantity,
            payment_amount=payment_amount,
            status="failed",
            message=f"Failed to start workflow: {str(exc)}",
        )


@router.get(
    "/holdings/{investor_id}",
    response_model=InvestorPortfolioResponse,
)
async def get_investor_holdings(
    investor_id: UUID,
    session: Session = Depends(get_session),
) -> InvestorPortfolioResponse:
    """
    Get investor's token holdings across all properties.
    
    Returns complete portfolio with value calculations.
    """
    service = TokenService(session)
    portfolio = await service.get_investor_portfolio(investor_id)
    return InvestorPortfolioResponse(**portfolio)


@router.get(
    "/available/{property_id}",
    response_model=dict,
)
async def get_available_tokens(
    property_id: UUID,
    session: Session = Depends(get_session),
) -> dict:
    """Get number of tokens available for purchase."""
    service = TokenService(session)
    available = await service.get_available_tokens(property_id)
    return {
        "property_id": str(property_id),
        "available_tokens": available,
    }



