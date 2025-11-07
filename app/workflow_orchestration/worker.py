"""Temporal worker bootstrap."""

from __future__ import annotations

import asyncio

from temporalio.worker import Worker

from app.workflow_orchestration.activities import (
    archive_documents_activity,
    invalidate_permissions_activity,
    issue_receipt_activity,
)
from app.workflow_orchestration.client import get_temporal_client
from app.workflow_orchestration.config import get_temporal_config
from app.workflow_orchestration.workflows import (
    DocumentVerifiedWorkflow,
    EntityCascadeArchiveWorkflow,
    PermissionChangeWorkflow,
)


async def run_worker() -> None:
    config = get_temporal_config()
    if not config.enabled:
        raise RuntimeError("Temporal service is not configured")

    client = await get_temporal_client(config)
    worker = Worker(
        client,
        task_queue=config.task_queue,
        workflows=[EntityCascadeArchiveWorkflow, DocumentVerifiedWorkflow, PermissionChangeWorkflow],
        activities=[
            archive_documents_activity,
            invalidate_permissions_activity,
            issue_receipt_activity,
        ],
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(run_worker())
