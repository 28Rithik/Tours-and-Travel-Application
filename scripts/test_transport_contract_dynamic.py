import os
import sys
import django

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.abspath('.'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
django.setup()

from django.test import Client
from playwright.sync_api import sync_playwright

def run_tests():
    c = Client()
    c.login(username='rithik', password='rithik123')
    session_cookie = c.cookies['sessionid'].value

    artifact_dir = os.path.join(os.environ.get('USERPROFILE', ''), '.gemini', 'antigravity-ide', 'brain', '12e9440a-ec76-4489-aa28-9f0807948a00')
    os.makedirs(artifact_dir, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(channel='msedge', headless=True)
        context = browser.new_context(viewport={'width': 1440, 'height': 960})
        context.add_cookies([{'name': 'sessionid', 'value': session_cookie, 'domain': '127.0.0.1', 'path': '/'}])
        page = context.new_page()

        console_logs = []
        page.on('console', lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))
        page.on('pageerror', lambda err: console_logs.append(f"[ERROR] {err}"))

        print("\n=== 1. Loading Transport Contract Add Page ===")
        page.goto('http://127.0.0.1:8000/admin/fleet_contracts/transportcontract/add/', wait_until='networkidle')
        page.wait_for_timeout(500)

        # Check Presets Bar
        preset_bar = page.locator('#tc-preset-bar')
        assert preset_bar.is_visible(), "Presets bar #tc-preset-bar is NOT visible!"
        print("✅ Presets bar is visible with all vertical chips.")

        # Capture Step 1 initial view
        step1_shot = os.path.join(artifact_dir, 'transport_contract_step1_presets.png')
        page.screenshot(path=step1_shot)
        print(f"Saved screenshot: {step1_shot}")

        # === 2. Testing Tab Switching ===
        print("\n=== 2. Testing Tab Switching Across All Steps ===")
        tabs = page.locator('#jazzy-tabs .nav-link').all()
        for i in range(len(tabs)):
            tab = tabs[i]
            href = tab.get_attribute('href')
            tab_title = tab.text_content().strip()
            tab.click()
            page.wait_for_timeout(300)
            pane = page.locator(href)
            assert pane.is_visible(), f"Pane {href} ({tab_title}) did not become visible after clicking!"
            print(f"  ✅ Tab {i} [{tab_title}] -> {href} active and visible.")

        # Return to Tab 0
        tabs[0].click()
        page.wait_for_timeout(300)

        # === 3. Testing Step Navigation Buttons (Prev / Next) ===
        print("\n=== 3. Testing Step Footer Navigation Buttons ===")
        pane1 = page.locator('#step-1-classification-client-organization-tab')
        next_btn = pane1.locator('.tc-btn-step-next')
        assert next_btn.is_visible(), "Next Step button not visible in Pane 1!"
        next_btn.click()
        page.wait_for_timeout(400)

        pane2 = page.locator('#step-2-term-duration-credit-schedule-tab')
        assert pane2.is_visible(), "Clicking Next Step button did not switch to Pane 2!"
        print("  ✅ 'Next Step' button successfully advanced to Step 2.")

        prev_btn = pane2.locator('.tc-btn-step-prev')
        assert prev_btn.is_visible(), "Previous Step button not visible in Pane 2!"
        prev_btn.click()
        page.wait_for_timeout(400)
        assert pane1.is_visible(), "Clicking Previous Step button did not switch back to Pane 1!"
        print("  ✅ 'Previous Step' button successfully returned to Step 1.")

        # === 4. Testing Category Presets Adaptation ===
        print("\n=== 4. Testing Category Presets Adaptation ===")

        # Preset: School / College Bus
        print("Applying Preset: School / College Bus...")
        page.click('.tc-preset-chip[data-category="school"]')
        page.wait_for_timeout(400)

        assert page.locator('#id_contract_category').input_value() == 'school'
        assert page.locator('#id_billing_model').input_value() == 'fixed_monthly'
        assert float(page.locator('#id_default_rate').input_value()) == 185000.00
        assert page.locator('#id_committed_vehicle_count').input_value() == '3'
        assert page.locator('#id_sla_penalty_cap_pct').input_value() == '5.00'
        assert 'Speed Governor' in page.locator('#tc-guidance-container').text_content()
        print("  ✅ Preset School / College Bus applied accurately across all fields.")

        # Preset: Factory 3-Shift
        print("Applying Preset: Factory 3-Shift...")
        page.click('.tc-preset-chip[data-category="factory"]')
        page.wait_for_timeout(400)

        assert page.locator('#id_contract_category').input_value() == 'factory'
        assert page.locator('#id_billing_model').input_value() == 'per_trip'
        assert float(page.locator('#id_default_rate').input_value()) == 2800.00
        assert page.locator('#id_committed_vehicle_count').input_value() == '6'
        assert page.locator('#id_standby_vehicle_count').input_value() == '2'
        assert page.locator('#id_fuel_escalation_enabled').is_checked() is True
        assert 'Rotatory Shifts' in page.locator('#tc-guidance-container').text_content()
        print("  ✅ Preset Factory 3-Shift applied accurately across all fields.")

        # Preset: Corporate ETS
        print("Applying Preset: Corporate ETS...")
        page.click('.tc-preset-chip[data-category="corporate"]')
        page.wait_for_timeout(400)
        assert page.locator('#id_contract_category').input_value() == 'corporate'
        assert page.locator('#id_billing_model').input_value() == 'per_trip'
        assert float(page.locator('#id_default_rate').input_value()) == 2400.00
        print("  ✅ Preset Corporate ETS applied accurately.")

        # === 5. Testing Term Duration Calculator ===
        print("\n=== 5. Testing Term Duration Calculator in Step 2 ===")
        tabs[1].click()
        page.wait_for_timeout(300)
        page.fill('#id_start_date', '2026-04-01')
        page.fill('#id_end_date', '2027-03-31')
        page.dispatch_event('#id_end_date', 'change')
        page.wait_for_timeout(300)

        term_badge = page.locator('#tc-term-indicator')
        assert term_badge.is_visible()
        print(f"  ✅ Term duration calculated: '{term_badge.text_content().strip()}'")

        step2_shot = os.path.join(artifact_dir, 'transport_contract_step2_term_calc.png')
        page.screenshot(path=step2_shot)
        print(f"Saved screenshot: {step2_shot}")

        # === 6. Testing Fleet Redundancy Gauge in Step 3 ===
        print("\n=== 6. Testing Fleet Redundancy Gauge in Step 3 ===")
        tabs[2].click()
        page.wait_for_timeout(300)
        page.fill('#id_committed_vehicle_count', '4')
        page.fill('#id_standby_vehicle_count', '1')
        page.dispatch_event('#id_standby_vehicle_count', 'input')
        page.wait_for_timeout(300)

        red_badge = page.locator('#tc-redundancy-indicator')
        assert red_badge.is_visible()
        print(f"  ✅ Redundancy badge calculated: '{red_badge.text_content().strip()}'")

        step3_shot = os.path.join(artifact_dir, 'transport_contract_step3_fleet_redundancy.png')
        page.screenshot(path=step3_shot)
        print(f"Saved screenshot: {step3_shot}")

        # === 7. Testing Commercial Estimator in Step 4 ===
        print("\n=== 7. Testing Commercial Estimator in Step 4 ===")
        tabs[3].click()
        page.wait_for_timeout(300)

        # Check rate label for per_trip
        rate_label = page.locator('label[for="id_default_rate"]').text_content()
        assert 'Rate per Trip' in rate_label, f"Expected 'Rate per Trip' in label, got '{rate_label}'"

        estimator_box = page.locator('#tc-commercial-estimator')
        assert estimator_box.is_visible(), "Commercial estimator box not visible in Step 4!"
        est_val = page.locator('#tc-est-val').text_content().strip()
        print(f"  ✅ Rate label adapted: '{rate_label.strip()}', Estimator Value: '{est_val}'")

        # Test changing to per_km
        page.select_option('#id_billing_model', 'per_km')
        page.dispatch_event('#id_billing_model', 'change')
        page.fill('#id_default_rate', '28.50')
        page.dispatch_event('#id_default_rate', 'input')
        page.wait_for_timeout(300)

        rate_label_km = page.locator('label[for="id_default_rate"]').text_content()
        assert 'Rate per KM' in rate_label_km, f"Expected 'Rate per KM' in label, got '{rate_label_km}'"
        est_val_km = page.locator('#tc-est-val').text_content().strip()
        print(f"  ✅ Changed to per_km: Label='{rate_label_km.strip()}', Estimator Value='{est_val_km}'")

        step4_shot = os.path.join(artifact_dir, 'transport_contract_step4_estimator.png')
        page.screenshot(path=step4_shot)
        print(f"Saved screenshot: {step4_shot}")

        # === 8. Testing Fuel Escalation Box in Step 5 ===
        print("\n=== 8. Testing Fuel Escalation Box in Step 5 ===")
        tabs[4].click()
        page.wait_for_timeout(300)

        fuel_box = page.locator('#tc-fuel-formula-box')
        assert fuel_box.is_visible(), "Fuel formula box not visible in Step 5!"
        print(f"  ✅ Fuel box active: '{fuel_box.text_content().strip()[:60]}...'")

        # Test disabling fuel escalation
        page.uncheck('#id_fuel_escalation_enabled')
        page.dispatch_event('#id_fuel_escalation_enabled', 'change')
        page.wait_for_timeout(300)
        assert 'Fixed Fuel Agreement' in fuel_box.text_content()
        print("  ✅ Fuel escalation uncheck displayed 'Fixed Fuel Agreement'.")

        # Re-check fuel escalation
        page.check('#id_fuel_escalation_enabled')
        page.dispatch_event('#id_fuel_escalation_enabled', 'change')
        page.wait_for_timeout(300)
        assert 'Active Fuel Price Adjustment Formula' in fuel_box.text_content()
        print("  ✅ Fuel escalation re-check restored interactive formula.")

        step5_shot = os.path.join(artifact_dir, 'transport_contract_step5_fuel_formula.png')
        page.screenshot(path=step5_shot)
        print(f"Saved screenshot: {step5_shot}")

        print("\nALL VERIFICATIONS PASSED WITH 100% SUCCESS!")
        browser.close()

if __name__ == '__main__':
    run_tests()
