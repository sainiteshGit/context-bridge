"""
Context Bridge Demo — "Alex's Day"

Run this script to see Context Bridge in action:
  python -m samples.demo

It starts the API, creates a user, adds personal context facts,
registers an AI app, grants consent, and shows how the app reads
only the context it's allowed to see.
"""

from __future__ import annotations

import asyncio
from uuid import UUID

from context_bridge.adapters.memory import (
    InMemoryConsentStorage,
    InMemoryContextStorage,
    InMemoryUserStorage,
)
from context_bridge.broker.context_broker import ContextBroker
from context_bridge.core.models.consent import (
    ConsentRequestInput,
    ContextScope,
    RegisterAppInput,
    ScopeAction,
)
from context_bridge.core.models.context import (
    ContextCategory,
    CreateFactInput,
    SensitivityLevel,
)
from context_bridge.core.models.user import CreateUserInput
from context_bridge.core.services.consent_service import ConsentService
from context_bridge.core.services.context_service import ContextService
from context_bridge.core.services.user_service import UserService


def header(text: str) -> None:
    print(f"\n{'='*50}")
    print(f"  {text}")
    print(f"{'='*50}")


async def main() -> None:
    # ── Wire up (in-memory for demo) ─────────────────────────
    ctx_storage = InMemoryContextStorage()
    user_storage = InMemoryUserStorage()
    consent_storage = InMemoryConsentStorage()

    ctx_svc = ContextService(ctx_storage)
    user_svc = UserService(user_storage)
    consent_svc = ConsentService(consent_storage)

    broker = ContextBroker(ctx_svc, user_svc, consent_svc)

    # ── 1. Create Alex ───────────────────────────────────────
    header("1. Creating user: Alex")
    alex = await user_svc.create_user(
        CreateUserInput(display_name="Alex", location="Portland, OR", timezone="America/Los_Angeles")
    )
    print(f"   User ID: {alex.id}")
    print(f"   Name:    {alex.display_name}")
    print(f"   Location: {alex.location}")

    # ── 2. Alex adds personal context ────────────────────────
    header("2. Alex adds personal context facts")

    facts_data = [
        (ContextCategory.PROFILE, "name", "Alex", SensitivityLevel.LOW),
        (ContextCategory.PROFILE, "age", "32", SensitivityLevel.MEDIUM),
        (ContextCategory.FITNESS, "morning_run", "5K at 6:30 AM daily", SensitivityLevel.LOW),
        (ContextCategory.FITNESS, "goal", "Train for half marathon", SensitivityLevel.LOW),
        (ContextCategory.PET, "pet_name", "Luna", SensitivityLevel.LOW),
        (ContextCategory.PET, "pet_type", "Golden Retriever", SensitivityLevel.LOW),
        (ContextCategory.PET, "vet_appointment", "March 15, annual checkup", SensitivityLevel.MEDIUM),
        (ContextCategory.FOOD, "diet", "Mostly plant-based", SensitivityLevel.LOW),
        (ContextCategory.FOOD, "allergy", "Tree nuts", SensitivityLevel.HIGH),
        (ContextCategory.FOOD, "favorite_cuisine", "Thai", SensitivityLevel.LOW),
        (ContextCategory.HOME, "smart_thermostat", "Nest, set to 68°F", SensitivityLevel.LOW),
        (ContextCategory.TRAVEL, "commute", "Bike, 20 min", SensitivityLevel.LOW),
        (ContextCategory.HEALTH, "blood_type", "O+", SensitivityLevel.CRITICAL),
        (ContextCategory.HOBBY, "hobby", "Film photography", SensitivityLevel.LOW),
    ]

    for cat, key, value, sens in facts_data:
        await ctx_svc.add_fact(
            alex.id, CreateFactInput(category=cat, key=key, value=value, sensitivity=sens)
        )
        print(f"   + [{cat.value}] {key} = {value}")

    count = await ctx_svc.count_facts(alex.id)
    print(f"\n   Total facts stored: {count}")

    # ── 3. Alex views their full context ─────────────────────
    header("3. Alex views all their context snapshots")
    snapshots = await broker.get_my_full_context(alex.id)
    for snap in snapshots:
        if snap.fact_count > 0:
            print(f"   📂 {snap.category.value}: {snap.fact_count} facts")
            for f in snap.facts:
                print(f"      • {f.key} = {f.value}  (sensitivity: {f.sensitivity.value})")

    # ── 4. Register an AI fitness app ────────────────────────
    header("4. Register AI app: 'FitCoach AI'")
    app = await consent_svc.register_app(
        RegisterAppInput(
            name="FitCoach AI",
            description="AI-powered fitness coaching app",
        )
    )
    print(f"   App ID:   {app.id}")
    print(f"   App Name: {app.name}")

    # ── 5. Alex grants consent ───────────────────────────────
    header("5. Alex grants FitCoach AI read access to fitness + food")
    grant = await consent_svc.grant_consent(
        alex.id,
        ConsentRequestInput(
            app_id=app.id,
            requested_scopes=[
                ContextScope(action=ScopeAction.READ, category=ContextCategory.FITNESS),
                ContextScope(action=ScopeAction.READ, category=ContextCategory.FOOD),
            ],
            max_sensitivity=SensitivityLevel.MEDIUM,
        ),
    )
    print(f"   Grant ID: {grant.id}")
    print(f"   Scopes:   {[str(s) for s in grant.scopes]}")
    print(f"   Max sensitivity: {grant.max_sensitivity.value}")

    # ── 6. FitCoach AI requests context through the broker ───
    header("6. FitCoach AI requests Alex's context (consent enforced)")
    app_facts = await broker.request_context(
        user_id=alex.id, app_id=app.id
    )
    print(f"   Facts received by FitCoach AI: {len(app_facts)}")
    for f in app_facts:
        print(f"   ✓ [{f.category.value}] {f.key} = {f.value}")

    # ── 7. Show what FitCoach CANNOT see ─────────────────────
    header("7. What FitCoach AI CANNOT see")
    denied_cats = [
        ContextCategory.PET,
        ContextCategory.HEALTH,
        ContextCategory.HOME,
    ]
    denied_facts = await broker.request_context(
        user_id=alex.id, app_id=app.id, categories=denied_cats
    )
    print(f"   Requested: {[c.value for c in denied_cats]}")
    print(f"   Facts returned: {len(denied_facts)}  (blocked by consent!)")

    # Also show that HIGH sensitivity food allergy is filtered out
    print(f"\n   Note: Alex's tree nut allergy (sensitivity=high) is also")
    print(f"   hidden because FitCoach max sensitivity = medium")

    # ── 8. Audit trail ───────────────────────────────────────
    header("8. Alex checks the audit trail")
    audit = await consent_svc.get_audit_log(alex.id)
    for entry in audit:
        print(f"   [{entry.timestamp.strftime('%H:%M:%S')}] "
              f"{entry.action} by app:{str(entry.app_id)[:8]}… — "
              f"{entry.fact_count} facts")

    # ── Done ─────────────────────────────────────────────────
    header("Demo Complete!")
    print("   Context Bridge keeps Alex in control.")
    print("   Every app only sees what Alex explicitly allows.")
    print("   Every access is audited.\n")


if __name__ == "__main__":
    asyncio.run(main())
