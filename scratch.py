import asyncio
from playwright.async_api import async_playwright
import json

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(storage_state="data/sessions/handshake_session/state.json")
        page = await context.new_page()
        await page.goto("https://utaustin.joinhandshake.com/job-search/11406875")
        
        # Wait a bit
        await page.wait_for_timeout(5000)
        
        # Dump document.title
        title = await page.title()
        print("document.title:", title)
        
        # See what h1 we have
        h1s = await page.evaluate("() => Array.from(document.querySelectorAll('h1')).map(e => e.innerText)")
        print("h1s:", h1s)
        
        # See what employers links we have
        emp_links = await page.evaluate("() => Array.from(document.querySelectorAll('a[href*=\"/employers/\"]')).map(e => e.innerText)")
        print("employer links:", emp_links)

        # Print all headers just in case
        h2s = await page.evaluate("() => Array.from(document.querySelectorAll('h2')).map(e => e.innerText)")
        print("h2s:", h2s)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
