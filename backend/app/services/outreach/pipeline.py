"""End-to-end outreach preparation pipeline for a job."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    Application,
    ApplicationStatus,
    CandidateProfile,
    Company,
    Job,
    JobMatch,
    OutreachMessage,
    OutreachStatus,
    Resume,
    ResumeVersion,
)
from app.services.contacts.discovery import resolve_outreach_recipient
from app.services.matching.matcher import match_job
from app.services.outreach.duplicates import check_duplicate_outreach
from app.services.outreach.email_gen import generate_email
from app.services.qc.gate import run_qc
from app.services.tailoring.tailor import tailor_resume


async def prepare_outreach_for_job(
    db: AsyncSession,
    user_id: str,
    job_id: str,
    *,
    use_llm: bool = False,
) -> OutreachMessage:
    job_result = await db.execute(
        select(Job).options(selectinload(Job.company)).where(Job.id == job_id)
    )
    job = job_result.scalar_one()
    company: Company = job.company

    profile_result = await db.execute(
        select(CandidateProfile).where(CandidateProfile.user_id == user_id)
    )
    profile_row = profile_result.scalar_one_or_none()
    if not profile_row:
        raise ValueError("Candidate profile required — upload resume first")
    profile = {
        "candidate": profile_row.data.get("candidate", profile_row.data),
        "skills_evidence": profile_row.skills_evidence or profile_row.data.get("skills_evidence", []),
    }

    resume_result = await db.execute(
        select(Resume).where(Resume.user_id == user_id, Resume.is_master == True).limit(1)  # noqa: E712
    )
    resume = resume_result.scalar_one_or_none()
    resume_text = resume.raw_text if resume else ""

    dup = await check_duplicate_outreach(db, user_id, job_id)
    if not dup["allowed"]:
        msg = OutreachMessage(
            user_id=user_id,
            job_id=job_id,
            subject="",
            body="",
            status=OutreachStatus.blocked_duplicate.value,
            qc_issues=dup["reasons"],
            fallback_application_url=job.application_url or company.application_url,
        )
        db.add(msg)
        await db.flush()
        return msg

    # Match
    match_data = await match_job(profile, job.job_title, job.description, use_llm=use_llm)
    match_result = await db.execute(
        select(JobMatch).where(JobMatch.user_id == user_id, JobMatch.job_id == job_id)
    )
    jm = match_result.scalar_one_or_none()
    if not jm:
        jm = JobMatch(user_id=user_id, job_id=job_id)
        db.add(jm)
    jm.overall_score = match_data["overall_score"]
    jm.technical_skills = match_data["technical_skills"]
    jm.experience_score = match_data["experience_score"]
    jm.education_score = match_data["education_score"]
    jm.projects_score = match_data["projects_score"]
    jm.role_alignment = match_data["role_alignment"]
    jm.strong_matches = match_data["strong_matches"]
    jm.potential_gaps = match_data["potential_gaps"]
    jm.why_this_job = match_data["why_this_job"]
    jm.analysis = match_data.get("analysis") or {}
    await db.flush()

    # Tailor
    tailored = await tailor_resume(
        profile, resume_text, job.job_title, job.description, use_llm=use_llm
    )
    rv = ResumeVersion(
        resume_id=resume.id if resume else None,
        job_id=job.id,
        content=tailored.get("content") or {},
        plain_text=tailored.get("plain_text") or "",
        diff=tailored.get("diff") or {},
        qc_passed=not tailored.get("fabrication_issues"),
        qc_issues=tailored.get("fabrication_issues") or [],
    )
    if resume:
        db.add(rv)
        await db.flush()

    # Contact
    recipient = await resolve_outreach_recipient(db, company)
    contact = recipient.get("contact")
    mode = recipient["mode"]

    email_data = await generate_email(
        profile=profile,
        job_title=job.job_title,
        company_name=company.name,
        description=job.description,
        strong_matches=match_data["strong_matches"],
        recruiter_name=contact.name if contact else None,
        use_llm=use_llm,
    )

    qc = run_qc(
        resume_text=resume_text,
        tailored=tailored,
        email_subject=email_data["subject"],
        email_body=email_data["body"],
        company_name=company.name,
        role_title=job.job_title,
        job_url=job.job_url,
        recruiter_name=contact.name if contact else None,
        recipient_email=contact.email if contact else None,
        contact_verified=bool(contact and contact.verified and not contact.is_guessed),
    )

    if mode == "application_url":
        status = OutreachStatus.no_contact.value
        # QC for email content still useful for review, but send blocked
        qc_verified = False
        qc_issues = list(qc["issues"]) + ["No verified public contact — use official application URL"]
    elif not qc["verified"]:
        status = OutreachStatus.blocked_qc.value
        qc_verified = False
        qc_issues = qc["issues"]
    else:
        status = OutreachStatus.pending_review.value
        qc_verified = True
        qc_issues = []

    msg = OutreachMessage(
        user_id=user_id,
        job_id=job_id,
        contact_id=contact.id if contact else None,
        resume_version_id=rv.id if resume else None,
        subject=email_data["subject"],
        body=email_data["body"],
        personalization=email_data.get("personalization") or {},
        status=status,
        recipient_email=contact.email if contact else None,
        qc_verified=qc_verified,
        qc_issues=qc_issues,
        fallback_application_url=recipient.get("application_url") or job.application_url,
    )
    db.add(msg)

    # Application row
    app_result = await db.execute(
        select(Application).where(Application.user_id == user_id, Application.job_id == job_id)
    )
    app = app_result.scalar_one_or_none()
    if not app:
        app = Application(user_id=user_id, job_id=job_id, status=ApplicationStatus.outreach_ready.value)
        db.add(app)
    else:
        app.status = ApplicationStatus.outreach_ready.value

    await db.flush()
    return msg
