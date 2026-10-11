import os
from playwright.sync_api import sync_playwright

OUTPUT_DIR = r"C:\Users\rithi\.gemini\antigravity-ide\brain\38a90fa8-4427-4e87-a010-66c145b9a064"

def test_otp():
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900}, color_scheme="light")
        page = context.new_page()

        print("Testing WhatsApp OTP flow on /client/login/ ...")
        page.goto("http://127.0.0.1:8000/client/login/", wait_until="networkidle")

        # Click WhatsApp / SMS OTP tab
        otp_tab = page.locator("button:has-text('WhatsApp / SMS OTP')")
        otp_tab.click()
        page.wait_for_timeout(400)

        # Fill phone
        phone_input = page.locator("input[name='phone']")
        phone_input.fill("9840112345")
        page.screenshot(path=os.path.join(OUTPUT_DIR, "10_otp_tab_input.png"))
        print("   -> Screenshot saved: 10_otp_tab_input.png")

        # Click Send Code
        send_btn = page.locator("button:has-text('Send Code via WhatsApp & SMS')")
        send_btn.click()
        page.wait_for_load_state("networkidle")
        page.screenshot(path=os.path.join(OUTPUT_DIR, "11_otp_code_dispatched.png"))
        print("   -> Screenshot saved: 11_otp_code_dispatched.png")

        # Click Auto-Fill button
        autofill_btn = page.locator("button:has-text('Auto-Fill')")
        if autofill_btn.count() > 0:
            autofill_btn.click()
            page.wait_for_timeout(300)

        # Click Verify & Sign In
        verify_btn = page.locator("button:has-text('Verify & Open Commute Desk')")
        verify_btn.click()
        page.wait_for_load_state("networkidle")
        print("   -> Landed URL after OTP:", page.url)
        page.screenshot(path=os.path.join(OUTPUT_DIR, "12_otp_authenticated_portal.png"))
        print("   -> Screenshot saved: 12_otp_authenticated_portal.png")

        browser.close()
        print("WhatsApp OTP flow completed successfully!")

if __name__ == "__main__":
    test_otp()
