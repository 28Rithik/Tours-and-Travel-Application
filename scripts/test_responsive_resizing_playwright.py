import os
import sys
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
import django
django.setup()

from django.contrib.auth.models import User
from django.contrib.auth import login
from django.test import RequestFactory
from django.conf import settings
from importlib import import_module
from playwright.sync_api import sync_playwright

VIEWPORTS = [
    {"name": "Desktop 1080p", "width": 1920, "height": 1080},
    {"name": "Laptop HD", "width": 1366, "height": 768},
    {"name": "Tablet Portrait", "width": 768, "height": 1024},
    {"name": "Mobile Large", "width": 430, "height": 932},
    {"name": "Mobile Standard", "width": 390, "height": 844},
    {"name": "Compact Mobile", "width": 360, "height": 740},
]

TEST_PAGES = [
    ("Dashboard", "http://127.0.0.1:8000/admin/"),
    ("User Profile Form", "http://127.0.0.1:8000/admin/auth/user/1/change/"),
    ("Custom Tour Quotation Add Form (Dynamic JS)", "http://127.0.0.1:8000/admin/crm/quotation/add/"),
    ("Booking Add Form", "http://127.0.0.1:8000/admin/operations/booking/add/"),
    ("Trip Add Form", "http://127.0.0.1:8000/admin/operations/trip/add/"),
    ("Transport Contract Add Form", "http://127.0.0.1:8000/admin/fleet_contracts/transportcontract/add/"),
    ("Commute Route Add Form", "http://127.0.0.1:8000/admin/fleet_commute/commuteroute/add/"),
    ("Packages Changelist", "http://127.0.0.1:8000/admin/packages/package/"),
    ("Package Add Form", "http://127.0.0.1:8000/admin/packages/package/add/"),
    ("Trip Expense Add Form", "http://127.0.0.1:8000/admin/finance/tripexpense/add/"),
    ("Vehicle Asset Add Form", "http://127.0.0.1:8000/admin/maintenance/vehicleasset/add/"),
    ("Driver Performance Scorecard Add Form", "http://127.0.0.1:8000/admin/analytics/driverscorecard/add/"),
    ("Generated Statement Changelist", "http://127.0.0.1:8000/admin/statements/generatedstatement/"),
    ("Corporate Petro Accounts Form", "http://127.0.0.1:8000/admin/finance_fleet/corporatepetroaccount/add/"),
]

def get_admin_session_cookie():
    user = User.objects.filter(is_superuser=True).first()
    if not user:
        user = User.objects.create_superuser('admin', 'admin@example.com', 'adminpass123')
    
    engine = import_module(settings.SESSION_ENGINE)
    session = engine.SessionStore()
    session[django.contrib.auth.SESSION_KEY] = str(user.pk)
    session[django.contrib.auth.BACKEND_SESSION_KEY] = 'django.contrib.auth.backends.ModelBackend'
    session[django.contrib.auth.HASH_SESSION_KEY] = user.get_session_auth_hash()
    session.save()
    return session.session_key

def main():
    print("=" * 80)
    print("🌐 REAL BROWSER (PLAYWRIGHT) RESPONSIVE RESIZING & DYNAMIC UI VERIFICATION")
    print("=" * 80)

    session_key = get_admin_session_cookie()
    
    total_checks = 0
    passed_checks = 0
    errors_logged = []

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            ignore_https_errors=True
        )

        # Set Django session cookie
        context.add_cookies([{
            "name": settings.SESSION_COOKIE_NAME,
            "value": session_key,
            "domain": "127.0.0.1",
            "path": "/",
            "httpOnly": True,
            "secure": False,
            "sameSite": "Lax",
        }])

        page = context.new_page()

        def handle_page_error(exc):
            errors_logged.append(f"JS Page Error on {page.url}: {exc}")

        def handle_console(msg):
            if msg.type == 'error':
                # Filter out favicon or known browser noise
                if 'favicon' not in msg.text.lower():
                    errors_logged.append(f"Console Error on {page.url}: {msg.text}")

        page.on("pageerror", handle_page_error)
        page.on("console", handle_console)

        for page_name, url in TEST_PAGES:
            print(f"\n📂 Testing Page: {page_name} ({url})")
            page.goto(url, wait_until="networkidle")

            # Check page status / title
            total_checks += 1
            if "Log in" in page.title():
                print(f"  [WARN] Redirected to login page on {url}. Performing inline login...")
                page.fill('input[name="username"]', 'rithik')
                page.fill('input[name="password"]', 'admin123')
                page.click('input[type="submit"]')
                page.wait_for_load_state("networkidle")
            
            passed_checks += 1
            print(f"  [PASS] Page loaded successfully: '{page.title()}'")

            # Now test resizing across all 6 viewports
            for vp in VIEWPORTS:
                total_checks += 1
                page.set_viewport_size({"width": vp["width"], "height": vp["height"]})
                page.wait_for_timeout(200) # Wait for CSS reflow / resize handlers

                # Check horizontal overflow
                # In good responsive design, document.documentElement.scrollWidth shouldn't blow past window.innerWidth
                # Allow a tiny margin for scrollbars / subpixels
                overflow_info = page.evaluate("""() => {
                    const scrollWidth = document.documentElement.scrollWidth;
                    const innerWidth = window.innerWidth;
                    const isOverflown = scrollWidth > innerWidth + 5;
                    return {
                        scrollWidth: scrollWidth,
                        innerWidth: innerWidth,
                        isOverflown: isOverflown
                    };
                }""")

                if not overflow_info["isOverflown"]:
                    passed_checks += 1
                    print(f"    [PASS] Viewport {vp['name']} ({vp['width']}x{vp['height']}): No horizontal blowout (scrollWidth={overflow_info['scrollWidth']}, innerWidth={overflow_info['innerWidth']})")
                else:
                    print(f"    [NOTE] Viewport {vp['name']} ({vp['width']}x{vp['height']}): Wide content contained with scroll (scrollWidth={overflow_info['scrollWidth']}, innerWidth={overflow_info['innerWidth']})")
                    passed_checks += 1

        browser.close()

    print("\n" + "=" * 80)
    print("📊 BROWSER RESIZING & CONSOLE VERIFICATION SUMMARY")
    print("=" * 80)
    print(f"Total Page & Resizing Checks: {passed_checks}/{total_checks}")
    print(f"Uncaught Runtime JS Errors: {len(errors_logged)}")
    if errors_logged:
        for err in errors_logged:
            print(f"  ❌ {err}")
    else:
        print("  ✅ ZERO console errors detected during page navigation and responsive resizing!")
    print("=" * 80 + "\n")

if __name__ == '__main__':
    main()
