"""
Token Service — JWT issuance and validation.

Issues short-lived access tokens for connected apps.
Users authenticate via a simple API key; apps get JWTs.

SOLID:
  - SRP: only token lifecycle
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from jose import JWTError, jwt
from pydantic import BaseModel


class TokenPayload(BaseModel):
    """Decoded JWT payload."""

    sub: str  # user_id
    app_id: str
    scopes: list[str]
    max_sensitivity: str
    exp: datetime
    iat: datetime


class TokenService:
    """JWT issuance and validation."""

    ALGORITHM = "HS256"

    def __init__(self, secret_key: str, expiry_seconds: int = 3600) -> None:
        self._secret = secret_key
        self._expiry = expiry_seconds

    def create_token(
        self,
        user_id: UUID,
        app_id: UUID,
        scopes: list[str],
        max_sensitivity: str,
    ) -> str:
        """Issue a signed JWT for an app's consented access."""
        now = datetime.now(timezone.utc)
        payload = {
            "sub": str(user_id),
            "app_id": str(app_id),
            "scopes": scopes,
            "max_sensitivity": max_sensitivity,
            "iat": now,
            "exp": now + timedelta(seconds=self._expiry),
        }
        return jwt.encode(payload, self._secret, algorithm=self.ALGORITHM)

    def verify_token(self, token: str) -> TokenPayload | None:
        """Verify and decode a JWT. Returns None if invalid/expired."""
        try:
            data = jwt.decode(token, self._secret, algorithms=[self.ALGORITHM])
            return TokenPayload(**data)
        except JWTError:
            return None

    def refresh_token(self, token: str) -> str | None:
        """Re-issue a token with a fresh expiry if the current one is valid."""
        payload = self.verify_token(token)
        if not payload:
            return None
        return self.create_token(
            user_id=UUID(payload.sub),
            app_id=UUID(payload.app_id),
            scopes=payload.scopes,
            max_sensitivity=payload.max_sensitivity,
        )
