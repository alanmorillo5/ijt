import asyncio
import urllib.parse
from pathlib import Path
from playwright.async_api import async_playwright
from ijt.config import load_config
from ijt.scrapers.base import ScrapedJob
from ijt.scoring import score_job

async def main():
    config_path = Path("config.yaml")
    config = load_config(config_path)
    
    session_dir = Path("data/sessions/handshake_session")
    state_path = session_dir / "state.json"
    school_url = config.scraper.get("handshake", {}).get("school_url", "https://tamu.joinhandshake.com")
    
    print("\n--- FETCHING HANDSHAKE JOBS DIRECTLY ---")
    jobs = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context_kwargs = {}
        if state_path.exists():
            context_kwargs["storage_state"] = state_path
            
        context = await browser.new_context(**context_kwargs)
        page = await context.new_page()
        
        query = urllib.parse.urlencode({"query": "software engineer intern"})
        await page.goto(f"{school_url}/job-search?{query}")
        await page.wait_for_timeout(5000)
        
        all_hrefs = await page.evaluate("""() => {
            return Array.from(document.querySelectorAll("a")).map(a => a.getAttribute("href")).filter(Boolean)
        }""")
        job_hrefs = list(set([h for h in all_hrefs if "/job-search/" in h]))[:5]
        
        for href in job_hrefs:
            full_url = f"{school_url}{href}".split("?")[0]
            
            await page.goto(full_url)
            await page.wait_for_timeout(3000)
            
            title = await page.locator("h1").first.inner_text() if await page.locator("h1").count() > 0 else "Unknown"
            desc = await page.evaluate("document.body.innerText")
            
            jobs.append(ScrapedJob(
                title=title.strip(), company="", location="", url=full_url, source="handshake",
                description=desc.strip(), posted_date=None, deadline_month=None, deadline_year=None, requirements=[]
            ))
            
        await browser.close()

    print(f"Scraped {len(jobs)} jobs. Scoring them...")
    
    print("\n--- REGEX SCORING ---")
    config.search["scoring_engine"] = "regex"
    for job in jobs:
        res = await score_job(job, config)
        print(f"[{job.title}] Eligible: {res.is_eligible} | Score: {res.score} | Reason: {res.reason}")
        
    print("\n--- LLM SCORING ---")
    config.search["scoring_engine"] = "llm"
    for job in jobs:
        res = await score_job(job, config)
        print(f"[{job.title}] Eligible: {res.is_eligible} | Score: {res.score} | Reason: {res.reason}")

if __name__ == "__main__":
    asyncio.run(main())
