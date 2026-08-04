from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class ScrapedJob:
    """Raw job data from a scraping source."""
    title: str
    company: str
    location: str
    url: str
    source: str              # 'linkedin' | 'handshake'
    description: str         # Full job description text
    posted_date: str | None
    deadline_month: int | None  # 1-12, None if not listed
    deadline_year: int | None   # e.g., 2026, None if not listed
    requirements: list[str]  # Extracted requirements/qualifications

class BaseScraper(ABC):
    """Abstract base class for all job scrapers."""

    @abstractmethod
    async def login(self) -> None: ...

    @abstractmethod
    async def search(self, keywords: list[str], filters: dict) -> list[ScrapedJob]: ...

    @abstractmethod
    async def get_job_details(self, url: str) -> ScrapedJob: ...
