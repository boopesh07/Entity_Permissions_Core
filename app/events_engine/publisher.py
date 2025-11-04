"""Publishers responsible for delivering events to external transports."""

from __future__ import annotations

import json
import logging
from typing import Protocol

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.events_engine.schemas import EventEnvelope

LOGGER = logging.getLogger("app.events_engine.publisher")


class EventPublisher(Protocol):
    """Transport abstraction for event delivery."""

    def publish(self, envelope: EventEnvelope) -> None:
        ...


class NullEventPublisher(EventPublisher):
    """No-op publisher used when the engine is disabled."""

    def publish(self, envelope: EventEnvelope) -> None:  # noqa: D401
        LOGGER.debug(
            "events_engine_publish_skipped",
            extra={"event_id": str(envelope.event_id), "event_type": envelope.event_type},
        )


class SnsEventPublisher(EventPublisher):
    """Publishes events to an AWS SNS topic."""

    def __init__(self, *, topic_arn: str, region_name: str) -> None:
        self._topic_arn = topic_arn
        self._client = boto3.client("sns", region_name=region_name)

    def publish(self, envelope: EventEnvelope) -> None:
        message = json.dumps(envelope.model_dump(mode="json"))
        try:
            self._client.publish(
                TopicArn=self._topic_arn,
                Message=message,
                MessageAttributes={
                    "event_type": {
                        "DataType": "String",
                        "StringValue": envelope.event_type,
                    }
                },
            )
        except (BotoCoreError, ClientError) as exc:  # pragma: no cover - rely on logging/alerts
            LOGGER.exception(
                "events_engine_publish_failed",
                extra={
                    "event_id": str(envelope.event_id),
                    "event_type": envelope.event_type,
                    "topic_arn": self._topic_arn,
                },
            )
            raise exc
