"""Core ports — abstract interfaces (Dependency Inversion)."""

from .consent_storage import ConsentStoragePort
from .context_provider import ContextProviderPort
from .context_storage import ContextStoragePort
from .user_storage import UserStoragePort

__all__ = [
    "ContextStoragePort",
    "UserStoragePort",
    "ConsentStoragePort",
    "ContextProviderPort",
]
