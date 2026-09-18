"""Email sending via Gmail / Microsoft Graph — safe no-op if not configured (SPEC §11)."""
from __future__ import annotations

import base64
import logging
from dataclasses import dataclass
from typing import Optional

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class SendResult:
    success: bool
    provider: str
    message_id: Optional[str] = None
    detail: str = ""
    noop: bool = False


async def send_via_gmail(
    access_token: str,
    *,
    to: str,
    subject: str,
    body: str,
    from_email: Optional[str] = None,
) -> SendResult:
    """Send using Gmail API users.messages.send. Requires gmail.send scope."""
    settings = get_settings()
    if not settings.gmail_configured:
        return SendResult(
            success=True,
            provider="gmail",
            detail="Gmail OAuth not configured — safe no-op (email NOT sent)",
            noop=True,
        )

    # RFC 2822 raw message
    lines = [
        f"To: {to}",
        f"Subject: {subject}",
        "Content-Type: text/plain; charset=utf-8",
        "",
        body,
    ]
    if from_email:
        lines.insert(0, f"From: {from_email}")
    raw = base64.urlsafe_b64encode("\n".join(lines).encode()).decode().rstrip("=")

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"raw": raw},
        )
        if resp.status_code >= 400:
            return SendResult(False, "gmail", detail=resp.text)
        data = resp.json()
        return SendResult(True, "gmail", message_id=data.get("id"), detail="sent")


async def send_via_microsoft(
    access_token: str,
    *,
    to: str,
    subject: str,
    body: str,
) -> SendResult:
    settings = get_settings()
    if not settings.microsoft_configured:
        return SendResult(
            success=True,
            provider="microsoft",
            detail="Microsoft Graph OAuth not configured — safe no-op (email NOT sent)",
            noop=True,
        )

    payload = {
        "message": {
            "subject": subject,
            "body": {"contentType": "Text", "content": body},
            "toRecipients": [{"emailAddress": {"address": to}}],
        },
        "saveToSentItems": True,
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            "https://graph.microsoft.com/v1.0/me/sendMail",
            headers={"Authorization": f"Bearer {access_token}"},
            json=payload,
        )
        if resp.status_code >= 400:
            return SendResult(False, "microsoft", detail=resp.text)
        return SendResult(True, "microsoft", detail="sent")


async def send_email(
    *,
    provider: str,
    access_token: Optional[str],
    to: str,
    subject: str,
    body: str,
) -> SendResult:
    """Unified send. If provider/tokens missing → safe no-op."""
    settings = get_settings()
    provider = (provider or "noop").lower()

    if provider == "gmail":
        if not access_token or not settings.gmail_configured:
            logger.info("Gmail send no-op to=%s subject=%s", to, subject)
            return SendResult(True, "gmail", detail="no-op: not configured", noop=True)
        return await send_via_gmail(access_token, to=to, subject=subject, body=body)

    if provider in {"microsoft", "outlook"}:
        if not access_token or not settings.microsoft_configured:
            logger.info("Microsoft send no-op to=%s subject=%s", to, subject)
            return SendResult(True, "microsoft", detail="no-op: not configured", noop=True)
        return await send_via_microsoft(access_token, to=to, subject=subject, body=body)

    logger.info("Send no-op provider=%s to=%s subject=%s", provider, to, subject)
    return SendResult(True, "noop", detail="safe no-op — no email provider configured", noop=True)
