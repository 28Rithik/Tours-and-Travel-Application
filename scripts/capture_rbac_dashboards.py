import os
from playwright.sync_api import sync_playwright

ARTIFACT_DIR = r"C:\Users\rithi\.gemini\antigravity-ide\brain\3c044726-a75e-47a0-949a-d96c5805a71d"

TEST_USERS = [
    ("admin", "admin", "rbac_admin_dashboard.png"),
    ("fleet_mgr", "fleet123", "rbac_fleet_mgr_dashboard.png"),
    ("booking_mgr", "booking123", "rbac_booking_mgr_dashboard.png"),
    ("finance_user", "finance123", "rbac_finance_user_dashboard.png"),
]

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)

        for username, password, filename in TEST_USERS:
            print(f"Logging in as {username} ...")
            context = browser.new_context(viewport={"width": 1440, "height": 950})
            page = context.new_page()

            page.goto("http://127.0.0.1:8000/login/?next=/dashboard/", wait_until="domcontentloaded", timeout=30000)
            page.fill("input[name='username']", username)
            page.fill("input[name='password']", password)
            page.click("button[type='submit']")
            page.wait_for_timeout(2000)

            if "/dashboard/" not in page.url:
                page.goto("http://127.0.0.1:8000/dashboard/", wait_until="domcontentloaded", timeout=30000)
            
            page.wait_for_selector(".cr-wrapper", timeout=15000)
            page.wait_for_timeout(1000)

            out_path = os.path.join(ARTIFACT_DIR, filename)
            page.screenshot(path=out_path, full_page=False)
            print(f"Successfully captured: {out_path}")
            context.close()

        browser.close()
        print("All 4 RBAC role dashboards captured successfully.")

if __name__ == "__main__":
    main()
