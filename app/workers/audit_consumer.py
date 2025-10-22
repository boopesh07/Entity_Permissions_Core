"""SNS -> SQS audit ingestion worker."""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Dict, Optional

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.core.database import session_scope
from app.schemas.audit import AuditEvent
from app.services.audit import AuditService

LOGGER = logging.getLogger("app.workers.audit_consumer")


class SQSAuditConsumer:
    """Long-polling SQS consumer that persists audit events."""

    def __init__(
        self,
        *,
        queue_url: str,
        region_name: Optional[str] = None,
        wait_time_seconds: int = 20,
        visibility_timeout: Optional[int] = None,
        max_messages: int = 5,
    ) -> None:
        self._queue_url = queue_url
        self._wait_time_seconds = wait_time_seconds
        self._max_messages = max_messages
        self._sqs = boto3.client("sqs", region_name=region_name)
        self._receive_kwargs: Dict[str, Any] = {
            "QueueUrl": queue_url,
            "MaxNumberOfMessages": max_messages,
            "WaitTimeSeconds": wait_time_seconds,
            "MessageAttributeNames": ["All"],
        }
        if visibility_timeout is not None:
            self._receive_kwargs["VisibilityTimeout"] = visibility_timeout

    def run_forever(self) -> None:
        LOGGER.info("Starting SQS audit consumer", extra={"queue_url": self._queue_url})
        while True:
            try:
                messages = self._receive_messages()
            except (BotoCoreError, ClientError) as exc:
                LOGGER.exception("Failed to receive messages", extra={"error": str(exc)})
                time.sleep(5)
                continue

            if not messages:
                continue

            for message in messages:
                receipt_handle = message["ReceiptHandle"]
                try:
                    event = self._parse_message(message)
                    self._persist_event(event, message_id=message.get("MessageId"))
                except Exception as exc:  # noqa: BLE001 broad for worker resilience
                    LOGGER.exception("Failed to process audit message", extra={"error": str(exc)})
                    continue

                try:
                    self._sqs.delete_message(QueueUrl=self._queue_url, ReceiptHandle=receipt_handle)
                except (BotoCoreError, ClientError) as exc:
                    LOGGER.exception(
                        "Failed to delete processed message",
                        extra={"error": str(exc), "receipt_handle": receipt_handle},
                    )

    def _receive_messages(self) -> list[Dict[str, Any]]:
        response = self._sqs.receive_message(**self._receive_kwargs)
        return response.get("Messages", [])

    @staticmethod
    def _parse_message(message: Dict[str, Any]) -> AuditEvent:
        body = message.get("Body", "")
        payload: Dict[str, Any]
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            # Direct SQS publish with raw JSON event.
            payload = {}

        if payload and "Message" in payload:
            # SNS envelope
            inner = payload["Message"]
            if isinstance(inner, str):
                event_payload = json.loads(inner)
            else:
                event_payload = inner
        elif payload:
            event_payload = payload
        else:
            event_payload = json.loads(body)

        return AuditEvent.model_validate(event_payload)

    @staticmethod
    def _persist_event(event: AuditEvent, *, message_id: Optional[str]) -> None:
        with session_scope() as session:
            audit_service = AuditService(session)
            entry = audit_service.record_event(event)
            LOGGER.info(
                "audit_event_ingested",
                extra={
                    "sequence": entry.sequence,
                    "message_id": message_id,
                    "event_id": event.event_id,
                    "source": event.source,
                },
            )


def build_consumer_from_env() -> SQSAuditConsumer:
    """Factory that reads configuration from environment variables."""

    queue_url = os.environ["EPR_AUDIT_SQS_URL"]
    region = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION")
    max_messages = int(os.getenv("EPR_AUDIT_SQS_MAX_MESSAGES", "5"))
    wait_time = int(os.getenv("EPR_AUDIT_SQS_WAIT_TIME", "20"))
    visibility_timeout = os.getenv("EPR_AUDIT_SQS_VISIBILITY_TIMEOUT")
    visibility = int(visibility_timeout) if visibility_timeout else None

    return SQSAuditConsumer(
        queue_url=queue_url,
        region_name=region,
        max_messages=max_messages,
        wait_time_seconds=wait_time,
        visibility_timeout=visibility,
    )


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    consumer = build_consumer_from_env()
    consumer.run_forever()


if __name__ == "__main__":
    main()
