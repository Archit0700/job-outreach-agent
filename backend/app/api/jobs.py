"""Jobs, discovery, matching."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbSession
from app.models import Company, Job, JobMatch
from app.schemas.schemas import CompanyOut, DiscoverRequest, JobOut, MatchOut, PrepareRequest
from app.services.jobs.discovery import ensure_seed_companies, run_discovery
from app.services.matching.matcher import match_job
from app.models import CandidateProfile

router = APIRouter(prefix="/api", tags=["jobs"])


@router.get("/companies", response_model=list[CompanyOut])
async def list_companies(user: CurrentUser, db: DbSession):
    await ensure_seed_companies(db)
    result = await db.execute(select(Company).order_by(Company.name))
    return list(result.scalars().all())


@router.post("/companies")
async def add_company(user: CurrentUser, db: DbSession, name: str, careers_url: str = "", greenhouse_board: str = ""):
    result = await db.execute(select(Company).where(Company.name == name))
    c = result.scalar_one_or_none()
    if c:
        return c
    c = Company(
        name=name,
        careers_url=careers_url or None,
        application_url=careers_url or None,
        greenhouse_board=greenhouse_board or None,
        is_target=True,
    )
    db.add(c)
    await db.flush()
    return c


@router.post("/jobs/discover")
async def discover_jobs(body: DiscoverRequest, user: CurrentUser, db: DbSession):
    return await run_discovery(db, body.company_ids)


@router.get("/jobs", response_model=list[JobOut])
async def list_jobs(
    user: CurrentUser,
    db: DbSession,
    role: str | None = None,
    company: str | None = None,
    location: str | None = None,
    remote: bool | None = None,
    employment_type: str | None = None,
    min_match: float | None = Query(default=None),
    limit: int = Query(default=50, le=200),
):
    q = select(Job).options(selectinload(Job.company)).order_by(Job.created_at.desc()).limit(limit)
    result = await db.execute(q)
    jobs = list(result.scalars().all())

    # Matches map
    match_result = await db.execute(select(JobMatch).where(JobMatch.user_id == user.id))
    matches = {m.job_id: m for m in match_result.scalars().all()}

    out: list[JobOut] = []
    for j in jobs:
        if role and role.lower() not in j.job_title.lower():
            continue
        if company and company.lower() not in j.company.name.lower():
            continue
        if location and location.lower() not in (j.location or "").lower():
            continue
        if remote is not None and j.is_remote != remote:
            continue
        if employment_type and j.employment_type != employment_type:
            continue
        m = matches.get(j.id)
        score = m.overall_score if m else None
        if min_match is not None and (score is None or score < min_match):
            continue
        out.append(
            JobOut(
                id=j.id,
                company_id=j.company_id,
                company_name=j.company.name,
                job_title=j.job_title,
                location=j.location,
                employment_type=j.employment_type,
                job_url=j.job_url,
                application_url=j.application_url,
                source=j.source,
                description=j.description[:2000],
                posted_date=j.posted_date,
                is_remote=j.is_remote,
                match_score=score,
                why_this_job=m.why_this_job if m else None,
            )
        )
    return out


@router.get("/jobs/{job_id}", response_model=JobOut)
async def get_job(job_id: str, user: CurrentUser, db: DbSession):
    result = await db.execute(
        select(Job).options(selectinload(Job.company)).where(Job.id == job_id)
    )
    j = result.scalar_one_or_none()
    if not j:
        raise HTTPException(404, "Job not found")
    m_result = await db.execute(
        select(JobMatch).where(JobMatch.user_id == user.id, JobMatch.job_id == job_id)
    )
    m = m_result.scalar_one_or_none()
    return JobOut(
        id=j.id,
        company_id=j.company_id,
        company_name=j.company.name,
        job_title=j.job_title,
        location=j.location,
        employment_type=j.employment_type,
        job_url=j.job_url,
        application_url=j.application_url,
        source=j.source,
        description=j.description,
        posted_date=j.posted_date,
        is_remote=j.is_remote,
        match_score=m.overall_score if m else None,
        why_this_job=m.why_this_job if m else None,
    )


@router.post("/jobs/{job_id}/match", response_model=MatchOut)
async def match_single_job(job_id: str, user: CurrentUser, db: DbSession):
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(404, "Job not found")
    profile_result = await db.execute(
        select(CandidateProfile).where(CandidateProfile.user_id == user.id)
    )
    profile_row = profile_result.scalar_one_or_none()
    if not profile_row:
        raise HTTPException(400, "Upload resume first")
    profile = {
        "candidate": profile_row.data.get("candidate", profile_row.data),
        "skills_evidence": profile_row.skills_evidence or [],
    }
    data = await match_job(profile, job.job_title, job.description)
    m_result = await db.execute(
        select(JobMatch).where(JobMatch.user_id == user.id, JobMatch.job_id == job_id)
    )
    jm = m_result.scalar_one_or_none()
    if not jm:
        jm = JobMatch(user_id=user.id, job_id=job_id)
        db.add(jm)
    for k in (
        "overall_score",
        "technical_skills",
        "experience_score",
        "education_score",
        "projects_score",
        "role_alignment",
        "strong_matches",
        "potential_gaps",
        "why_this_job",
    ):
        setattr(jm, k if k != "overall_score" else "overall_score", data[k])
    jm.analysis = data.get("analysis") or {}
    await db.flush()
    return jm
