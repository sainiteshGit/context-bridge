"""
User Service — Core Business Logic

Single Responsibility: manages only user profile operations.
"""

from __future__ import annotations

from uuid import UUID

from context_bridge.core.models.user import CreateUserInput, UpdateUserInput, UserProfile
from context_bridge.core.ports.user_storage import UserStoragePort


class UserService:
    """Business logic for user profile management."""

    def __init__(self, storage: UserStoragePort) -> None:
        self._storage = storage

    async def create_user(self, input_data: CreateUserInput) -> UserProfile:
        return await self._storage.create_user(input_data)

    async def get_user(self, user_id: UUID) -> UserProfile | None:
        return await self._storage.get_user(user_id)

    async def update_user(
        self, user_id: UUID, input_data: UpdateUserInput
    ) -> UserProfile | None:
        return await self._storage.update_user(user_id, input_data)

    async def delete_user(self, user_id: UUID) -> bool:
        return await self._storage.delete_user(user_id)
