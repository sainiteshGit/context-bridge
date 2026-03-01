"""
Dependency Injection Container.

Wires up storage adapters, services, and broker based on config.
FastAPI's Depends() system uses these factories.

SOLID:
  - DIP: selects concrete adapter at runtime based on config
  - OCP: adding a new backend = adding one elif branch
"""

from __future__ import annotations

from functools import lru_cache

from context_bridge.config import Settings, StorageBackend, get_settings
from context_bridge.core.ports.consent_storage import ConsentStoragePort
from context_bridge.core.ports.context_storage import ContextStoragePort
from context_bridge.core.ports.user_storage import UserStoragePort
from context_bridge.core.services.consent_service import ConsentService
from context_bridge.core.services.context_service import ContextService
from context_bridge.core.services.user_service import UserService
from context_bridge.broker.context_broker import ContextBroker
from context_bridge.protocol.token_service import TokenService


# ─── Singletons (module-level) ───────────────────────────────

_context_storage: ContextStoragePort | None = None
_user_storage: UserStoragePort | None = None
_consent_storage: ConsentStoragePort | None = None


def _build_storage(settings: Settings) -> tuple[ContextStoragePort, UserStoragePort, ConsentStoragePort]:
    """Instantiate storage adapters based on config."""
    if settings.storage_backend == StorageBackend.COSMOSDB:
        from context_bridge.adapters.cosmosdb import (
            CosmosConsentStorage,
            CosmosContextStorage,
            CosmosUserStorage,
        )
        from context_bridge.adapters.cosmosdb.client import CosmosClientFactory

        factory = CosmosClientFactory(
            endpoint=settings.cosmos_endpoint,
            key=settings.cosmos_key if not settings.cosmos_use_aad else None,
            database_name=settings.cosmos_database,
        )
        return (
            CosmosContextStorage(factory),
            CosmosUserStorage(factory),
            CosmosConsentStorage(factory),
        )
    else:
        from context_bridge.adapters.memory import (
            InMemoryConsentStorage,
            InMemoryContextStorage,
            InMemoryUserStorage,
        )
        return (
            InMemoryContextStorage(),
            InMemoryUserStorage(),
            InMemoryConsentStorage(),
        )


def init_container(settings: Settings | None = None) -> None:
    """Initialize all singletons. Called once at app startup."""
    global _context_storage, _user_storage, _consent_storage
    s = settings or get_settings()
    _context_storage, _user_storage, _consent_storage = _build_storage(s)


# ─── Dependency Factories ─────────────────────────────────────

def get_context_storage() -> ContextStoragePort:
    assert _context_storage is not None, "Container not initialized"
    return _context_storage


def get_user_storage() -> UserStoragePort:
    assert _user_storage is not None, "Container not initialized"
    return _user_storage


def get_consent_storage() -> ConsentStoragePort:
    assert _consent_storage is not None, "Container not initialized"
    return _consent_storage


def get_context_service() -> ContextService:
    return ContextService(get_context_storage())


def get_user_service() -> UserService:
    return UserService(get_user_storage())


def get_consent_service() -> ConsentService:
    s = get_settings()
    return ConsentService(
        storage=get_consent_storage(),
        secret_key=s.secret_key,
        token_expiry_seconds=s.token_expiry_seconds,
    )


def get_token_service() -> TokenService:
    s = get_settings()
    return TokenService(
        secret_key=s.secret_key,
        expiry_seconds=s.token_expiry_seconds,
    )


def get_broker() -> ContextBroker:
    return ContextBroker(
        context_service=get_context_service(),
        user_service=get_user_service(),
        consent_service=get_consent_service(),
    )
