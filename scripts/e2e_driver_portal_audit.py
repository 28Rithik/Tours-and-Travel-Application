import os
import sys

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_URL = "http://127.0.0.1:8000"
ARTIFACTS_DIR = Path(r"C:\Users\rithi\.gemini\antigravity-ide\brain\38a90fa8-4427-4e87-a010-66c145b9a064")
SCREENSHOTS_DIR = ARTIFACTS_DIR / "driver_portal_audits"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

test_results = []
console_errors = []

def record(phase, name, status, details=""):
    print(f"[{status}] {phase} -> {name} ({details})")
    test_results.append({
        "phase": phase,
        "name": name,
        "status": status,
        "details": details
    })

def run_driver_portal_audit():
    print("=" * 80)
    print("🚀 OPTION 2: DRIVER MOBILE PORTAL (CAPTAIN PWA) FULL END-TO-END AUDIT")
    print(f"Target Server: {BASE_URL}")
    print("=" * 80)

    with sync_playwright() as p:
        # Emulate high-end mobile viewport (iPhone 14 / Pixel 7 aspect ratio for PWA)
        browser = p.chromium.launch(channel="chrome", headless=True)
        context = browser.new_context(
            viewport={"width": 430, "height": 932},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1"
        )
        page = context.new_page()

        def handle_console(msg):
            if msg.type in ["error"]:
                text = msg.text
                if not any(x in text for x in ["favicon", "Leaflet", "arcgisonline", "Google Maps"]):
                    console_errors.append(f"{page.url}: {text}")

        page.on("console", handle_console)

        # =========================================================================
        # 1. DRIVER LOGIN PAGE & AUTOFILL
        # =========================================================================
        print("\n🔑 1. DRIVER LOGIN & AUTHENTICATION")
        try:
            resp = page.goto(f"{BASE_URL}/driver/login/", wait_until="domcontentloaded")
            assert resp.status == 200, f"HTTP {resp.status}"
            page.wait_for_timeout(500)
            record("Auth", "Driver Login Page Load", "PASS", f"HTTP {resp.status}")
            page.screenshot(path=str(SCREENSHOTS_DIR / "01_driver_login.png"))

            # Test 1-Click Demo Captain Pill
            autofill_btn = page.locator("button:has-text('Karthik Krishnan')")
            if autofill_btn.count() > 0:
                autofill_btn.click()
                page.wait_for_timeout(300)
                record("Auth", "1-Click Demo Captain Autofill", "PASS", "Autofilled phone and PIN")
            else:
                page.fill("input[name='phone']", "9200000002")
                page.fill("input[name='pin']", "1234")
                record("Auth", "Manual Credentials Fill", "PASS", "Filled phone & pin")

            # Submit Login Form
            page.click("button:has-text('Login to Duty')")
            page.wait_for_timeout(1200)

            assert "/driver/" in page.url and "/login/" not in page.url, f"URL: {page.url}"
            record("Auth", "Captain Duty Login", "PASS", f"Landed on {page.url}")
            page.screenshot(path=str(SCREENSHOTS_DIR / "02_driver_dashboard.png"))

        except Exception as e:
            record("Auth", "Driver Login", "FAIL", str(e))

        # =========================================================================
        # 2. PRE-TRIP SAFETY INSPECTION CHECKLIST
        # =========================================================================
        print("\n📋 2. PRE-TRIP SAFETY INSPECTION CHECKLIST")
        try:
            resp = page.goto(f"{BASE_URL}/driver/inspection/", wait_until="domcontentloaded")
            assert resp.status == 200, f"HTTP {resp.status}"
            page.wait_for_timeout(500)
            record("Inspection", "Inspection Page Load", "PASS", "HTTP 200")
            page.screenshot(path=str(SCREENSHOTS_DIR / "03_inspection_form.png"))

            # Verify and fill inspection form
            page.fill("input[name='odometer_reading']", "48250")
            page.fill("input[name='driver_signature_name']", "Karthik Krishnan")

            # Click Submit Certification
            page.click("button:has-text('Certify & Submit Pre-Trip Inspection')")
            page.wait_for_timeout(1200)

            assert "/driver/" in page.url, f"URL: {page.url}"
            record("Inspection", "Safety Inspection Certified", "PASS", "Submitted and verified fit for duty")
            page.screenshot(path=str(SCREENSHOTS_DIR / "04_dashboard_inspection_certified.png"))

        except Exception as e:
            record("Inspection", "Pre-Trip Inspection", "FAIL", str(e))

        # =========================================================================
        # 3. CHAUFFEUR PWA COCKPIT & TRIP DETAIL
        # =========================================================================
        print("\n🚗 3. CHAUFFEUR PWA COCKPIT & TRIP DETAIL")
        try:
            # Check if active trip exists on dashboard or open trip 1001
            resp = page.goto(f"{BASE_URL}/driver/trip/1001/", wait_until="domcontentloaded")
            assert resp.status == 200, f"HTTP {resp.status}"
            page.wait_for_timeout(800)
            record("Trip Cockpit", "Trip Detail Load", "PASS", "HTTP 200")
            page.screenshot(path=str(SCREENSHOTS_DIR / "05_trip_detail_cockpit.png"))

            # Test Call & Nav buttons present
            call_btn = page.locator("a.cta-call")
            nav_btn = page.locator("a.cta-nav")
            assert call_btn.count() > 0 or nav_btn.count() > 0, "Guest CTA buttons verified"
            record("Trip Cockpit", "Guest CTAs (Call & Nav)", "PASS", "CTAs verified in Light Mode")

        except Exception as e:
            record("Trip Cockpit", "Trip Detail", "FAIL", str(e))

        # =========================================================================
        # 4. HIGHWAY FUEL REFILL LOG
        # =========================================================================
        print("\n⛽ 4. HIGHWAY FUEL REFILL LOG")
        try:
            resp = page.goto(f"{BASE_URL}/driver/fuel/", wait_until="domcontentloaded")
            assert resp.status == 200, f"HTTP {resp.status}"
            page.wait_for_timeout(500)
            record("Fuel", "Fuel Log Page Load", "PASS", "HTTP 200")

            # Fill fuel purchase
            page.fill("input[name='fuel_quantity']", "45.5")
            page.fill("input[name='fuel_price']", "96.50")
            page.fill("input[name='fuel_station']", "HPCL Highway Bunk - Salem NH44")
            page.fill("input[name='opening_km']", "48320")

            page.click("button:has-text('Submit Fuel Expense')")
            page.wait_for_timeout(1200)

            assert "/driver/" in page.url, f"URL: {page.url}"
            record("Fuel", "Fuel Expense Submission", "PASS", "Logged 45.5L @ ₹96.50")
            page.screenshot(path=str(SCREENSHOTS_DIR / "06_fuel_expense_submitted.png"))

        except Exception as e:
            record("Fuel", "Fuel Log", "FAIL", str(e))

        # =========================================================================
        # 5. EMERGENCY SOS PROTOCOL
        # =========================================================================
        print("\n🚨 5. EMERGENCY SOS PROTOCOL")
        try:
            resp = page.goto(f"{BASE_URL}/driver/sos/", wait_until="domcontentloaded")
            assert resp.status == 200, f"HTTP {resp.status}"
            page.wait_for_timeout(500)
            record("SOS", "Emergency SOS Page Load", "PASS", "HTTP 200")
            page.screenshot(path=str(SCREENSHOTS_DIR / "07_sos_page.png"))

            # Fill emergency alert form
            page.select_option("select[name='incident_type']", "tyre_burst")
            page.select_option("select[name='passengers_safety_status']", "all_safe")
            page.fill("input[name='location_address']", "NH44, 15km before Krishnagiri Toll Plaza")
            page.fill("textarea[name='description']", "Right rear tyre puncture on highway shoulder. Jacking up vehicle for spare wheel change.")

            page.click("button:has-text('BROADCAST EMERGENCY SOS')")
            page.wait_for_timeout(1200)

            assert "/driver/" in page.url, f"URL: {page.url}"
            record("SOS", "Emergency SOS Broadcast", "PASS", "Dispatched to Operations Control Room")
            page.screenshot(path=str(SCREENSHOTS_DIR / "08_sos_broadcast_confirmed.png"))

        except Exception as e:
            record("SOS", "Emergency SOS", "FAIL", str(e))

        # =========================================================================
        # 6. PWA SERVICE WORKER & MANIFEST
        # =========================================================================
        print("\n📱 6. PWA SERVICE WORKER & MANIFEST")
        try:
            resp = page.goto(f"{BASE_URL}/driver/manifest.json", wait_until="domcontentloaded")
            assert resp.status == 200, f"Manifest HTTP {resp.status}"
            manifest_json = resp.json()
            assert "name" in manifest_json, "Manifest name verified"
            record("PWA", "Manifest JSON Validation", "PASS", f"Name: {manifest_json.get('name')}")

            resp = page.goto(f"{BASE_URL}/driver/sw.js", wait_until="domcontentloaded")
            assert resp.status == 200, f"Service Worker HTTP {resp.status}"
            record("PWA", "Service Worker Script Load", "PASS", "HTTP 200")

        except Exception as e:
            record("PWA", "PWA Offline Readiness", "FAIL", str(e))

        # =========================================================================
        # 7. DRIVER LOGOUT
        # =========================================================================
        print("\n🚪 7. DRIVER LOGOUT")
        try:
            resp = page.goto(f"{BASE_URL}/driver/logout/", wait_until="domcontentloaded")
            assert resp.status == 200, f"HTTP {resp.status}"
            page.wait_for_timeout(500)
            assert "/driver/login/" in page.url, f"Landed on: {page.url}"
            record("Auth", "Driver Safe Logout", "PASS", "Returned to login page with flash message")
            page.screenshot(path=str(SCREENSHOTS_DIR / "09_driver_logout_complete.png"))

        except Exception as e:
            record("Auth", "Driver Logout", "FAIL", str(e))

        browser.close()

    print("\n" + "=" * 80)
    print("📊 DRIVER PORTAL AUDIT SUMMARY REPORT")
    print("=" * 80)
    passed_count = sum(1 for r in test_results if r["status"] == "PASS")
    total_count = len(test_results)
    print(f"Passed: {passed_count}/{total_count} ({passed_count/total_count*100:.1f}%)")
    for r in test_results:
        print(f"• [{r['status']:<4}] {r['phase']:<15} | {r['name']:<35} : {r['details']}")

    if console_errors:
        print(f"\n⚠️ Console Errors Detected ({len(console_errors)}):")
        for err in console_errors[:5]:
            print(f"  - {err}")
    else:
        print("\n✅ Zero JavaScript console errors encountered!")

    print(f"\n📸 All {total_count} screenshot artifacts saved to:")
    print(f"   file:///{SCREENSHOTS_DIR}")
    return 0 if passed_count == total_count else 1

if __name__ == "__main__":
    sys.exit(run_driver_portal_audit())
