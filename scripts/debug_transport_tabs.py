import os
import sys
import django

sys.path.insert(0, os.path.abspath('.'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
django.setup()

from django.test import Client
from playwright.sync_api import sync_playwright

def test_tabs():
    c = Client()
    c.login(username='rithik', password='rithik123')
    session_cookie = c.cookies['sessionid'].value

    with sync_playwright() as p:
        browser = p.chromium.launch(channel='msedge', headless=True)
        context = browser.new_context(viewport={'width': 1400, 'height': 900})
        context.add_cookies([{'name': 'sessionid', 'value': session_cookie, 'domain': '127.0.0.1', 'path': '/'}])
        page = context.new_page()

        console_logs = []
        page.on('console', lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))
        page.on('pageerror', lambda err: console_logs.append(f"[PAGE ERROR] {err}"))

        page.goto('http://127.0.0.1:8000/admin/fleet_contracts/transportcontract/add/', wait_until='networkidle')

        tab_links = page.locator('#jazzy-tabs .nav-link').all()
        print(f"Found {len(tab_links)} tab links", flush=True)
        for i, t in enumerate(tab_links):
            print(f"  Tab {i}: text='{t.text_content().strip()}', href='{t.get_attribute('href')}'")

        # Now test clicking tab 1 (Step 2)
        href_tab2 = tab_links[1].get_attribute('href')
        pane1 = page.locator(tab_links[0].get_attribute('href'))
        pane2 = page.locator(href_tab2)
        print(f"Before click - Pane 1 visible: {pane1.is_visible()}, Pane 2 visible: {pane2.is_visible()}", flush=True)

        print(f"Clicking Tab 2 ({href_tab2})...", flush=True)
        tab_links[1].click()
        page.wait_for_timeout(600)

        print(f"After click - Pane 1 visible: {pane1.is_visible()}, Pane 2 visible: {pane2.is_visible()}", flush=True)

        # Now test clicking Tab 3
        href_tab3 = tab_links[2].get_attribute('href')
        pane3 = page.locator(href_tab3)
        print(f"Clicking Tab 3 ({href_tab3})...", flush=True)
        tab_links[2].click()
        page.wait_for_timeout(600)
        print(f"After click Tab 3 - Pane 2 visible: {pane2.is_visible()}, Pane 3 visible: {pane3.is_visible()}", flush=True)

        browser.close()

if __name__ == '__main__':
    test_tabs()
