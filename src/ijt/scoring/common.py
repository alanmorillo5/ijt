import re
from typing import Any
from ijt.scrapers.base import ScrapedJob
from .types import ScoreResult

def evaluate_common_regex(job: ScrapedJob, config: Any, extra_penalties: float = 0.0) -> ScoreResult:
    """Core regex evaluation shared across platforms."""
    description = (job.description or "").lower()
    title = (job.title or "").lower()
    location = (job.location or "").lower()
    
    eligibility = config.search.get("eligibility_filters", {})
    
    # 1. High Priority (Strict Knock-Outs)
    if eligibility.get("must_be_internship", False):
        if "intern" not in title and "intern" not in description:
            return ScoreResult(False, 0.0, "Missing 'intern' in title/description", [])
            
    grad_year = eligibility.get("graduation_year")
    variance = eligibility.get("graduation_year_variance", 0)
    if grad_year:
        years_found = [int(y) for y in re.findall(r'\b202[0-9]\b', description)]
        if years_found:
            valid_range = range(grad_year - variance, grad_year + variance + 1)
            if not any(y in valid_range for y in years_found):
                return ScoreResult(False, 0.0, f"Grad year mismatch. Found: {years_found}, Expected: {list(valid_range)}", [])

    # 2. Score Calculation
    score = 0.0 - extra_penalties
    matched_keywords = []
    
    bonus_keywords = config.search.get("bonus_keywords", [])
    for keyword in bonus_keywords:
        if keyword.lower() in description or keyword.lower() in title:
            score += 1.0
            matched_keywords.append(keyword)
        else:
            score -= 0.5
            
    preferred_locations = config.search.get("preferred_locations", [])
    location_matched = False
    for loc in preferred_locations:
        if loc.lower() in location or loc.lower() in description:
            score += 1.0
            matched_keywords.append(f"Location: {loc}")
            location_matched = True
            break
            
    if preferred_locations and not location_matched:
        score -= 0.5
        
    return ScoreResult(True, score, "Eligible (Regex)", matched_keywords)
