"""Greenhouse public board API adapter (real, no auth required).

API: https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true
"""
from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any

import httpx

from app.services.jobs.base import DiscoveredJob, JobSourceAdapter

ENTRY_KEYWORDS = re.compile(
    r"intern|internship|graduate|entry.?level|new.?grad|junior|university|campus|fresher",
    re.I,
)
ENG_KEYWORDS = re.compile(
    r"software|engineer|developer|sde|backend|full.?stack|frontend|android|"
    r"mobile|machine learning|ml engineer|ai engineer|data engineer|swe",
    re.I,
)


def _infer_employment(title: str, text: str) -> str:
    blob = f"{title} {text}"
    if re.search(r"intern", blob, re.I):
        return "internship"
    return "full_time"


def _is_remote(location: str, text: str) -> bool:
    return bool(re.search(r"\bremote\b", f"{location} {text}", re.I))


class GreenhouseAdapter(JobSourceAdapter):
    name = "greenhouse"

    def __init__(self, timeout: float = 30.0) -> None:
        self.timeout = timeout

    async def fetch_jobs(self, board_token: str, company_name: str) -> list[DiscoveredJob]:
        url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs"
        params = {"content": "true"}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(url, params=params)
            if resp.status_code == 404:
                return []
            resp.raise_for_status()
            data = resp.json()

        jobs: list[DiscoveredJob] = []
        for item in data.get("jobs") or []:
            title = item.get("title") or ""
            # Prefer technical / entry roles but still store all for filtering later
            content = item.get("content") or ""
            # Strip basic HTML
            description = re.sub(r"<[^>]+>", " ", content)
            description = re.sub(r"\s+", " ", description).strip()
            location = ""
            if item.get("location") and isinstance(item["location"], dict):
                location = item["location"].get("name") or ""
            abs_url = item.get("absolute_url") or ""
            ext_id = str(item.get("id") or "")
            posted = None
            if item.get("updated_at"):
                try:
                    posted = datetime.fromisoformat(
                        item["updated_at"].replace("Z", "+00:00")
                    ).date()
                except ValueError:
                    posted = None
            jobs.append(
                DiscoveredJob(
                    company_name=company_name,
                    job_title=title,
                    location=location,
                    employment_type=_infer_employment(title, description),
                    job_url=abs_url,
                    application_url=abs_url,
                    source="greenhouse",
                    description=description[:50000],
                    posted_date=posted,
                    external_id=ext_id,
                    is_remote=_is_remote(location, description),
                    greenhouse_board=board_token,
                    raw_payload={"id": item.get("id"), "title": title},
                )
            )
        return jobs

    @staticmethod
    def filter_relevant(jobs: list[DiscoveredJob], prefer_entry: bool = True) -> list[DiscoveredJob]:
        out = []
        for j in jobs:
            if not ENG_KEYWORDS.search(j.job_title):
                continue
            if prefer_entry and not ENTRY_KEYWORDS.search(f"{j.job_title} {j.description[:1000]}"):
                # Still include SWE roles for fresher targeting
                if not re.search(r"senior|staff|principal|director|manager", j.job_title, re.I):
                    out.append(j)
                continue
            out.append(j)
        return out or [j for j in jobs if ENG_KEYWORDS.search(j.job_title)]
