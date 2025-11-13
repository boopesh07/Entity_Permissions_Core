"""Document verification workflow."""

from __future__ import annotations

from datetime import timedelta
from typing import Any, Dict

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from app.workflow_orchestration import tokenization_activities


@workflow.defn(name="document_verification")
class DocumentVerificationWorkflow:
    """
    Orchestrates automated and manual document verification.
    
    Flow:
    1. Perform automated verification (hash, format, size checks)
    2. Wait for manual approval if required
    3. Mark document as verified
    4. Trigger dependent workflows based on entity type
    """
    
    def __init__(self) -> None:
        self.manual_approval_received = False
        self.manual_approval_result = False
    
    @workflow.run
    async def run(
        self,
        document_id: str,
        entity_id: str,
        document_type: str,
        verifier_id: str = None,
    ) -> str:
        """
        Execute document verification workflow.
        
        Args:
            document_id: Document identifier
            entity_id: Associated entity ID
            document_type: Type of document
            verifier_id: ID of entity performing verification (agent, owner, etc.)
        
        Returns:
            Workflow completion status
        """
        # Use entity_id as verifier_id if not provided (fallback)
        verifier = verifier_id or entity_id
        
        # Step 1: Automated verification
        auto_verify_result = await workflow.execute_activity(
            tokenization_activities.automated_document_verification_activity,
            {
                "document_id": document_id,
                "verifier_id": verifier,
            },
            start_to_close_timeout=timedelta(minutes=10),
        )
        
        if not auto_verify_result["passed"]:
            return "verification.failed.automated"
        
        # Step 2: Manual review for sensitive document types
        # For MVP demo, we skip manual approval and auto-approve
        # In production, wait for agent approval signal
        if document_type in ["offering_memorandum", "kyc", "operating_agreement"]:
            # For demo: auto-approve
            self.manual_approval_received = True
            self.manual_approval_result = True
            
            # In production, uncomment this:
            # await workflow.wait_condition(
            #     lambda: self.manual_approval_received,
            #     timeout=timedelta(days=3),
            # )
            # if not self.manual_approval_result:
            #     return "verification.failed.manual"
        
        # Step 3: Mark document as verified
        await workflow.execute_activity(
            tokenization_activities.mark_document_verified_activity,
            {"document_id": document_id},
            start_to_close_timeout=timedelta(minutes=2),
        )
        
        # Step 4: Trigger dependent workflows
        if entity_id:
            await workflow.execute_activity(
                tokenization_activities.trigger_entity_workflow_activity,
                {
                    "entity_id": entity_id,
                    "event": "documents_verified",
                },
                start_to_close_timeout=timedelta(minutes=1),
            )
        
        return "verification.completed"
    
    @workflow.signal
    async def manual_approval_signal(self, approved: bool) -> None:
        """
        Signal manual approval decision.
        
        Args:
            approved: Whether document is approved
        """
        self.manual_approval_received = True
        self.manual_approval_result = approved


