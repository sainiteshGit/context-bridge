"""
User Storage Port — Abstract Interface

SOLID: Interface Segregation — user operations are separate from context and consent.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from context_bridge.core.models.user import CreateUserInput, UpdateUserInput, UserProfile


class UserStoragePort(ABC):
    """Abstract port for user profile persistence."""

    @abstractmethod
    async def create_user(self, input_data: CreateUserInput) -> UserProfile:
        ...

    @abstractmethod
    async def get_user(self, user_id: UUID) -> UserProfile | None:
        ...

    @abstractmethod
    async def update_user(self, user_id: UUID, input_data: UpdateUserInput) -> UserProfile | None:
        ...

    @abstractmethod
    async def delete_user(self, user_id: UUID) -> bool:
        ...
