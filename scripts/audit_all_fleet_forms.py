import os
import sys
import django

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.abspath('.'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
django.setup()

from django.test import Client
from playwright.sync_api import sync_playwright
from fleet_contracts.models import (
    TransportContract, ContractFleetRoster, ContractSLAPenalty, ContractMonthlyInvoice
)

def test_all_forms():
    c = Client()
    c.login(username='rithik', password='rithik123')
    session_cookie = c.cookies['sessionid'].value

    urls_to_test = [
        # 1. Transport Contracts
        ('/admin/fleet_contracts/transportcontract/add/', 'TransportContract Add'),
        (f'/admin/fleet_contracts/transportcontract/{TransportContract.objects.first().id}/change/', 'TransportContract Change'),
        # 2. Dedicated Fleet & Crew Roster
        ('/admin/fleet_contracts/contractfleetroster/add/', 'ContractFleetRoster Add'),
        (f'/admin/fleet_contracts/contractfleetroster/{ContractFleetRoster.objects.first().id}/change/', 'ContractFleetRoster Change'),
        # 3. SLA Penalties & Deductions
        ('/admin/fleet_contracts/contractslapenalty/add/', 'ContractSLAPenalty Add'),
        (f'/admin/fleet_contracts/contractslapenalty/{ContractSLAPenalty.objects.first().id}/change/', 'ContractSLAPenalty Change'),
        # 4. Contract Monthly Invoices
        ('/admin/fleet_contracts/contractmonthlyinvoice/add/', 'ContractMonthlyInvoice Add'),
        (f'/admin/fleet_contracts/contractmonthlyinvoice/{ContractMonthlyInvoice.objects.first().id}/change/', 'ContractMonthlyInvoice Change'),
    ]

    with sync_playwright() as p:
        browser = p.chromium.launch(channel='msedge', headless=True)
        context = browser.new_context(viewport={'width': 1440, 'height': 960})
        context.add_cookies([{'name': 'sessionid', 'value': session_cookie, 'domain': '127.0.0.1', 'path': '/'}])
        page = context.new_page()

        console_errors = []
        page.on('console', lambda msg: console_errors.append(f"[{msg.type}] {msg.text}") if msg.type in ['error', 'warning'] else None)
        page.on('pageerror', lambda err: console_errors.append(f"[PAGE ERROR] {err}"))

        print("\n=== AUDITING ALL FORMS IN FLEET_CONTRACTS ===")
        for path, label in urls_to_test:
            print(f"\n--- Testing {label} ({path}) ---")
            console_errors.clear()
            resp = page.goto(f'http://127.0.0.1:8000{path}', wait_until='networkidle')
            print(f"  HTTP Status: {resp.status}")
            assert resp.status == 200, f"Expected 200, got {resp.status}"

            # Check tabs
            tabs = page.locator('#jazzy-tabs .nav-link').all()
            print(f"  Found {len(tabs)} tabs.")
            for i, tab in enumerate(tabs):
                href = tab.get_attribute('href')
                tab_title = tab.text_content().strip()
                # Test clicking tab
                try:
                    tab.click(timeout=2000)
                    page.wait_for_timeout(200)
                    pane = page.locator(href)
                    visible = pane.is_visible()
                    if not visible:
                        print(f"  ❌ TAB CLICK FAILED to switch pane! Tab {i} '{tab_title}' -> href '{href}' is NOT visible!")
                    else:
                        print(f"  ✅ Tab {i} '{tab_title}' switched successfully.")
                except Exception as e:
                    print(f"  ❌ EXCEPTION clicking tab {i} '{tab_title}' ({href}): {e}")

            if console_errors:
                print("  Console Errors/Warnings:")
                for err in console_errors[:5]:
                    print(f"    {err}")
            else:
                print("  No console errors.")

        browser.close()

if __name__ == '__main__':
    test_all_forms()
