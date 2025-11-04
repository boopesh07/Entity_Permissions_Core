"""Configuration helpers for the events engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.core.config import AppSettings, get_settings


@dataclass
class EventEngineConfig:
    """Resolved configuration values for the events engine."""

    topic_arn: Optional[str]
    source: str


def get_event_engine_config(settings: Optional[AppSettings] = None) -> EventEngineConfig:
    """Materialize events engine configuration from application settings."""

    settings = settings or get_settings()
    topic_arn = getattr(settings, "document_vault_topic_arn", None)
    source = getattr(settings, "document_event_source", "entity_permissions_core")
    return EventEngineConfig(topic_arn=topic_arn, source=source)
