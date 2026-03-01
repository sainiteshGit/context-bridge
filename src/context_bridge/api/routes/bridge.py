"""
Broker Routes — app-facing endpoints that go through the consent-enforced broker.

These are used by connected AI apps to fetch/write user context.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from context_bridge.api.dependencies import get_broker
from context_bridge.broker.context_broker import ContextBroker
from context_bridge.core.models.context import (
    ContextCategory,
    ContextFact,
    ContextSnapshot,
)

router = APIRouter(prefix="/bridge", tags=["bridge"])


class BridgeReadRequest(BaseModel):
    """Request body for an app reading user context."""
    app_id: UUID
    categories: list[ContextCategory] | None = None


class BridgeWriteRequest(BaseModel):
    """Request body for an app writing a fact."""
    app_id: UUID
    category: ContextCategory
    key: str
    value: str
    confidence: float = 0.7


@router.post("/{user_id}/read", response_model=list[ContextFact])
async def bridge_read(
    user_id: UUID,
    body: BridgeReadRequest,
    broker: ContextBroker = Depends(get_broker),
) -> list[ContextFact]:
    """
    App requests context for a user. Consent is enforced by the broker.
    Returns only allowed facts.
    """
    return await broker.request_context(
        user_id=user_id,
        app_id=body.app_id,
        categories=body.categories,
    )


@router.post("/{user_id}/snapshot/{category}", response_model=ContextSnapshot)
async def bridge_snapshot(
    user_id: UUID,
    category: ContextCategory,
    app_id: UUID = Query(...),
    broker: ContextBroker = Depends(get_broker),
) -> ContextSnapshot:
    """App requests a category snapshot — consent enforced."""
    snapshot = await broker.request_snapshot(
        user_id=user_id, app_id=app_id, category=category
    )
    if snapshot is None:
        raise HTTPException(
            status_code=403, detail="No consent for this category"
        )
    return snapshot


@router.post("/{user_id}/write", response_model=ContextFact)
async def bridge_write(
    user_id: UUID,
    body: BridgeWriteRequest,
    broker: ContextBroker = Depends(get_broker),
) -> ContextFact:
    """App writes a fact on behalf of the user — consent enforced."""
    fact = await broker.write_fact_as_app(
        user_id=user_id,
        app_id=body.app_id,
        category=body.category,
        key=body.key,
        value=body.value,
        confidence=body.confidence,
    )
    if fact is None:
        raise HTTPException(
            status_code=403, detail="No write consent for this category"
        )
    return fact
