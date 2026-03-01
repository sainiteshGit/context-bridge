"""
In-Memory Storage Adapter — Context Facts

Implements ContextStoragePort using plain dictionaries.
Used for development, testing, and demos. Zero external dependencies.

SOLID: Liskov Substitution — fully interchangeable with CosmosDB adapter.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from context_bridge.core.models.context import (
    ContextFact,
    ContextQuery,
    CreateFactInput,
    SensitivityLevel,
    UpdateFactInput,
)
from context_bridge.core.ports.context_storage import ContextStoragePort


class InMemoryContextStorage(ContextStoragePort):
    """In-memory context storage for development and testing."""

    def __init__(self) -> None:
        # {user_id: {fact_id: ContextFact}}
        self._store: dict[UUID, dict[UUID, ContextFact]] = {}

    def _user_store(self, user_id: UUID) -> dict[UUID, ContextFact]:
        if user_id not in self._store:
            self._store[user_id] = {}
        return self._store[user_id]

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
        self._user_store(user_id)[fact.id] = fact
        return fact

    async def get_fact(self, user_id: UUID, fact_id: UUID) -> ContextFact | None:
        return self._user_store(user_id).get(fact_id)

    async def update_fact(
        self, user_id: UUID, fact_id: UUID, input_data: UpdateFactInput
    ) -> ContextFact | None:
        store = self._user_store(user_id)
        existing = store.get(fact_id)
        if not existing:
            return None

        update_data = input_data.model_dump(exclude_unset=True)
        updated = existing.model_copy(
            update={**update_data, "updated_at": datetime.utcnow()}
        )
        store[fact_id] = updated
        return updated

    async def delete_fact(self, user_id: UUID, fact_id: UUID) -> bool:
        store = self._user_store(user_id)
        if fact_id in store:
            del store[fact_id]
            return True
        return False

    async def query_facts(self, query: ContextQuery) -> list[ContextFact]:
        store = self._user_store(query.user_id)
        results: list[ContextFact] = []

        for fact in store.values():
            # Filter by categories
            if query.categories and fact.category not in query.categories:
                continue

            # Filter by max sensitivity
            if query.max_sensitivity and fact.sensitivity > query.max_sensitivity:
                continue

            # Filter by tags (any match)
            if query.tags and not any(t in fact.tags for t in query.tags):
                continue

            # Filter by search (simple substring match on key+value)
            if query.search:
                search_lower = query.search.lower()
                if (
                    search_lower not in fact.key.lower()
                    and search_lower not in fact.value.lower()
                ):
                    continue

            # Skip expired facts
            if fact.expires_at and datetime.utcnow() > fact.expires_at:
                continue

            results.append(fact)

        # Sort by updated_at descending
        results.sort(key=lambda f: f.updated_at, reverse=True)

        # Pagination
        return results[query.offset : query.offset + query.limit]

    async def count_facts(self, user_id: UUID) -> int:
        return len(self._user_store(user_id))

    async def delete_by_category(self, user_id: UUID, category: str) -> int:
        store = self._user_store(user_id)
        to_delete = [fid for fid, f in store.items() if f.category.value == category]
        for fid in to_delete:
            del store[fid]
        return len(to_delete)

    async def delete_all(self, user_id: UUID) -> int:
        store = self._user_store(user_id)
        count = len(store)
        store.clear()
        return count

    async def delete_expired(self) -> int:
        now = datetime.utcnow()
        total_deleted = 0
        for store in self._store.values():
            to_delete = [
                fid
                for fid, f in store.items()
                if f.expires_at and now > f.expires_at
            ]
            for fid in to_delete:
                del store[fid]
            total_deleted += len(to_delete)
        return total_deleted
