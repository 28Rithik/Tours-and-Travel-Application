import os
from playwright.sync_api import sync_playwright

artifact_dir = r"C:\Users\rithi\.gemini\antigravity-ide\brain\3c044726-a75e-47a0-949a-d96c5805a71d"

with sync_playwright() as p:
    browser = p.chromium.launch(channel='chrome', headless=True)
    page = browser.new_page(viewport={'width': 1400, 'height': 900})
    page.goto('http://127.0.0.1:8000/admin/login/')
    page.fill('input[name="username"]', 'admin')
    page.fill('input[name="password"]', 'admin123')
    page.click('button[type="submit"]')
    page.wait_for_load_state('networkidle')
    print('Logged in, current url:', page.url)

    pages = [
        ('pw_vehicles.png', 'http://127.0.0.1:8000/admin/core/vehicle/'),
        ('pw_transport_contracts.png', 'http://127.0.0.1:8000/admin/fleet_contracts/transportcontract/'),
        ('pw_operations_booking.png', 'http://127.0.0.1:8000/admin/operations/booking/'),
        ('pw_operations_trip.png', 'http://127.0.0.1:8000/admin/operations/trip/'),
        ('pw_packages.png', 'http://127.0.0.1:8000/admin/packages/package/'),
        ('pw_package_tours.png', 'http://127.0.0.1:8000/admin/package_tours/collegeivproxy/'),
        ('pw_journal_entries.png', 'http://127.0.0.1:8000/admin/finance/journalentry/'),
        ('pw_maintenance.png', 'http://127.0.0.1:8000/admin/maintenance/servicerecord/'),
    ]

    for filename, url in pages:
        try:
            page.goto(url)
            page.wait_for_load_state('networkidle')
            page.screenshot(path=os.path.join(artifact_dir, filename))
            print(f'Captured {filename}')
        except Exception as e:
            print(f'Error for {url}: {e}')

    browser.close()
print('All remaining screenshots captured!')
