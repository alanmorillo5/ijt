from pathlib import Path
from typing import List, Dict
from playwright.async_api import async_playwright
import urllib.parse
from ijt.scrapers.base import BaseScraper, ScrapedJob
from ijt.logging import get_logger
from ijt.scrapers.utils import rate_limit

logger = get_logger("scrapers.linkedin")

class LinkedInScraper(BaseScraper):
    def __init__(self, session_dir: Path):
        self.session_dir = session_dir
        self.source = "linkedin"

    async def login(self) -> None:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            
            state_path = self.session_dir / "state.json"
            context_kwargs = {}
            if state_path.exists():
                context_kwargs["storage_state"] = state_path
                
            context = await browser.new_context(**context_kwargs)
            page = await context.new_page()
            
            await page.goto("https://www.linkedin.com/login")
            
            print("\n" + "="*50)
            print("🛑 ACTION REQUIRED 🛑")
            print("1. A browser window has opened.")
            print("2. Please log into LinkedIn manually.")
            print("3. Return to this terminal and press ENTER when done.")
            print("="*50 + "\n")
            
            import asyncio
            await asyncio.to_thread(input, "Press ENTER here after logging in: ")
            
            self.session_dir.mkdir(parents=True, exist_ok=True)
            await context.storage_state(path=state_path)
            await browser.close()
            logger.info("LinkedIn session saved.")

    async def search(self, keywords: list[str], filters: dict) -> list[ScrapedJob]:
        logger.info(f"Searching LinkedIn for {keywords}")
        jobs = []
        state_path = self.session_dir / "state.json"
        max_jobs = filters.get("max_results_per_source", 50)
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context_kwargs = {}
            if state_path.exists():
                context_kwargs["storage_state"] = state_path
            else:
                logger.error("Session not found. Please run 'ijt login linkedin' first.")
                return []
                
            context = await browser.new_context(**context_kwargs)
            page = await context.new_page()
            
            for keyword in keywords:
                if len(jobs) >= max_jobs:
                    break
                    
                query = urllib.parse.urlencode({'keywords': keyword})
                await page.goto(f"https://www.linkedin.com/jobs/search/?{query}")
                await rate_limit(3, 5)
                
                # Try to find some job cards (this is a simplified example)
                job_cards = await page.locator(".job-card-container").all()
                for card in job_cards[:max_jobs - len(jobs)]:
                    try:
                        title_el = card.locator("a.job-card-container__link").first
                        company_el = card.locator(".artdeco-entity-lockup__subtitle").first
                        location_el = card.locator(".artdeco-entity-lockup__caption").first
                        
                        title = await title_el.inner_text()
                        company = await company_el.inner_text()
                        location = await location_el.inner_text()
                        href = await title_el.get_attribute("href")
                        
                        if href:
                            full_url = f"https://www.linkedin.com{href}"
                            # Extract base URL without query params
                            full_url = full_url.split("?")[0]
                            
                            jobs.append(ScrapedJob(
                                title=title.strip(),
                                company=company.strip(),
                                location=location.strip(),
                                url=full_url,
                                source=self.source,
                                description="", # Will be fetched later
                                posted_date=None,
                                deadline_month=None,
                                deadline_year=None,
                                requirements=[]
                            ))
                    except Exception as e:
                        logger.error(f"Error extracting job card: {e}")
                        
            await browser.close()
            
        return jobs

    from ijt.scrapers.utils import retry_async
    @retry_async(max_retries=3)
    async def get_job_details(self, url: str) -> ScrapedJob:
        state_path = self.session_dir / "state.json"
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(storage_state=state_path if state_path.exists() else None)
            page = await context.new_page()
            
            await page.goto(url)
            await rate_limit(3, 5)
            
            # Extract details
            try:
                title_el = page.locator("h1")
                title = await title_el.first.inner_text(timeout=2000) if await title_el.count() > 0 else ""
                
                company_el = page.locator(".jobs-unified-top-card__company-name, .topcard__org-name-link")
                company = await company_el.first.inner_text(timeout=2000) if await company_el.count() > 0 else ""
                
                location_el = page.locator(".jobs-unified-top-card__bullet, .topcard__flavor--bullet")
                location = await location_el.first.inner_text(timeout=2000) if await location_el.count() > 0 else ""
                
                description_el = page.locator("#job-details, .description__text, .core-section-container__content")
                description = await description_el.first.inner_text(timeout=5000) if await description_el.count() > 0 else ""
                
                # Truncate boilerplate "About the company" if it was included in the description text
                desc_clean = description.split("About the company")[0].split("About the Company")[0]
                desc_clean = desc_clean.split("About Us")[0].split("About us")[0]
                
                job = ScrapedJob(
                    title=title.strip(),
                    company=company.strip(),
                    location=location.strip(),
                    url=url,
                    source=self.source,
                    description=desc_clean.strip(),
                    posted_date=None,
                    deadline_month=None,
                    deadline_year=None,
                    requirements=[]
                )
            except Exception as e:
                logger.error(f"Error getting details for {url}: {e}")
                job = ScrapedJob("", "", "", url, self.source, "", None, None, None, [])
                
            await browser.close()
            
        return job
