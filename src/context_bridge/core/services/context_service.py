"""
Context Service — Core Business Logic

SOLID Principles:
  - Single Responsibility: handles ONLY context fact operations.
  - Dependency Inversion: depends on ContextStoragePort, not concrete adapters.
  - Open/Closed: extend behavior by decorating, not modifying.

This service is the single entry point for all context operations.
It enforces business rules before delegating to storage.
"""

from __future__ import annotations

from uuid import UUID

from context_bridge.core.models.context import (
    ContextCategory,
    ContextFact,
    ContextQuery,
    ContextSnapshot,
    CreateFactInput,
    SensitivityLevel,
    UpdateFactInput,
)
from context_bridge.core.ports.context_storage import ContextStoragePort


class ContextService:
    """
    Business logic for managing context facts.

    Injected with a storage port — works with ANY adapter
    (in-memory, Cosmos DB, PostgreSQL, etc.)
    """

    def __init__(self, storage: ContextStoragePort) -> None:
        self._storage = storage

    # ─── CRUD ─────────────────────────────────────────────────

    async def add_fact(self, user_id: UUID, input_data: CreateFactInput) -> ContextFact:
        """Add a new context fact for a user."""
        return await self._storage.create_fact(user_id, input_data)

    async def get_fact(self, user_id: UUID, fact_id: UUID) -> ContextFact | None:
        """Retrieve a single fact."""
        return await self._storage.get_fact(user_id, fact_id)

    async def update_fact(
        self, user_id: UUID, fact_id: UUID, input_data: UpdateFactInput
    ) -> ContextFact | None:
        """Update an existing fact."""
        return await self._storage.update_fact(user_id, fact_id, input_data)

    async def remove_fact(self, user_id: UUID, fact_id: UUID) -> bool:
        """Delete a single fact."""
        return await self._storage.delete_fact(user_id, fact_id)

    # ─── Queries ──────────────────────────────────────────────

    async def get_facts(
        self,
        user_id: UUID,
        categories: list[ContextCategory] | None = None,
        max_sensitivity: SensitivityLevel | None = None,
        search: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ContextFact]:
        """Query facts with flexible filters."""
        query = ContextQuery(
            user_id=user_id,
            categories=categories,
            max_sensitivity=max_sensitivity,
            search=search,
            limit=limit,
            offset=offset,
        )
        return await self._storage.query_facts(query)

    async def get_snapshot(self, user_id: UUID, category: ContextCategory) -> ContextSnapshot:
        """Get all facts for a specific category as a snapshot."""
        query = ContextQuery(user_id=user_id, categories=[category])
        facts = await self._storage.query_facts(query)
        last_updated = max((f.updated_at for f in facts), default=None)
        from datetime import datetime

        return ContextSnapshot(
            fact_count=len(facts),
            category=category,
            facts=facts,
            last_updated=last_updated or datetime.utcnow(),
        )

    async def get_all_snapshots(self, user_id: UUID) -> list[ContextSnapshot]:
        """Get snapshots for all categories that have facts."""
        snapshots = []
        for category in ContextCategory:
            snapshot = await self.get_snapshot(user_id, category)
            if snapshot.facts:
                snapshots.append(snapshot)
        return snapshots

    async def count_facts(self, user_id: UUID) -> int:
        """Count total facts for a user."""
        return await self._storage.count_facts(user_id)

    # ─── Bulk Operations ──────────────────────────────────────

    async def clear_category(self, user_id: UUID, category: ContextCategory) -> int:
        """Delete all facts in a category."""
        return await self._storage.delete_by_category(user_id, category.value)

    async def clear_all(self, user_id: UUID) -> int:
        """Delete ALL facts for a user. Nuclear option."""
        return await self._storage.delete_all(user_id)

    async def cleanup_expired(self) -> int:
        """Remove expired facts across all users."""
        return await self._storage.delete_expired()

    # ─── Scoped Access (for apps with limited consent) ────────

    async def get_facts_for_app(
        self,
        user_id: UUID,
        allowed_categories: list[ContextCategory],
        max_sensitivity: SensitivityLevel,
        search: str | None = None,
    ) -> list[ContextFact]:
        """
        Retrieve facts constrained by an app's consent grant.
        Only returns facts within allowed categories and sensitivity.
        """
        query = ContextQuery(
            user_id=user_id,
            categories=allowed_categories,
            max_sensitivity=max_sensitivity,
            search=search,
        )
        return await self._storage.query_facts(query)
