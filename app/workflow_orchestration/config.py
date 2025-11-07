"""Temporal workflow orchestration configuration helpers."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import AppSettings, get_settings


@dataclass
class TemporalConfig:
    """Materialized Temporal connection settings."""

    host: str | None
    namespace: str | None
    api_key: str | None
    task_queue: str
    tls_enabled: bool

    @property
    def enabled(self) -> bool:
        return bool(self.host and self.namespace and self.api_key)


def get_temporal_config(settings: AppSettings | None = None) -> TemporalConfig:
    settings = settings or get_settings()
    return TemporalConfig(
        host=settings.temporal_host,
        namespace=settings.temporal_namespace,
        api_key=settings.temporal_api_key,
        task_queue=settings.temporal_task_queue,
        tls_enabled=settings.temporal_tls_enabled,
    )
