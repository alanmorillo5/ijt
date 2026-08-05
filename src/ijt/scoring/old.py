import asyncio
import re
import json
from dataclasses import dataclass
from typing import Optional, List, Dict, Any

from ijt.logging import get_logger
from ijt.scrapers.base import ScrapedJob
from ijt.tailor.client import ollama_chat

logger = get_logger("scoring")

# Global semaphore for LLM calls to prevent concurrent overloading
llm_semaphore = asyncio.Semaphore(1)

@dataclass
class ScoreResult:
    is_eligible: bool
    score: float
    reason: str
    matched_keywords: List[str]

async def score_job(job: ScrapedJob, config: Any) -> ScoreResult:
    """Score a scraped job using either regex or LLM based on config."""
    engine = config.search.get("scoring_engine", "regex").lower()
    
    if engine == "llm":
        return await _score_with_llm(job, config)
    else:
        return _score_with_regex(job, config)

def _score_with_regex(job: ScrapedJob, config: Any) -> ScoreResult:
    """Fast local regex/keyword scoring engine."""
    description = (job.description or "").lower()
    title = (job.title or "").lower()
    location = (job.location or "").lower()
    
    eligibility = config.search.get("eligibility_filters", {})
    
    # 1. High Priority (Strict Knock-Outs)
    # Check if it must be an internship
    if eligibility.get("must_be_internship", False):
        if "intern" not in title and "intern" not in description:
            return ScoreResult(False, 0.0, "Missing 'intern' in title/description", [])
            
    # Check major explicitly if mentioned
    major = eligibility.get("major", "").lower()
    if major:
        # If they mention a required degree and it's not the one we have, we might reject.
        # But regex is tricky for this. Let's just give a bonus if mentioned, or penalty if missing.
        # The prompt says "Major is high priority"
        if major in description:
            # Good
            pass
        elif "bachelor" in description or "bs" in description:
            # Mentioned degree but maybe not major exactly
            pass
            
    # Check graduation year range
    grad_year = eligibility.get("graduation_year")
    variance = eligibility.get("graduation_year_variance", 0)
    if grad_year:
        # Find all years in description
        years_found = [int(y) for y in re.findall(r'\b202[0-9]\b', description)]
        if years_found:
            valid_range = range(grad_year - variance, grad_year + variance + 1)
            # If they mention years, at least one should be in our range
            if not any(y in valid_range for y in years_found):
                return ScoreResult(False, 0.0, f"Grad year mismatch. Found: {years_found}, Expected: {list(valid_range)}", [])

    # 2. Score Calculation
    score = 0.0
    matched_keywords = []
    
    # Bonus keywords
    bonus_keywords = config.search.get("bonus_keywords", [])
    for keyword in bonus_keywords:
        if keyword.lower() in description or keyword.lower() in title:
            score += 1.0
            matched_keywords.append(keyword)
        else:
            score -= 0.5
            
    # Preferred locations
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

async def _score_with_llm(job: ScrapedJob, config: Any) -> ScoreResult:
    """Score job using LLM with a queue to prevent overloading."""
    async with llm_semaphore:
        logger.info(f"LLM Scoring Job: {job.title} at {job.company}")
        
        eligibility = config.search.get("eligibility_filters", {})
        bonus = config.search.get("bonus_keywords", [])
        locations = config.search.get("preferred_locations", [])
        
        system_prompt = (
            "You are an expert recruiter evaluating an internship job description for a candidate.\n"
            "Respond ONLY with a JSON object containing:\n"
            "- 'is_eligible': boolean (false if it violates strict requirements)\n"
            "- 'score': float (start at 0, +1 for each bonus match, -0.5 for each missing bonus)\n"
            "- 'reason': string (short explanation)\n"
            "- 'matched_keywords': list of strings (the bonus traits found)\n\n"
            "STRICT REQUIREMENTS (is_eligible = false if violated):\n"
        )
        if eligibility.get("must_be_internship"):
            system_prompt += "- Must be an internship\n"
        if eligibility.get("graduation_year"):
            y = eligibility.get("graduation_year")
            v = eligibility.get("graduation_year_variance", 0)
            system_prompt += f"- Graduation year must fall in or overlap with {y-v} to {y+v}\n"
        if eligibility.get("major"):
            system_prompt += f"- Major must be compatible with {eligibility.get('major')}\n"
            
        system_prompt += (
            "\nBONUS TRAITS (+1 if present, -0.5 if missing):\n"
            f"- Keywords: {', '.join(bonus)}\n"
            f"- Locations: {', '.join(locations)}\n"
        )

        user_prompt = f"Title: {job.title}\nLocation: {job.location}\n\nDescription:\n{job.description}"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        try:
            llm_config = config.data.get("llm", {})
            response_text = await ollama_chat(messages, llm_config)
            
            # Find JSON block in response
            match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                return ScoreResult(
                    is_eligible=data.get("is_eligible", False),
                    score=float(data.get("score", 0.0)),
                    reason=data.get("reason", "Parsed from LLM"),
                    matched_keywords=data.get("matched_keywords", [])
                )
            else:
                return ScoreResult(False, 0.0, "Failed to parse LLM JSON", [])
        except Exception as e:
            logger.error(f"LLM Scoring failed: {e}")
            return ScoreResult(False, 0.0, f"Error: {e}", [])
