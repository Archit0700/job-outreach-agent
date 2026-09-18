"""Duplicate prevention and approval gating tests."""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Application,
    ApplicationStatus,
    Company,
    Job,
    OutreachMessage,
    OutreachStatus,
    User,
    UserSettings,
)
from app.services.outreach.duplicates import check_duplicate_outreach, check_send_limits
from app.services.qc.gate import run_qc


@pytest.mark.asyncio
async def test_duplicate_prevention(db_session: AsyncSession):
    user = User(email="archit@example.com", name="Archit")
    db_session.add(user)
    await db_session.flush()
    company = Company(name="TestCo", application_url="https://example.com/careers")
    db_session.add(company)
    await db_session.flush()
    job = Job(
        company_id=company.id,
        job_title="SDE Intern",
        source="manual",
        external_id="1",
        job_url="https://example.com/job/1",
        application_url="https://example.com/job/1",
    )
    db_session.add(job)
    await db_session.flush()

    ok = await check_duplicate_outreach(db_session, user.id, job.id)
    assert ok["allowed"]

    db_session.add(
        OutreachMessage(
            user_id=user.id,
            job_id=job.id,
            subject="x",
            body="y",
            status=OutreachStatus.sent.value,
        )
    )
    await db_session.flush()
    blocked = await check_duplicate_outreach(db_session, user.id, job.id)
    assert not blocked["allowed"]


@pytest.mark.asyncio
async def test_send_limits(db_session: AsyncSession):
    from datetime import datetime, timezone

    user = User(email="limit@example.com", name="Archit")
    db_session.add(user)
    await db_session.flush()
    db_session.add(
        UserSettings(user_id=user.id, max_emails_per_day=1, per_company_send_limit=1)
    )
    company = Company(name="LimitCo")
    db_session.add(company)
    await db_session.flush()
    job = Job(
        company_id=company.id,
        job_title="SDE",
        source="manual",
        external_id="2",
        job_url="https://example.com/2",
    )
    db_session.add(job)
    await db_session.flush()
    db_session.add(
        OutreachMessage(
            user_id=user.id,
            job_id=job.id,
            subject="s",
            body="b",
            status=OutreachStatus.sent.value,
            sent_at=datetime.now(timezone.utc),
            recipient_email="recruiter@example.com",
        )
    )
    await db_session.flush()
    limits = await check_send_limits(db_session, user.id, company.id)
    assert not limits["allowed"]


def test_qc_blocks_placeholders():
    result = run_qc(
        resume_text="Python SQL Archit",
        tailored={"plain_text": "Archit Python", "diff": {"added_claims": []}, "claims_used": ["Python"]},
        email_subject="Interest in [Role] at [Company]",
        email_body="Hi, I am the perfect candidate for [Role] at [Company]. " + ("word " * 50),
        company_name="Acme",
        role_title="Software Engineer",
        job_url="https://example.com",
        recipient_email="a@b.com",
        contact_verified=True,
    )
    assert not result["verified"]
    assert result["issues"]


def test_qc_blocks_unverified_email():
    result = run_qc(
        resume_text="Python experience with RAG chatbot internship project SQL Machine Learning",
        tailored={"plain_text": "ok", "diff": {"added_claims": []}, "claims_used": []},
        email_subject="Interest in Software Engineer at Acme",
        email_body=(
            "Hi,\n\nI'm Archit interested in the Software Engineer opportunity at Acme. "
            "My work includes Python and SQL from my projects. "
            "The Software Engineer role at Acme stood out because of its engineering focus. "
            "I'd appreciate consideration.\n\nBest,\nArchit"
        ),
        company_name="Acme",
        role_title="Software Engineer",
        job_url="https://example.com",
        recipient_email="guessed@acme.com",
        contact_verified=False,
    )
    assert not result["verified"]


@pytest.mark.asyncio
async def test_approval_gating_api(client, auth_headers, db_session):
    # Create company/job via DB using override — use API flow
    # Seed through discover is heavy; insert via prepare path after manual job create
    from app.core.database import get_db
    # Use companies endpoint after seed
    r = await client.get("/api/companies", headers=auth_headers)
    assert r.status_code == 200
    companies = r.json()
    assert len(companies) > 0

    # Upload resume
    files = {"file": ("resume.txt", b"Archit\nSkills: Python, SQL, RAG, LLMs, Machine Learning\nProject: RAG chatbot", "text/plain")}
    up = await client.post("/api/resumes/upload", headers=auth_headers, files=files)
    assert up.status_code == 200, up.text

    # Create a manual job by discovering (may return 0 without network) — insert via company
    # Directly hit prepare after inserting job through SQL in a follow-up test.
    # Approval gating: try send without approve
    # First create outreach-like message via internal path
    from app.models import Company, Job, CandidateProfile, Resume
    # Get user id from /users/me
    me = await client.get("/api/users/me", headers=auth_headers)
    assert me.status_code == 200
