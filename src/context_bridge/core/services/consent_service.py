"""
Consent Service — Core Business Logic

Manages app registration, consent grants, token issuance, and audit.
Enforces authorization rules before any context access.

SOLID:
  - SRP: only consent/auth logic
  - DIP: depends on ConsentStoragePort abstraction
"""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID

from context_bridge.core.models.consent import (
    AccessToken,
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


class ConsentService:
    """Business logic for consent management and access control."""

    def __init__(
        self,
        storage: ConsentStoragePort,
        secret_key: str = "default-dev-key",
        token_expiry_seconds: int = 3600,
    ) -> None:
        self._storage = storage
        self._secret_key = secret_key
        self._token_expiry = token_expiry_seconds

    # ─── App Management ───────────────────────────────────────

    async def register_app(self, input_data: RegisterAppInput) -> ConnectedApp:
        """Register a new AI app that wants to access context."""
        # Check for duplicate name
        existing = await self._storage.get_app_by_name(input_data.name)
        if existing:
            raise ValueError(f"App with name '{input_data.name}' already exists")
        return await self._storage.register_app(input_data)

    async def get_app(self, app_id: UUID) -> ConnectedApp | None:
        return await self._storage.get_app(app_id)

    async def list_apps(self) -> list[ConnectedApp]:
        return await self._storage.list_apps()

    async def deactivate_app(self, app_id: UUID) -> bool:
        return await self._storage.deactivate_app(app_id)

    # ─── Consent Grants ───────────────────────────────────────

    async def grant_consent(
        self, user_id: UUID, input_data: ConsentRequestInput
    ) -> ConsentGrant:
        """
        Grant an app permission to access specified context categories.
        Replaces any existing grant for the same app.
        """
        # Verify app exists
        app = await self._storage.get_app(input_data.app_id)
        if not app or not app.is_active:
            raise ValueError("App not found or is deactivated")

        # Revoke existing grant for this app if any
        existing = await self._storage.get_grant_by_app(user_id, input_data.app_id)
        if existing:
            await self._storage.revoke_grant(existing.id)

        return await self._storage.create_grant(user_id, input_data)

    async def revoke_consent(self, grant_id: UUID) -> bool:
        """Revoke a consent grant immediately."""
        return await self._storage.revoke_grant(grant_id)

    async def list_grants(self, user_id: UUID) -> list[ConsentGrant]:
        """List all consent grants for a user (active and revoked)."""
        return await self._storage.list_grants(user_id)

    async def get_active_grant(self, user_id: UUID, app_id: UUID) -> ConsentGrant | None:
        """Get the active consent grant for a specific app."""
        return await self._storage.get_grant_by_app(user_id, app_id)

    # ─── Access Validation ────────────────────────────────────

    async def check_access(
        self,
        user_id: UUID,
        app_id: UUID,
        action: ScopeAction,
        category: ContextCategory,
    ) -> bool:
        """Check if an app has permission to perform an action on a category."""
        grant = await self._storage.get_grant_by_app(user_id, app_id)
        if not grant or not grant.is_valid:
            return False
        return grant.has_scope(action, category)

    async def get_allowed_categories(
        self, user_id: UUID, app_id: UUID, action: ScopeAction
    ) -> list[ContextCategory]:
        """Get all categories an app is allowed to access for a given action."""
        grant = await self._storage.get_grant_by_app(user_id, app_id)
        if not grant or not grant.is_valid:
            return []
        return [
            scope.category
            for scope in grant.scopes
            if scope.action == action
        ]

    async def get_max_sensitivity(
        self, user_id: UUID, app_id: UUID
    ) -> SensitivityLevel | None:
        """Get the max sensitivity level an app is allowed to see."""
        grant = await self._storage.get_grant_by_app(user_id, app_id)
        if not grant or not grant.is_valid:
            return None
        return grant.max_sensitivity

    # ─── Audit Trail ──────────────────────────────────────────

    async def log_access(
        self,
        user_id: UUID,
        app_id: UUID,
        action: ScopeAction,
        categories: list[ContextCategory],
        fact_count: int,
        detail: str | None = None,
    ) -> AuditEntry:
        """Log a context access event. Called after every read/write."""
        return await self._storage.log_access(
            user_id=user_id,
            app_id=app_id,
            action=action,
            categories=[c.value for c in categories],
            fact_count=fact_count,
            detail=detail,
        )

    async def get_audit_log(self, user_id: UUID, limit: int = 50) -> list[AuditEntry]:
        """Retrieve recent audit log entries for a user."""
        return await self._storage.get_audit_log(user_id, limit)
