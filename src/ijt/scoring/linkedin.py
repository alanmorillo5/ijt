import re
from typing import Any
from ijt.scrapers.base import ScrapedJob
from .types import ScoreResult
from .common import evaluate_common_regex

def score_linkedin_regex(job: ScrapedJob, config: Any) -> ScoreResult:
    """Regex scoring tailored for LinkedIn's format."""
    # LinkedIn job details are usually scraped perfectly into `job.description`
    # We can add custom penalties if it looks like a promoted spam job
    # or apply specific LinkedIn format parsers.
    
    desc = (job.description or "").lower()
    extra_penalties = 0.0
    
    # LinkedIn specific patterns to penalize
    if "sr." in job.title.lower() or "senior" in job.title.lower() or "lead" in job.title.lower():
        extra_penalties += 2.0
        
    if "years of experience" in desc:
        # Check if they want > 3 years
        exp_match = re.search(r'([0-9]+)\+?\s+years?\s+of\s+experience', desc)
        if exp_match and int(exp_match.group(1)) >= 3:
            return ScoreResult(False, 0.0, f"Requires {exp_match.group(1)} years of experience (LinkedIn Specific)", [])
            
    return evaluate_common_regex(job, config, extra_penalties)
