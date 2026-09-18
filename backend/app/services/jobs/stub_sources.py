"""Stubs for Workday / Wellfound / LinkedIn — labeled clearly, not used for real scrape.

These return empty lists and document extension points. No CAPTCHA/auth bypass.
"""
from __future__ import annotations

from app.services.jobs.base import DiscoveredJob, JobSourceAdapter


class WorkdayStubAdapter(JobSourceAdapter):
    """STUB: Workday career sites often require browser sessions; not implemented."""

    name = "workday_stub"

    async def fetch_jobs(self, board_token: str, company_name: str) -> list[DiscoveredJob]:
        return []


class WellfoundStubAdapter(JobSourceAdapter):
    """STUB: Wellfound has no stable public unauthenticated API in this MVP."""

    name = "wellfound_stub"

    async def fetch_jobs(self, board_token: str, company_name: str) -> list[DiscoveredJob]:
        return []


class LinkedInStubAdapter(JobSourceAdapter):
    """STUB: LinkedIn Jobs — only use official permitted APIs; not wired."""

    name = "linkedin_stub"

    async def fetch_jobs(self, board_token: str, company_name: str) -> list[DiscoveredJob]:
        return []
