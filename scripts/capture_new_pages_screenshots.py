import os
from playwright.sync_api import sync_playwright

ARTIFACT_DIR = r"C:\Users\rithi\.gemini\antigravity-ide\brain\3c044726-a75e-47a0-949a-d96c5805a71d"

def main():
    pages = [
        ("http://127.0.0.1:8000/customer-portal/services/airport-transfers/", "service_airport_transfers.png"),
        ("http://127.0.0.1:8000/customer-portal/services/wedding-event-transport/", "service_wedding_convoys.png"),
        ("http://127.0.0.1:8000/customer-portal/services/mice-corporate-offsites/", "service_mice_offsites.png"),
        ("http://127.0.0.1:8000/customer-portal/services/industrial-factory-transit/", "service_industrial_transit.png"),
        ("http://127.0.0.1:8000/customer-portal/services/luxury-camper-caravan/", "service_camper_caravan.png"),
    ]

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        context = browser.new_context(viewport={"width": 1366, "height": 900})
        page = context.new_page()

        for url, fname in pages:
            print(f"Navigating to {url} ...")
            page.goto(url, wait_until="networkidle", timeout=15000)
            page.wait_for_timeout(800)
            out_path = os.path.join(ARTIFACT_DIR, fname)
            page.screenshot(path=out_path, full_page=False)
            print(f"Captured: {out_path}")

        browser.close()
        print("All 5 service screenshots captured successfully.")

if __name__ == "__main__":
    main()
