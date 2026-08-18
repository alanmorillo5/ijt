from pathlib import Path
from typing import List, Dict
from playwright.async_api import async_playwright, Page
from playwright_stealth import Stealth
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
        cf_timeout_ms = filters.get("cloudflare_wait_timeout", 120) * 1000
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context_kwargs = {}
            if state_path.exists():
                context_kwargs["storage_state"] = state_path
            else:
                logger.error("Session not found. Please run 'ijt login handshake' first.")
                return []
                
            context = await browser.new_context(**context_kwargs)
            page = await context.new_page()
            await Stealth().apply_stealth_async(page)
            
            for keyword in keywords:
                if len(jobs) >= max_jobs:
                    break
                    
                query = urllib.parse.urlencode({'query': keyword})
                await page.goto(f"{self.school_url}/job-search?{query}")
                await rate_limit(3, 5)
                
                try:
                    # Check for Cloudflare challenge
                    try:
                        cf = page.locator("text='Performing security verification'")
                        if await cf.count() > 0:
                            print(f"\n[!] Cloudflare challenge detected! Please check the opened browser window and manually click the checkbox. Waiting up to {cf_timeout_ms/1000}s...")
                            try:
                                await page.frame_locator("iframe").locator("input[type='checkbox']").click(timeout=5000)
                            except:
                                pass
                            await page.wait_for_selector("a[href*='/job-search/']", timeout=cf_timeout_ms) # Wait for user to solve CF
                    except Exception:
                        pass
                        
                    await page.wait_for_timeout(5000) # Give it time to load
                    try:
                        await page.wait_for_load_state("networkidle", timeout=5000)
                    except:
                        pass # Ignore timeout if network isn't fully idle
                    
                    # Extract job info directly from the result cards via DOM
                    card_data = await page.evaluate("""() => {
                        let cards = document.querySelectorAll('div[data-hook^="job-result-card | "]');
                        let data = [];
                        for (let c of cards) {
                            let a = c.querySelector('a');
                            if (a) {
                                let lines = c.innerText.split('\\n');
                                data.push({
                                    url: a.href,
                                    company: lines[0] || "",
                                    title: lines[1] || "",
                                    location: lines[2] || ""
                                });
                            }
                        }
                        return data;
                    }""")
                    
                    # Deduplicate by url
                    seen_urls = set()
                    for job_data in card_data:
                        if len(jobs) >= max_jobs:
                            break
                            
                        # Clean url
                        full_url = job_data["url"].split("?")[0]
                        if full_url in seen_urls or "/job-search/" not in full_url:
                            continue
                            
                        seen_urls.add(full_url)
                        
                        jobs.append(ScrapedJob(
                            title=job_data["title"].strip(),
                            company=job_data["company"].strip(),
                            location=job_data["location"].strip(),
                            url=full_url,
                            source=self.source,
                            description="",
                            posted_date=None, deadline_month=None, deadline_year=None, requirements=[]
                        ))
                    
                    print(f"Found {len(jobs)} jobs from {keyword} search")
                except Exception as e:
                    logger.error(f"Error extracting Handshake jobs: {e}")
                    
            await browser.close()
            
        return jobs

    async def get_job_details(self, url: str) -> ScrapedJob:
        state_path = self.session_dir / "state.json"
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context(storage_state=state_path if state_path.exists() else None)
            page = await context.new_page()
            await Stealth().apply_stealth_async(page)
            
            await page.goto(url)
            await rate_limit(3, 5)
            
            try:
                # Need to wait for job details to load
                try:
                    await page.wait_for_load_state("networkidle", timeout=5000)
                except:
                    pass
                await page.wait_for_timeout(2000)
                
                # Handshake usually stores the job description in a specific div or within the main element
                desc = await page.evaluate("""() => {
                    let jd = document.querySelector('div[data-hook="job-description"]');
                    if (jd) return jd.innerText;
                    
                    let main = document.querySelector('main');
                    if (main) return main.innerText;
                    
                    return document.body.innerText;
                }""")
                
                # Truncate text to remove noise from employer info and similar jobs
                desc_clean = desc.split("Similar jobs")[0].split("Similar Jobs")[0]
                desc_clean = desc_clean.split("About the employer")[0].split("About the Employer")[0]
                
                job = ScrapedJob(
                    title="", # Will be filled by CLI from prelim
                    company="", 
                    location="",
                    url=url,
                    source=self.source,
                    description=desc_clean.strip(),
                    posted_date=None, deadline_month=None, deadline_year=None, requirements=[]
                )
            except Exception as e:
                logger.error(f"Error getting details for {url}: {e}")
                job = ScrapedJob("", "", "", url, self.source, "", None, None, None, [])
                
            await browser.close()
            
        return job
