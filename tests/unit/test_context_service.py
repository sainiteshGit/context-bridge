"""Unit tests for ContextService."""

from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest

from context_bridge.adapters.memory import InMemoryContextStorage
from context_bridge.core.models.context import (
    ContextCategory,
    CreateFactInput,
    SensitivityLevel,
    UpdateFactInput,
)
from context_bridge.core.services.context_service import ContextService


@pytest.fixture
def svc() -> ContextService:
    return ContextService(InMemoryContextStorage())


@pytest.fixture
def user_id():
    return uuid4()


@pytest.mark.asyncio
async def test_add_and_get_fact(svc: ContextService, user_id):
    fact = await svc.add_fact(
        user_id,
        CreateFactInput(category=ContextCategory.FOOD, key="diet", value="vegetarian"),
    )
    assert fact.key == "diet"
    assert fact.value == "vegetarian"
    assert fact.category == ContextCategory.FOOD

    retrieved = await svc.get_fact(user_id, fact.id)
    assert retrieved is not None
    assert retrieved.id == fact.id


@pytest.mark.asyncio
async def test_update_fact(svc: ContextService, user_id):
    fact = await svc.add_fact(
        user_id,
        CreateFactInput(category=ContextCategory.FITNESS, key="goal", value="5K"),
    )
    updated = await svc.update_fact(
        user_id, fact.id, UpdateFactInput(value="half marathon")
    )
    assert updated is not None
    assert updated.value == "half marathon"
    assert updated.key == "goal"


@pytest.mark.asyncio
async def test_remove_fact(svc: ContextService, user_id):
    fact = await svc.add_fact(
        user_id,
        CreateFactInput(category=ContextCategory.PET, key="name", value="Luna"),
    )
    removed = await svc.remove_fact(user_id, fact.id)
    assert removed is True

    got = await svc.get_fact(user_id, fact.id)
    assert got is None


@pytest.mark.asyncio
async def test_get_facts_filter_by_category(svc: ContextService, user_id):
    await svc.add_fact(user_id, CreateFactInput(category=ContextCategory.FOOD, key="a", value="1"))
    await svc.add_fact(user_id, CreateFactInput(category=ContextCategory.PET, key="b", value="2"))
    await svc.add_fact(user_id, CreateFactInput(category=ContextCategory.FOOD, key="c", value="3"))

    food = await svc.get_facts(user_id, categories=[ContextCategory.FOOD])
    assert len(food) == 2
    assert all(f.category == ContextCategory.FOOD for f in food)


@pytest.mark.asyncio
async def test_get_facts_filter_by_sensitivity(svc: ContextService, user_id):
    await svc.add_fact(
        user_id,
        CreateFactInput(category=ContextCategory.HEALTH, key="blood", value="O+", sensitivity=SensitivityLevel.CRITICAL),
    )
    await svc.add_fact(
        user_id,
        CreateFactInput(category=ContextCategory.FOOD, key="diet", value="veg", sensitivity=SensitivityLevel.LOW),
    )

    low_only = await svc.get_facts(user_id, max_sensitivity=SensitivityLevel.LOW)
    assert len(low_only) == 1
    assert low_only[0].key == "diet"


@pytest.mark.asyncio
async def test_count_facts(svc: ContextService, user_id):
    assert await svc.count_facts(user_id) == 0
    await svc.add_fact(user_id, CreateFactInput(category=ContextCategory.HOBBY, key="h", value="photo"))
    await svc.add_fact(user_id, CreateFactInput(category=ContextCategory.HOBBY, key="h2", value="music"))
    assert await svc.count_facts(user_id) == 2


@pytest.mark.asyncio
async def test_snapshot(svc: ContextService, user_id):
    await svc.add_fact(user_id, CreateFactInput(category=ContextCategory.PET, key="name", value="Luna"))
    await svc.add_fact(user_id, CreateFactInput(category=ContextCategory.PET, key="type", value="dog"))

    snap = await svc.get_snapshot(user_id, ContextCategory.PET)
    assert snap.category == ContextCategory.PET
    assert snap.fact_count == 2
    assert len(snap.facts) == 2


@pytest.mark.asyncio
async def test_clear_category(svc: ContextService, user_id):
    await svc.add_fact(user_id, CreateFactInput(category=ContextCategory.FOOD, key="a", value="1"))
    await svc.add_fact(user_id, CreateFactInput(category=ContextCategory.PET, key="b", value="2"))

    await svc.clear_category(user_id, ContextCategory.FOOD)
    assert await svc.count_facts(user_id) == 1


@pytest.mark.asyncio
async def test_clear_all(svc: ContextService, user_id):
    await svc.add_fact(user_id, CreateFactInput(category=ContextCategory.FOOD, key="a", value="1"))
    await svc.add_fact(user_id, CreateFactInput(category=ContextCategory.PET, key="b", value="2"))

    await svc.clear_all(user_id)
    assert await svc.count_facts(user_id) == 0
