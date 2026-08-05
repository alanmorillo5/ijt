import asyncio
import os
from pathlib import Path
from ijt.config import load_config
from ijt.scrapers.base import ScrapedJob
from ijt.scoring import score_job

async def test_edge_cases():
    config_path = Path("config.yaml")
    config = load_config(config_path)

    # Edge Case 1: Perfect match
    job1 = ScrapedJob(
        title="Software Engineer Intern",
        company="TechCorp",
        location="Austin, TX",
        url="http://example.com/1",
        source="test",
        description="We are looking for a software engineer intern. You must be graduating in 2028 with a Computer Science degree. You will use python and cloud technologies, including react.",
        posted_date=None, deadline_month=None, deadline_year=None, requirements=[]
    )

    # Edge Case 2: Missing 'intern' in description, but in title
    job2 = ScrapedJob(
        title="Software Intern",
        company="TechCorp",
        location="Remote",
        url="http://example.com/2",
        source="test",
        description="Join our team to build scalable software. You need a CS degree.",
        posted_date=None, deadline_month=None, deadline_year=None, requirements=[]
    )

    # Edge Case 3: Wrong grad year (strictly 2024)
    job3 = ScrapedJob(
        title="Data Science Intern",
        company="TechCorp",
        location="Austin, TX",
        url="http://example.com/3",
        source="test",
        description="Must be graduating in 2024. Python and cloud skills required.",
        posted_date=None, deadline_month=None, deadline_year=None, requirements=[]
    )
    
    # Edge Case 4: No grad year mentioned, few bonuses
    job4 = ScrapedJob(
        title="Backend Engineer Intern",
        company="Startup",
        location="Unknown",
        url="http://example.com/4",
        source="test",
        description="Great internship! We use rust.",
        posted_date=None, deadline_month=None, deadline_year=None, requirements=[]
    )
    
    # Edge Case 5: PhD / Wrong Major
    job5 = ScrapedJob(
        title="Research Intern",
        company="Lab",
        location="Austin, TX",
        url="http://example.com/5",
        source="test",
        description="Must be a PhD student in Chemistry.",
        posted_date=None, deadline_month=None, deadline_year=None, requirements=[]
    )

    jobs = [job1, job2, job3, job4, job5]

    print("--- REGEX ENGINE TESTS ---")
    config.search["scoring_engine"] = "regex"
    for i, job in enumerate(jobs, 1):
        res = await score_job(job, config)
        print(f"[{i}] {job.title} | Eligible: {res.is_eligible} | Score: {res.score} | Reason: {res.reason} | Keywords: {res.matched_keywords}")

    print("\n--- LLM ENGINE TESTS ---")
    config.search["scoring_engine"] = "llm"
    for i, job in enumerate(jobs, 1):
        res = await score_job(job, config)
        print(f"[{i}] {job.title} | Eligible: {res.is_eligible} | Score: {res.score} | Reason: {res.reason} | Keywords: {res.matched_keywords}")

if __name__ == "__main__":
    asyncio.run(test_edge_cases())
