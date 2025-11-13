"""Token purchase workflow for real estate tokens."""

from __future__ import annotations

from datetime import timedelta
from typing import Any, Dict

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from app.workflow_orchestration import tokenization_activities


@workflow.defn(name="token_purchase")
class TokenPurchaseWorkflow:
    """
    Orchestrates token purchase from payment to blockchain recording.
    
    Flow:
    1. Validate purchase eligibility
    2. Process payment
    3. Transfer tokens on blockchain
    4. Record transaction on blockchain
    5. Update token registry
    6. Publish token.purchased event
    """
    
    @workflow.run
    async def run(
        self,
        investor_id: str,
        property_id: str,
        token_quantity: int,
        payment_amount: float,
        payment_method: str = "card",
    ) -> str:
        """
        Execute token purchase workflow.
        
        Args:
            investor_id: Investor entity ID
            property_id: Property entity ID
            token_quantity: Number of tokens to purchase
            payment_amount: Total payment amount
            payment_method: Payment method (card, bank_transfer, crypto)
        
        Returns:
            Workflow completion status
        """
        # Step 1: Validate purchase eligibility
        validation_result = await workflow.execute_activity(
            tokenization_activities.validate_token_purchase_activity,
            {
                "investor_id": investor_id,
                "property_id": property_id,
                "quantity": token_quantity,
            },
            start_to_close_timeout=timedelta(seconds=30),
        )
        
        if not validation_result["valid"]:
            return f"purchase.failed: {validation_result['reason']}"
        
        # Step 2: Process payment
        payment_result = await workflow.execute_activity(
            tokenization_activities.process_payment_activity,
            {
                "investor_id": investor_id,
                "amount": payment_amount,
                "currency": "USD",
                "payment_method": payment_method,
                "metadata": {
                    "property_id": property_id,
                    "token_quantity": token_quantity,
                },
            },
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=workflow.RetryPolicy(
                maximum_attempts=2,
                initial_interval=timedelta(seconds=5),
            ),
        )
        
        if not payment_result["success"]:
            return "payment.failed"
        
        # Step 3: Transfer tokens on blockchain
        transfer_result = await workflow.execute_activity(
            tokenization_activities.transfer_tokens_activity,
            {
                "from_address": validation_result["property_owner_wallet"],
                "to_address": validation_result["investor_wallet"],
                "property_id": property_id,
                "quantity": token_quantity,
                "payment_reference": payment_result["transaction_id"],
            },
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=workflow.RetryPolicy(maximum_attempts=3),
        )
        
        # Step 4: Record transaction on blockchain
        blockchain_result = await workflow.execute_activity(
            tokenization_activities.record_blockchain_transaction_activity,
            {
                "transaction_type": "token_purchase",
                "token_transfer": transfer_result,
                "payment_reference": payment_result["transaction_id"],
            },
            start_to_close_timeout=timedelta(minutes=2),
        )
        
        # Step 5: Update token registry
        await workflow.execute_activity(
            tokenization_activities.update_token_registry_activity,
            {
                "investor_id": investor_id,
                "property_id": property_id,
                "quantity": token_quantity,
                "transaction_hash": blockchain_result["transaction_hash"],
            },
            start_to_close_timeout=timedelta(seconds=30),
        )
        
        # Step 6: Publish token.purchased event
        await workflow.execute_activity(
            tokenization_activities.publish_platform_event_activity,
            {
                "event_type": "token.purchased",
                "payload": {
                    "investor_id": investor_id,
                    "property_id": property_id,
                    "quantity": token_quantity,
                    "amount": payment_amount,
                    "transaction_hash": blockchain_result["transaction_hash"],
                    "payment_transaction_id": payment_result["transaction_id"],
                },
            },
            start_to_close_timeout=timedelta(minutes=1),
        )
        
        return "purchase.completed"


