"""
Context Bridge — Core Domain Models: Context

Pure domain types with zero infrastructure dependencies.
These represent the "what" of context — categories, facts, and metadata.
"""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


# ─── Context Categories ──────────────────────────────────────────
# Personal life domains — NOT enterprise/work


class ContextCategory(str, enum.Enum):
    """Personal context domains. Each represents an area of daily life."""

    PROFILE = "profile"       # Name, location, language, timezone
    FITNESS = "fitness"       # Training, health metrics, goals
    FAMILY = "family"        # Family members, preferences, events
    FOOD = "food"            # Diet, allergies, meal preferences
    HOME = "home"            # Property, renovations, maintenance
    PET = "pet"              # Pet health, vet info, schedules
    FINANCE = "finance"      # Budget, savings, expenses
    TRAVEL = "travel"        # Preferences, upcoming trips
    HOBBY = "hobby"          # Hobbies, projects, interests
    HEALTH = "health"        # Personal health, medications, conditions


class SensitivityLevel(str, enum.Enum):
    """How sensitive the data is — controls default sharing behavior."""

    LOW = "low"              # Name, timezone, language preference
    MEDIUM = "medium"        # Diet, hobbies, general preferences
    HIGH = "high"            # Health data, financial info
    CRITICAL = "critical"    # SSN, passwords — never shared automatically

    @property
    def numeric(self) -> int:
        """Numeric ordering for comparison."""
        return {"low": 0, "medium": 1, "high": 2, "critical": 3}[self.value]

    def __ge__(self, other: SensitivityLevel) -> bool:
        return self.numeric >= other.numeric

    def __gt__(self, other: SensitivityLevel) -> bool:
        return self.numeric > other.numeric

    def __le__(self, other: SensitivityLevel) -> bool:
        return self.numeric <= other.numeric

    def __lt__(self, other: SensitivityLevel) -> bool:
        return self.numeric < other.numeric


# ─── Context Fact ─────────────────────────────────────────────────
# A single piece of context — the atomic unit


class ContextFact(BaseModel):
    """
    A single fact about the user.
    Examples: "diet: vegetarian", "dog_name: Cooper", "mortgage: $2,400/mo"
    """

    id: UUID = Field(default_factory=uuid4)
    category: ContextCategory
    key: str = Field(..., min_length=1, max_length=256)
    value: str = Field(..., min_length=1)
    sensitivity: SensitivityLevel = SensitivityLevel.MEDIUM
    source: Optional[str] = None         # Which app/provider created this
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ─── Create / Update DTOs ────────────────────────────────────────


class CreateFactInput(BaseModel):
    """Input for creating a new context fact."""

    category: ContextCategory
    key: str = Field(..., min_length=1, max_length=256)
    value: str = Field(..., min_length=1)
    sensitivity: SensitivityLevel = SensitivityLevel.MEDIUM
    source: Optional[str] = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    tags: list[str] = Field(default_factory=list)
    expires_at: Optional[datetime] = None


class UpdateFactInput(BaseModel):
    """Input for updating an existing context fact. All fields optional."""

    value: Optional[str] = Field(default=None, min_length=1)
    sensitivity: Optional[SensitivityLevel] = None
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    tags: Optional[list[str]] = None
    expires_at: Optional[datetime] = None


# ─── Context Snapshot ─────────────────────────────────────────────


class ContextSnapshot(BaseModel):
    """Grouped view of facts for a single category."""

    category: ContextCategory
    facts: list[ContextFact]
    fact_count: int = 0
    last_updated: datetime


# ─── Query Filters ────────────────────────────────────────────────


class ContextQuery(BaseModel):
    """Flexible query for filtering context facts."""

    user_id: Optional[UUID] = None
    categories: Optional[list[ContextCategory]] = None
    tags: Optional[list[str]] = None
    max_sensitivity: Optional[SensitivityLevel] = None
    search: Optional[str] = None
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)
