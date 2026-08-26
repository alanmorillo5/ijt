import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(storage_state="data/sessions/handshake_session/state.json")
        page = await context.new_page()
        
        await page.goto("https://utaustin.joinhandshake.com/job-search")
        await page.wait_for_timeout(5000)
        
        # Get first job link
        all_hrefs = await page.evaluate("""() => {
            return Array.from(document.querySelectorAll("a")).map(a => a.getAttribute("href")).filter(Boolean)
        }""")
        links = list(set([h for h in all_hrefs if "/job-search/" in h]))
        
        if not links:
            print("No links found.")
            return
            
        full_url = f"https://utaustin.joinhandshake.com{links[0]}".split("?")[0]
        print("Testing URL:", full_url)
        
        await page.goto(full_url)
        await page.wait_for_timeout(8000)
        
        # Look for data-hooks
        hooks = await page.evaluate("""() => {
            let els = document.querySelectorAll('[data-hook]');
            let results = {};
            for(let el of els) {
                let h = el.getAttribute('data-hook');
                if(h.includes('job') || h.includes('title')) {
                    results[h] = el.innerText.trim().substring(0, 50);
                }
            }
            return results;
        }""")
        print("Hooks:", hooks)
        
        await browser.close()

asyncio.run(main())
