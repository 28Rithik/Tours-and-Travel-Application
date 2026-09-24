import os
import sys
import json
import django

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.abspath('.'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
django.setup()

from django.test import Client
from playwright.sync_api import sync_playwright
from fleet_contracts.models import TransportContract

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

        print("\n=== 1. Testing Step 2 Vertical Panel on Add Form ===")
        page.goto('http://127.0.0.1:8000/admin/fleet_contracts/transportcontract/add/', wait_until='networkidle')
        page.wait_for_timeout(500)

        # Tab 1 is Step 2: Operational & Compliance Specifications
        tabs = page.locator('#jazzy-tabs .nav-link').all()
        step2_tab = tabs[1]
        print(f"Clicking Step 2 Tab: '{step2_tab.text_content().strip()}'...")
        step2_tab.click()
        page.wait_for_timeout(400)

        # By default corporate is selected
        panel = page.locator('#tc-adaptive-spec-panel')
        assert panel.is_visible(), "Adaptive panel not visible in Step 2!"
        assert 'Corporate ETS' in panel.text_content()
        print("✅ Default Corporate ETS vertical panel is visible in Step 2.")

        corp_shot = os.path.join(artifact_dir, 'transport_contract_corporate_panel.png')
        page.screenshot(path=corp_shot)
        print(f"Saved screenshot: {corp_shot}")

        # === 2. Testing Switching to School / College Bus ===
        print("\n=== 2. Testing Switching to School / College Bus ===")
        tabs[0].click() # Return to step 1
        page.wait_for_timeout(300)
        page.click('.tc-preset-chip[data-category="school"]')
        page.wait_for_timeout(400)

        step2_tab.click() # Go to step 2
        page.wait_for_timeout(400)
        panel = page.locator('#tc-adaptive-spec-panel')
        assert 'School & College Bus' in panel.text_content(), "School panel not rendered!"
        assert 'Speed Governor' in panel.text_content()
        print("✅ School & College Bus vertical panel rendered dynamically.")

        school_shot = os.path.join(artifact_dir, 'transport_contract_school_panel.png')
        page.screenshot(path=school_shot)
        print(f"Saved screenshot: {school_shot}")

        # === 3. Testing Switching to Factory Shift ===
        print("\n=== 3. Testing Switching to Factory Shift ===")
        tabs[0].click()
        page.wait_for_timeout(300)
        page.click('.tc-preset-chip[data-category="factory"]')
        page.wait_for_timeout(400)

        step2_tab.click()
        page.wait_for_timeout(400)
        panel = page.locator('#tc-adaptive-spec-panel')
        assert 'Factory Shift Logistics' in panel.text_content(), "Factory panel not rendered!"
        assert 'Gate Siren' in panel.text_content()
        print("✅ Factory Shift vertical panel rendered dynamically.")

        factory_shot = os.path.join(artifact_dir, 'transport_contract_factory_panel.png')
        page.screenshot(path=factory_shot)
        print(f"Saved screenshot: {factory_shot}")

        # === 4. Testing Two-Way Binding to JSONField ===
        print("\n=== 4. Testing Two-Way Data Binding to category_specifications JSON ===")
        # Edit the assembly line downtime penalty rate
        penalty_input = page.locator('input[data-spec-key="assembly_downtime_penalty_rate"]')
        penalty_input.fill('8500')
        penalty_input.dispatch_event('input')
        page.wait_for_timeout(300)

        raw_json = page.locator('#id_category_specifications').input_value()
        parsed = json.loads(raw_json)
        assert parsed.get('assembly_downtime_penalty_rate') == '8500', f"Expected 8500 in JSON, got {parsed.get('assembly_downtime_penalty_rate')}"
        print(f"✅ Input edit successfully serialized into JSONField: assembly_downtime_penalty_rate={parsed.get('assembly_downtime_penalty_rate')}")

        # === 5. Testing Existing Contract Edit & Pre-population ===
        print("\n=== 5. Testing Existing Contract Edit View ===")
        school_contract = TransportContract.objects.filter(contract_category='school').first()
        assert school_contract is not None
        edit_url = f"http://127.0.0.1:8000/admin/fleet_contracts/transportcontract/{school_contract.id}/change/"
        print(f"Navigating to School Contract #{school_contract.id} ({school_contract.name})...")
        page.goto(edit_url, wait_until='networkidle')
        page.wait_for_timeout(500)

        # Click Step 2
        tabs = page.locator('#jazzy-tabs .nav-link').all()
        tabs[1].click()
        page.wait_for_timeout(400)

        attendant_input = page.locator('input[data-spec-key="female_attendant_name"]')
        attendant_val = attendant_input.input_value()
        print(f"  ✅ Saved Female Attendant loaded from database: '{attendant_val}'")
        assert len(attendant_val) > 0, "Attendant name was not loaded from category_specifications!"

        # === 6. Testing Printable Service Agreement with Annexure B ===
        print("\n=== 6. Testing Printable Service Agreement Summary View ===")
        summary_url = f"http://127.0.0.1:8000/admin/fleet_contracts/transportcontract/{school_contract.id}/summary/"
        page.goto(summary_url, wait_until='networkidle')
        page.wait_for_timeout(500)

        content = page.content()
        assert "Institutional Student Safety" in content and "RTO Regulatory Charter" in content
        assert "RTO Speed Governor Certification" in content
        assert attendant_val in content
        print("✅ Printable Service Agreement successfully generated Annexure B tailored to School Bus RTO Charter!")

        agreement_shot = os.path.join(artifact_dir, 'transport_contract_printable_agreement.png')
        page.screenshot(path=agreement_shot)
        print(f"Saved screenshot: {agreement_shot}")

        print("\nALL ADAPTIVE VERTICAL CONTRACT TESTS COMPLETED WITH 100% SUCCESS!")
        browser.close()

if __name__ == '__main__':
    run_tests()
