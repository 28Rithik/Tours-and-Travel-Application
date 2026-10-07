import os
import asyncio
from playwright.async_api import async_playwright

async def main():
    os.makedirs(r"C:\Users\rithi\.gemini\antigravity-ide\brain\3c044726-a75e-47a0-949a-d96c5805a71d", exist_ok=True)
    screenshot_path = r"C:\Users\rithi\.gemini\antigravity-ide\brain\3c044726-a75e-47a0-949a-d96c5805a71d\dispatch_control_center.png"

    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=True)
        context = await browser.new_context(viewport={'width': 1440, 'height': 900})
        page = await context.new_page()

        # Login as admin
        await page.goto("http://127.0.0.1:8000/login/?next=/dispatch/")
        await page.fill('input[name="username"]', 'admin')
        await page.fill('input[name="password"]', 'admin')
        await page.click('button[type="submit"]')
        await page.wait_for_timeout(2000)

        # Navigate to /dispatch/
        await page.goto("http://127.0.0.1:8000/dispatch/")
        await page.wait_for_timeout(1500)

        await page.screenshot(path=screenshot_path, full_page=True)
        await browser.close()
        print(f"Screenshot saved to: {screenshot_path}")

if __name__ == "__main__":
    asyncio.run(main())
