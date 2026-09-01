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
            
    internship_year = eligibility.get("internship_year")
    if internship_year:
        if str(internship_year) not in title and str(internship_year) not in description:
            return ScoreResult(False, 0.0, f"Missing internship year {internship_year} in title or description", [])
            
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
    
    def parse_keywords(cfg_value):
        result = {}
        if not cfg_value: return result
        if isinstance(cfg_value, dict):
            for k, v in cfg_value.items():
                result[str(k).lower()] = float(v)
        elif isinstance(cfg_value, list):
            for item in cfg_value:
                if isinstance(item, dict):
                    for k, v in item.items():
                        result[str(k).lower()] = float(v)
                else:
                    result[str(item).lower()] = 1.0
        return result

    # Process Bonus Keywords (+ points if found)
    bonus_keywords = parse_keywords(config.search.get("bonus_keywords"))
    for keyword, weight in bonus_keywords.items():
        if keyword in description or keyword in title:
            score += weight
            matched_keywords.append(f"+{keyword} ({weight})")
            
    internship_season = eligibility.get("internship_season")
    if internship_season:
        if str(internship_season).lower() in title or str(internship_season).lower() in description:
            score += 2.0
            matched_keywords.append(f"+Season: {internship_season} (2.0)")
            
    # Process Required Keywords (- points if missing)
    required_keywords = parse_keywords(config.search.get("required_keywords"))
    for keyword, weight in required_keywords.items():
        if keyword not in description and keyword not in title:
            score -= weight
            matched_keywords.append(f"-[missing] {keyword} (-{weight})")
            
    # Location matching logic
    preferred_locations = config.search.get("preferred_locations", [])
    if preferred_locations:
        location_matched = False
        for loc in preferred_locations:
            if loc.lower() in location or loc.lower() in description:
                score += 1.0
                matched_keywords.append(f"+Location: {loc} (1.0)")
                location_matched = True
                break
                
        if not location_matched:
            score -= 1.0
            matched_keywords.append(f"-[missing] preferred location (-1.0)")
        
    return ScoreResult(True, score, "Eligible (Regex)", matched_keywords)
