"""
Azure Cosmos DB Storage Adapter — Consent, Apps & Audit

Implements ConsentStoragePort using Azure Cosmos DB.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from azure.cosmos import ContainerProxy, exceptions

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


class CosmosConsentStorage(ConsentStoragePort):
    """Azure Cosmos DB adapter for consent, app registration, and audit."""

    def __init__(self, container: ContainerProxy) -> None:
        self._container = container

    # ─── Serialization Helpers ────────────────────────────────

    @staticmethod
    def _scope_to_dict(scope: ContextScope) -> dict[str, str]:
        return {"action": scope.action.value, "category": scope.category.value}

    @staticmethod
    def _scope_from_dict(d: dict[str, str]) -> ContextScope:
        return ContextScope(
            action=ScopeAction(d["action"]),
            category=ContextCategory(d["category"]),
        )

    # ─── Connected Apps ───────────────────────────────────────

    async def register_app(self, input_data: RegisterAppInput) -> ConnectedApp:
        app = ConnectedApp(
            id=uuid4(),
            name=input_data.name,
            description=input_data.description,
            callback_url=input_data.callback_url,
            created_at=datetime.utcnow(),
        )
        doc: dict[str, Any] = {
            "id": str(app.id),
            "partitionKey": "apps",
            "name": app.name,
            "description": app.description,
            "callback_url": app.callback_url,
            "is_active": app.is_active,
            "created_at": app.created_at.isoformat(),
            "doc_type": "connected_app",
        }
        self._container.create_item(body=doc)
        return app

    async def get_app(self, app_id: UUID) -> ConnectedApp | None:
        try:
            doc = self._container.read_item(item=str(app_id), partition_key="apps")
            if doc.get("doc_type") != "connected_app":
                return None
            return ConnectedApp(
                id=UUID(doc["id"]),
                name=doc["name"],
                description=doc.get("description"),
                callback_url=doc.get("callback_url"),
                is_active=doc.get("is_active", True),
                created_at=datetime.fromisoformat(doc["created_at"]),
            )
        except exceptions.CosmosResourceNotFoundError:
            return None

    async def get_app_by_name(self, name: str) -> ConnectedApp | None:
        sql = (
            "SELECT * FROM c WHERE c.doc_type = 'connected_app' "
            "AND LOWER(c.name) = @name"
        )
        items = list(
            self._container.query_items(
                query=sql,
                parameters=[{"name": "@name", "value": name.lower()}],
                partition_key="apps",
            )
        )
        if not items:
            return None
        doc = items[0]
        return ConnectedApp(
            id=UUID(doc["id"]),
            name=doc["name"],
            description=doc.get("description"),
            callback_url=doc.get("callback_url"),
            is_active=doc.get("is_active", True),
            created_at=datetime.fromisoformat(doc["created_at"]),
        )

    async def list_apps(self) -> list[ConnectedApp]:
        sql = "SELECT * FROM c WHERE c.doc_type = 'connected_app' AND c.is_active = true"
        items = list(
            self._container.query_items(query=sql, partition_key="apps")
        )
        return [
            ConnectedApp(
                id=UUID(doc["id"]),
                name=doc["name"],
                description=doc.get("description"),
                callback_url=doc.get("callback_url"),
                is_active=True,
                created_at=datetime.fromisoformat(doc["created_at"]),
            )
            for doc in items
        ]

    async def deactivate_app(self, app_id: UUID) -> bool:
        try:
            doc = self._container.read_item(item=str(app_id), partition_key="apps")
            doc["is_active"] = False
            self._container.replace_item(item=str(app_id), body=doc)
            return True
        except exceptions.CosmosResourceNotFoundError:
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
        doc: dict[str, Any] = {
            "id": str(grant.id),
            "partitionKey": str(user_id),
            "user_id": str(user_id),
            "app_id": str(grant.app_id),
            "scopes": [self._scope_to_dict(s) for s in grant.scopes],
            "max_sensitivity": grant.max_sensitivity.value,
            "granted_at": grant.granted_at.isoformat(),
            "expires_at": grant.expires_at.isoformat() if grant.expires_at else None,
            "revoked": False,
            "revoked_at": None,
            "doc_type": "consent_grant",
        }
        self._container.create_item(body=doc)
        return grant

    async def get_grant(self, grant_id: UUID) -> ConsentGrant | None:
        sql = "SELECT * FROM c WHERE c.id = @id AND c.doc_type = 'consent_grant'"
        items = list(
            self._container.query_items(
                query=sql,
                parameters=[{"name": "@id", "value": str(grant_id)}],
                enable_cross_partition_query=True,
            )
        )
        if not items:
            return None
        return self._grant_from_doc(items[0])

    async def get_grant_by_app(self, user_id: UUID, app_id: UUID) -> ConsentGrant | None:
        sql = (
            "SELECT * FROM c WHERE c.doc_type = 'consent_grant' "
            "AND c.user_id = @uid AND c.app_id = @aid AND c.revoked = false"
        )
        items = list(
            self._container.query_items(
                query=sql,
                parameters=[
                    {"name": "@uid", "value": str(user_id)},
                    {"name": "@aid", "value": str(app_id)},
                ],
                partition_key=str(user_id),
            )
        )
        if not items:
            return None
        grant = self._grant_from_doc(items[0])
        return grant if grant.is_valid else None

    async def revoke_grant(self, grant_id: UUID) -> bool:
        grant = await self.get_grant(grant_id)
        if not grant or grant.revoked:
            return False

        # Read full doc to replace
        doc = self._container.read_item(
            item=str(grant_id), partition_key=str(grant.user_id)
        )
        doc["revoked"] = True
        doc["revoked_at"] = datetime.utcnow().isoformat()
        self._container.replace_item(item=str(grant_id), body=doc)
        return True

    async def list_grants(self, user_id: UUID) -> list[ConsentGrant]:
        sql = (
            "SELECT * FROM c WHERE c.doc_type = 'consent_grant' AND c.user_id = @uid"
        )
        items = list(
            self._container.query_items(
                query=sql,
                parameters=[{"name": "@uid", "value": str(user_id)}],
                partition_key=str(user_id),
            )
        )
        return [self._grant_from_doc(doc) for doc in items]

    def _grant_from_doc(self, doc: dict[str, Any]) -> ConsentGrant:
        return ConsentGrant(
            id=UUID(doc["id"]),
            user_id=UUID(doc["user_id"]),
            app_id=UUID(doc["app_id"]),
            scopes=[self._scope_from_dict(s) for s in doc["scopes"]],
            max_sensitivity=SensitivityLevel(doc["max_sensitivity"]),
            granted_at=datetime.fromisoformat(doc["granted_at"]),
            expires_at=(
                datetime.fromisoformat(doc["expires_at"]) if doc.get("expires_at") else None
            ),
            revoked=doc.get("revoked", False),
            revoked_at=(
                datetime.fromisoformat(doc["revoked_at"]) if doc.get("revoked_at") else None
            ),
        )

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
        doc: dict[str, Any] = {
            "id": str(entry.id),
            "partitionKey": str(user_id),
            "user_id": str(user_id),
            "app_id": str(app_id),
            "action": entry.action.value,
            "categories": [c.value for c in entry.categories],
            "fact_count": entry.fact_count,
            "timestamp": entry.timestamp.isoformat(),
            "detail": entry.detail,
            "doc_type": "audit_entry",
        }
        self._container.create_item(body=doc)
        return entry

    async def get_audit_log(self, user_id: UUID, limit: int = 50) -> list[AuditEntry]:
        sql = (
            "SELECT * FROM c WHERE c.doc_type = 'audit_entry' AND c.user_id = @uid "
            "ORDER BY c.timestamp DESC OFFSET 0 LIMIT @limit"
        )
        items = list(
            self._container.query_items(
                query=sql,
                parameters=[
                    {"name": "@uid", "value": str(user_id)},
                    {"name": "@limit", "value": limit},
                ],
                partition_key=str(user_id),
            )
        )
        return [
            AuditEntry(
                id=UUID(doc["id"]),
                user_id=UUID(doc["user_id"]),
                app_id=UUID(doc["app_id"]),
                action=ScopeAction(doc["action"]),
                categories=[ContextCategory(c) for c in doc["categories"]],
                fact_count=doc.get("fact_count", 0),
                timestamp=datetime.fromisoformat(doc["timestamp"]),
                detail=doc.get("detail"),
            )
            for doc in items
        ]
