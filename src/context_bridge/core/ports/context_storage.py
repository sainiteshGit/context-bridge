"""
Context Storage Port — Abstract Interface

SOLID Principles Applied:
  - Interface Segregation: Only context fact operations. No user or consent logic.
  - Dependency Inversion: Core services depend on THIS abstraction, never on concrete adapters.
  - Liskov Substitution: Any adapter implementing this port is fully interchangeable.

To swap storage (Cosmos DB → PostgreSQL → MongoDB):
  Write a new adapter implementing this ABC. Zero changes to business logic.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from context_bridge.core.models.context import (
    ContextFact,
    ContextQuery,
    CreateFactInput,
    UpdateFactInput,
)


class ContextStoragePort(ABC):
    """Abstract port for context fact persistence."""

    # ─── Single Fact CRUD ─────────────────────────────────────

    @abstractmethod
    async def create_fact(self, user_id: UUID, input_data: CreateFactInput) -> ContextFact:
        """Persist a new context fact."""
        ...

    @abstractmethod
    async def get_fact(self, user_id: UUID, fact_id: UUID) -> ContextFact | None:
        """Retrieve a single fact by ID. Returns None if not found."""
        ...

    @abstractmethod
    async def update_fact(
        self, user_id: UUID, fact_id: UUID, input_data: UpdateFactInput
    ) -> ContextFact | None:
        """Update an existing fact. Returns None if not found."""
        ...

    @abstractmethod
    async def delete_fact(self, user_id: UUID, fact_id: UUID) -> bool:
        """Delete a fact. Returns True if deleted, False if not found."""
        ...

    # ─── Queries ──────────────────────────────────────────────

    @abstractmethod
    async def query_facts(self, query: ContextQuery) -> list[ContextFact]:
        """Query facts with flexible filtering."""
        ...

    @abstractmethod
    async def count_facts(self, user_id: UUID) -> int:
        """Count total facts for a user."""
        ...

    # ─── Bulk Operations ──────────────────────────────────────

    @abstractmethod
    async def delete_by_category(self, user_id: UUID, category: str) -> int:
        """Delete all facts in a category. Returns count deleted."""
        ...

    @abstractmethod
    async def delete_all(self, user_id: UUID) -> int:
        """Delete ALL facts for a user. Returns count deleted."""
        ...

    @abstractmethod
    async def delete_expired(self) -> int:
        """Clean up expired facts across all users. Returns count deleted."""
        ...
