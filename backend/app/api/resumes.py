"""Resume upload and versions."""
from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.core.config import get_settings
from app.models import CandidateProfile, Resume, ResumeVersion
from app.schemas.schemas import ResumeOut, ResumeVersionOut
from app.services.resume.parser import extract_text, parse_resume_to_profile, text_hash

router = APIRouter(prefix="/api", tags=["resumes"])


@router.post("/resumes/upload", response_model=ResumeOut)
async def upload_resume(
    user: CurrentUser,
    db: DbSession,
    file: UploadFile = File(...),
):
    data = await file.read()
    if not data:
        raise HTTPException(400, "Empty file")
    filename = file.filename or "resume.pdf"
    try:
        raw_text = extract_text(filename, data)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e

    settings = get_settings()
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    storage_name = f"{user.id}_{uuid.uuid4().hex}_{filename}"
    path = upload_dir / storage_name
    path.write_bytes(data)

    # Demote previous masters
    result = await db.execute(select(Resume).where(Resume.user_id == user.id, Resume.is_master == True))  # noqa: E712
    for r in result.scalars().all():
        r.is_master = False

    resume = Resume(
        user_id=user.id,
        filename=filename,
        storage_path=str(path),
        content_type=file.content_type or "application/octet-stream",
        raw_text=raw_text,
        is_master=True,
    )
    db.add(resume)
    await db.flush()

    parsed = await parse_resume_to_profile(raw_text)
    profile_result = await db.execute(
        select(CandidateProfile).where(CandidateProfile.user_id == user.id)
    )
    profile = profile_result.scalar_one_or_none()
    if not profile:
        profile = CandidateProfile(user_id=user.id)
        db.add(profile)
    profile.data = parsed
    profile.skills_evidence = parsed.get("skills_evidence") or []
    profile.raw_text_hash = parsed.get("raw_text_hash") or text_hash(raw_text)
    await db.flush()
    return resume


@router.get("/resumes", response_model=list[ResumeOut])
async def list_resumes(user: CurrentUser, db: DbSession):
    result = await db.execute(select(Resume).where(Resume.user_id == user.id))
    return list(result.scalars().all())


@router.get("/resume-versions", response_model=list[ResumeVersionOut])
async def list_versions(user: CurrentUser, db: DbSession):
    result = await db.execute(
        select(ResumeVersion)
        .join(Resume, Resume.id == ResumeVersion.resume_id)
        .where(Resume.user_id == user.id)
        .order_by(ResumeVersion.created_at.desc())
    )
    return list(result.scalars().all())


@router.get("/resume-versions/{version_id}", response_model=ResumeVersionOut)
async def get_version(version_id: str, user: CurrentUser, db: DbSession):
    result = await db.execute(
        select(ResumeVersion)
        .join(Resume, Resume.id == ResumeVersion.resume_id)
        .where(ResumeVersion.id == version_id, Resume.user_id == user.id)
    )
    v = result.scalar_one_or_none()
    if not v:
        raise HTTPException(404, "Version not found")
    return v
