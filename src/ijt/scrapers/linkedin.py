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
            logger.info("Please log in manually. Close the browser when done.")
            
            try:
                # Wait for the browser to be closed by the user
                while len(context.pages) > 0:
                    await page.wait_for_timeout(1000)
            except Exception:
                pass
            
            self.session_dir.mkdir(parents=True, exist_ok=True)
            await context.storage_state(path=state_path)
            await browser.close()
            logger.info("LinkedIn session saved.")

    async def search(self, keywords: list[str], filters: dict) -> list[ScrapedJob]:
        logger.info(f"Searching LinkedIn for {keywords}")
        jobs = []
        state_path = self.session_dir / "state.json"
        
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
                query = urllib.parse.urlencode({'keywords': keyword})
                await page.goto(f"https://www.linkedin.com/jobs/search/?{query}")
                await rate_limit(3, 5)
                
                # Try to find some job cards (this is a simplified example)
                job_cards = await page.locator(".job-card-container").all()
                for card in job_cards[:5]:  # limit for demo
                    try:
                        title_el = card.locator(".job-card-list__title")
                        company_el = card.locator(".job-card-container__company-name")
                        location_el = card.locator(".job-card-container__metadata-item")
                        
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
                title = await page.locator("h1.t-24").inner_text()
                company = await page.locator(".jobs-unified-top-card__company-name").inner_text()
                location = await page.locator(".jobs-unified-top-card__bullet").first.inner_text()
                
                description_el = page.locator("#job-details")
                description = await description_el.inner_text() if await description_el.count() > 0 else ""
                
                job = ScrapedJob(
                    title=title.strip(),
                    company=company.strip(),
                    location=location.strip(),
                    url=url,
                    source=self.source,
                    description=description.strip(),
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
