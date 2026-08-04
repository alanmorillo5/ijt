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
            browser = await p.chromium.launch(headless=False)
            
            state_path = self.session_dir / "state.json"
            context_kwargs = {}
            if state_path.exists():
                context_kwargs["storage_state"] = state_path
                
            context = await browser.new_context(**context_kwargs)
            page = await context.new_page()
            
            await page.goto(self.school_url)
            logger.info("Please log in manually via SSO. Close the browser when done.")
            
            try:
                while len(context.pages) > 0:
                    await page.wait_for_timeout(1000)
            except Exception:
                pass
            
            self.session_dir.mkdir(parents=True, exist_ok=True)
            await context.storage_state(path=state_path)
            await browser.close()
            logger.info("Handshake session saved.")

    async def search(self, keywords: list[str], filters: dict) -> list[ScrapedJob]:
        logger.info(f"Searching Handshake for {keywords}")
        jobs = []
        state_path = self.session_dir / "state.json"
        
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
                query = urllib.parse.urlencode({'query': keyword})
                await page.goto(f"https://app.joinhandshake.com/stu/jobs?{query}")
                await rate_limit(3, 5)
                
                # Try to find some job cards
                try:
                    job_cards = await page.locator(".style__job-list___11Bw- li").all()
                    for card in job_cards[:5]:
                        title_el = card.locator("h2 a")
                        company_el = card.locator(".style__employer-name___23N2M")
                        location_el = card.locator(".style__location___3gTzR")
                        
                        title = await title_el.inner_text()
                        company = await company_el.inner_text() if await company_el.count() > 0 else "Unknown"
                        location = await location_el.inner_text() if await location_el.count() > 0 else "Unknown"
                        href = await title_el.get_attribute("href")
                        
                        if href:
                            full_url = f"https://app.joinhandshake.com{href}"
                            full_url = full_url.split("?")[0]
                            
                            jobs.append(ScrapedJob(
                                title=title.strip(),
                                company=company.strip(),
                                location=location.strip(),
                                url=full_url,
                                source=self.source,
                                description="",
                                posted_date=None,
                                deadline_month=None,
                                deadline_year=None,
                                requirements=[]
                            ))
                except Exception as e:
                    logger.error(f"Error extracting Handshake jobs: {e}")
                    
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
            
            try:
                title = await page.locator("h1").first.inner_text()
                company_el = page.locator(".style__employer-name___23N2M").first
                company = await company_el.inner_text() if await company_el.count() > 0 else "Unknown"
                
                description_el = page.locator(".style__description___3Rj1N").first
                description = await description_el.inner_text() if await description_el.count() > 0 else ""
                
                job = ScrapedJob(
                    title=title.strip(),
                    company=company.strip(),
                    location="Unknown",
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
