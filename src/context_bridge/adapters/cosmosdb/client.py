"""
Azure Cosmos DB Client Factory

Single Responsibility: handles ONLY Cosmos DB connection setup.
Dependency Inversion: returns ContainerProxy objects that adapters use.
"""

from __future__ import annotations

from azure.cosmos import CosmosClient, DatabaseProxy, ContainerProxy


class CosmosClientFactory:
    """Factory for creating Cosmos DB client and container references."""

    def __init__(self, endpoint: str, key: str, database_name: str) -> None:
        self._client = CosmosClient(endpoint, credential=key)
        self._database: DatabaseProxy = self._client.get_database_client(database_name)

    def get_container(self, container_name: str) -> ContainerProxy:
        """Get a reference to a Cosmos DB container."""
        return self._database.get_container_client(container_name)

    def ensure_container(
        self,
        container_name: str,
        partition_key: str = "/partitionKey",
    ) -> ContainerProxy:
        """Create container if it doesn't exist, then return reference."""
        self._database.create_container_if_not_exists(
            id=container_name,
            partition_key={"paths": [partition_key], "kind": "Hash"},
        )
        return self.get_container(container_name)

    @property
    def database(self) -> DatabaseProxy:
        return self._database
