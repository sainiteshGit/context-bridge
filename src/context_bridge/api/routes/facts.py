"""
Context Fact Routes — CRUD for personal context facts.

All endpoints are owner-only (user manages their own data).
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from context_bridge.api.dependencies import get_context_service
from context_bridge.core.models.context import (
    ContextCategory,
    ContextFact,
    ContextQuery,
    ContextSnapshot,
    CreateFactInput,
    SensitivityLevel,
    UpdateFactInput,
)
from context_bridge.core.services.context_service import ContextService

router = APIRouter(prefix="/users/{user_id}/facts", tags=["facts"])


@router.post("/", response_model=ContextFact, status_code=status.HTTP_201_CREATED)
async def add_fact(
    user_id: UUID,
    body: CreateFactInput,
    svc: ContextService = Depends(get_context_service),
) -> ContextFact:
    return await svc.add_fact(user_id, body)


@router.get("/", response_model=list[ContextFact])
async def list_facts(
    user_id: UUID,
    categories: list[ContextCategory] | None = Query(None),
    max_sensitivity: SensitivityLevel | None = None,
    tags: list[str] | None = Query(None),
    search: str | None = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    svc: ContextService = Depends(get_context_service),
) -> list[ContextFact]:
    query = ContextQuery(
        categories=categories,
        max_sensitivity=max_sensitivity,
        tags=tags,
        search=search,
        limit=limit,
        offset=offset,
    )
    return await svc.get_facts(user_id, query)


@router.get("/count")
async def count_facts(
    user_id: UUID,
    svc: ContextService = Depends(get_context_service),
) -> dict[str, int]:
    count = await svc.count_facts(user_id)
    return {"count": count}


@router.get("/snapshots", response_model=list[ContextSnapshot])
async def all_snapshots(
    user_id: UUID,
    svc: ContextService = Depends(get_context_service),
) -> list[ContextSnapshot]:
    return await svc.get_all_snapshots(user_id)


@router.get("/snapshots/{category}", response_model=ContextSnapshot)
async def category_snapshot(
    user_id: UUID,
    category: ContextCategory,
    svc: ContextService = Depends(get_context_service),
) -> ContextSnapshot:
    return await svc.get_snapshot(user_id, category)


@router.get("/{fact_id}", response_model=ContextFact)
async def get_fact(
    user_id: UUID,
    fact_id: UUID,
    svc: ContextService = Depends(get_context_service),
) -> ContextFact:
    fact = await svc.get_fact(user_id, fact_id)
    if not fact:
        raise HTTPException(status_code=404, detail="Fact not found")
    return fact


@router.patch("/{fact_id}", response_model=ContextFact)
async def update_fact(
    user_id: UUID,
    fact_id: UUID,
    body: UpdateFactInput,
    svc: ContextService = Depends(get_context_service),
) -> ContextFact:
    fact = await svc.update_fact(user_id, fact_id, body)
    if not fact:
        raise HTTPException(status_code=404, detail="Fact not found")
    return fact


@router.delete("/{fact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_fact(
    user_id: UUID,
    fact_id: UUID,
    svc: ContextService = Depends(get_context_service),
) -> None:
    removed = await svc.remove_fact(user_id, fact_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Fact not found")


@router.delete("/category/{category}", status_code=status.HTTP_204_NO_CONTENT)
async def clear_category(
    user_id: UUID,
    category: ContextCategory,
    svc: ContextService = Depends(get_context_service),
) -> None:
    await svc.clear_category(user_id, category)


@router.delete("/", status_code=status.HTTP_204_NO_CONTENT)
async def clear_all(
    user_id: UUID,
    svc: ContextService = Depends(get_context_service),
) -> None:
    await svc.clear_all(user_id)
