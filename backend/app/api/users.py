"""User profile and settings."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.models import CandidateProfile, UserSettings
from app.schemas.schemas import ProfileOut, SettingsOut, SettingsUpdate, UserOut

router = APIRouter(prefix="/api", tags=["users"])


@router.get("/users/me", response_model=UserOut)
async def me(user: CurrentUser):
    return user


@router.get("/profile", response_model=ProfileOut)
async def get_profile(user: CurrentUser, db: DbSession):
    result = await db.execute(select(CandidateProfile).where(CandidateProfile.user_id == user.id))
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(404, "No profile — upload a resume first")
    return profile


@router.get("/settings", response_model=SettingsOut)
async def get_settings(user: CurrentUser, db: DbSession):
    result = await db.execute(select(UserSettings).where(UserSettings.user_id == user.id))
    s = result.scalar_one_or_none()
    if not s:
        raise HTTPException(404, "Settings not found")
    return s


@router.patch("/settings", response_model=SettingsOut)
async def update_settings(body: SettingsUpdate, user: CurrentUser, db: DbSession):
    result = await db.execute(select(UserSettings).where(UserSettings.user_id == user.id))
    s = result.scalar_one_or_none()
    if not s:
        raise HTTPException(404, "Settings not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(s, k, v)
    await db.flush()
    return s
