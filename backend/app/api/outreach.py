"""Outreach prepare, review, approve, reject, send."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbSession
from app.core.config import get_settings
from app.core.security import decrypt_secret
from app.models import (
    Application,
    ApplicationStatus,
    AuditLog,
    Contact,
    EmailEvent,
    FollowUp,
    Job,
    JobMatch,
    OutreachMessage,
    OutreachStatus,
    UserSettings,
)
from app.schemas.schemas import (
    BulkApprove,
    FollowUpCreate,
    OutreachEdit,
    OutreachOut,
    PrepareRequest,
)
from app.services.email.sender import send_email
from app.services.outreach.duplicates import check_duplicate_outreach, check_send_limits
from app.services.outreach.pipeline import prepare_outreach_for_job
from app.services.qc.gate import run_qc

router = APIRouter(prefix="/api", tags=["outreach"])


async def _to_out(db, msg: OutreachMessage) -> OutreachOut:
    job_result = await db.execute(
        select(Job).options(selectinload(Job.company)).where(Job.id == msg.job_id)
    )
    job = job_result.scalar_one_or_none()
    match_score = None
    m_result = await db.execute(
        select(JobMatch).where(JobMatch.user_id == msg.user_id, JobMatch.job_id == msg.job_id)
    )
    m = m_result.scalar_one_or_none()
    if m:
        match_score = m.overall_score
    recruiter_name = None
    recruiter_confidence = None
    if msg.contact_id:
        c_result = await db.execute(select(Contact).where(Contact.id == msg.contact_id))
        c = c_result.scalar_one_or_none()
        if c:
            recruiter_name = c.name
            recruiter_confidence = c.confidence
    return OutreachOut(
        id=msg.id,
        job_id=msg.job_id,
        company_name=job.company.name if job else None,
        role=job.job_title if job else None,
        subject=msg.subject,
        body=msg.body,
        status=msg.status,
        recipient_email=msg.recipient_email,
        recruiter_name=recruiter_name,
        recruiter_confidence=recruiter_confidence,
        match_score=match_score,
        qc_verified=msg.qc_verified,
        qc_issues=msg.qc_issues or [],
        personalization=msg.personalization or {},
        fallback_application_url=msg.fallback_application_url,
        resume_version_id=msg.resume_version_id,
        sent_at=msg.sent_at,
        created_at=msg.created_at,
    )


@router.post("/outreach/prepare", response_model=OutreachOut)
async def prepare(body: PrepareRequest, user: CurrentUser, db: DbSession):
    try:
        msg = await prepare_outreach_for_job(db, user.id, body.job_id, use_llm=body.use_llm)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return await _to_out(db, msg)


@router.get("/outreach", response_model=list[OutreachOut])
async def list_outreach(user: CurrentUser, db: DbSession, status: str | None = None):
    q = select(OutreachMessage).where(OutreachMessage.user_id == user.id).order_by(
        OutreachMessage.created_at.desc()
    )
    if status:
        q = q.where(OutreachMessage.status == status)
    result = await db.execute(q)
    msgs = list(result.scalars().all())
    return [await _to_out(db, m) for m in msgs]


@router.get("/outreach/{message_id}", response_model=OutreachOut)
async def get_outreach(message_id: str, user: CurrentUser, db: DbSession):
    result = await db.execute(
        select(OutreachMessage).where(
            OutreachMessage.id == message_id, OutreachMessage.user_id == user.id
        )
    )
    msg = result.scalar_one_or_none()
    if not msg:
        raise HTTPException(404, "Not found")
    return await _to_out(db, msg)


@router.patch("/outreach/{message_id}", response_model=OutreachOut)
async def edit_outreach(message_id: str, body: OutreachEdit, user: CurrentUser, db: DbSession):
    result = await db.execute(
        select(OutreachMessage).where(
            OutreachMessage.id == message_id, OutreachMessage.user_id == user.id
        )
    )
    msg = result.scalar_one_or_none()
    if not msg:
        raise HTTPException(404, "Not found")
    if msg.status == OutreachStatus.sent.value:
        raise HTTPException(400, "Cannot edit sent message")
    edits = dict(msg.user_edits or {})
    if body.subject is not None:
        edits["subject_before"] = msg.subject
        msg.subject = body.subject
    if body.body is not None:
        edits["body_before"] = msg.body
        msg.body = body.body
    msg.user_edits = edits
    # Re-run lightweight QC on content
    from app.models import Resume

    resume_result = await db.execute(
        select(Resume).where(Resume.user_id == user.id, Resume.is_master == True).limit(1)  # noqa: E712
    )
    resume = resume_result.scalar_one_or_none()
    job_result = await db.execute(
        select(Job).options(selectinload(Job.company)).where(Job.id == msg.job_id)
    )
    job = job_result.scalar_one()
    qc = run_qc(
        resume_text=resume.raw_text if resume else "",
        tailored={"plain_text": "", "diff": {"added_claims": []}, "claims_used": []},
        email_subject=msg.subject,
        email_body=msg.body,
        company_name=job.company.name,
        role_title=job.job_title,
        job_url=job.job_url,
        recipient_email=msg.recipient_email,
        contact_verified=bool(msg.recipient_email),
    )
    msg.qc_verified = qc["verified"]
    msg.qc_issues = qc["issues"]
    if msg.status == OutreachStatus.blocked_qc.value and qc["verified"]:
        msg.status = OutreachStatus.pending_review.value
    await db.flush()
    return await _to_out(db, msg)


@router.post("/outreach/{message_id}/approve", response_model=OutreachOut)
async def approve(message_id: str, user: CurrentUser, db: DbSession):
    result = await db.execute(
        select(OutreachMessage).where(
            OutreachMessage.id == message_id, OutreachMessage.user_id == user.id
        )
    )
    msg = result.scalar_one_or_none()
    if not msg:
        raise HTTPException(404, "Not found")
    if msg.status in {
        OutreachStatus.blocked_duplicate.value,
        OutreachStatus.blocked_limit.value,
        OutreachStatus.sent.value,
        OutreachStatus.rejected.value,
    }:
        raise HTTPException(400, f"Cannot approve from status {msg.status}")
    if msg.status == OutreachStatus.no_contact.value:
        raise HTTPException(
            400,
            "No verified contact — use official application URL instead of email send",
        )
    if not msg.qc_verified:
        raise HTTPException(400, f"QC not verified: {msg.qc_issues}")
    msg.status = OutreachStatus.approved.value
    msg.approved_at = datetime.now(timezone.utc)
    db.add(AuditLog(user_id=user.id, action="outreach_approved", detail={"message_id": msg.id}))
    await db.flush()
    return await _to_out(db, msg)


@router.post("/outreach/{message_id}/reject", response_model=OutreachOut)
async def reject(message_id: str, user: CurrentUser, db: DbSession):
    result = await db.execute(
        select(OutreachMessage).where(
            OutreachMessage.id == message_id, OutreachMessage.user_id == user.id
        )
    )
    msg = result.scalar_one_or_none()
    if not msg:
        raise HTTPException(404, "Not found")
    msg.status = OutreachStatus.rejected.value
    app_result = await db.execute(
        select(Application).where(Application.user_id == user.id, Application.job_id == msg.job_id)
    )
    app = app_result.scalar_one_or_none()
    if app:
        app.status = ApplicationStatus.rejected.value
    # Cancel followups
    fu_result = await db.execute(select(FollowUp).where(FollowUp.message_id == msg.id))
    for fu in fu_result.scalars().all():
        fu.status = "cancelled"
        fu.enabled = False
    await db.flush()
    return await _to_out(db, msg)


@router.post("/outreach/{message_id}/save", response_model=OutreachOut)
async def save_for_later(message_id: str, user: CurrentUser, db: DbSession):
    result = await db.execute(
        select(OutreachMessage).where(
            OutreachMessage.id == message_id, OutreachMessage.user_id == user.id
        )
    )
    msg = result.scalar_one_or_none()
    if not msg:
        raise HTTPException(404, "Not found")
    msg.status = OutreachStatus.saved.value
    await db.flush()
    return await _to_out(db, msg)


@router.post("/outreach/bulk-approve")
async def bulk_approve(body: BulkApprove, user: CurrentUser, db: DbSession):
    """Bulk approve only explicitly selected message IDs (SPEC §10)."""
    if not body.message_ids:
        raise HTTPException(400, "No messages selected")
    results = []
    for mid in body.message_ids:
        try:
            out = await approve(mid, user, db)
            results.append({"id": mid, "ok": True, "status": out.status})
        except HTTPException as e:
            results.append({"id": mid, "ok": False, "error": e.detail})
    return {"results": results}


@router.post("/outreach/{message_id}/send", response_model=OutreachOut)
async def send(message_id: str, user: CurrentUser, db: DbSession, provider: str = "noop"):
    """Send only after approval. Never auto-send (SPEC §10–11, §22)."""
    settings = get_settings()
    result = await db.execute(
        select(OutreachMessage).where(
            OutreachMessage.id == message_id, OutreachMessage.user_id == user.id
        )
    )
    msg = result.scalar_one_or_none()
    if not msg:
        raise HTTPException(404, "Not found")

    user_settings_result = await db.execute(
        select(UserSettings).where(UserSettings.user_id == user.id)
    )
    user_settings = user_settings_result.scalar_one_or_none()
    require = settings.require_approval if not user_settings else user_settings.require_manual_approval
    if require and msg.status != OutreachStatus.approved.value:
        raise HTTPException(400, "Message must be approved before send")

    if not msg.recipient_email:
        raise HTTPException(400, "No recipient — use application URL fallback")
    if not msg.qc_verified:
        raise HTTPException(400, "QC gate blocked send")

    job_result = await db.execute(select(Job).where(Job.id == msg.job_id))
    job = job_result.scalar_one()

    dup = await check_duplicate_outreach(db, user.id, msg.job_id, msg.contact_id)
    # Allow if this message itself was the approved one — check other sent
    sent_check = await db.execute(
        select(OutreachMessage).where(
            OutreachMessage.user_id == user.id,
            OutreachMessage.job_id == msg.job_id,
            OutreachMessage.status == OutreachStatus.sent.value,
            OutreachMessage.id != msg.id,
        )
    )
    if sent_check.scalars().first():
        msg.status = OutreachStatus.blocked_duplicate.value
        await db.flush()
        raise HTTPException(400, "Duplicate: already sent for this role")

    limits = await check_send_limits(db, user.id, job.company_id)
    if not limits["allowed"]:
        msg.status = OutreachStatus.blocked_limit.value
        msg.qc_issues = limits["reasons"]
        await db.flush()
        raise HTTPException(400, f"Send limits: {limits['reasons']}")

    # Block list
    if user_settings and msg.recipient_email in (user_settings.block_list_emails or []):
        raise HTTPException(400, "Recipient is on block list")

    access_token = None
    if provider == "gmail" and user.gmail_token_enc:
        try:
            access_token = decrypt_secret(user.gmail_token_enc)
        except ValueError:
            access_token = None
    elif provider in {"microsoft", "outlook"} and user.microsoft_token_enc:
        try:
            access_token = decrypt_secret(user.microsoft_token_enc)
        except ValueError:
            access_token = None

    msg.status = OutreachStatus.sending.value
    await db.flush()

    send_result = await send_email(
        provider=provider,
        access_token=access_token,
        to=msg.recipient_email,
        subject=msg.subject,
        body=msg.body,
    )

    if not send_result.success:
        msg.status = OutreachStatus.failed.value
        db.add(
            EmailEvent(
                message_id=msg.id,
                event_type="failed",
                payload={"detail": send_result.detail, "provider": send_result.provider},
            )
        )
        await db.flush()
        raise HTTPException(502, f"Send failed: {send_result.detail}")

    msg.status = OutreachStatus.sent.value
    msg.sent_at = datetime.now(timezone.utc)
    db.add(
        EmailEvent(
            message_id=msg.id,
            event_type="sent",
            payload={
                "provider": send_result.provider,
                "noop": send_result.noop,
                "message_id": send_result.message_id,
                "detail": send_result.detail,
            },
        )
    )
    app_result = await db.execute(
        select(Application).where(Application.user_id == user.id, Application.job_id == msg.job_id)
    )
    app = app_result.scalar_one_or_none()
    if app:
        app.status = ApplicationStatus.sent.value
        app.applied_at = msg.sent_at

    # Schedule follow-ups only if enabled
    if user_settings and user_settings.followups_enabled:
        for i, days in enumerate(user_settings.followup_days or [5, 12], start=1):
            from datetime import timedelta

            fu_body = (
                f"Hi,\n\nJust a brief follow-up on my application for {job.job_title}. "
                f"Happy to share more details if helpful.\n\nBest,\n{user.name}"
            )
            db.add(
                FollowUp(
                    message_id=msg.id,
                    scheduled_for=msg.sent_at + timedelta(days=days),
                    body=fu_body,
                    sequence_number=i,
                    status="scheduled",
                    enabled=True,
                )
            )

    db.add(
        AuditLog(
            user_id=user.id,
            action="outreach_sent",
            detail={"message_id": msg.id, "noop": send_result.noop, "provider": send_result.provider},
        )
    )
    await db.flush()
    return await _to_out(db, msg)


@router.post("/followups")
async def create_followup(body: FollowUpCreate, user: CurrentUser, db: DbSession):
    result = await db.execute(
        select(OutreachMessage).where(
            OutreachMessage.id == body.message_id, OutreachMessage.user_id == user.id
        )
    )
    msg = result.scalar_one_or_none()
    if not msg:
        raise HTTPException(404, "Message not found")
    from datetime import timedelta

    fu = FollowUp(
        message_id=msg.id,
        scheduled_for=datetime.now(timezone.utc) + timedelta(days=body.days_from_now),
        body=body.body
        or "Hi,\n\nBrief follow-up on my earlier note — happy to provide anything else useful.\n\nBest",
        sequence_number=1,
        status="scheduled",
        enabled=True,
    )
    db.add(fu)
    await db.flush()
    return {"id": fu.id, "scheduled_for": fu.scheduled_for, "enabled": fu.enabled}
