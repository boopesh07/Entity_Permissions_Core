"""Document vault integration helpers."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Optional, Protocol
from uuid import UUID, uuid4

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import get_settings

LOGGER = logging.getLogger("app.notifications.document_vault")


class DocumentVaultPublisher(Protocol):
    """Publishes events consumed by the document vault service."""

    def publish_entity_deleted(self, *, entity_id: UUID, entity_type: str) -> None:
        ...


@dataclass
class NullDocumentVaultPublisher(DocumentVaultPublisher):
    """No-op publisher used when integration is disabled."""

    def publish_entity_deleted(self, *, entity_id: UUID, entity_type: str) -> None:  # noqa: D401
        LOGGER.debug(
            "document_vault_event_skipped",
            extra={"entity_id": str(entity_id), "entity_type": entity_type},
        )


class SnsDocumentVaultPublisher(DocumentVaultPublisher):
    """Publishes document events to an SNS topic."""

    def __init__(self, *, topic_arn: str, region: str, source: str) -> None:
        self._topic_arn = topic_arn
        self._source = source
        self._client = boto3.client("sns", region_name=region)

    def publish_entity_deleted(self, *, entity_id: UUID, entity_type: str) -> None:
        payload = {
            "event_id": str(uuid4()),
            "source": self._source,
            "action": "entity.deleted",
            "entity_id": str(entity_id),
            "entity_type": entity_type,
        }
        try:
            self._client.publish(
                TopicArn=self._topic_arn,
                Message=json.dumps(payload),
                MessageAttributes={
                    "event_type": {"DataType": "String", "StringValue": "entity.deleted"}
                },
            )
            LOGGER.info(
                "document_vault_event_published",
                extra={
                    "topic_arn": self._topic_arn,
                    "entity_id": payload["entity_id"],
                    "entity_type": entity_type,
                },
            )
        except (BotoCoreError, ClientError) as exc:  # pragma: no cover - rely on logging
            LOGGER.exception(
                "document_vault_event_failure",
                extra={"entity_id": str(entity_id), "entity_type": entity_type},
            )
            raise exc


_publisher: Optional[DocumentVaultPublisher] = None


def get_document_publisher() -> DocumentVaultPublisher:
    """Return cached document publisher instance."""

    global _publisher
    if _publisher is not None:
        return _publisher

    settings = get_settings()
    topic_arn = settings.document_vault_topic_arn
    if topic_arn:
        region = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "us-east-1"
        _publisher = SnsDocumentVaultPublisher(
            topic_arn=topic_arn,
            region=region,
            source=settings.document_event_source,
        )
    else:
        _publisher = NullDocumentVaultPublisher()
    return _publisher
