"""Temporal worker bootstrap."""

from __future__ import annotations

import asyncio
import logging

from temporalio.worker import Worker

logger = logging.getLogger(__name__)

from app.workflow_orchestration.activities import (
    archive_documents_activity,
    invalidate_permissions_activity,
    issue_receipt_activity,
)
from app.workflow_orchestration.tokenization_activities import (
    activate_property_activity,
    automated_document_verification_activity,
    create_investor_wallet_activity,
    create_smart_contract_activity,
    mark_document_verified_activity,
    mint_property_tokens_activity,
    process_payment_activity,
    publish_platform_event_activity,
    record_blockchain_transaction_activity,
    reject_investor_activity,
    transfer_tokens_activity,
    trigger_entity_workflow_activity,
    update_token_registry_activity,
    upgrade_investor_permissions_activity,
    validate_token_purchase_activity,
    verify_kyc_documents_activity,
    verify_property_documents_activity,
)
from app.workflow_orchestration.client import get_temporal_client
from app.workflow_orchestration.config import get_temporal_config
from app.workflow_orchestration.workflows import (
    DocumentVerificationWorkflow,
    DocumentVerifiedWorkflow,
    EntityCascadeArchiveWorkflow,
    InvestorOnboardingWorkflow,
    PermissionChangeWorkflow,
    PropertyOnboardingWorkflow,
    TokenPurchaseWorkflow,
)


async def run_worker() -> None:
    """Run the Temporal worker with all registered workflows and activities."""
    logger.info("=" * 80)
    logger.info("Starting Temporal Worker")
    logger.info("=" * 80)
    
    config = get_temporal_config()
    if not config.enabled:
        logger.error("Temporal service is not configured properly")
        logger.error("Please set EPR_TEMPORAL_HOST, EPR_TEMPORAL_NAMESPACE, and EPR_TEMPORAL_API_KEY")
        raise RuntimeError("Temporal service is not configured")

    logger.info(f"Connecting to Temporal Cloud: {config.host}")
    logger.info(f"Namespace: {config.namespace}")
    logger.info(f"Task Queue: {config.task_queue}")
    
    client = await get_temporal_client(config)
    logger.info("✅ Connected to Temporal Cloud successfully")
    
    workflows = [
        # Original workflows
        EntityCascadeArchiveWorkflow,
        DocumentVerifiedWorkflow,
        PermissionChangeWorkflow,
        # Tokenization workflows
        PropertyOnboardingWorkflow,
        InvestorOnboardingWorkflow,
        TokenPurchaseWorkflow,
        DocumentVerificationWorkflow,
    ]
    
    activities = [
        # Original activities
        archive_documents_activity,
        invalidate_permissions_activity,
        issue_receipt_activity,
        # Tokenization activities
        verify_property_documents_activity,
        create_smart_contract_activity,
        mint_property_tokens_activity,
        activate_property_activity,
        verify_kyc_documents_activity,
        reject_investor_activity,
        create_investor_wallet_activity,
        upgrade_investor_permissions_activity,
        validate_token_purchase_activity,
        process_payment_activity,
        transfer_tokens_activity,
        record_blockchain_transaction_activity,
        update_token_registry_activity,
        publish_platform_event_activity,
        automated_document_verification_activity,
        mark_document_verified_activity,
        trigger_entity_workflow_activity,
    ]
    
    worker = Worker(
        client,
        task_queue=config.task_queue,
        workflows=workflows,
        activities=activities,
    )
    
    logger.info(f"✅ Worker created with {len(workflows)} workflows and {len(activities)} activities")
    logger.info("=" * 80)
    logger.info("🎯 Worker is now running and ready to execute workflows!")
    logger.info("   Press Ctrl+C to stop")
    logger.info("=" * 80)
    
    await worker.run()


if __name__ == "__main__":
    asyncio.run(run_worker())
