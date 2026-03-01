"""
Consent Storage Port — Abstract Interface

SOLID: Interface Segregation — consent/auth operations are fully separated.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from context_bridge.core.models.consent import (
    AuditEntry,
    ConnectedApp,
    ConsentGrant,
    ConsentRequestInput,
    RegisterAppInput,
    ScopeAction,
)


class ConsentStoragePort(ABC):
    """Abstract port for consent, app registration, and audit persistence."""

    # ─── Connected Apps ───────────────────────────────────────

    @abstractmethod
    async def register_app(self, input_data: RegisterAppInput) -> ConnectedApp:
        ...

    @abstractmethod
    async def get_app(self, app_id: UUID) -> ConnectedApp | None:
        ...

    @abstractmethod
    async def get_app_by_name(self, name: str) -> ConnectedApp | None:
        ...

    @abstractmethod
    async def list_apps(self) -> list[ConnectedApp]:
        ...

    @abstractmethod
    async def deactivate_app(self, app_id: UUID) -> bool:
        ...

    # ─── Consent Grants ───────────────────────────────────────

    @abstractmethod
    async def create_grant(self, user_id: UUID, input_data: ConsentRequestInput) -> ConsentGrant:
        ...

    @abstractmethod
    async def get_grant(self, grant_id: UUID) -> ConsentGrant | None:
        ...

    @abstractmethod
    async def get_grant_by_app(self, user_id: UUID, app_id: UUID) -> ConsentGrant | None:
        ...

    @abstractmethod
    async def revoke_grant(self, grant_id: UUID) -> bool:
        ...

    @abstractmethod
    async def list_grants(self, user_id: UUID) -> list[ConsentGrant]:
        ...

    # ─── Audit Trail ──────────────────────────────────────────

    @abstractmethod
    async def log_access(
        self,
        user_id: UUID,
        app_id: UUID,
        action: ScopeAction,
        categories: list[str],
        fact_count: int,
        detail: str | None = None,
    ) -> AuditEntry:
        ...

    @abstractmethod
    async def get_audit_log(self, user_id: UUID, limit: int = 50) -> list[AuditEntry]:
        ...
