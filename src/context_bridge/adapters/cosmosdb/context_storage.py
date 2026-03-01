"""
Azure Cosmos DB Storage Adapter — Context Facts

Implements ContextStoragePort using Azure Cosmos DB (NoSQL API).
Fully interchangeable with InMemoryContextStorage via the port interface.

SOLID: Liskov Substitution — drop-in replacement for any ContextStoragePort impl.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from azure.cosmos import ContainerProxy, exceptions

from context_bridge.core.models.context import (
    ContextCategory,
    ContextFact,
    ContextQuery,
    CreateFactInput,
    SensitivityLevel,
    UpdateFactInput,
)
from context_bridge.core.ports.context_storage import ContextStoragePort


class CosmosContextStorage(ContextStoragePort):
    """Azure Cosmos DB adapter for context fact persistence."""

    def __init__(self, container: ContainerProxy) -> None:
        self._container = container

    # ─── Helpers ──────────────────────────────────────────────

    @staticmethod
    def _to_document(user_id: UUID, fact: ContextFact) -> dict[str, Any]:
        """Convert a ContextFact to a Cosmos DB document."""
        return {
            "id": str(fact.id),
            "partitionKey": str(user_id),
            "user_id": str(user_id),
            "category": fact.category.value,
            "key": fact.key,
            "value": fact.value,
            "sensitivity": fact.sensitivity.value,
            "source": fact.source,
            "confidence": fact.confidence,
            "tags": fact.tags,
            "created_at": fact.created_at.isoformat(),
            "updated_at": fact.updated_at.isoformat(),
            "expires_at": fact.expires_at.isoformat() if fact.expires_at else None,
            "doc_type": "context_fact",
        }

    @staticmethod
    def _from_document(doc: dict[str, Any]) -> ContextFact:
        """Convert a Cosmos DB document back to a ContextFact."""
        return ContextFact(
            id=UUID(doc["id"]),
            category=ContextCategory(doc["category"]),
            key=doc["key"],
            value=doc["value"],
            sensitivity=SensitivityLevel(doc["sensitivity"]),
            source=doc.get("source"),
            confidence=doc.get("confidence", 1.0),
            tags=doc.get("tags", []),
            created_at=datetime.fromisoformat(doc["created_at"]),
            updated_at=datetime.fromisoformat(doc["updated_at"]),
            expires_at=(
                datetime.fromisoformat(doc["expires_at"]) if doc.get("expires_at") else None
            ),
        )

    # ─── CRUD ─────────────────────────────────────────────────

    async def create_fact(self, user_id: UUID, input_data: CreateFactInput) -> ContextFact:
        now = datetime.utcnow()
        fact = ContextFact(
            id=uuid4(),
            category=input_data.category,
            key=input_data.key,
            value=input_data.value,
            sensitivity=input_data.sensitivity,
            source=input_data.source,
            confidence=input_data.confidence,
            tags=input_data.tags,
            created_at=now,
            updated_at=now,
            expires_at=input_data.expires_at,
        )
        doc = self._to_document(user_id, fact)
        self._container.create_item(body=doc)
        return fact

    async def get_fact(self, user_id: UUID, fact_id: UUID) -> ContextFact | None:
        try:
            doc = self._container.read_item(
                item=str(fact_id), partition_key=str(user_id)
            )
            return self._from_document(doc)
        except exceptions.CosmosResourceNotFoundError:
            return None

    async def update_fact(
        self, user_id: UUID, fact_id: UUID, input_data: UpdateFactInput
    ) -> ContextFact | None:
        existing = await self.get_fact(user_id, fact_id)
        if not existing:
            return None

        update_data = input_data.model_dump(exclude_unset=True)
        updated = existing.model_copy(
            update={**update_data, "updated_at": datetime.utcnow()}
        )
        doc = self._to_document(user_id, updated)
        self._container.replace_item(item=str(fact_id), body=doc)
        return updated

    async def delete_fact(self, user_id: UUID, fact_id: UUID) -> bool:
        try:
            self._container.delete_item(
                item=str(fact_id), partition_key=str(user_id)
            )
            return True
        except exceptions.CosmosResourceNotFoundError:
            return False

    # ─── Queries ──────────────────────────────────────────────

    async def query_facts(self, query: ContextQuery) -> list[ContextFact]:
        conditions = [
            "c.doc_type = 'context_fact'",
            f"c.user_id = '{query.user_id}'",
        ]
        params: list[dict[str, Any]] = []

        if query.categories:
            cat_values = [c.value for c in query.categories]
            placeholders = ", ".join(f"'{c}'" for c in cat_values)
            conditions.append(f"c.category IN ({placeholders})")

        if query.max_sensitivity:
            sensitivity_order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
            max_val = sensitivity_order[query.max_sensitivity.value]
            allowed = [k for k, v in sensitivity_order.items() if v <= max_val]
            placeholders = ", ".join(f"'{s}'" for s in allowed)
            conditions.append(f"c.sensitivity IN ({placeholders})")

        if query.search:
            conditions.append(
                "(CONTAINS(LOWER(c.key), @search) OR CONTAINS(LOWER(c.value), @search))"
            )
            params.append({"name": "@search", "value": query.search.lower()})

        # Exclude expired
        now_iso = datetime.utcnow().isoformat()
        conditions.append(
            f"(NOT IS_DEFINED(c.expires_at) OR c.expires_at = null OR c.expires_at > '{now_iso}')"
        )

        where_clause = " AND ".join(conditions)
        sql = (
            f"SELECT * FROM c WHERE {where_clause} "
            f"ORDER BY c.updated_at DESC "
            f"OFFSET {query.offset} LIMIT {query.limit}"
        )

        items = list(
            self._container.query_items(
                query=sql,
                parameters=params if params else None,
                partition_key=str(query.user_id),
            )
        )
        return [self._from_document(doc) for doc in items]

    async def count_facts(self, user_id: UUID) -> int:
        sql = (
            "SELECT VALUE COUNT(1) FROM c "
            "WHERE c.doc_type = 'context_fact' AND c.user_id = @uid"
        )
        items = list(
            self._container.query_items(
                query=sql,
                parameters=[{"name": "@uid", "value": str(user_id)}],
                partition_key=str(user_id),
            )
        )
        return items[0] if items else 0

    # ─── Bulk Operations ──────────────────────────────────────

    async def delete_by_category(self, user_id: UUID, category: str) -> int:
        sql = (
            "SELECT c.id FROM c "
            "WHERE c.doc_type = 'context_fact' AND c.user_id = @uid AND c.category = @cat"
        )
        items = list(
            self._container.query_items(
                query=sql,
                parameters=[
                    {"name": "@uid", "value": str(user_id)},
                    {"name": "@cat", "value": category},
                ],
                partition_key=str(user_id),
            )
        )
        for item in items:
            self._container.delete_item(item=item["id"], partition_key=str(user_id))
        return len(items)

    async def delete_all(self, user_id: UUID) -> int:
        sql = (
            "SELECT c.id FROM c "
            "WHERE c.doc_type = 'context_fact' AND c.user_id = @uid"
        )
        items = list(
            self._container.query_items(
                query=sql,
                parameters=[{"name": "@uid", "value": str(user_id)}],
                partition_key=str(user_id),
            )
        )
        for item in items:
            self._container.delete_item(item=item["id"], partition_key=str(user_id))
        return len(items)

    async def delete_expired(self) -> int:
        now_iso = datetime.utcnow().isoformat()
        sql = (
            "SELECT c.id, c.user_id FROM c "
            "WHERE c.doc_type = 'context_fact' "
            f"AND IS_DEFINED(c.expires_at) AND c.expires_at != null AND c.expires_at < '{now_iso}'"
        )
        # Cross-partition query for cleanup
        items = list(
            self._container.query_items(query=sql, enable_cross_partition_query=True)
        )
        for item in items:
            self._container.delete_item(
                item=item["id"], partition_key=item["user_id"]
            )
        return len(items)
