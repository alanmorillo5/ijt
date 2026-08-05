from dataclasses import dataclass
from typing import List

@dataclass
class ScoreResult:
    is_eligible: bool
    score: float
    reason: str
    matched_keywords: List[str]
