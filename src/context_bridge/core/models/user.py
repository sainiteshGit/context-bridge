"""
Context Bridge — Core Domain Models: User Profile

Represents the vault owner. Personal context only — never enterprise.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class UserProfile(BaseModel):
    """The person who owns the context vault."""

    id: UUID = Field(default_factory=uuid4)
    display_name: str = Field(..., min_length=1, max_length=128)
    location: Optional[str] = None
    timezone: str = "UTC"
    language: str = "en"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True


class CreateUserInput(BaseModel):
    """Input for creating a new user."""

    display_name: str = Field(..., min_length=1, max_length=128)
    location: Optional[str] = None
    timezone: str = "UTC"
    language: str = "en"


class UpdateUserInput(BaseModel):
    """Input for updating user profile. All fields optional."""

    display_name: Optional[str] = Field(default=None, min_length=1, max_length=128)
    location: Optional[str] = None
    timezone: Optional[str] = None
    language: Optional[str] = None
