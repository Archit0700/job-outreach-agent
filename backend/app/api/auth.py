"""Auth routes — demo login + Google OAuth stub."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy import select

from app.api.deps import DbSession
from app.core.config import get_settings
from app.core.security import create_access_token
from app.models import User, UserSettings
from app.schemas.schemas import TokenResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])

DEFAULT_ROLES = [
    "Software Engineer",
    "SDE",
    "Backend Engineer",
    "Full Stack Engineer",
    "ML Engineer",
    "AI Engineer",
    "Android Developer",
]
DEFAULT_LOCATIONS = [
    "India",
    "Bengaluru",
    "Delhi NCR",
    "Hyderabad",
    "Pune",
    "Mumbai",
    "Remote",
]


class DemoLogin(BaseModel):
    email: EmailStr = "archit@example.com"
    name: str = "Archit"


async def _ensure_settings(db, user: User) -> None:
    result = await db.execute(select(UserSettings).where(UserSettings.user_id == user.id))
    if result.scalar_one_or_none():
        return
    settings = get_settings()
    db.add(
        UserSettings(
            user_id=user.id,
            target_roles=DEFAULT_ROLES,
            preferred_locations=DEFAULT_LOCATIONS,
            employment_types=["internship", "full_time"],
            experience_level="entry_level",
            max_emails_per_day=settings.default_daily_send_limit,
            per_company_send_limit=settings.default_per_company_send_limit,
            require_manual_approval=True,
            target_companies=[
                "Google", "Microsoft", "Amazon", "Adobe", "Atlassian",
                "Deloitte", "PwC", "EY", "KPMG", "ZS", "Mu Sigma", "Tredence", "BlackRock",
            ],
        )
    )


@router.post("/demo", response_model=TokenResponse)
async def demo_login(body: DemoLogin, db: DbSession):
    """Local/dev login without OAuth — creates user if needed."""
    result = await db.execute(select(User).where(User.email == body.email.lower()))
    user = result.scalar_one_or_none()
    if not user:
        user = User(email=body.email.lower(), name=body.name, oauth_provider="demo")
        db.add(user)
        await db.flush()
        await _ensure_settings(db, user)
    token = create_access_token(user.id, {"email": user.email})
    return TokenResponse(
        access_token=token, user_id=user.id, email=user.email, name=user.name
    )


@router.get("/google/start")
async def google_start():
    settings = get_settings()
    if not settings.google_client_id:
        return {
            "configured": False,
            "message": "Set GOOGLE_CLIENT_ID/SECRET for Google app login. Use POST /api/auth/demo meanwhile.",
        }
    from urllib.parse import urlencode

    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "online",
    }
    return {
        "configured": True,
        "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params),
    }


@router.get("/me")
async def auth_me(db: DbSession, authorization: str | None = None):
    from app.api.deps import get_current_user
    from fastapi import Header

    # Thin wrapper — use deps properly via Depends in production routes
    raise HTTPException(status_code=400, detail="Use Authorization bearer with /api/users/me")
