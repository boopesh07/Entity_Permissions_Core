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
    default_roles_seeded: bool = Field(default=False, repr=False)

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


@lru_cache
def get_settings() -> AppSettings:
    """Return cached application settings instance."""

    return AppSettings()
