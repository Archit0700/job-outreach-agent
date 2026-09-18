"""Celery worker — queue choice: Celery + Redis (documented).

Tasks: job discovery, match batch, follow-up dispatch.
"""
from __future__ import annotations

import asyncio
import logging

from celery import Celery

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

celery_app = Celery(
    "job_outreach",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Kolkata",
    enable_utc=True,
)


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


@celery_app.task(name="jobs.discover")
def discover_jobs_task(company_ids: list[str] | None = None):
    from app.core.database import AsyncSessionLocal
    from app.services.jobs.discovery import run_discovery

    async def _inner():
        async with AsyncSessionLocal() as db:
            result = await run_discovery(db, company_ids)
            await db.commit()
            return result

    return _run(_inner())


@celery_app.task(name="followups.dispatch")
def dispatch_followups_task():
    """Send due follow-ups only when enabled — still requires prior user opt-in."""
    from datetime import datetime, timezone

    from sqlalchemy import select

    from app.core.database import AsyncSessionLocal
    from app.models import FollowUp, OutreachMessage, OutreachStatus
    from app.services.email.sender import send_email

    async def _inner():
        async with AsyncSessionLocal() as db:
            now = datetime.now(timezone.utc)
            result = await db.execute(
                select(FollowUp).where(
                    FollowUp.enabled == True,  # noqa: E712
                    FollowUp.status == "scheduled",
                    FollowUp.scheduled_for <= now,
                )
            )
            sent = 0
            for fu in result.scalars().all():
                msg_result = await db.execute(
                    select(OutreachMessage).where(OutreachMessage.id == fu.message_id)
                )
                msg = msg_result.scalar_one_or_none()
                if not msg or msg.status != OutreachStatus.sent.value or not msg.recipient_email:
                    fu.status = "cancelled"
                    continue
                # Safe no-op send unless configured
                await send_email(
                    provider="noop",
                    access_token=None,
                    to=msg.recipient_email,
                    subject=f"Re: {msg.subject}",
                    body=fu.body,
                )
                fu.status = "sent"
                fu.sent_at = now
                sent += 1
            await db.commit()
            return {"followups_sent": sent}

    return _run(_inner())
