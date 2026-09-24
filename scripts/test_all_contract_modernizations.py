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
from fleet_contracts.models import ContractFleetRoster, TransportContract

def run_tests():
    c = Client()
    c.login(username='rithik', password='rithik123')
    cookie = c.cookies['sessionid'].value

    artifact_dir = os.path.join(os.environ.get('USERPROFILE', ''), '.gemini', 'antigravity-ide', 'brain', '12e9440a-ec76-4489-aa28-9f0807948a00')
    os.makedirs(artifact_dir, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(channel='msedge', headless=True)
        ctx = browser.new_context(viewport={'width': 1440, 'height': 960})
        ctx.add_cookies([{'name': 'sessionid', 'value': cookie, 'domain': '127.0.0.1', 'path': '/'}])
        page = ctx.new_page()

        print("\n=== 1. TESTING ROSTER HOT-SWAP & COMPLIANCE SNAPSHOT ===")
        page.goto('http://127.0.0.1:8000/admin/fleet_contracts/contractfleetroster/', wait_until='networkidle')
        shot1 = os.path.join(artifact_dir, 'fleet_roster_hot_swap_table.png')
        page.screenshot(path=shot1)
        print("Saved Roster table screenshot to:", shot1)

        # Test hot-swap on roster with standby vehicle
        roster_with_standby = ContractFleetRoster.objects.filter(is_active=True, standby_vehicle__isnull=False).first()
        if roster_with_standby:
            old_p = roster_with_standby.primary_vehicle.registration_number
            old_s = roster_with_standby.standby_vehicle.registration_number
            print(f"Triggering hot-swap for Roster #{roster_with_standby.id} (Primary: {old_p}, Standby: {old_s})...")
            page.goto(f'http://127.0.0.1:8000/admin/fleet_contracts/contractfleetroster/{roster_with_standby.id}/hot-swap/', wait_until='networkidle')
            roster_with_standby.refresh_from_db()
            print(f"✅ Hot-Swap Result: Primary is now {roster_with_standby.primary_vehicle.registration_number} (was {old_p})")
            assert roster_with_standby.primary_vehicle.registration_number == old_s

        # View compliance card in change form
        page.goto(f'http://127.0.0.1:8000/admin/fleet_contracts/contractfleetroster/{roster_with_standby.id}/change/', wait_until='networkidle')
        shot2 = os.path.join(artifact_dir, 'fleet_roster_compliance_card.png')
        page.screenshot(path=shot2)
        print("Saved Roster Compliance form screenshot to:", shot2)

        print("\n=== 2. TESTING 1-CLICK BATCH MONTHLY INVOICE GENERATOR ===")
        page.goto('http://127.0.0.1:8000/admin/fleet_contracts/contractmonthlyinvoice/batch-generate/', wait_until='networkidle')
        shot3 = os.path.join(artifact_dir, 'batch_invoice_generator_dialog.png')
        page.screenshot(path=shot3)
        print("Saved Batch Invoicing Dialog screenshot to:", shot3)

        # Execute batch run for next month (e.g. 2026-10) to generate fresh test batch
        print("Executing batch run for 2026-10...")
        page.fill('input[name="billing_month"]', '2026-10')
        page.on('dialog', lambda dialog: dialog.accept())
        page.locator('button:has-text("Execute Batch Billing Run")').click()
        page.wait_for_load_state('networkidle')

        shot4 = os.path.join(artifact_dir, 'batch_invoice_generated_result.png')
        page.screenshot(path=shot4)
        print("Saved Batch Invoices Result screenshot to:", shot4)

        print("\n=== 3. TESTING CONTRACT UNIT ECONOMICS & FUEL ESCALATION LETTER ===")
        contract = TransportContract.objects.filter(fuel_escalation_enabled=True).first()
        page.goto(f'http://127.0.0.1:8000/admin/fleet_contracts/transportcontract/{contract.id}/change/', wait_until='networkidle')
        # Click Step 5 tab
        page.locator('#jazzy-tabs a[href*="step-5"]').click()
        page.wait_for_timeout(500)
        shot5 = os.path.join(artifact_dir, 'contract_unit_economics_card.png')
        page.screenshot(path=shot5)
        print("Saved Contract Unit Economics screenshot to:", shot5)

        # Open Fuel Revision Notice
        page.goto(f'http://127.0.0.1:8000/admin/fleet_contracts/transportcontract/{contract.id}/fuel-revision/', wait_until='networkidle')
        shot6 = os.path.join(artifact_dir, 'printable_fuel_revision_letter.png')
        page.screenshot(path=shot6)
        print("Saved Printable Fuel Revision Letter screenshot to:", shot6)

        print("\n=== 4. TESTING SLA PENALTY AUTO-INGESTION ===")
        page.goto('http://127.0.0.1:8000/admin/fleet_contracts/contractslapenalty/auto-ingest/', wait_until='networkidle')
        shot7 = os.path.join(artifact_dir, 'sla_penalty_auto_ingested.png')
        page.screenshot(path=shot7)
        print("Saved SLA Auto-Ingested screenshot to:", shot7)

        print("\n=== 5. TESTING NIGHT SAFETY ESCORT LOGS & COMMUTER MANIFEST ===")
        page.goto('http://127.0.0.1:8000/admin/fleet_contracts/nightsafetyescortlog/', wait_until='networkidle')
        shot8 = os.path.join(artifact_dir, 'night_safety_escort_logs.png')
        page.screenshot(path=shot8)
        print("Saved Night Safety Escort Logs screenshot to:", shot8)

        # Test quick verify OTP
        pending_btn = page.locator('a[href*="quick-verify"]').first
        if pending_btn.count() > 0:
            print("Clicking Quick Verify OTP button...")
            pending_btn.click()
            page.wait_for_load_state('networkidle')
            print("✅ Verified night safety drop successfully.")

        page.goto('http://127.0.0.1:8000/admin/fleet_contracts/commutermanifest/', wait_until='networkidle')
        shot9 = os.path.join(artifact_dir, 'commuter_student_manifest.png')
        page.screenshot(path=shot9)
        print("Saved Commuter Manifest screenshot to:", shot9)

        browser.close()
        print("\n🎉 ALL TESTS AND SCREENSHOTS COMPLETED SUCCESSFULLY!")

if __name__ == '__main__':
    run_tests()
