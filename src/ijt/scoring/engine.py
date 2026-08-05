import asyncio
import re
import json
from typing import Any

from ijt.logging import get_logger
from ijt.scrapers.base import ScrapedJob
from ijt.tailor.client import ollama_chat
from .types import ScoreResult
from .linkedin import score_linkedin_regex
from .handshake import score_handshake_regex

logger = get_logger("scoring")
llm_semaphore = asyncio.Semaphore(1)

async def score_job(job: ScrapedJob, config: Any) -> ScoreResult:
    """Score a scraped job using either regex or LLM based on config."""
    engine = config.search.get("scoring_engine", "regex").lower()
    
    if engine == "llm":
        return await _score_with_llm(job, config)
    else:
        # Route to platform-specific regex scorers
        if job.source == "linkedin":
            return score_linkedin_regex(job, config)
        elif job.source == "handshake":
            return score_handshake_regex(job, config)
        else:
            # Fallback
            return score_linkedin_regex(job, config)

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
