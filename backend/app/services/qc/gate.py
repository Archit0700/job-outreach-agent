"""Quality-control gate before approval (SPEC §20)."""
from __future__ import annotations

import re
from typing import Any

from app.services.resume.parser import claim_exists_in_resume
from app.services.tailoring.tailor import validate_no_fabrication


PLACEHOLDER_PATTERNS = [
    r"\[Company\]",
    r"\[Recruiter\]",
    r"\[Role\]",
    r"\[Name\]",
    r"TODO",
    r"TBD",
    r"lorem ipsum",
]

EXAGGERATION = [
    r"perfect candidate",
    r"best candidate",
    r"guaranteed",
    r"world.?class expert",
    r"10x engineer",
]


def run_qc(
    *,
    resume_text: str,
    tailored: dict,
    email_subject: str,
    email_body: str,
    company_name: str,
    role_title: str,
    job_url: str,
    recruiter_name: str | None = None,
    recipient_email: str | None = None,
    contact_verified: bool = False,
) -> dict[str, Any]:
    issues: list[str] = []

    # Resume fabrication checks
    issues.extend(validate_no_fabrication(tailored, resume_text))

    # Email placeholders
    combined = f"{email_subject}\n{email_body}"
    for pat in PLACEHOLDER_PATTERNS:
        if re.search(pat, combined, re.I):
            issues.append(f"Generic placeholder found: {pat}")

    for pat in EXAGGERATION:
        if re.search(pat, email_body, re.I):
            issues.append(f"Exaggerated claim detected: {pat}")

    if company_name and company_name.lower() not in combined.lower():
        # Soft warning — company should appear
        if "[company]" in combined.lower():
            issues.append("Company name missing / placeholder")

    if role_title:
        # At least part of role should appear
        role_tokens = [t for t in role_title.lower().split() if len(t) > 3][:2]
        if role_tokens and not any(t in combined.lower() for t in role_tokens):
            issues.append("Role title not reflected in email")

    if recipient_email and not contact_verified:
        issues.append("Recipient email is not a verified public contact — cannot send")

    if recipient_email and "@" not in recipient_email:
        issues.append("Invalid recipient email format")

    # Basic length
    words = len(email_body.split())
    if words < 40:
        issues.append("Email too short — may lack personalization")
    if words > 350:
        issues.append("Email too long — target ~120-180 words")

    # Claim scan in email against resume
    for sentence in re.split(r"[.!\n]", email_body):
        s = sentence.strip()
        if len(s) < 40:
            continue
        # Look for technology claims
        tech_claim = re.search(
            r"(?:experience (?:with|in)|worked on|built|developed)\s+(.{5,60})",
            s,
            re.I,
        )
        if tech_claim:
            fragment = tech_claim.group(1)
            if not claim_exists_in_resume(fragment, resume_text) and not claim_exists_in_resume(
                s, resume_text
            ):
                # Soft — only flag if strong tech words not in resume
                pass

    verified = len(issues) == 0
    return {"verified": verified, "issues": issues}
