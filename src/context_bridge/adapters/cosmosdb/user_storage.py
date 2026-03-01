"""
Azure Cosmos DB Storage Adapter — User Profiles

Implements UserStoragePort using Azure Cosmos DB.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from azure.cosmos import ContainerProxy, exceptions

from context_bridge.core.models.user import CreateUserInput, UpdateUserInput, UserProfile
from context_bridge.core.ports.user_storage import UserStoragePort


class CosmosUserStorage(UserStoragePort):
    """Azure Cosmos DB adapter for user profile persistence."""

    def __init__(self, container: ContainerProxy) -> None:
        self._container = container

    @staticmethod
    def _to_document(user: UserProfile) -> dict[str, Any]:
        return {
            "id": str(user.id),
            "partitionKey": str(user.id),
            "display_name": user.display_name,
            "location": user.location,
            "timezone": user.timezone,
            "language": user.language,
            "created_at": user.created_at.isoformat(),
            "updated_at": user.updated_at.isoformat(),
            "doc_type": "user_profile",
        }

    @staticmethod
    def _from_document(doc: dict[str, Any]) -> UserProfile:
        return UserProfile(
            id=UUID(doc["id"]),
            display_name=doc["display_name"],
            location=doc.get("location"),
            timezone=doc.get("timezone", "UTC"),
            language=doc.get("language", "en"),
            created_at=datetime.fromisoformat(doc["created_at"]),
            updated_at=datetime.fromisoformat(doc["updated_at"]),
        )

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
        self._container.create_item(body=self._to_document(user))
        return user

    async def get_user(self, user_id: UUID) -> UserProfile | None:
        try:
            doc = self._container.read_item(
                item=str(user_id), partition_key=str(user_id)
            )
            return self._from_document(doc)
        except exceptions.CosmosResourceNotFoundError:
            return None

    async def update_user(
        self, user_id: UUID, input_data: UpdateUserInput
    ) -> UserProfile | None:
        existing = await self.get_user(user_id)
        if not existing:
            return None

        update_data = input_data.model_dump(exclude_unset=True)
        updated = existing.model_copy(
            update={**update_data, "updated_at": datetime.utcnow()}
        )
        self._container.replace_item(
            item=str(user_id), body=self._to_document(updated)
        )
        return updated

    async def delete_user(self, user_id: UUID) -> bool:
        try:
            self._container.delete_item(
                item=str(user_id), partition_key=str(user_id)
            )
            return True
        except exceptions.CosmosResourceNotFoundError:
            return False
