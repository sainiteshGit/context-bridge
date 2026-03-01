"""
Consent & App Routes — manage connected apps, consent grants, and audit.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from context_bridge.api.dependencies import get_consent_service, get_token_service
from context_bridge.core.models.consent import (
    AuditEntry,
    ConnectedApp,
    ConsentGrant,
    ConsentRequestInput,
    RegisterAppInput,
    ScopeAction,
)
from context_bridge.core.services.consent_service import ConsentService
from context_bridge.protocol.token_service import TokenService

router = APIRouter(tags=["consent"])


# ─── App Management ──────────────────────────────────────────

@router.post("/apps", response_model=ConnectedApp, status_code=status.HTTP_201_CREATED)
async def register_app(
    body: RegisterAppInput,
    svc: ConsentService = Depends(get_consent_service),
) -> ConnectedApp:
    try:
        return await svc.register_app(body)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/apps", response_model=list[ConnectedApp])
async def list_apps(
    svc: ConsentService = Depends(get_consent_service),
) -> list[ConnectedApp]:
    return await svc.list_apps()


@router.get("/apps/{app_id}", response_model=ConnectedApp)
async def get_app(
    app_id: UUID,
    svc: ConsentService = Depends(get_consent_service),
) -> ConnectedApp:
    app = await svc.get_app(app_id)
    if not app:
        raise HTTPException(status_code=404, detail="App not found")
    return app


@router.delete("/apps/{app_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_app(
    app_id: UUID,
    svc: ConsentService = Depends(get_consent_service),
) -> None:
    ok = await svc.deactivate_app(app_id)
    if not ok:
        raise HTTPException(status_code=404, detail="App not found")


# ─── Consent Grants ──────────────────────────────────────────

@router.post(
    "/users/{user_id}/consent",
    response_model=ConsentGrant,
    status_code=status.HTTP_201_CREATED,
)
async def grant_consent(
    user_id: UUID,
    body: ConsentRequestInput,
    svc: ConsentService = Depends(get_consent_service),
) -> ConsentGrant:
    try:
        return await svc.grant_consent(user_id, body)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/users/{user_id}/consent", response_model=list[ConsentGrant])
async def list_grants(
    user_id: UUID,
    svc: ConsentService = Depends(get_consent_service),
) -> list[ConsentGrant]:
    return await svc.list_grants(user_id)


@router.delete(
    "/users/{user_id}/consent/{grant_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def revoke_consent(
    user_id: UUID,
    grant_id: UUID,
    svc: ConsentService = Depends(get_consent_service),
) -> None:
    ok = await svc.revoke_consent(grant_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Grant not found")


# ─── Token Issuance ──────────────────────────────────────────

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


@router.post("/users/{user_id}/token", response_model=TokenResponse)
async def issue_token(
    user_id: UUID,
    app_id: UUID = Query(...),
    consent_svc: ConsentService = Depends(get_consent_service),
    token_svc: TokenService = Depends(get_token_service),
) -> TokenResponse:
    """Issue a JWT to an app after verifying active consent."""
    grant = await consent_svc.get_active_grant(user_id, app_id)
    if not grant or not grant.is_valid:
        raise HTTPException(status_code=403, detail="No active consent grant")

    scopes = [str(s) for s in grant.scopes]
    token = token_svc.create_token(
        user_id=user_id,
        app_id=app_id,
        scopes=scopes,
        max_sensitivity=grant.max_sensitivity.value,
    )

    from context_bridge.config import get_settings
    settings = get_settings()

    return TokenResponse(
        access_token=token,
        expires_in=settings.token_expiry_seconds,
    )


# ─── Audit Log ────────────────────────────────────────────────

@router.get("/users/{user_id}/audit", response_model=list[AuditEntry])
async def get_audit_log(
    user_id: UUID,
    limit: int = Query(50, ge=1, le=500),
    svc: ConsentService = Depends(get_consent_service),
) -> list[AuditEntry]:
    return await svc.get_audit_log(user_id, limit)
