"""Gmail / Microsoft OAuth for sending (wired; no-op if unset)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse

from app.api.deps import CurrentUser, DbSession
from app.core.config import get_settings
from app.core.security import encrypt_secret
from app.services.email.oauth import gmail_authorize_url, microsoft_authorize_url

router = APIRouter(prefix="/api/oauth", tags=["oauth-email"])


@router.get("/gmail/start")
async def gmail_start(user: CurrentUser):
    url = gmail_authorize_url(state=user.id)
    if not url:
        return {
            "configured": False,
            "message": "Set GMAIL_CLIENT_ID and GMAIL_CLIENT_SECRET. Send path remains a safe no-op until configured.",
        }
    return {"configured": True, "authorize_url": url}


@router.get("/gmail/callback")
async def gmail_callback(
    db: DbSession,
    code: str = Query(...),
    state: str = Query(...),
):
    """Exchange code for tokens and store encrypted on user. state = user_id."""
    settings = get_settings()
    if not settings.gmail_configured:
        raise HTTPException(400, "Gmail not configured")
    import httpx
    from sqlalchemy import select
    from app.models import User

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": settings.gmail_client_id,
                "client_secret": settings.gmail_client_secret,
                "redirect_uri": settings.gmail_redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        if resp.status_code >= 400:
            raise HTTPException(400, f"Token exchange failed: {resp.text}")
        tokens = resp.json()
    access = tokens.get("access_token")
    if not access:
        raise HTTPException(400, "No access_token")
    result = await db.execute(select(User).where(User.id == state))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")
    # Store access token encrypted (refresh token handling is MVP-simple)
    payload = access
    if tokens.get("refresh_token"):
        payload = f"{access}|refresh|{tokens['refresh_token']}"
    user.gmail_token_enc = encrypt_secret(payload)
    await db.flush()
    return RedirectResponse(f"{settings.frontend_url}/settings?gmail=connected")


@router.get("/microsoft/start")
async def ms_start(user: CurrentUser):
    url = microsoft_authorize_url(state=user.id)
    if not url:
        return {
            "configured": False,
            "message": "Set MS_CLIENT_ID and MS_CLIENT_SECRET. Send path remains a safe no-op until configured.",
        }
    return {"configured": True, "authorize_url": url}


@router.get("/microsoft/callback")
async def ms_callback(db: DbSession, code: str = Query(...), state: str = Query(...)):
    settings = get_settings()
    if not settings.microsoft_configured:
        raise HTTPException(400, "Microsoft not configured")
    import httpx
    from sqlalchemy import select
    from app.models import User

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"https://login.microsoftonline.com/{settings.ms_tenant_id}/oauth2/v2.0/token",
            data={
                "client_id": settings.ms_client_id,
                "client_secret": settings.ms_client_secret,
                "code": code,
                "redirect_uri": settings.ms_redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        if resp.status_code >= 400:
            raise HTTPException(400, f"Token exchange failed: {resp.text}")
        tokens = resp.json()
    access = tokens.get("access_token")
    if not access:
        raise HTTPException(400, "No access_token")
    result = await db.execute(select(User).where(User.id == state))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")
    payload = access
    if tokens.get("refresh_token"):
        payload = f"{access}|refresh|{tokens['refresh_token']}"
    user.microsoft_token_enc = encrypt_secret(payload)
    await db.flush()
    return RedirectResponse(f"{settings.frontend_url}/settings?microsoft=connected")
