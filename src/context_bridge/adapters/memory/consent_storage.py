"""
In-Memory Storage Adapter — Consent, Apps & Audit

Implements ConsentStoragePort using plain dictionaries.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID, uuid4

from context_bridge.core.models.consent import (
    AuditEntry,
    ConnectedApp,
    ConsentGrant,
    ConsentRequestInput,
    ContextScope,
    RegisterAppInput,
    ScopeAction,
)
from context_bridge.core.models.context import ContextCategory, SensitivityLevel
from context_bridge.core.ports.consent_storage import ConsentStoragePort


class InMemoryConsentStorage(ConsentStoragePort):
    """In-memory consent storage for development and testing."""

    def __init__(self) -> None:
        self._apps: dict[UUID, ConnectedApp] = {}
        self._grants: dict[UUID, ConsentGrant] = {}
        self._audit: list[AuditEntry] = []

    # ─── Connected Apps ───────────────────────────────────────

    async def register_app(self, input_data: RegisterAppInput) -> ConnectedApp:
        app = ConnectedApp(
            id=uuid4(),
            name=input_data.name,
            description=input_data.description,
            callback_url=input_data.callback_url,
            created_at=datetime.utcnow(),
        )
        self._apps[app.id] = app
        return app

    async def get_app(self, app_id: UUID) -> ConnectedApp | None:
        return self._apps.get(app_id)

    async def get_app_by_name(self, name: str) -> ConnectedApp | None:
        for app in self._apps.values():
            if app.name.lower() == name.lower():
                return app
        return None

    async def list_apps(self) -> list[ConnectedApp]:
        return [a for a in self._apps.values() if a.is_active]

    async def deactivate_app(self, app_id: UUID) -> bool:
        app = self._apps.get(app_id)
        if app:
            self._apps[app_id] = app.model_copy(update={"is_active": False})
            return True
        return False

    # ─── Consent Grants ───────────────────────────────────────

    async def create_grant(
        self, user_id: UUID, input_data: ConsentRequestInput
    ) -> ConsentGrant:
        now = datetime.utcnow()
        expires_at = None
        if input_data.expires_in_seconds:
            expires_at = now + timedelta(seconds=input_data.expires_in_seconds)

        grant = ConsentGrant(
            id=uuid4(),
            user_id=user_id,
            app_id=input_data.app_id,
            scopes=input_data.requested_scopes,
            max_sensitivity=input_data.max_sensitivity,
            granted_at=now,
            expires_at=expires_at,
        )
        self._grants[grant.id] = grant
        return grant

    async def get_grant(self, grant_id: UUID) -> ConsentGrant | None:
        return self._grants.get(grant_id)

    async def get_grant_by_app(self, user_id: UUID, app_id: UUID) -> ConsentGrant | None:
        for grant in self._grants.values():
            if grant.user_id == user_id and grant.app_id == app_id and grant.is_valid:
                return grant
        return None

    async def revoke_grant(self, grant_id: UUID) -> bool:
        grant = self._grants.get(grant_id)
        if grant and not grant.revoked:
            self._grants[grant_id] = grant.model_copy(
                update={"revoked": True, "revoked_at": datetime.utcnow()}
            )
            return True
        return False

    async def list_grants(self, user_id: UUID) -> list[ConsentGrant]:
        return [g for g in self._grants.values() if g.user_id == user_id]

    # ─── Audit Trail ──────────────────────────────────────────

    async def log_access(
        self,
        user_id: UUID,
        app_id: UUID,
        action: ScopeAction,
        categories: list[str],
        fact_count: int,
        detail: str | None = None,
    ) -> AuditEntry:
        entry = AuditEntry(
            id=uuid4(),
            user_id=user_id,
            app_id=app_id,
            action=action,
            categories=[ContextCategory(c) for c in categories],
            fact_count=fact_count,
            timestamp=datetime.utcnow(),
            detail=detail,
        )
        self._audit.append(entry)
        return entry

    async def get_audit_log(self, user_id: UUID, limit: int = 50) -> list[AuditEntry]:
        user_entries = [e for e in self._audit if e.user_id == user_id]
        user_entries.sort(key=lambda e: e.timestamp, reverse=True)
        return user_entries[:limit]
