"""Unit tests for ContextBroker — consent enforcement."""

from __future__ import annotations

from uuid import uuid4

import pytest

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
from context_bridge.core.services.consent_service import ConsentService
from context_bridge.core.services.context_service import ContextService
from context_bridge.core.services.user_service import UserService


@pytest.fixture
def broker():
    ctx = ContextService(InMemoryContextStorage())
    usr = UserService(InMemoryUserStorage())
    con = ConsentService(InMemoryConsentStorage())
    return ContextBroker(ctx, usr, con), ctx, con


@pytest.fixture
def user_id():
    return uuid4()


@pytest.mark.asyncio
async def test_owner_sees_everything(broker, user_id):
    b, ctx, _ = broker
    await ctx.add_fact(user_id, CreateFactInput(category=ContextCategory.HEALTH, key="bp", value="120/80", sensitivity=SensitivityLevel.CRITICAL))
    await ctx.add_fact(user_id, CreateFactInput(category=ContextCategory.FOOD, key="diet", value="veg"))

    facts = await b.get_my_facts(user_id)
    assert len(facts) == 2


@pytest.mark.asyncio
async def test_app_only_sees_consented_categories(broker, user_id):
    b, ctx, con = broker

    # Add facts in multiple categories
    await ctx.add_fact(user_id, CreateFactInput(category=ContextCategory.FITNESS, key="goal", value="5K"))
    await ctx.add_fact(user_id, CreateFactInput(category=ContextCategory.FOOD, key="diet", value="veg"))
    await ctx.add_fact(user_id, CreateFactInput(category=ContextCategory.HEALTH, key="bp", value="120/80"))

    # Register app and grant only FITNESS read
    app = await con.register_app(RegisterAppInput(name="FitApp"))
    await con.grant_consent(
        user_id,
        ConsentRequestInput(
            app_id=app.id,
            requested_scopes=[ContextScope(action=ScopeAction.READ, category=ContextCategory.FITNESS)],
        ),
    )

    facts = await b.request_context(user_id, app.id)
    assert len(facts) == 1
    assert facts[0].category == ContextCategory.FITNESS


@pytest.mark.asyncio
async def test_app_blocked_with_no_consent(broker, user_id):
    b, ctx, _ = broker
    await ctx.add_fact(user_id, CreateFactInput(category=ContextCategory.FOOD, key="diet", value="veg"))

    facts = await b.request_context(user_id, uuid4())  # random app id
    assert facts == []


@pytest.mark.asyncio
async def test_sensitivity_filtering(broker, user_id):
    b, ctx, con = broker

    await ctx.add_fact(user_id, CreateFactInput(category=ContextCategory.FOOD, key="diet", value="veg", sensitivity=SensitivityLevel.LOW))
    await ctx.add_fact(user_id, CreateFactInput(category=ContextCategory.FOOD, key="allergy", value="nuts", sensitivity=SensitivityLevel.HIGH))

    app = await con.register_app(RegisterAppInput(name="MealApp"))
    await con.grant_consent(
        user_id,
        ConsentRequestInput(
            app_id=app.id,
            requested_scopes=[ContextScope(action=ScopeAction.READ, category=ContextCategory.FOOD)],
            max_sensitivity=SensitivityLevel.MEDIUM,
        ),
    )

    facts = await b.request_context(user_id, app.id)
    assert len(facts) == 1
    assert facts[0].key == "diet"  # allergy (high) filtered out


@pytest.mark.asyncio
async def test_write_with_consent(broker, user_id):
    b, ctx, con = broker

    app = await con.register_app(RegisterAppInput(name="FitApp"))
    await con.grant_consent(
        user_id,
        ConsentRequestInput(
            app_id=app.id,
            requested_scopes=[ContextScope(action=ScopeAction.WRITE, category=ContextCategory.FITNESS)],
        ),
    )

    fact = await b.write_fact_as_app(user_id, app.id, ContextCategory.FITNESS, "steps", "10000")
    assert fact is not None
    assert fact.key == "steps"


@pytest.mark.asyncio
async def test_write_without_consent_returns_none(broker, user_id):
    b, ctx, con = broker

    app = await con.register_app(RegisterAppInput(name="FitApp"))
    await con.grant_consent(
        user_id,
        ConsentRequestInput(
            app_id=app.id,
            requested_scopes=[ContextScope(action=ScopeAction.READ, category=ContextCategory.FITNESS)],
        ),
    )

    # Has READ but not WRITE
    fact = await b.write_fact_as_app(user_id, app.id, ContextCategory.FITNESS, "steps", "10000")
    assert fact is None
