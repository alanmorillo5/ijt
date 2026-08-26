import asyncio
from playwright.async_api import async_playwright
import json

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(storage_state="data/sessions/handshake_session/state.json")
        page = await context.new_page()
        
        # Go to a typical handshake job search
        await page.goto("https://tamu.joinhandshake.com/job-search")
        await page.wait_for_timeout(5000)
        
        # Get first job link
        all_hrefs = await page.evaluate("""() => {
            return Array.from(document.querySelectorAll("a")).map(a => a.getAttribute("href")).filter(Boolean)
        }""")
        links = list(set([h for h in all_hrefs if "/job-search/" in h]))
        
        if not links:
            print("No links found.")
            return
            
        full_url = f"https://tamu.joinhandshake.com{links[0]}".split("?")[0]
        print("Testing URL:", full_url)
        
        await page.goto(full_url)
        await page.wait_for_timeout(5000)
        
        title_el = page.locator("h1")
        title = await title_el.first.inner_text() if await title_el.count() > 0 else ""
        print("H1 Title:", repr(title))
        
        # get H2s
        h2s = await page.evaluate("Array.from(document.querySelectorAll('h2')).map(h => h.innerText)")
        print("H2s:", h2s)
        
        await browser.close()

asyncio.run(main())
