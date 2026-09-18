"""All ORM models per SPEC §17."""
from __future__ import annotations

import enum
import uuid
from datetime import date, datetime
from typing import Any, Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON, TypeDecorator

from app.core.database import Base


# Use JSON that works on both Postgres and SQLite (tests)
class JSONType(TypeDecorator):
    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB())
        return dialect.type_descriptor(JSON())


def _uuid() -> str:
    return str(uuid.uuid4())


class EmploymentType(str, enum.Enum):
    internship = "internship"
    full_time = "full_time"
    contract = "contract"
    unknown = "unknown"


class OutreachStatus(str, enum.Enum):
    draft = "draft"
    pending_review = "pending_review"
    approved = "approved"
    rejected = "rejected"
    saved = "saved"
    sending = "sending"
    sent = "sent"
    failed = "failed"
    blocked_qc = "blocked_qc"
    blocked_duplicate = "blocked_duplicate"
    blocked_limit = "blocked_limit"
    no_contact = "no_contact"  # fallback to application URL


class ApplicationStatus(str, enum.Enum):
    discovered = "discovered"
    matched = "matched"
    tailored = "tailored"
    outreach_ready = "outreach_ready"
    sent = "sent"
    responded = "responded"
    interview = "interview"
    rejected = "rejected"
    closed = "closed"
    applied_official = "applied_official"


class ContactConfidence(str, enum.Enum):
    high = "high"
    medium = "medium"
    low = "low"
    none = "none"


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    oauth_provider: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    oauth_subject: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    # Encrypted OAuth tokens for Gmail/Outlook sending
    gmail_token_enc: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    microsoft_token_enc: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    profile: Mapped[Optional["CandidateProfile"]] = relationship(back_populates="user", uselist=False)
    resumes: Mapped[list["Resume"]] = relationship(back_populates="user")
    settings: Mapped[Optional["UserSettings"]] = relationship(back_populates="user", uselist=False)
    applications: Mapped[list["Application"]] = relationship(back_populates="user")
    outreach_messages: Mapped[list["OutreachMessage"]] = relationship(back_populates="user")


class CandidateProfile(Base):
    __tablename__ = "candidate_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), unique=True)
    # Canonical structured profile (SPEC §3)
    data: Mapped[dict] = mapped_column(JSONType, default=dict)
    # Skills with evidence: [{skill, evidence: []}]
    skills_evidence: Mapped[list] = mapped_column(JSONType, default=list)
    raw_text_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="profile")


class Resume(Base):
    __tablename__ = "resumes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    filename: Mapped[str] = mapped_column(String(512))
    storage_path: Mapped[str] = mapped_column(String(1024))
    content_type: Mapped[str] = mapped_column(String(128))
    raw_text: Mapped[str] = mapped_column(Text, default="")
    is_master: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="resumes")
    versions: Mapped[list["ResumeVersion"]] = relationship(back_populates="source_resume")


