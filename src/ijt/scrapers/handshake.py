from pathlib import Path
from typing import List, Dict
from playwright.async_api import async_playwright
import urllib.parse
from ijt.scrapers.base import BaseScraper, ScrapedJob
from ijt.logging import get_logger
from ijt.scrapers.utils import rate_limit

logger = get_logger("scrapers.handshake")

class HandshakeScraper(BaseScraper):
    def __init__(self, session_dir: Path, school_url: str = "https://app.joinhandshake.com"):
        self.session_dir = session_dir
        self.school_url = school_url
        self.source = "handshake"

    async def login(self) -> None:
        async with async_playwright() as p:
            # Handshake uses strict Cloudflare anti-bot, so we must run headed
            browser = await p.chromium.launch(headless=False)
            
            state_path = self.session_dir / "state.json"
            context_kwargs = {}
            if state_path.exists():
                context_kwargs["storage_state"] = state_path
                
            context = await browser.new_context(**context_kwargs)
            page = await context.new_page()
            
            await page.goto(self.school_url)
            
            print("\n" + "="*50)
            print("🛑 ACTION REQUIRED 🛑")
            print("1. A browser window has opened.")
            print("2. Please log into Handshake manually.")
            print("3. Return to this terminal and press ENTER when done.")
            print("="*50 + "\n")
            
            import asyncio
            await asyncio.to_thread(input, "Press ENTER here after logging in: ")
            
            self.session_dir.mkdir(parents=True, exist_ok=True)
            await context.storage_state(path=state_path)
            await browser.close()
            logger.info("Handshake session saved.")

    async def search(self, keywords: list[str], filters: dict) -> list[ScrapedJob]:
        logger.info(f"Searching Handshake for {keywords}")
        jobs = []
        state_path = self.session_dir / "state.json"
        max_jobs = filters.get("max_results_per_source", 50)
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context_kwargs = {}
            if state_path.exists():
                context_kwargs["storage_state"] = state_path
            else:
                logger.error("Session not found. Please run 'ijt login handshake' first.")
                return []
                
            context = await browser.new_context(**context_kwargs)
            page = await context.new_page()
            
            for keyword in keywords:
                if len(jobs) >= max_jobs:
                    break
                    
                query = urllib.parse.urlencode({'query': keyword})
                await page.goto(f"{self.school_url}/job-search?{query}")
                await rate_limit(3, 5)
                
                # Extract job links directly via DOM to avoid regex issues
                try:
                    await page.wait_for_timeout(3000) # Give it time to load
                    
                    all_hrefs = await page.evaluate("""() => {
                        return Array.from(document.querySelectorAll("a")).map(a => a.getAttribute("href")).filter(Boolean)
                    }""")
                    links = list(set([h for h in all_hrefs if "/job-search/" in h]))
                    print("Found job links:", len(links))
                    
                    for link in links[:max_jobs - len(jobs)]:
                        full_url = f"{self.school_url}{link}".split("?")[0]
                        
                        jobs.append(ScrapedJob(
                            title="", # Handled in get_job_details
                            company="",
                            location="Unknown",
                            url=full_url,
                            source=self.source,
                            description="", 
                            posted_date=None, deadline_month=None, deadline_year=None, requirements=[]
                        ))
                except Exception as e:
                    logger.error(f"Error extracting Handshake jobs: {e}")
                    
            await browser.close()
            
        return jobs

    async def get_job_details(self, url: str) -> ScrapedJob:
        state_path = self.session_dir / "state.json"
        print("Scraper State Path:", state_path, "Exists:", state_path.exists())
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context(storage_state=state_path if state_path.exists() else None)
            page = await context.new_page()
            
            await page.goto(url)
            await rate_limit(3, 5)
            
            try:
                title_el = page.locator("h1")
                title = await title_el.first.inner_text(timeout=2000) if await title_el.count() > 0 else ""
                
                # Handshake usually stores the job description in a specific div or within the main element
                desc = await page.evaluate("""() => {
                    let jd = document.querySelector('div[data-hook="job-description"]');
                    if (jd) return jd.innerText;
                    
                    let main = document.querySelector('main');
                    if (main) return main.innerText;
                    
                    return document.body.innerText;
                }""")
                job = ScrapedJob(
                    title=title.strip(),
                    company="", 
                    location="",
                    url=url,
                    source=self.source,
                    description=desc.strip(),
                    posted_date=None, deadline_month=None, deadline_year=None, requirements=[]
                )
            except Exception as e:
                logger.error(f"Error getting details for {url}: {e}")
                job = ScrapedJob("", "", "", url, self.source, "", None, None, None, [])
                
            await browser.close()
            
        return job
