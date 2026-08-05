import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(storage_state="data/sessions/handshake_session/state.json")
        page = await context.new_page()
        
        await page.goto("https://utaustin.joinhandshake.com/job-search")
        await page.wait_for_timeout(5000)
        
        results = await page.evaluate("""() => {
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
        print("Extracted Data:", results)
        
        await browser.close()

asyncio.run(main())
