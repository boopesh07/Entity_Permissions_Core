"""Temporal client factory."""

from __future__ import annotations

from temporalio.client import Client

from app.workflow_orchestration.config import TemporalConfig, get_temporal_config


async def get_temporal_client(config: TemporalConfig | None = None) -> Client:
    """Create a Temporal client using service configuration."""

    config = config or get_temporal_config()
    if not config.enabled:
        raise RuntimeError("Temporal service is not configured")

    return await Client.connect(
        config.host,
        namespace=config.namespace,
        api_key=config.api_key,
        tls=config.tls_enabled,
    )
