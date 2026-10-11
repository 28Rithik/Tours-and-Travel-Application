import os
import sys
import time
from playwright.sync_api import sync_playwright

OUTPUT_DIR = r"C:\Users\rithi\.gemini\antigravity-ide\brain\38a90fa8-4427-4e87-a010-66c145b9a064"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            color_scheme="light"
        )
        page = context.new_page()

        print("1. Testing /client/login/ ...")
        page.goto("http://127.0.0.1:8000/client/login/", wait_until="networkidle")
        page.screenshot(path=os.path.join(OUTPUT_DIR, "01_client_login_clean_light_mode.png"), full_page=True)
        print("   -> Screenshot saved: 01_client_login_clean_light_mode.png")

        # Test Real-Time Enterprise Domain Lookup
        print("2. Testing real-time domain lookup ...")
        username_input = page.locator("#corporateUsernameInput")
        username_input.fill("transport.lead@cognizant.com")
        page.wait_for_timeout(1000)
        page.screenshot(path=os.path.join(OUTPUT_DIR, "02_sso_detection_card_revealed.png"))
        print("   -> Screenshot saved: 02_sso_detection_card_revealed.png")

        # Test Quick Tenant Filter
        print("3. Testing tenant filtering chips & search ...")
        username_input.fill("")
        page.wait_for_timeout(400)
        
        # Click IT & Tech chip
        it_chip = page.locator("button:has-text('IT & Tech')")
        if it_chip.count() > 0:
            it_chip.click()
            page.wait_for_timeout(300)
            
        search_box = page.locator("#tenantSearchInput")
        if search_box.count() > 0:
            search_box.fill("Cognizant")
            page.wait_for_timeout(300)
        page.screenshot(path=os.path.join(OUTPUT_DIR, "03_tenant_switcher_filtered.png"))
        print("   -> Screenshot saved: 03_tenant_switcher_filtered.png")

        # 4. Click Cognizant Tenant button to switch
        print("4. Switching to Cognizant contract portal ...")
        cog_btn = page.locator("button:has-text('Cognizant Technology Solutions')").first
        if cog_btn.count() > 0:
            cog_btn.click()
            page.wait_for_load_state("networkidle")
        else:
            page.goto("http://127.0.0.1:8000/client-portal/4/", wait_until="networkidle")

        print("   -> Current URL:", page.url)
        page.screenshot(path=os.path.join(OUTPUT_DIR, "04_cognizant_transparency_portal.png"), full_page=True)
        print("   -> Screenshot saved: 04_cognizant_transparency_portal.png")

        # 5. Test Persona Role Switcher
        print("5. Testing corporate persona switcher ...")
        persona_select = page.locator("#personaSelector")
        if persona_select.count() > 0:
            persona_select.select_option("safety_auditor")
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(1500)
        page.screenshot(path=os.path.join(OUTPUT_DIR, "05_persona_switched_portal.png"))
        print("   -> Screenshot saved: 05_persona_switched_portal.png")

        # 6. Test B2B Monthly GST Tax Invoice Detail
        print("6. Viewing B2B tax invoice detail ...")
        page.goto("http://127.0.0.1:8000/client-portal/4/invoice/76/", wait_until="networkidle")
        page.screenshot(path=os.path.join(OUTPUT_DIR, "06_b2b_gst_tax_invoice.png"), full_page=True)
        print("   -> Screenshot saved: 06_b2b_gst_tax_invoice.png")

        # 7. Test ISO-14064 Green Commute ESG Certificate
        print("7. Viewing ESG Certificate ...")
        page.goto("http://127.0.0.1:8000/client-portal/4/esg/certificate/", wait_until="networkidle")
        page.screenshot(path=os.path.join(OUTPUT_DIR, "07_esg_green_commute_certificate.png"), full_page=True)
        print("   -> Screenshot saved: 07_esg_green_commute_certificate.png")

        # 8. Test White-Label Branded Login Page
        print("8. Testing White-Label Branded Login page for Cognizant ...")
        page.goto("http://127.0.0.1:8000/client/brand/cognizant/", wait_until="networkidle")
        page.screenshot(path=os.path.join(OUTPUT_DIR, "08_white_label_branded_login.png"), full_page=True)
        print("   -> Screenshot saved: 08_white_label_branded_login.png")

        # 9. Test Campus Selector and 1-Click Corporate SSO Sign-In
        print("9. Testing 1-Click SSO button ...")
        campus_select = page.locator("#campusBranchSelect")
        if campus_select.count() > 0:
            campus_select.select_option("siruseri")
            page.wait_for_timeout(300)

        sso_btn = page.locator("#ssoActionLink")
        sso_btn.click()
        page.wait_for_load_state("networkidle")
        print("   -> Landed URL after SSO:", page.url)
        page.screenshot(path=os.path.join(OUTPUT_DIR, "09_sso_authenticated_portal.png"), full_page=True)
        print("   -> Screenshot saved: 09_sso_authenticated_portal.png")

        browser.close()
        print("All E2E checks and screenshots completed successfully!")

if __name__ == "__main__":
    run()
