"""Reusable SQS consumer utilities for the events engine."""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Callable, Dict, Optional, Protocol

import boto3
from botocore.exceptions import BotoCoreError, ClientError

LOGGER = logging.getLogger("app.events_engine.consumer")


class EventHandler(Protocol):
    """Handler invoked for each deserialized message."""

    def __call__(self, message: Dict[str, Any]) -> None:
        ...


def unwrap_sns_envelope(message_body: str) -> Dict[str, Any]:
    """Extract the inner payload when delivered via SNS -> SQS."""

    payload = json.loads(message_body)
    if isinstance(payload, dict) and "Message" in payload:
        inner = payload["Message"]
        if isinstance(inner, str):
            return json.loads(inner)
        if isinstance(inner, dict):
            return inner
    return payload


class SQSEventConsumer:
    """Generic long-polling consumer that feeds messages to a handler."""

    def __init__(
        self,
        *,
        queue_url: str,
        handler: EventHandler,
        region_name: Optional[str] = None,
        wait_time_seconds: int = 20,
        visibility_timeout: Optional[int] = None,
        max_messages: int = 5,
    ) -> None:
        self._queue_url = queue_url
        self._handler = handler
        self._receive_kwargs: Dict[str, Any] = {
            "QueueUrl": queue_url,
            "MaxNumberOfMessages": max_messages,
            "WaitTimeSeconds": wait_time_seconds,
            "MessageAttributeNames": ["All"],
        }
        if visibility_timeout is not None:
            self._receive_kwargs["VisibilityTimeout"] = visibility_timeout
        self._sqs = boto3.client("sqs", region_name=region_name)

    def run_forever(self) -> None:
        LOGGER.info("Starting SQS consumer", extra={"queue_url": self._queue_url})
        while True:
            try:
                messages = self._receive_messages()
            except (BotoCoreError, ClientError) as exc:  # pragma: no cover - resiliency
                LOGGER.exception("Failed to receive messages", extra={"error": str(exc)})
                time.sleep(5)
                continue

            if not messages:
                continue

            for message in messages:
                receipt_handle = message["ReceiptHandle"]
                try:
                    body = message.get("Body", "")
                    payload = unwrap_sns_envelope(body)
                    self._handler(payload)
                except Exception as exc:  # noqa: BLE001 - intentionally broad for worker safety
                    LOGGER.exception("Failed to process message", extra={"error": str(exc)})
                    continue

                try:
                    self._sqs.delete_message(QueueUrl=self._queue_url, ReceiptHandle=receipt_handle)
                except (BotoCoreError, ClientError) as exc:  # pragma: no cover - resiliency
                    LOGGER.exception(
                        "Failed to delete message",
                        extra={"error": str(exc), "receipt_handle": receipt_handle},
                    )

    def _receive_messages(self) -> list[Dict[str, Any]]:
        response = self._sqs.receive_message(**self._receive_kwargs)
        return response.get("Messages", [])
