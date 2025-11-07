"""Temporal activities used by workflows."""

from __future__ import annotations

import logging
from typing import Any, Dict

from temporalio import activity

LOGGER = logging.getLogger("app.workflow.activities")


@activity.defn(name="archive_documents_activity")
async def archive_documents_activity(payload: Dict[str, Any]) -> None:
    LOGGER.info("workflow_archive_documents", extra={"payload": payload})


@activity.defn(name="invalidate_permissions_activity")
async def invalidate_permissions_activity(payload: Dict[str, Any]) -> None:
    LOGGER.info("workflow_invalidate_permissions", extra={"payload": payload})


@activity.defn(name="issue_receipt_activity")
async def issue_receipt_activity(payload: Dict[str, Any]) -> None:
    LOGGER.info("workflow_issue_receipt", extra={"payload": payload})
