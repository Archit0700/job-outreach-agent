"""Pydantic API schemas."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel, EmailStr, Field


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    name: str


class UserOut(BaseModel):
    id: str
    email: str
    name: str

    model_config = {"from_attributes": True}


class SettingsUpdate(BaseModel):
    target_roles: Optional[list[str]] = None
    preferred_locations: Optional[list[str]] = None
    remote_preference: Optional[str] = None
    employment_types: Optional[list[str]] = None
    min_salary: Optional[int] = None
    graduation_year: Optional[int] = None
    emphasize_technologies: Optional[list[str]] = None
    target_companies: Optional[list[str]] = None
    excluded_companies: Optional[list[str]] = None
    max_emails_per_day: Optional[int] = None
    per_company_send_limit: Optional[int] = None
    require_manual_approval: Optional[bool] = None
    followups_enabled: Optional[bool] = None
    followup_days: Optional[list[int]] = None
    experience_level: Optional[str] = None
    block_list_emails: Optional[list[str]] = None


class SettingsOut(SettingsUpdate):
    id: str
    user_id: str

    model_config = {"from_attributes": True}


class ProfileOut(BaseModel):
    id: str
    data: dict
    skills_evidence: list

    model_config = {"from_attributes": True}


class ResumeOut(BaseModel):
    id: str
    filename: str
    is_master: bool
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class CompanyOut(BaseModel):
    id: str
    name: str
    careers_url: Optional[str] = None
    application_url: Optional[str] = None
    greenhouse_board: Optional[str] = None
    is_target: bool
    is_excluded: bool

    model_config = {"from_attributes": True}


class JobOut(BaseModel):
    id: str
    company_id: str
    company_name: Optional[str] = None
    job_title: str
    location: str
    employment_type: str
    job_url: str
    application_url: str
    source: str
    description: str = ""
    posted_date: Optional[date] = None
    is_remote: bool = False
    match_score: Optional[float] = None
    why_this_job: Optional[dict] = None

    model_config = {"from_attributes": True}


class MatchOut(BaseModel):
    id: str
    job_id: str
    overall_score: float
    technical_skills: float
    experience_score: float
    education_score: float
    projects_score: float
    role_alignment: float
    strong_matches: list
    potential_gaps: list
    why_this_job: dict

    model_config = {"from_attributes": True}


class ContactCreate(BaseModel):
    company_id: str
    name: str
    email: EmailStr
    role: str = ""
    source: str = "user_provided"


class ContactOut(BaseModel):
    id: str
    company_id: str
    name: str
    email: Optional[str]
    role: str
    source: str
    confidence: str
    verified: bool
    is_guessed: bool

    model_config = {"from_attributes": True}


class OutreachOut(BaseModel):
    id: str
    job_id: str
    company_name: Optional[str] = None
    role: Optional[str] = None
    subject: str
    body: str
    status: str
    recipient_email: Optional[str] = None
    recruiter_name: Optional[str] = None
    recruiter_confidence: Optional[str] = None
    match_score: Optional[float] = None
    qc_verified: bool
    qc_issues: list = Field(default_factory=list)
    personalization: dict = Field(default_factory=dict)
    fallback_application_url: Optional[str] = None
    resume_version_id: Optional[str] = None
    sent_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class OutreachEdit(BaseModel):
    subject: Optional[str] = None
    body: Optional[str] = None


class BulkApprove(BaseModel):
    message_ids: list[str]


class ResumeVersionOut(BaseModel):
    id: str
    job_id: Optional[str]
    plain_text: str
    diff: dict
    qc_passed: bool
    qc_issues: list
    content: dict
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class MetricsOut(BaseModel):
    jobs_found: int
    relevant_jobs: int
    emails_approved: int
    emails_sent: int
    responses: int
    interviews: int
    pending_reviews: int
    followups: int
    rejected: int


class FollowUpCreate(BaseModel):
    message_id: str
    days_from_now: int = 5
    body: Optional[str] = None


class DiscoverRequest(BaseModel):
    company_ids: Optional[list[str]] = None


class PrepareRequest(BaseModel):
    job_id: str
    use_llm: bool = False
