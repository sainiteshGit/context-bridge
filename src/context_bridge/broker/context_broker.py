"""
Context Broker — Central Coordinator

Aggregates context, user, and consent services.
Enforces consent before returning context to apps.
Follows Mediator pattern to keep services loosely coupled.

SOLID:
  - SRP: coordination / orchestration only
  - OCP: new providers can be added without modifying existing code
  - DIP: depends on service abstractions, not storage details
"""

from __future__ import annotations

from uuid import UUID

from context_bridge.core.models.consent import AuditEntry, ConsentGrant, ScopeAction
from context_bridge.core.models.context import (
    ContextCategory,
    ContextFact,
    ContextQuery,
    ContextSnapshot,
    SensitivityLevel,
)
from context_bridge.core.ports.context_provider import ContextProviderPort
from context_bridge.core.services.consent_service import ConsentService
from context_bridge.core.services.context_service import ContextService
from context_bridge.core.services.user_service import UserService


class ContextBroker:
    """
    Orchestrates context delivery with consent enforcement.

    This is the single entry point for external apps requesting context.
    All access flows through here so that consent, sensitivity filtering,
    and audit logging are guaranteed.
    """

    def __init__(
        self,
        context_service: ContextService,
        user_service: UserService,
        consent_service: ConsentService,
    ) -> None:
        self._context = context_service
        self._users = user_service
        self._consent = consent_service
        self._providers: dict[str, ContextProviderPort] = {}

    # ─── Provider Management ──────────────────────────────────

    def register_provider(self, provider: ContextProviderPort) -> None:
        """Register a context provider (browser extension, app, etc.)."""
        self._providers[provider.provider_id] = provider

    def unregister_provider(self, provider_id: str) -> None:
        self._providers.pop(provider_id, None)

    @property
    def providers(self) -> dict[str, ContextProviderPort]:
        return dict(self._providers)

    # ─── Owner Operations (no consent check) ──────────────────

    async def get_my_facts(
        self, user_id: UUID, query: ContextQuery | None = None
    ) -> list[ContextFact]:
        """Owner retrieves their own context — no consent check needed."""
        return await self._context.get_facts(user_id, query)

    async def get_my_snapshot(
        self, user_id: UUID, category: ContextCategory
    ) -> ContextSnapshot:
        """Owner gets a snapshot of one of their categories."""
        return await self._context.get_snapshot(user_id, category)

    async def get_my_full_context(
        self, user_id: UUID
    ) -> list[ContextSnapshot]:
        """Owner sees everything — all categories."""
        return await self._context.get_all_snapshots(user_id)

    # ─── App Operations (consent enforced) ────────────────────

    async def request_context(
        self,
        user_id: UUID,
        app_id: UUID,
        categories: list[ContextCategory] | None = None,
    ) -> list[ContextFact]:
        """
        An external app requests context for a user.
        Only returns facts from consented categories and below
        the max sensitivity the grant allows.
        """
        # 1. Determine allowed categories
        allowed = await self._consent.get_allowed_categories(
            user_id, app_id, ScopeAction.READ
        )
        if not allowed:
            return []

        # Narrow to requested categories (intersect with allowed)
        if categories:
            target = [c for c in categories if c in allowed]
        else:
            target = allowed

        if not target:
            return []

        # 2. Determine max sensitivity
        max_sens = await self._consent.get_max_sensitivity(user_id, app_id)

        # 3. Fetch facts with filtering
        facts = await self._context.get_facts_for_app(
            user_id=user_id,
            allowed_categories=target,
            max_sensitivity=max_sens or SensitivityLevel.LOW,
        )

        # 4. Audit trail
        await self._consent.log_access(
            user_id=user_id,
            app_id=app_id,
            action=ScopeAction.READ,
            categories=target,
            fact_count=len(facts),
        )

        return facts

    async def request_snapshot(
        self,
        user_id: UUID,
        app_id: UUID,
        category: ContextCategory,
    ) -> ContextSnapshot | None:
        """App requests a snapshot of a single category — consent enforced."""
        has_access = await self._consent.check_access(
            user_id, app_id, ScopeAction.READ, category
        )
        if not has_access:
            return None

        max_sens = await self._consent.get_max_sensitivity(user_id, app_id)
        snapshot = await self._context.get_snapshot(user_id, category)

        # Filter facts by sensitivity
        if max_sens:
            snapshot.facts = [
                f for f in snapshot.facts if f.sensitivity <= max_sens
            ]
            snapshot.fact_count = len(snapshot.facts)

        await self._consent.log_access(
            user_id=user_id,
            app_id=app_id,
            action=ScopeAction.READ,
            categories=[category],
            fact_count=snapshot.fact_count,
        )

        return snapshot

    async def write_fact_as_app(
        self,
        user_id: UUID,
        app_id: UUID,
        category: ContextCategory,
        key: str,
        value: str,
        confidence: float = 0.7,
    ) -> ContextFact | None:
        """
        An app writes a fact on behalf of the user.
        Requires WRITE consent for the category.
        """
        has_access = await self._consent.check_access(
            user_id, app_id, ScopeAction.WRITE, category
        )
        if not has_access:
            return None

        from context_bridge.core.models.context import CreateFactInput

        fact_input = CreateFactInput(
            category=category,
            key=key,
            value=value,
            source=f"app:{app_id}",
            confidence=confidence,
        )
        fact = await self._context.add_fact(user_id, fact_input)

        await self._consent.log_access(
            user_id=user_id,
            app_id=app_id,
            action=ScopeAction.WRITE,
            categories=[category],
            fact_count=1,
            detail=f"wrote fact '{key}' in {category.value}",
        )

        return fact

    # ─── Ingestion from Providers ─────────────────────────────

    async def ingest_from_provider(
        self, user_id: UUID, provider_id: str, raw_data: dict
    ) -> list[ContextFact]:
        """
        Extract facts from a context provider and store them.
        Used by browser extensions, apps, manual input, etc.
        """
        provider = self._providers.get(provider_id)
        if not provider:
            raise ValueError(f"Unknown provider: {provider_id}")

        from context_bridge.core.models.context import CreateFactInput

        extracted = await provider.extract_facts(raw_data)
        stored: list[ContextFact] = []

        for fact_input in extracted:
            validated = await provider.validate_fact(fact_input)
            if not validated:
                continue

            enriched = await provider.enrich_fact(validated)

            create_input = CreateFactInput(
                category=enriched.category,
                key=enriched.key,
                value=enriched.value,
                source=f"provider:{provider_id}",
                confidence=enriched.confidence if hasattr(enriched, "confidence") else 0.8,
                sensitivity=enriched.sensitivity if hasattr(enriched, "sensitivity") else SensitivityLevel.LOW,
                tags=enriched.tags if hasattr(enriched, "tags") else [],
            )
            fact = await self._context.add_fact(user_id, create_input)
            stored.append(fact)

        return stored

    # ─── Cross-cutting Queries ────────────────────────────────

    async def get_related_context(
        self,
        user_id: UUID,
        seed_category: ContextCategory,
        related_categories: list[ContextCategory] | None = None,
    ) -> dict[ContextCategory, list[ContextFact]]:
        """
        Owner query: get facts from a seed category plus related ones.
        Example: pet health + fitness schedule + food preferences.
        """
        targets = [seed_category]
        if related_categories:
            targets.extend(related_categories)
        targets = list(set(targets))

        result: dict[ContextCategory, list[ContextFact]] = {}
        for cat in targets:
            facts = await self._context.get_facts(
                user_id, ContextQuery(categories=[cat])
            )
            if facts:
                result[cat] = facts

        return result
