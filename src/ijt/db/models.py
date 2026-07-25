from dataclasses import dataclass
from typing import Optional

@dataclass
class Job:
    id: str
    title: str
    company: str
    url: str
    source: str
    location: Optional[str] = None
    description: Optional[str] = None
    deadline_month: Optional[int] = None
    deadline_year: Optional[int] = None
    status: str = 'not_applied'
    folder_name: Optional[str] = None
    relevance_score: Optional[float] = None
    matched_keywords: Optional[str] = None

@dataclass
class SeenUrl:
    url_hash: str
    url: str
    source: str
