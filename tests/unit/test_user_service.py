"""Unit tests for UserService."""

from __future__ import annotations

import pytest

from context_bridge.adapters.memory import InMemoryUserStorage
from context_bridge.core.models.user import CreateUserInput, UpdateUserInput
from context_bridge.core.services.user_service import UserService


@pytest.fixture
def svc() -> UserService:
    return UserService(InMemoryUserStorage())


@pytest.mark.asyncio
async def test_create_and_get_user(svc: UserService):
    user = await svc.create_user(CreateUserInput(display_name="Alex"))
    assert user.display_name == "Alex"

    got = await svc.get_user(user.id)
    assert got is not None
    assert got.id == user.id


@pytest.mark.asyncio
async def test_update_user(svc: UserService):
    user = await svc.create_user(CreateUserInput(display_name="Alex"))
    updated = await svc.update_user(user.id, UpdateUserInput(location="Portland"))
    assert updated is not None
    assert updated.location == "Portland"
    assert updated.display_name == "Alex"


@pytest.mark.asyncio
async def test_delete_user(svc: UserService):
    user = await svc.create_user(CreateUserInput(display_name="Alex"))
    assert await svc.delete_user(user.id) is True
    assert await svc.get_user(user.id) is None


@pytest.mark.asyncio
async def test_delete_nonexistent_user(svc: UserService):
    from uuid import uuid4
    assert await svc.delete_user(uuid4()) is False
