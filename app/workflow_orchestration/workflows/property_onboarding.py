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
    1. Check if property documents are verified
    2. If not verified, wait for document.verified signal (with timeout)
    3. Create smart contract on blockchain
    4. Mint tokens for the property
    5. Activate property (make available to investors)
    6. Publish property.activated event
    """
    
    def __init__(self) -> None:
        self.documents_verified = False
        self.verification_result: Dict[str, Any] = {}
    
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
        # Step 1: Check if property documents are already verified
        initial_check = await workflow.execute_activity(
            tokenization_activities.verify_property_documents_activity,
            {"property_id": property_id},
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=RetryPolicy(
                maximum_attempts=3,
                initial_interval=timedelta(seconds=10),
            ),
        )
        
        if not initial_check["approved"]:
            # Documents not verified yet - wait for signal
            workflow.logger.info(
                f"Property {property_id} documents not verified. Waiting for document.verified signal..."
            )
            
            # Wait up to 7 days for documents to be verified
            await workflow.wait_condition(
                lambda: self.documents_verified,
                timeout=timedelta(days=7),
            )
            
            if not self.documents_verified:
                # Timeout - documents were not verified in time
                workflow.logger.error(f"Property {property_id} document verification timed out after 7 days")
                return "property.verification_timeout"
            
            # Documents verified via signal
            # If signal has incomplete property_details, fetch from database
            signal_data = self.verification_result
            
            if not signal_data.get("property_details") or not signal_data["property_details"].get("total_tokens"):
                workflow.logger.info(
                    f"Signal data incomplete, fetching property details from database for {property_id}"
                )
                # Re-fetch property details from database
                property_check = await workflow.execute_activity(
                    tokenization_activities.verify_property_documents_activity,
                    {"property_id": property_id},
                    start_to_close_timeout=timedelta(minutes=5),
                )
                verification_result = {
                    "approved": True,
                    "property_details": property_check["property_details"],
                }
            else:
                verification_result = signal_data
        else:
            # Documents already verified - proceed immediately
            verification_result = initial_check
        
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
    async def document_verified_signal(self, verification_data: Dict[str, Any]) -> None:
        """
        Signal that property documents have been verified.
        
        Args:
            verification_data: Contains property_details and approval status
        """
        workflow.logger.info(f"Received document_verified_signal with data: {verification_data}")
        self.documents_verified = True
        self.verification_result = verification_data

