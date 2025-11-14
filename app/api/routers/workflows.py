"""Workflow trigger endpoints."""

from __future__ import annotations

import asyncio
import logging
from typing import Dict

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.workflow_orchestration.client import get_temporal_client
from app.workflow_orchestration.config import get_temporal_config
from app.workflow_orchestration.workflows import DocumentVerificationWorkflow

router = APIRouter()
logger = logging.getLogger("app.api.workflows")


class DocumentVerificationTrigger(BaseModel):
    """Request to trigger document verification workflow."""
    
    document_id: str = Field(..., description="Document UUID")
    entity_id: str = Field(..., description="Entity ID (property, investor, etc.)")
    entity_type: str = Field(..., description="Entity type: issuer, investor, property, offering")
    document_type: str = Field(..., description="Document type: offering_memorandum, kyc_id_proof, etc.")
    verifier_id: str | None = Field(None, description="Optional: ID of entity performing verification")


@router.post(
    "/document-verification/trigger",
    response_model=Dict[str, str],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger Document Verification Workflow",
    description="Called by Document Vault service after document upload to start verification workflow",
)
async def trigger_document_verification(
    request: DocumentVerificationTrigger,
) -> Dict[str, str]:
    """
    Trigger document verification workflow.
    
    This endpoint should be called by Document Vault service immediately after
    a document is uploaded and stored.
    
    The workflow will:
    1. Perform automated verification (hash, format, size)
    2. Mark document as verified
    3. Fetch entity details
    4. Emit document.verified event (triggers property-onboarding workflow)
    
    Args:
        request: Document verification trigger request
    
    Returns:
        Workflow ID and status
    
    Raises:
        HTTPException: If workflow fails to start
    """
    config = get_temporal_config()
    
    if not config.enabled:
        logger.warning("temporal_disabled_workflow_not_started")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Temporal workflows are disabled",
        )
    
    workflow_id = f"document-verification-{request.document_id}"
    
    logger.info(
        "triggering_document_verification_workflow",
        extra={
            "workflow_id": workflow_id,
            "document_id": request.document_id,
            "entity_id": request.entity_id,
            "entity_type": request.entity_type,
            "document_type": request.document_type,
        },
    )
    
    try:
        # Get Temporal client
        client = await get_temporal_client(config)
        
        # Start workflow
        handle = await client.start_workflow(
            DocumentVerificationWorkflow.run,
            args=(
                request.document_id,
                request.entity_id,
                request.entity_type,
                request.document_type,
                request.verifier_id,
            ),
            id=workflow_id,
            task_queue=config.task_queue,
        )
        
        logger.info(
            "document_verification_workflow_started",
            extra={
                "workflow_id": workflow_id,
                "run_id": handle.first_execution_run_id,
            },
        )
        
        return {
            "workflow_id": workflow_id,
            "run_id": handle.first_execution_run_id,
            "status": "started",
            "message": "Document verification workflow started successfully",
        }
    
    except Exception as exc:
        logger.error(
            "document_verification_workflow_start_failed",
            extra={
                "workflow_id": workflow_id,
                "error": str(exc),
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start workflow: {str(exc)}",
        ) from exc


@router.get(
    "/document-verification/{workflow_id}/status",
    response_model=Dict[str, str],
    summary="Get Document Verification Workflow Status",
    description="Check the status of a running document verification workflow",
)
async def get_workflow_status(workflow_id: str) -> Dict[str, str]:
    """
    Get status of a document verification workflow.
    
    Args:
        workflow_id: Workflow ID (format: document-verification-{document_id})
    
    Returns:
        Workflow status information
    """
    config = get_temporal_config()
    
    if not config.enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Temporal workflows are disabled",
        )
    
    try:
        client = await get_temporal_client(config)
        handle = client.get_workflow_handle(workflow_id)
        
        # Try to get result (non-blocking)
        try:
            result = await asyncio.wait_for(handle.result(), timeout=0.1)
            return {
                "workflow_id": workflow_id,
                "status": "completed",
                "result": result,
            }
        except asyncio.TimeoutError:
            # Workflow still running
            return {
                "workflow_id": workflow_id,
                "status": "running",
            }
    
    except Exception as exc:
        logger.error(
            "workflow_status_check_failed",
            extra={"workflow_id": workflow_id, "error": str(exc)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get workflow status: {str(exc)}",
        ) from exc


