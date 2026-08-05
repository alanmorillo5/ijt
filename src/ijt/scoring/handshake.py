import re
from typing import Any
from ijt.scrapers.base import ScrapedJob
from .types import ScoreResult
from .common import evaluate_common_regex

def score_handshake_regex(job: ScrapedJob, config: Any) -> ScoreResult:
    """Regex scoring tailored for Handshake's format."""
    
    # Handshake's scraper sometimes pulls the entire page text (including the sidebar) 
    # if the specific job details DOM isn't perfectly isolated.
    # We can detect this if the title is generic, like "Jobs", or if the description
    # contains the navigation menu.
    
    title = (job.title or "").strip().lower()
    desc = (job.description or "").lower()
    
    if title == "jobs" or title == "explore":
        return ScoreResult(False, 0.0, "Generic Handshake navigation menu detected (Handshake Specific)", [])
        
    if "skip to content" in desc and "inbox" in desc and "events" in desc:
        # It scraped the whole page. Let's try to isolate the role description if possible
        # Look for typical Handshake job description headers
        match = re.search(r'(about the role|role description|what you\'ll do|qualifications)(.*)', desc, re.DOTALL)
        if match:
            # We found the actual job description part!
            job.description = match.group(0)
        else:
            # We couldn't isolate the job description, this is likely just the job board
            return ScoreResult(False, 0.0, "No specific job description found in page text (Handshake Specific)", [])
            
    # Also check if it's explicitly a work-study (often on Handshake) and user only wants internships
    eligibility = config.search.get("eligibility_filters", {})
    if eligibility.get("must_be_internship", False):
        if "work study" in desc or "work-study" in desc:
            return ScoreResult(False, 0.0, "Work-study role detected (Handshake Specific)", [])

    return evaluate_common_regex(job, config, extra_penalties=0.0)
