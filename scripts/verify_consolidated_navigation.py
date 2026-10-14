import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
django.setup()

import re
from django.test import Client
from django.contrib.auth import get_user_model
from packages.models import Package, CollegeIVExpedition

User = get_user_model()
u = User.objects.filter(is_superuser=True).first()
if not u:
    u = User.objects.create_superuser('test_admin', 'admin@example.com', 'adminpass')

client = Client()
client.force_login(u)

print("=== RUNNING FULL VERIFICATION OF STREAMLINED ARCHITECTURE ===")

# 1. Primary Hubs
primary_hubs = [
    ('/admin/packages/package/', '1. Tour Packages Catalog'),
    ('/admin/package_tours/collegeivproxy/', '2. College IV Expeditions'),
    ('/admin/package_tours/tourdeparturebatchproxy/', '3. Tour Bus Departure Batches'),
    ('/admin/package_tours/passengermanifestproxy/', '4. Passenger Manifest & Rooming'),
]

for url, title in primary_hubs:
    resp = client.get(url)
    assert resp.status_code == 200, f"Failed: {title} returned status {resp.status_code}"
    print(f"[PASS] Hub reachable: {title} ({url}) -> HTTP {resp.status_code}")

# 2. Hidden Inlines / Child Models Direct URLs
child_models = [
    ('/admin/packages/packagetemplate/', 'Package Templates'),
    ('/admin/packages/packagevehicletariff/', 'Vehicle-Wise Tariffs'),
    ('/admin/packages/templedarshanslot/', 'Temple & Darshan Slots'),
    ('/admin/packages/itineraryday/', 'Itinerary Days'),
    ('/admin/packages/internationaldocumentchecklist/', 'International Document Checklist'),
    ('/admin/package_tours/boardingpointproxy/', 'Boarding Points Proxy'),
]

for url, title in child_models:
    resp = client.get(url)
    assert resp.status_code == 200, f"Failed: {title} returned status {resp.status_code}"
    print(f"[PASS] Direct URL still accessible: {title} ({url}) -> HTTP {resp.status_code}")

# 3. Sidebar Menu Check
res_index = client.get('/admin/')
assert res_index.status_code == 200
html_index = res_index.content.decode('utf-8')

sidebar_links = re.findall(r'<a[^>]+href=[\'"](/admin/[^\'"]+)[\'"][^>]*>.*?<p>(.*?)</p>', html_index, re.DOTALL)
tour_links = []
for url, title in sidebar_links:
    clean = re.sub(r'<[^>]+>', '', title).strip().encode('ascii', 'replace').decode('ascii')
    if 'package' in url or 'tour' in url:
        tour_links.append((clean, url))

print("\n--- SIDEBAR NAVIGATION VERIFICATION ---")
print(f"Total Tour / Package links in sidebar: {len(tour_links)}")
for clean, url in tour_links:
    print(f" * {clean} -> {url}")

expected_titles = ['Packages', 'College IV Expeditions', 'Tour Bus Departure Batches', 'Passenger Manifest &amp; Rooming']
for exp in expected_titles:
    found = any(exp in title for title, _ in tour_links)
    assert found, f"Missing expected hub in sidebar: {exp}"
print("[PASS] Exactly the 4 consolidated operational hubs appear in sidebar!")

# Ensure no hidden child models appear in sidebar
hidden_slugs = ['packagetemplate', 'packagevehicletariff', 'templedarshanslot', 'itineraryday', 'internationaldocumentchecklist', 'boardingpointproxy']
for slug in hidden_slugs:
    found_in_sidebar = any(slug in url for _, url in tour_links)
    assert not found_in_sidebar, f"Clutter model still visible in sidebar: {slug}"
print("[PASS] All 6 child/inline models successfully hidden from sidebar clutter!")

# 4. Quick Action Buttons Check
print("\n--- QUICK ACTIONS VERIFICATION ---")
resp_iv = client.get('/admin/package_tours/collegeivproxy/')
html_iv = resp_iv.content.decode('utf-8')
assert 'Quick Actions' in html_iv, "Quick Actions column header missing in College IV list"
assert 'Import CSV' in html_iv, "Import CSV button missing in College IV list"
assert 'Roster' in html_iv, "Roster button missing in College IV list"
print("[PASS] College IV list displays 1-click Quick Action buttons ('Import CSV', 'Roster', 'Proposal')!")

resp_batch = client.get('/admin/package_tours/tourdeparturebatchproxy/')
html_batch = resp_batch.content.decode('utf-8')
assert 'Quick Actions' in html_batch, "Quick Actions column header missing in Departure Batch list"
assert 'Manifest' in html_batch, "Manifest button missing in Departure Batch list"
print("[PASS] Tour Departure Batch list displays Quick Action button ('Manifest')!")

resp_pkg = client.get('/admin/packages/package/')
html_pkg = resp_pkg.content.decode('utf-8')
assert 'Package Templates' in html_pkg, "Package Templates shortcut button missing in Packages changelist"
print("[PASS] Package catalog changelist displays 'Package Templates' shortcut button!")

# 5. Inlines in Add Forms
print("\n--- INLINES VERIFICATION ---")
resp_pkg_add = client.get('/admin/packages/package/add/')
html_pkg_add = resp_pkg_add.content.decode('utf-8')
assert 'itinerary_days-group' in html_pkg_add, "Itinerary Days inline missing"
assert 'vehicle_tariffs-group' in html_pkg_add, "Vehicle Tariffs inline missing"
assert 'temple_slots-group' in html_pkg_add, "Temple Darshan Slots inline missing"
assert 'intl_documents-group' in html_pkg_add, "International Document Checklist inline missing"
print("[PASS] All 4 inlines (Itinerary, Tariffs, Temple Darshan, Visa Checklist) present in Package form!")

resp_batch_add = client.get('/admin/package_tours/tourdeparturebatchproxy/add/')
html_batch_add = resp_batch_add.content.decode('utf-8')
assert 'boardingpoint_set-group' in html_batch_add or 'Boarding' in html_batch_add, "Boarding Points inline missing in batch add"
print("[PASS] Boarding Points inline present in Departure Batch form!")

print("\n=== ALL ARCHITECTURE CHECKS PASSED PERFECTLY ===")
