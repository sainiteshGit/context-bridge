"""Unit tests for ConsentService."""

from __future__ import annotations

from uuid import uuid4

import pytest

from context_bridge.adapters.memory import InMemoryConsentStorage
from context_bridge.core.models.consent import (
    ConsentRequestInput,
    ContextScope,
    RegisterAppInput,
    ScopeAction,
)
from context_bridge.core.models.context import ContextCategory, SensitivityLevel
from context_bridge.core.services.consent_service import ConsentService


@pytest.fixture
def svc() -> ConsentService:
    return ConsentService(InMemoryConsentStorage())


@pytest.fixture
def user_id():
    return uuid4()


@pytest.mark.asyncio
async def test_register_app(svc: ConsentService):
    app = await svc.register_app(RegisterAppInput(name="TestApp", description="A test"))
    assert app.name == "TestApp"
    assert app.is_active is True


@pytest.mark.asyncio
async def test_register_duplicate_app_raises(svc: ConsentService):
    await svc.register_app(RegisterAppInput(name="TestApp"))
    with pytest.raises(ValueError, match="already exists"):
        await svc.register_app(RegisterAppInput(name="TestApp"))


@pytest.mark.asyncio
async def test_deactivate_app(svc: ConsentService):
    app = await svc.register_app(RegisterAppInput(name="TestApp"))
    assert await svc.deactivate_app(app.id) is True

    got = await svc.get_app(app.id)
    assert got is not None
    assert got.is_active is False


@pytest.mark.asyncio
async def test_grant_consent(svc: ConsentService, user_id):
    app = await svc.register_app(RegisterAppInput(name="FitApp"))
    grant = await svc.grant_consent(
        user_id,
        ConsentRequestInput(
            app_id=app.id,
            requested_scopes=[
                ContextScope(action=ScopeAction.READ, category=ContextCategory.FITNESS),
            ],
            max_sensitivity=SensitivityLevel.MEDIUM,
        ),
    )
    assert grant.user_id == user_id
    assert grant.app_id == app.id
    assert len(grant.scopes) == 1
    assert grant.is_valid is True


@pytest.mark.asyncio
async def test_grant_consent_to_inactive_app_raises(svc: ConsentService, user_id):
    app = await svc.register_app(RegisterAppInput(name="FitApp"))
    await svc.deactivate_app(app.id)

    with pytest.raises(ValueError, match="not found or is deactivated"):
        await svc.grant_consent(
            user_id,
            ConsentRequestInput(
                app_id=app.id,
                requested_scopes=[
                    ContextScope(action=ScopeAction.READ, category=ContextCategory.FITNESS),
                ],
            ),
        )


@pytest.mark.asyncio
async def test_revoke_consent(svc: ConsentService, user_id):
    app = await svc.register_app(RegisterAppInput(name="FitApp"))
    grant = await svc.grant_consent(
        user_id,
        ConsentRequestInput(
            app_id=app.id,
            requested_scopes=[
                ContextScope(action=ScopeAction.READ, category=ContextCategory.FOOD),
            ],
        ),
    )
    assert await svc.revoke_consent(grant.id) is True

    active = await svc.get_active_grant(user_id, app.id)
    assert active is None


@pytest.mark.asyncio
async def test_check_access(svc: ConsentService, user_id):
    app = await svc.register_app(RegisterAppInput(name="FitApp"))
    await svc.grant_consent(
        user_id,
        ConsentRequestInput(
            app_id=app.id,
            requested_scopes=[
                ContextScope(action=ScopeAction.READ, category=ContextCategory.FITNESS),
            ],
        ),
    )
    assert await svc.check_access(user_id, app.id, ScopeAction.READ, ContextCategory.FITNESS) is True
    assert await svc.check_access(user_id, app.id, ScopeAction.READ, ContextCategory.HEALTH) is False
    assert await svc.check_access(user_id, app.id, ScopeAction.WRITE, ContextCategory.FITNESS) is False


@pytest.mark.asyncio
async def test_audit_log(svc: ConsentService, user_id):
    app = await svc.register_app(RegisterAppInput(name="FitApp"))
    await svc.log_access(
        user_id=user_id,
        app_id=app.id,
        action=ScopeAction.READ,
        categories=[ContextCategory.FITNESS],
        fact_count=3,
    )
    log = await svc.get_audit_log(user_id)
    assert len(log) == 1
    assert log[0].fact_count == 3
