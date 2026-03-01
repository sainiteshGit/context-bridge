"""
In-Memory Storage Adapter — User Profiles

Implements UserStoragePort using plain dictionaries.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from context_bridge.core.models.user import CreateUserInput, UpdateUserInput, UserProfile
from context_bridge.core.ports.user_storage import UserStoragePort


class InMemoryUserStorage(UserStoragePort):
    """In-memory user storage for development and testing."""

    def __init__(self) -> None:
        self._store: dict[UUID, UserProfile] = {}

    async def create_user(self, input_data: CreateUserInput) -> UserProfile:
        now = datetime.utcnow()
        user = UserProfile(
            id=uuid4(),
            display_name=input_data.display_name,
            location=input_data.location,
            timezone=input_data.timezone,
            language=input_data.language,
            created_at=now,
            updated_at=now,
        )
        self._store[user.id] = user
        return user

    async def get_user(self, user_id: UUID) -> UserProfile | None:
        return self._store.get(user_id)

    async def update_user(
        self, user_id: UUID, input_data: UpdateUserInput
    ) -> UserProfile | None:
        existing = self._store.get(user_id)
        if not existing:
            return None

        update_data = input_data.model_dump(exclude_unset=True)
        updated = existing.model_copy(
            update={**update_data, "updated_at": datetime.utcnow()}
        )
        self._store[user_id] = updated
        return updated

    async def delete_user(self, user_id: UUID) -> bool:
        if user_id in self._store:
            del self._store[user_id]
            return True
        return False
