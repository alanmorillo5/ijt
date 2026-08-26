import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(storage_state="data/sessions/handshake_session/state.json")
        page = await context.new_page()
        await Stealth().apply_stealth_async(page)
        
        print("Opening handshake job detail page. PLEASE SOLVE CLOUDFLARE IF IT APPEARS...")
        await page.goto("https://utaustin.joinhandshake.com/job-search/11250192")
        
        # Wait up to 60s for Cloudflare
        try:
            await page.wait_for_selector('h1:not(:has-text("utaustin.joinhandshake.com"))', timeout=60000)
        except Exception:
            pass
            
        await page.wait_for_timeout(3000)
        
        # Dump the text structure to see how to split it
        # Try to find specific sections by header names
        extracted = await page.evaluate("""() => {
            let walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
            let texts = [];
            while(walker.nextNode()) {
                let t = walker.currentNode.nodeValue.trim();
                if(t && t.length > 3) texts.push(t);
            }
            return texts;
        }""")
        
        print("Text Dump Snippet:")
        for i, t in enumerate(extracted):
            print(f"[{i}] {t[:50]}")
        
        await browser.close()

asyncio.run(main())
