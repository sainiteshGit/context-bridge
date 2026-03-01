"""
Application Configuration — pydantic-settings.

Loads from environment variables or .env file.
Single source of truth for all configurable values.
"""

from __future__ import annotations

from enum import Enum

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class StorageBackend(str, Enum):
    MEMORY = "memory"
    COSMOSDB = "cosmosdb"


class Settings(BaseSettings):
    """All app settings loaded from env / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ─── General ──────────────────────────────────────────────
    app_name: str = "Context Bridge"
    debug: bool = False
    secret_key: str = Field(default="change-me-in-production", description="JWT signing key")
    token_expiry_seconds: int = 3600

    # ─── Storage ──────────────────────────────────────────────
    storage_backend: StorageBackend = StorageBackend.MEMORY

    # ─── Cosmos DB ────────────────────────────────────────────
    cosmos_endpoint: str = ""
    cosmos_key: str = ""
    cosmos_database: str = "context_bridge"
    cosmos_use_aad: bool = False  # use Azure AD (DefaultAzureCredential)

    # ─── CORS (browser extension) ─────────────────────────────
    cors_origins: str = "http://localhost:3000,chrome-extension://*"

    # ─── Server ───────────────────────────────────────────────
    host: str = "0.0.0.0"
    port: int = 8000
    limit_max_requests: int = 0  # 0 = unlimited; set > 0 to auto-restart after N requests

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


def get_settings() -> Settings:
    """Factory — can be overridden in tests via FastAPI dependency_overrides."""
    return Settings()
