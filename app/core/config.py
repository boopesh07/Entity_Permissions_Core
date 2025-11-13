"""Application configuration using Pydantic settings."""

from __future__ import annotations

from functools import lru_cache
from typing import List, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """Service configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="EPR_",
        extra="ignore",
    )

    environment: Literal["local", "test", "staging", "production"] = Field(
        default="local",
        validation_alias="env",
    )
    service_name: str = Field(default="omen-epr")
    database_url: str = Field(default="sqlite:///./data/epr.db")
    sql_echo: bool = Field(default=False)
    log_level: str = Field(default="INFO")
    log_json: bool = Field(default=True)
    cors_origins: List[str] | str = Field(default_factory=list)
    default_permissions: List[str] = Field(
        default_factory=lambda: [
            "document:upload",
            "document:verify",
            "document:download",
            "document:archive",
        ]
    )
    redis_url: str | None = Field(default=None)
    redis_token: str | None = Field(default=None)
    redis_cache_prefix: str = Field(default="epr")
    redis_cache_ttl: int = Field(default=300)
    document_vault_topic_arn: str | None = Field(default=None)
    document_event_source: str = Field(default="entity_permissions_core")
    event_publish_attempts: int = Field(default=2)
    temporal_host: str | None = Field(default=None)
    temporal_namespace: str | None = Field(default=None)
    temporal_api_key: str | None = Field(default=None)
    temporal_task_queue: str = Field(default="omen-workflows")
    temporal_tls_enabled: bool = Field(default=True)
    document_vault_service_url: str | None = Field(default=None)

    @field_validator("log_level")
    @classmethod
    def normalize_log_level(cls, value: str) -> str:
        return value.upper()

    @field_validator("cors_origins")
    @classmethod
    def parse_cors_origins(cls, value: str | List[str] | None) -> List[str]:
        if value is None or value == "":
            return []
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator(
        "redis_url",
        "redis_token",
        "document_vault_topic_arn",
        "temporal_host",
        "temporal_namespace",
        "temporal_api_key",
        "document_vault_service_url",
        mode="before",
    )
    @classmethod
    def empty_string_to_none(cls, value: str | None) -> str | None:
        if value == "":
            return None
        return value

    @field_validator("redis_cache_ttl", mode="before")
    @classmethod
    def ensure_int_ttl(cls, value: int | str | None) -> int | str | None:
        if value in (None, ""):
            return 300
        return value


@lru_cache
def get_settings() -> AppSettings:
    """Return cached application settings instance."""

    return AppSettings()
