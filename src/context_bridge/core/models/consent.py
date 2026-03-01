"""
Context Bridge — Core Domain Models: Consent & Permissions

OAuth-inspired consent system for context sharing.
Apps request scopes, users approve per-category.

SOLID: Single Responsibility — consent models handle ONLY authorization concerns.
"""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from .context import ContextCategory, SensitivityLevel


# ─── Scopes ───────────────────────────────────────────────────────
# What an app can do with context


class ScopeAction(str, enum.Enum):
    READ = "read"
    WRITE = "write"


class ContextScope(BaseModel):
    """A permission scope — e.g., read:fitness, write:food."""

    action: ScopeAction
    category: ContextCategory

    def __str__(self) -> str:
        return f"{self.action.value}:{self.category.value}"

    @classmethod
    def from_string(cls, scope_str: str) -> ContextScope:
        action_str, category_str = scope_str.split(":", 1)
        return cls(action=ScopeAction(action_str), category=ContextCategory(category_str))

    def __hash__(self) -> int:
        return hash(str(self))

    def __eq__(self, other: object) -> bool:
        if isinstance(other, ContextScope):
            return self.action == other.action and self.category == other.category
        return False


# ─── Connected App ────────────────────────────────────────────────
# An AI app that has been granted access


class ConnectedApp(BaseModel):
    """An external AI app registered with the context bridge."""

    id: UUID = Field(default_factory=uuid4)
    name: str = Field(..., min_length=1, max_length=128)
    description: Optional[str] = None
    api_key_hash: Optional[str] = None  # Hashed API key for authentication
    callback_url: Optional[str] = None
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True


class RegisterAppInput(BaseModel):
    """Input for registering a new connected app."""

    name: str = Field(..., min_length=1, max_length=128)
    description: Optional[str] = None
    callback_url: Optional[str] = None


# ─── Consent Grant ────────────────────────────────────────────────
# A user's approval for an app to access specific contexts


class ConsentGrant(BaseModel):
    """
    Record of user approving an app to access specific context categories.
    Follows principle of least privilege — apps get only what user approves.
    """

    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    app_id: UUID
    scopes: list[ContextScope]
    max_sensitivity: SensitivityLevel = SensitivityLevel.MEDIUM
    granted_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    revoked: bool = False
    revoked_at: Optional[datetime] = None

    class Config:
        from_attributes = True

    @property
    def is_valid(self) -> bool:
        """Check if this grant is still valid (not revoked, not expired)."""
        if self.revoked:
            return False
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False
        return True

    def has_scope(self, action: ScopeAction, category: ContextCategory) -> bool:
        """Check if this grant includes a specific scope."""
        target = ContextScope(action=action, category=category)
        return target in self.scopes


class ConsentRequestInput(BaseModel):
    """Input for requesting consent from a user."""

    app_id: UUID
    requested_scopes: list[ContextScope]
    max_sensitivity: SensitivityLevel = SensitivityLevel.MEDIUM
    expires_in_seconds: Optional[int] = Field(default=None, gt=0)


# ─── Access Token ─────────────────────────────────────────────────
# Short-lived token issued after consent


class AccessToken(BaseModel):
    """Token issued to an app after user grants consent."""

    token: str
    app_id: UUID
    user_id: UUID
    scopes: list[ContextScope]
    max_sensitivity: SensitivityLevel
    issued_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime


# ─── Audit Log Entry ──────────────────────────────────────────────
# Every single access is logged — full transparency


class AuditEntry(BaseModel):
    """Immutable record of a context access event."""

    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    app_id: UUID
    action: ScopeAction
    categories: list[ContextCategory]
    fact_count: int = 0
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    detail: Optional[str] = None

    class Config:
        from_attributes = True