class ResumeVersion(Base):
    __tablename__ = "resume_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    resume_id: Mapped[str] = mapped_column(String(36), ForeignKey("resumes.id"), index=True)
    job_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("jobs.id"), nullable=True)
    # Tailored structured content + plain text + diff
    content: Mapped[dict] = mapped_column(JSONType, default=dict)
    plain_text: Mapped[str] = mapped_column(Text, default="")
    diff: Mapped[dict] = mapped_column(JSONType, default=dict)
    qc_passed: Mapped[bool] = mapped_column(Boolean, default=False)
    qc_issues: Mapped[list] = mapped_column(JSONType, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    source_resume: Mapped["Resume"] = relationship(back_populates="versions")
    job: Mapped[Optional["Job"]] = relationship(back_populates="resume_versions")


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    careers_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    greenhouse_board: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    lever_board: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    application_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    is_target: Mapped[bool] = mapped_column(Boolean, default=True)
    is_excluded: Mapped[bool] = mapped_column(Boolean, default=False)
    meta: Mapped[dict] = mapped_column(JSONType, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    jobs: Mapped[list["Job"]] = relationship(back_populates="company")
    contacts: Mapped[list["Contact"]] = relationship(back_populates="company")


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (UniqueConstraint("source", "external_id", name="uq_job_source_external"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), index=True)
    external_id: Mapped[str] = mapped_column(String(255), default="")
    job_title: Mapped[str] = mapped_column(String(512))
    location: Mapped[str] = mapped_column(String(512), default="")
    employment_type: Mapped[str] = mapped_column(String(50), default=EmploymentType.unknown.value)
    job_url: Mapped[str] = mapped_column(String(2048), default="")
    application_url: Mapped[str] = mapped_column(String(2048), default="")
    source: Mapped[str] = mapped_column(String(100), index=True)  # greenhouse, lever, stub, manual
    description: Mapped[str] = mapped_column(Text, default="")
    posted_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    is_remote: Mapped[bool] = mapped_column(Boolean, default=False)
    raw_payload: Mapped[dict] = mapped_column(JSONType, default=dict)
    # Embedding stored as JSON list for sqlite compatibility; pgvector used when available
    embedding: Mapped[Optional[list]] = mapped_column(JSONType, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    company: Mapped["Company"] = relationship(back_populates="jobs")
    matches: Mapped[list["JobMatch"]] = relationship(back_populates="job")
    resume_versions: Mapped[list["ResumeVersion"]] = relationship(back_populates="job")
    applications: Mapped[list["Application"]] = relationship(back_populates="job")


class JobMatch(Base):
    __tablename__ = "job_matches"
    __table_args__ = (UniqueConstraint("user_id", "job_id", name="uq_user_job_match"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("jobs.id"), index=True)
    overall_score: Mapped[float] = mapped_column(Float, default=0.0)
    technical_skills: Mapped[float] = mapped_column(Float, default=0.0)
    experience_score: Mapped[float] = mapped_column(Float, default=0.0)
    education_score: Mapped[float] = mapped_column(Float, default=0.0)
    projects_score: Mapped[float] = mapped_column(Float, default=0.0)
    role_alignment: Mapped[float] = mapped_column(Float, default=0.0)
    strong_matches: Mapped[list] = mapped_column(JSONType, default=list)
    potential_gaps: Mapped[list] = mapped_column(JSONType, default=list)
    why_this_job: Mapped[dict] = mapped_column(JSONType, default=dict)
    analysis: Mapped[dict] = mapped_column(JSONType, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    job: Mapped["Job"] = relationship(back_populates="matches")


class Contact(Base):
    __tablename__ = "contacts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), index=True)
    name: Mapped[str] = mapped_column(String(255), default="")
    email: Mapped[Optional[str]] = mapped_column(String(320), nullable=True)
    role: Mapped[str] = mapped_column(String(255), default="")
    source: Mapped[str] = mapped_column(String(512), default="")  # URL or "user_provided"
    confidence: Mapped[str] = mapped_column(String(20), default=ContactConfidence.none.value)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    # Never store guessed emails as verified
    is_guessed: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    company: Mapped["Company"] = relationship(back_populates="contacts")


class OutreachCampaign(Base):
    __tablename__ = "outreach_campaigns"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(255), default="Default")
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    messages: Mapped[list["OutreachMessage"]] = relationship(back_populates="campaign")


class OutreachMessage(Base):
    __tablename__ = "outreach_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    campaign_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("outreach_campaigns.id"), nullable=True
    )
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("jobs.id"), index=True)
    contact_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("contacts.id"), nullable=True)
    resume_version_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("resume_versions.id"), nullable=True
    )
    subject: Mapped[str] = mapped_column(String(998), default="")
    body: Mapped[str] = mapped_column(Text, default="")
    personalization: Mapped[dict] = mapped_column(JSONType, default=dict)
    status: Mapped[str] = mapped_column(String(50), default=OutreachStatus.draft.value, index=True)
    recipient_email: Mapped[Optional[str]] = mapped_column(String(320), nullable=True)
    qc_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    qc_issues: Mapped[list] = mapped_column(JSONType, default=list)
    fallback_application_url: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    user_edits: Mapped[dict] = mapped_column(JSONType, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="outreach_messages")
    campaign: Mapped[Optional["OutreachCampaign"]] = relationship(back_populates="messages")
    followups: Mapped[list["FollowUp"]] = relationship(back_populates="message")
    events: Mapped[list["EmailEvent"]] = relationship(back_populates="message")


class EmailEvent(Base):
    __tablename__ = "email_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    message_id: Mapped[str] = mapped_column(String(36), ForeignKey("outreach_messages.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(50))  # sent, failed, bounced, reply_detected
    payload: Mapped[dict] = mapped_column(JSONType, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    message: Mapped["OutreachMessage"] = relationship(back_populates="events")


class Application(Base):
    __tablename__ = "applications"
    __table_args__ = (UniqueConstraint("user_id", "job_id", name="uq_user_job_application"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("jobs.id"), index=True)
    status: Mapped[str] = mapped_column(String(50), default=ApplicationStatus.discovered.value)
    notes: Mapped[str] = mapped_column(Text, default="")
    applied_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="applications")
    job: Mapped["Job"] = relationship(back_populates="applications")


class FollowUp(Base):
    __tablename__ = "followups"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    message_id: Mapped[str] = mapped_column(String(36), ForeignKey("outreach_messages.id"), index=True)
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    body: Mapped[str] = mapped_column(Text, default="")
    sequence_number: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(50), default="scheduled")  # scheduled, sent, cancelled
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)  # only when user opts in
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    message: Mapped["OutreachMessage"] = relationship(back_populates="followups")


class UserSettings(Base):
    __tablename__ = "settings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), unique=True)
    target_roles: Mapped[list] = mapped_column(JSONType, default=list)
    preferred_locations: Mapped[list] = mapped_column(JSONType, default=list)
    remote_preference: Mapped[str] = mapped_column(String(50), default="any")  # remote|hybrid|onsite|any
    employment_types: Mapped[list] = mapped_column(JSONType, default=list)
    min_salary: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    graduation_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    emphasize_technologies: Mapped[list] = mapped_column(JSONType, default=list)
    target_companies: Mapped[list] = mapped_column(JSONType, default=list)
    excluded_companies: Mapped[list] = mapped_column(JSONType, default=list)
    max_emails_per_day: Mapped[int] = mapped_column(Integer, default=10)
    per_company_send_limit: Mapped[int] = mapped_column(Integer, default=2)
    require_manual_approval: Mapped[bool] = mapped_column(Boolean, default=True)
    followups_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    followup_days: Mapped[list] = mapped_column(JSONType, default=lambda: [5, 12])
    experience_level: Mapped[str] = mapped_column(String(50), default="entry_level")
    block_list_emails: Mapped[list] = mapped_column(JSONType, default=list)
    extra: Mapped[dict] = mapped_column(JSONType, default=dict)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="settings")


class AuditLog(Base):
    """Security audit trail (SPEC §21)."""

    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(100))
    detail: Mapped[dict] = mapped_column(JSONType, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
