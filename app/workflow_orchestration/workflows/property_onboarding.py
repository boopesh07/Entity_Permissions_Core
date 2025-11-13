"""Property onboarding workflow for real estate tokenization."""

from __future__ import annotations

from datetime import timedelta
from typing import Any, Dict

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from app.workflow_orchestration import tokenization_activities


@workflow.defn(name="property_onboarding")
class PropertyOnboardingWorkflow:
    """
    Orchestrates property onboarding from document upload to token activation.
    
    Flow:
    1. Wait for property documents to be uploaded
    2. Verify property documents
    3. Create smart contract on blockchain
    4. Mint tokens for the property
    5. Activate property (make available to investors)
    6. Publish property.activated event
    """
    
    def __init__(self) -> None:
        self.documents_uploaded = False
    
    @workflow.run
    async def run(self, property_id: str, owner_id: str) -> str:
        """
        Execute property onboarding workflow.
        
        Args:
            property_id: Property entity ID
            owner_id: Property owner entity ID
        
        Returns:
            Workflow completion status
        """
        # Step 1: Verify property documents
        verification_result = await workflow.execute_activity(
            tokenization_activities.verify_property_documents_activity,
            {"property_id": property_id},
            start_to_close_timeout=timedelta(hours=24),
            retry_policy=RetryPolicy(
                maximum_attempts=3,
                initial_interval=timedelta(seconds=10),
            ),
        )
        
        if not verification_result["approved"]:
            return "property.verification_failed"
        
        # Step 2: Create smart contract
        contract_result = await workflow.execute_activity(
            tokenization_activities.create_smart_contract_activity,
            {
                "property_id": property_id,
                "owner_id": owner_id,
                "property_details": verification_result["property_details"],
            },
            start_to_close_timeout=timedelta(minutes=10),
            retry_policy=RetryPolicy(maximum_attempts=3),
        )
        
        # Step 3: Mint tokens
        mint_result = await workflow.execute_activity(
            tokenization_activities.mint_property_tokens_activity,
            {
                "property_id": property_id,
                "smart_contract_address": contract_result["contract_address"],
                "total_tokens": verification_result["property_details"]["total_tokens"],
            },
            start_to_close_timeout=timedelta(minutes=10),
            retry_policy=RetryPolicy(maximum_attempts=3),
        )
        
        # Step 4: Activate property
        await workflow.execute_activity(
            tokenization_activities.activate_property_activity,
            {"property_id": property_id, "token_data": mint_result},
            start_to_close_timeout=timedelta(minutes=5),
        )
        
        # Step 5: Publish property.activated event
        await workflow.execute_activity(
            tokenization_activities.publish_platform_event_activity,
            {
                "event_type": "property.activated",
                "payload": {
                    "property_id": property_id,
                    "owner_id": owner_id,
                    "contract_address": contract_result["contract_address"],
                    "total_tokens": verification_result["property_details"]["total_tokens"],
                },
            },
            start_to_close_timeout=timedelta(minutes=2),
        )
        
        return "property.activated"
    
    @workflow.signal
    async def documents_uploaded_signal(self) -> None:
        """Signal that property documents have been uploaded."""
        self.documents_uploaded = True

