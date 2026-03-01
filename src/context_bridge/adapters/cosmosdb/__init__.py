"""Azure Cosmos DB adapters for production storage."""

from .client import CosmosClientFactory
from .consent_storage import CosmosConsentStorage
from .context_storage import CosmosContextStorage
from .user_storage import CosmosUserStorage

__all__ = [
    "CosmosClientFactory",
    "CosmosContextStorage",
    "CosmosUserStorage",
    "CosmosConsentStorage",
]
