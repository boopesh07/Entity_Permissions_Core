"""Workflow triggered when a document is verified."""

from __future__ import annotations

from datetime import timedelta
from typing import Any, Dict

from temporalio import workflow

from app.workflow_orchestration import activities


@workflow.defn(name="document_verified_to_receipt")
class DocumentVerifiedWorkflow:
    """Simulate receipt issuance once a document has been verified."""

    @workflow.run
    async def run(self, payload: Dict[str, Any]) -> str:  # noqa: D401
        await workflow.execute_activity(
            activities.issue_receipt_activity,
            payload,
            schedule_to_close_timeout=timedelta(seconds=60),
        )
        return "receipt.issued"
