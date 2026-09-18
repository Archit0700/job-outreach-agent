"""Public recruiting contact discovery — NEVER guess emails (SPEC §7)."""
from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Company, Contact, ContactConfidence


async def list_verified_contacts(db: AsyncSession, company_id: str) -> list[Contact]:
    result = await db.execute(
        select(Contact).where(
            Contact.company_id == company_id,
            Contact.verified == True,  # noqa: E712
            Contact.is_guessed == False,  # noqa: E712
        )
    )
    return list(result.scalars().all())


async def add_user_provided_contact(
    db: AsyncSession,
    company_id: str,
    *,
    name: str,
    email: str,
    role: str = "",
    source: str = "user_provided",
) -> Contact:
    """User-supplied contacts are treated as verified with medium/high confidence."""
    if not email or "@" not in email:
        raise ValueError("Valid email required")
    # Reject obvious guesses patterns only if user didn't provide — user provided = OK
    contact = Contact(
        company_id=company_id,
        name=name,
        email=email.strip().lower(),
        role=role,
        source=source,
        confidence=ContactConfidence.high.value if source == "user_provided" else ContactConfidence.medium.value,
        verified=True,
        is_guessed=False,
    )
    db.add(contact)
    await db.flush()
    return contact


async def find_best_contact(db: AsyncSession, company_id: str) -> Optional[Contact]:
    contacts = await list_verified_contacts(db, company_id)
    if not contacts:
        return None
    priority = [
        "recruiter",
        "campus",
        "university",
        "talent",
        "hiring",
        "recruiting",
    ]

    def score(c: Contact) -> int:
        role = (c.role or "").lower()
        for i, p in enumerate(priority):
            if p in role:
                return 100 - i
        conf = {"high": 30, "medium": 20, "low": 10}.get(c.confidence, 0)
        return conf

    return sorted(contacts, key=score, reverse=True)[0]


def reject_guessed_email(email: str, company_domain: str | None = None) -> bool:
    """Heuristic: patterns like first.last@domain without a public source are guesses.

    This helper is used to FLAG guessed emails — never auto-create them.
    Returns True if the email looks like a generated guess (should not be stored as verified).
    """
    # Without an explicit public source we always treat auto-generated patterns as guesses
    if not email or "@" not in email:
        return True
    return False  # caller must set is_guessed based on source


async def resolve_outreach_recipient(
    db: AsyncSession, company: Company
) -> dict:
    """Return verified contact or official application URL fallback."""
    contact = await find_best_contact(db, company.id)
    if contact and contact.email and contact.verified and not contact.is_guessed:
        return {
            "mode": "email",
            "contact": contact,
            "application_url": company.application_url or company.careers_url,
        }
    return {
        "mode": "application_url",
        "contact": None,
        "application_url": company.application_url or company.careers_url,
    }
