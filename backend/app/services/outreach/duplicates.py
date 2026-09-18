"""Duplicate prevention (SPEC §14) and send limits (SPEC §22)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Application, ApplicationStatus, Job, OutreachMessage, OutreachStatus, UserSettings


TERMINAL_BLOCK = {
    OutreachStatus.sent.value,
    OutreachStatus.approved.value,
    OutreachStatus.sending.value,
    OutreachStatus.rejected.value,
}


async def check_duplicate_outreach(
    db: AsyncSession, user_id: str, job_id: str, contact_id: str | None = None
) -> dict:
    """Return {allowed: bool, reasons: []}."""
    reasons = []

    # Already applied / closed / rejected for this job
    app_result = await db.execute(
        select(Application).where(Application.user_id == user_id, Application.job_id == job_id)
    )
    app = app_result.scalar_one_or_none()
    if app and app.status in {
        ApplicationStatus.sent.value,
        ApplicationStatus.rejected.value,
        ApplicationStatus.closed.value,
        ApplicationStatus.applied_official.value,
        ApplicationStatus.interview.value,
    }:
        reasons.append(f"Application already in status: {app.status}")

    # Existing outreach for same job
    msg_result = await db.execute(
        select(OutreachMessage).where(
            OutreachMessage.user_id == user_id,
            OutreachMessage.job_id == job_id,
            OutreachMessage.status.in_(list(TERMINAL_BLOCK)),
        )
    )
    existing = list(msg_result.scalars().all())
    if existing:
        reasons.append("Outreach already sent/approved/rejected for this role")

    # Same recruiter contacted for same company+role recently
    if contact_id:
        c_result = await db.execute(
            select(OutreachMessage).where(
                OutreachMessage.user_id == user_id,
                OutreachMessage.contact_id == contact_id,
                OutreachMessage.job_id == job_id,
                OutreachMessage.status == OutreachStatus.sent.value,
            )
        )
        if c_result.scalars().first():
            reasons.append("Already contacted this recruiter for this role")

    return {"allowed": len(reasons) == 0, "reasons": reasons}


async def check_send_limits(db: AsyncSession, user_id: str, company_id: str) -> dict:
    settings_result = await db.execute(select(UserSettings).where(UserSettings.user_id == user_id))
    settings = settings_result.scalar_one_or_none()
    daily_limit = settings.max_emails_per_day if settings else 10
    per_company = settings.per_company_send_limit if settings else 2

    since = datetime.now(timezone.utc) - timedelta(days=1)
    # Daily count
    daily_q = await db.execute(
        select(func.count())
        .select_from(OutreachMessage)
        .where(
            OutreachMessage.user_id == user_id,
            OutreachMessage.status == OutreachStatus.sent.value,
            OutreachMessage.sent_at >= since,
        )
    )
    daily_count = daily_q.scalar() or 0

    # Per-company: join jobs
    company_q = await db.execute(
        select(func.count())
        .select_from(OutreachMessage)
        .join(Job, Job.id == OutreachMessage.job_id)
        .where(
            OutreachMessage.user_id == user_id,
            Job.company_id == company_id,
            OutreachMessage.status == OutreachStatus.sent.value,
            OutreachMessage.sent_at >= since,
        )
    )
    company_count = company_q.scalar() or 0

    reasons = []
    if daily_count >= daily_limit:
        reasons.append(f"Daily send limit reached ({daily_limit})")
    if company_count >= per_company:
        reasons.append(f"Per-company send limit reached ({per_company})")
    return {
        "allowed": len(reasons) == 0,
        "reasons": reasons,
        "daily_count": daily_count,
        "company_count": company_count,
        "daily_limit": daily_limit,
        "per_company_limit": per_company,
    }
