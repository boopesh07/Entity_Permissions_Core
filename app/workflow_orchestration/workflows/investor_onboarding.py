"""Investor onboarding workflow with KYC verification."""

from __future__ import annotations

from datetime import timedelta
from typing import Any, Dict

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from app.workflow_orchestration import tokenization_activities


@workflow.defn(name="investor_onboarding")
class InvestorOnboardingWorkflow:
    """
    Orchestrates investor onboarding from KYC submission to activation.
    
    Flow:
    1. Wait for KYC documents to be uploaded
    2. Verify KYC documents
    3. Create blockchain wallet for investor
    4. Upgrade investor permissions (Pending → Active)
    5. Publish investor.activated event
    """
    
    def __init__(self) -> None:
        self.kyc_documents_uploaded = False
    
    @workflow.run
    async def run(self, investor_id: str) -> str:
        """
        Execute investor onboarding workflow.
        
        Args:
            investor_id: Investor entity ID
        
        Returns:
            Workflow completion status
        """
        # Step 1: Verify KYC documents
        kyc_result = await workflow.execute_activity(
            tokenization_activities.verify_kyc_documents_activity,
            {"investor_id": investor_id},
            start_to_close_timeout=timedelta(hours=48),
            retry_policy=workflow.RetryPolicy(
                maximum_attempts=3,
                initial_interval=timedelta(minutes=1),
            ),
        )
        
        if not kyc_result["approved"]:
            # Reject investor
            await workflow.execute_activity(
                tokenization_activities.reject_investor_activity,
                {
                    "investor_id": investor_id,
                    "reason": kyc_result.get("rejection_reason", "KYC verification failed"),
                },
                start_to_close_timeout=timedelta(minutes=5),
            )
            return "investor.rejected"
        
        # Step 2: Create blockchain wallet
        wallet_result = await workflow.execute_activity(
            tokenization_activities.create_investor_wallet_activity,
            {"investor_id": investor_id},
            start_to_close_timeout=timedelta(minutes=10),
            retry_policy=workflow.RetryPolicy(maximum_attempts=3),
        )
        
        # Step 3: Upgrade investor permissions
        await workflow.execute_activity(
            tokenization_activities.upgrade_investor_permissions_activity,
            {
                "investor_id": investor_id,
                "wallet_address": wallet_result["wallet_address"],
            },
            start_to_close_timeout=timedelta(minutes=5),
        )
        
        # Step 4: Publish investor.activated event
        await workflow.execute_activity(
            tokenization_activities.publish_platform_event_activity,
            {
                "event_type": "investor.activated",
                "payload": {
                    "investor_id": investor_id,
                    "wallet_address": wallet_result["wallet_address"],
                    "kyc_level": kyc_result.get("kyc_level", "full"),
                },
            },
            start_to_close_timeout=timedelta(minutes=2),
        )
        
        return "investor.activated"
    
    @workflow.signal
    async def kyc_documents_uploaded_signal(self) -> None:
        """Signal that KYC documents have been uploaded."""
        self.kyc_documents_uploaded = True


