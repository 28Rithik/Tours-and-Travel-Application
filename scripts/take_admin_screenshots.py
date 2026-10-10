import os
from playwright.sync_api import sync_playwright

artifact_dir = r"C:\Users\rithi\.gemini\antigravity-ide\brain\3c044726-a75e-47a0-949a-d96c5805a71d"

with sync_playwright() as p:
    browser = p.chromium.launch(channel='chrome', headless=True)
    page = browser.new_page(viewport={"width": 1400, "height": 900})
    
    # Login
    page.goto('http://127.0.0.1:8000/admin/login/')
    page.fill('input[name="username"]', 'admin')
    page.fill('input[name="password"]', 'admin123')
    page.click('button[type="submit"]')
    page.wait_for_load_state('networkidle')
    print('Current URL after login:', page.url)
    
    pages = [
        ('pw_admin_index.png', 'http://127.0.0.1:8000/admin/'),
        ('pw_inquiry_list.png', 'http://127.0.0.1:8000/admin/crm/inquiry/'),
        ('pw_service_vouchers.png', 'http://127.0.0.1:8000/admin/crm/supplierservicevoucher/'),
        ('pw_quotations.png', 'http://127.0.0.1:8000/admin/crm/quotation/'),
        ('pw_dmcinvoice.png', 'http://127.0.0.1:8000/admin/crm/dmcinvoice/'),
        ('pw_hotelmaster.png', 'http://127.0.0.1:8000/admin/crm/hotelmaster/'),
        ('pw_inquiry_form.png', 'http://127.0.0.1:8000/admin/crm/inquiry/135/change/'),
    ]
    
    for filename, url in pages:
        try:
            page.goto(url)
            page.wait_for_load_state('networkidle')
            page.screenshot(path=os.path.join(artifact_dir, filename))
            print(f"Saved {filename}")
        except Exception as e:
            print(f"Error for {url}: {e}")
            
    browser.close()
print("All screenshots taken successfully!")
