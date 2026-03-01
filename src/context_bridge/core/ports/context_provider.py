"""
Context Provider Port — Abstract Interface

A provider is a source/extractor of context for a specific domain.
Examples: Fitness provider extracts training facts from text,
a Food provider extracts dietary preferences.

SOLID: Open/Closed — add new providers by implementing this interface,
without modifying existing code.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from context_bridge.core.models.context import ContextCategory, ContextFact, CreateFactInput


class ContextProviderPort(ABC):
    """Abstract port for domain-specific context extraction and validation."""

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Unique identifier for this provider."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name."""
        ...

    @property
    @abstractmethod
    def supported_categories(self) -> list[ContextCategory]:
        """Which context categories this provider can handle."""
        ...

    @abstractmethod
    async def extract_facts(self, text: str) -> list[CreateFactInput]:
        """
        Extract context facts from raw text (e.g., an AI conversation).
        Returns suggested facts the user can review before saving.
        """
        ...

    @abstractmethod
    async def validate_fact(self, fact: CreateFactInput) -> bool:
        """Validate whether a fact makes sense for this provider's domain."""
        ...

    async def enrich_fact(self, fact: ContextFact) -> CreateFactInput | None:
        """
        Optional: enrich an existing fact with additional data.
        Default implementation returns None (no enrichment).
        """
        return None
