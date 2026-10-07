import os
from playwright.sync_api import sync_playwright

ARTIFACT_DIR = r"C:\Users\rithi\.gemini\antigravity-ide\brain\3c044726-a75e-47a0-949a-d96c5805a71d"

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 950})
        page = context.new_page()

        print("Navigating to login...")
        page.goto("http://127.0.0.1:8000/login/?next=/dashboard/", wait_until="domcontentloaded", timeout=30000)
        
        # Check if login form exists
        if page.locator("input[name='username']").count() > 0:
            print("Logging in with admin credentials...")
            page.fill("input[name='username']", "admin")
            page.fill("input[name='password']", "admin")
            page.click("button[type='submit']")
            page.wait_for_timeout(2000)
        
        print("Navigating to /dashboard/ ...")
        page.goto("http://127.0.0.1:8000/dashboard/", wait_until="domcontentloaded", timeout=30000)
        page.wait_for_selector(".cr-wrapper", timeout=15000)
        page.wait_for_timeout(1000)

        out_path = os.path.join(ARTIFACT_DIR, "staff_dashboard_redesigned.png")
        page.screenshot(path=out_path, full_page=False)
        print(f"Captured: {out_path}")

        # Also capture full page view
        out_full_path = os.path.join(ARTIFACT_DIR, "staff_dashboard_redesigned_full.png")
        page.screenshot(path=out_full_path, full_page=True)
        print(f"Captured: {out_full_path}")

        browser.close()

if __name__ == "__main__":
    main()
