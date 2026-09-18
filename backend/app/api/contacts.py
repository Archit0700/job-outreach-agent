"""Contact management — user-provided only; no guessing."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.models import Contact
from app.schemas.schemas import ContactCreate, ContactOut
from app.services.contacts.discovery import add_user_provided_contact

router = APIRouter(prefix="/api", tags=["contacts"])


@router.get("/contacts", response_model=list[ContactOut])
async def list_contacts(user: CurrentUser, db: DbSession, company_id: str | None = None):
    q = select(Contact)
    if company_id:
        q = q.where(Contact.company_id == company_id)
    result = await db.execute(q)
    # Never return guessed contacts as usable
    return [c for c in result.scalars().all() if not c.is_guessed]


@router.post("/contacts", response_model=ContactOut)
async def create_contact(body: ContactCreate, user: CurrentUser, db: DbSession):
    try:
        c = await add_user_provided_contact(
            db,
            body.company_id,
            name=body.name,
            email=str(body.email),
            role=body.role,
            source=body.source or "user_provided",
        )
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return c
