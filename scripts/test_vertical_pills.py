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

    print("Navigating to Transport Contracts Change List...")
    page.goto('http://127.0.0.1:8000/admin/fleet_contracts/transportcontract/', wait_until='networkidle')

    shot_path = os.path.join(artifact_dir, 'transport_contracts_vertical_pills.png')
    page.screenshot(path=shot_path)
    print("Saved screenshot to:", shot_path)

    # Click Corporate ETS filter
    page.locator('a[href*="contract_category=corporate"]').first.click()
    page.wait_for_timeout(500)
    print("Filtered URL:", page.url)
    assert 'contract_category=corporate' in page.url

    # Check rows filtered
    rows = page.locator('#result_list tbody tr').count()
    print(f"✅ Filtered to Corporate ETS: {rows} contracts displayed.")
    browser.close()
