"""
Auth middleware for FastAPI.

Extracts JWT from Authorization header, verifies it,
and injects the decoded payload into the request state.
"""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from context_bridge.protocol.token_service import TokenPayload, TokenService

_bearer_scheme = HTTPBearer(auto_error=False)


def get_token_service(request: Request) -> TokenService:
    """Retrieve the TokenService from app state (set during startup)."""
    return request.app.state.token_service


async def get_current_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    token_service: TokenService = Depends(get_token_service),
) -> TokenPayload:
    """
    Dependency that validates the Bearer token.
    Raises 401 if missing/invalid.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = token_service.verify_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return payload


async def require_owner(
    request: Request,
    token: TokenPayload = Depends(get_current_token),
) -> TokenPayload:
    """
    Dependency that ensures the token's subject matches the user_id
    in the path. Use for owner-only endpoints.
    """
    user_id_param = request.path_params.get("user_id")
    if user_id_param and str(token.sub) != str(user_id_param):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: not the resource owner",
        )
    return token
