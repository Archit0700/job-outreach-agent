"""Lever public postings API adapter.

STUB/REAL hybrid: uses public Lever postings endpoint when available.
API: https://api.lever.co/v0/postings/{company}?mode=json
"""
from __future__ import annotations

import re

import httpx

from app.services.jobs.base import DiscoveredJob, JobSourceAdapter


class LeverAdapter(JobSourceAdapter):
    name = "lever"

    def __init__(self, timeout: float = 30.0) -> None:
        self.timeout = timeout

    async def fetch_jobs(self, board_token: str, company_name: str) -> list[DiscoveredJob]:
        url = f"https://api.lever.co/v0/postings/{board_token}"
        params = {"mode": "json"}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(url, params=params)
            if resp.status_code >= 400:
                return []
            data = resp.json()
        if not isinstance(data, list):
            return []
        jobs = []
        for item in data:
            title = item.get("text") or ""
            cats = item.get("categories") or {}
            location = cats.get("location") or ""
            description = item.get("descriptionPlain") or item.get("description") or ""
            if description and "<" in description:
                description = re.sub(r"<[^>]+>", " ", description)
            hosted = item.get("hostedUrl") or item.get("applyUrl") or ""
            commitment = (cats.get("commitment") or "").lower()
            emp = "internship" if "intern" in commitment or "intern" in title.lower() else "full_time"
            jobs.append(
                DiscoveredJob(
                    company_name=company_name,
                    job_title=title,
                    location=location,
                    employment_type=emp,
                    job_url=hosted,
                    application_url=item.get("applyUrl") or hosted,
                    source="lever",
                    description=description[:50000],
                    external_id=str(item.get("id") or ""),
                    is_remote=bool(re.search(r"remote", location, re.I)),
                    raw_payload={"id": item.get("id")},
                )
            )
        return jobs
