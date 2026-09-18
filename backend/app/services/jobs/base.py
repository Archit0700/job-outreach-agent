"""Job source adapter interface."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from typing import Optional


@dataclass
class DiscoveredJob:
    company_name: str
    job_title: str
    location: str = ""
    employment_type: str = "unknown"
    job_url: str = ""
    application_url: str = ""
    source: str = ""
    description: str = ""
    posted_date: Optional[date] = None
    external_id: str = ""
    is_remote: bool = False
    greenhouse_board: Optional[str] = None
    raw_payload: dict = field(default_factory=dict)


class JobSourceAdapter(ABC):
    name: str = "base"

    @abstractmethod
    async def fetch_jobs(self, board_token: str, company_name: str) -> list[DiscoveredJob]:
        """Fetch public jobs. Must not bypass CAPTCHA/auth/robots."""
        ...
