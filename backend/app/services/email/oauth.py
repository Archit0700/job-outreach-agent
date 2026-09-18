"""OAuth URL helpers for Gmail and Microsoft Graph (sending)."""
from __future__ import annotations

from urllib.parse import urlencode

from app.core.config import get_settings


def gmail_authorize_url(state: str) -> str | None:
    settings = get_settings()
    if not settings.gmail_configured:
        return None
    params = {
        "client_id": settings.gmail_client_id,
        "redirect_uri": settings.gmail_redirect_uri,
        "response_type": "code",
        "scope": "https://www.googleapis.com/auth/gmail.send",
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    return "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)


def microsoft_authorize_url(state: str) -> str | None:
    settings = get_settings()
    if not settings.microsoft_configured:
        return None
    params = {
        "client_id": settings.ms_client_id,
        "response_type": "code",
        "redirect_uri": settings.ms_redirect_uri,
        "response_mode": "query",
        "scope": "offline_access Mail.Send User.Read",
        "state": state,
    }
    return (
        f"https://login.microsoftonline.com/{settings.ms_tenant_id}/oauth2/v2.0/authorize?"
        + urlencode(params)
    )
