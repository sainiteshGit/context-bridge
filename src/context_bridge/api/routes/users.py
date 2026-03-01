"""
User Routes — create / read / update / delete user profiles.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from context_bridge.api.dependencies import get_user_service
from context_bridge.core.models.user import CreateUserInput, UpdateUserInput, UserProfile
from context_bridge.core.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/", response_model=UserProfile, status_code=status.HTTP_201_CREATED)
async def create_user(
    body: CreateUserInput,
    svc: UserService = Depends(get_user_service),
) -> UserProfile:
    return await svc.create_user(body)


@router.get("/{user_id}", response_model=UserProfile)
async def get_user(
    user_id: UUID,
    svc: UserService = Depends(get_user_service),
) -> UserProfile:
    user = await svc.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.patch("/{user_id}", response_model=UserProfile)
async def update_user(
    user_id: UUID,
    body: UpdateUserInput,
    svc: UserService = Depends(get_user_service),
) -> UserProfile:
    user = await svc.update_user(user_id, body)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: UUID,
    svc: UserService = Depends(get_user_service),
) -> None:
    deleted = await svc.delete_user(user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="User not found")
