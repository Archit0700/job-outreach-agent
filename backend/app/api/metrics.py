"""Dashboard metrics (SPEC §13)."""
from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DbSession
from app.models import (
    Application,
    ApplicationStatus,
    FollowUp,
    Job,
    JobMatch,
    OutreachMessage,
    OutreachStatus,
)
from app.schemas.schemas import MetricsOut

router = APIRouter(prefix="/api", tags=["metrics"])


@router.get("/metrics", response_model=MetricsOut)
async def metrics(user: CurrentUser, db: DbSession):
    jobs_found = (await db.execute(select(func.count()).select_from(Job))).scalar() or 0
    relevant = (
        await db.execute(
            select(func.count())
            .select_from(JobMatch)
            .where(JobMatch.user_id == user.id, JobMatch.overall_score >= 60)
        )
    ).scalar() or 0
    approved = (
        await db.execute(
            select(func.count())
            .select_from(OutreachMessage)
            .where(
                OutreachMessage.user_id == user.id,
                OutreachMessage.status.in_(
                    [OutreachStatus.approved.value, OutreachStatus.sent.value]
                ),
            )
        )
    ).scalar() or 0
    sent = (
        await db.execute(
            select(func.count())
            .select_from(OutreachMessage)
            .where(
                OutreachMessage.user_id == user.id,
                OutreachMessage.status == OutreachStatus.sent.value,
            )
        )
    ).scalar() or 0
    pending = (
        await db.execute(
            select(func.count())
            .select_from(OutreachMessage)
            .where(
                OutreachMessage.user_id == user.id,
                OutreachMessage.status == OutreachStatus.pending_review.value,
            )
        )
    ).scalar() or 0
    responses = (
        await db.execute(
            select(func.count())
            .select_from(Application)
            .where(
                Application.user_id == user.id,
                Application.status == ApplicationStatus.responded.value,
            )
        )
    ).scalar() or 0
    interviews = (
        await db.execute(
            select(func.count())
            .select_from(Application)
            .where(
                Application.user_id == user.id,
                Application.status == ApplicationStatus.interview.value,
            )
        )
    ).scalar() or 0
    rejected = (
        await db.execute(
            select(func.count())
            .select_from(OutreachMessage)
            .where(
                OutreachMessage.user_id == user.id,
                OutreachMessage.status == OutreachStatus.rejected.value,
            )
        )
    ).scalar() or 0
    followups = (
        await db.execute(
            select(func.count())
            .select_from(FollowUp)
            .join(OutreachMessage, OutreachMessage.id == FollowUp.message_id)
            .where(OutreachMessage.user_id == user.id, FollowUp.enabled == True)  # noqa: E712
        )
    ).scalar() or 0

    return MetricsOut(
        jobs_found=jobs_found,
        relevant_jobs=relevant,
        emails_approved=approved,
        emails_sent=sent,
        responses=responses,
        interviews=interviews,
        pending_reviews=pending,
        followups=followups,
        rejected=rejected,
    )
