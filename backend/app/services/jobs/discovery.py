"""Job discovery orchestration across adapters."""
from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Company, Job
from app.services.jobs.base import DiscoveredJob, JobSourceAdapter
from app.services.jobs.greenhouse import GreenhouseAdapter
from app.services.jobs.lever import LeverAdapter
from app.services.jobs.stub_sources import (
    LinkedInStubAdapter,
    WellfoundStubAdapter,
    WorkdayStubAdapter,
)

# Known Greenhouse board tokens for SPEC §19 companies (public boards where known)
# These are public board names — may 404 if company changed boards; that's OK.
DEFAULT_GREENHOUSE_BOARDS: dict[str, str] = {
    "Stripe": "stripe",
    "Airbnb": "airbnb",
    "Coinbase": "coinbase",
    "Discord": "discord",
    "Dropbox": "dropbox",
    "Figma": "figma",
    "Notion": "notion",
    "Databricks": "databricks",
    "Cloudflare": "cloudflare",
    "Pinterest": "pinterest",
}

DEFAULT_LEVER_BOARDS: dict[str, str] = {
    "Netflix": "netflix",
    "Uber": "uber",
    "Shopify": "shopify",
}

# Spec §19 target list — careers URLs as official fallbacks
SPEC_TARGET_COMPANIES = [
    ("Google", "https://careers.google.com/", None, None),
    ("Microsoft", "https://careers.microsoft.com/", None, None),
    ("Amazon", "https://www.amazon.jobs/", None, None),
    ("Adobe", "https://careers.adobe.com/", None, None),
    ("Atlassian", "https://www.atlassian.com/company/careers", None, None),
    ("Deloitte", "https://www.deloitte.com/careers", None, None),
    ("PwC", "https://www.pwc.com/careers", None, None),
    ("EY", "https://www.ey.com/careers", None, None),
    ("KPMG", "https://home.kpmg/careers", None, None),
    ("ZS", "https://www.zs.com/careers", None, None),
    ("Mu Sigma", "https://www.mu-sigma.com/careers", None, None),
    ("Tredence", "https://www.tredence.com/careers", None, None),
    ("BlackRock", "https://careers.blackrock.com/", None, None),
]


def get_adapter(source: str) -> JobSourceAdapter:
    mapping = {
        "greenhouse": GreenhouseAdapter(),
        "lever": LeverAdapter(),
        "workday": WorkdayStubAdapter(),
        "wellfound": WellfoundStubAdapter(),
        "linkedin": LinkedInStubAdapter(),
    }
    return mapping.get(source, WorkdayStubAdapter())


async def ensure_seed_companies(db: AsyncSession) -> list[Company]:
    companies = []
    for name, url, gh, lever in SPEC_TARGET_COMPANIES:
        result = await db.execute(select(Company).where(Company.name == name))
        c = result.scalar_one_or_none()
        if not c:
            c = Company(
                name=name,
                careers_url=url,
                application_url=url,
                greenhouse_board=gh or DEFAULT_GREENHOUSE_BOARDS.get(name),
                lever_board=lever or DEFAULT_LEVER_BOARDS.get(name),
                is_target=True,
            )
            db.add(c)
            await db.flush()
        companies.append(c)

    # Also seed companies with known public Greenhouse boards for live discovery
    for name, board in DEFAULT_GREENHOUSE_BOARDS.items():
        result = await db.execute(select(Company).where(Company.name == name))
        c = result.scalar_one_or_none()
        if not c:
            c = Company(
                name=name,
                greenhouse_board=board,
                careers_url=f"https://boards.greenhouse.io/{board}",
                application_url=f"https://boards.greenhouse.io/{board}",
                is_target=True,
            )
            db.add(c)
            await db.flush()
            companies.append(c)
        elif not c.greenhouse_board:
            c.greenhouse_board = board
    await db.flush()
    return companies


async def upsert_discovered_job(db: AsyncSession, company: Company, dj: DiscoveredJob) -> Job:
    result = await db.execute(
        select(Job).where(Job.source == dj.source, Job.external_id == dj.external_id)
    )
    job = result.scalar_one_or_none()
    if job:
        job.job_title = dj.job_title
        job.location = dj.location
        job.description = dj.description
        job.job_url = dj.job_url
        job.application_url = dj.application_url
        job.employment_type = dj.employment_type
        job.is_remote = dj.is_remote
        job.posted_date = dj.posted_date
        return job
    job = Job(
        company_id=company.id,
        external_id=dj.external_id or dj.job_url,
        job_title=dj.job_title,
        location=dj.location,
        employment_type=dj.employment_type,
        job_url=dj.job_url,
        application_url=dj.application_url or dj.job_url,
        source=dj.source,
        description=dj.description,
        posted_date=dj.posted_date,
        is_remote=dj.is_remote,
        raw_payload=dj.raw_payload,
    )
    db.add(job)
    await db.flush()
    return job


async def discover_for_company(db: AsyncSession, company: Company) -> list[Job]:
    found: list[Job] = []
    if company.greenhouse_board:
        adapter = GreenhouseAdapter()
        try:
            djs = await adapter.fetch_jobs(company.greenhouse_board, company.name)
            for dj in GreenhouseAdapter.filter_relevant(djs):
                found.append(await upsert_discovered_job(db, company, dj))
        except Exception:
            pass
    if company.lever_board:
        adapter = LeverAdapter()
        try:
            djs = await adapter.fetch_jobs(company.lever_board, company.name)
            for dj in djs:
                found.append(await upsert_discovered_job(db, company, dj))
        except Exception:
            pass
    return found


async def run_discovery(db: AsyncSession, company_ids: Optional[list[str]] = None) -> dict:
    await ensure_seed_companies(db)
    q = select(Company).where(Company.is_target == True, Company.is_excluded == False)  # noqa: E712
    if company_ids:
        q = q.where(Company.id.in_(company_ids))
    result = await db.execute(q)
    companies = list(result.scalars().all())
    total = 0
    by_company = {}
    for c in companies:
        jobs = await discover_for_company(db, c)
        by_company[c.name] = len(jobs)
        total += len(jobs)
    await db.flush()
    return {"jobs_upserted": total, "by_company": by_company, "companies_scanned": len(companies)}
