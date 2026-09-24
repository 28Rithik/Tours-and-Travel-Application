import os
import sys
import re
import django

# Setup Django
sys.path.append('c:/Users/rithi/Documents/Documents Project Intership and Course/Projects/Rag chatbot/Travels Trip Managment Application')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
django.setup()

from packages.models import Package, ItineraryDay, PackageVehicleTariff, TempleDarshanSlot
from django.test import Client

sys.stdout.reconfigure(encoding='utf-8')

print("="*85)
print("VERIFICATION OF CHENNAI TOURS & TRAVELS (SGT-CTT) INGESTION & QUALITY AUDIT")
print("="*85)

# 1. Check counts
ctt_packages = Package.objects.filter(package_code__startswith='SGT-CTT-').order_by('package_code')
pkg_count = ctt_packages.count()
itin_count = ItineraryDay.objects.filter(package__package_code__startswith='SGT-CTT-').count()
tariff_count = PackageVehicleTariff.objects.filter(package__package_code__startswith='SGT-CTT-').count()
darshan_count = TempleDarshanSlot.objects.filter(package__package_code__startswith='SGT-CTT-').count()

print(f"Total SGT-CTT Packages:         {pkg_count}")
print(f"Total SGT-CTT Itinerary Days:   {itin_count}")
print(f"Total SGT-CTT Vehicle Tariffs:  {tariff_count}")
print(f"Total SGT-CTT Darshan Slots:    {darshan_count}")

assert pkg_count == 62, f"Expected 62 packages, found {pkg_count}"
assert itin_count == 176, f"Expected 176 itinerary days, found {itin_count}"
assert tariff_count == 310, f"Expected 310 tariffs, found {tariff_count}"
assert darshan_count == 38, f"Expected 38 darshan slots, found {darshan_count}"

print("\n[PASSED] Counts perfectly verified!")

# 2. Competitor Brand Leak Audit
print("\n--- AUDITING FOR COMPETITOR BRAND LEAKS ---")
forbidden_patterns = [
    r'chennaitourstravels',
    r'chennai tours\s*(?:and|&)?\s*travels',
    r'travel\s*ahead',
    r'adobe\s*flash',
    r'flash\s*player',
    r'index11\.php',
    r'book_tour\.php'
]

leaks_found = []

for pkg in ctt_packages:
    corpus = f"{pkg.name} {pkg.destination} {pkg.description} {pkg.inclusions} {pkg.exclusions} {pkg.terms_and_conditions} {pkg.contact_persons_footer}"
    for itin in pkg.itinerary_days.all():
        corpus += f" {itin.title} {itin.route_segment} {itin.activities} {itin.morning_activity} {itin.sightseeing_spots} {itin.evening_night_activity}"
    for slot in pkg.temple_slots.all():
        corpus += f" {slot.temple_name} {slot.deity_or_circuit} {slot.dress_code_notes} {slot.prasad_details}"
    
    for pat in forbidden_patterns:
        m = re.search(pat, corpus, re.I)
        if m:
            leaks_found.append((pkg.package_code, pat, m.group(0)))

if leaks_found:
    print(f"[FAILED] Found {len(leaks_found)} brand leaks:")
    for code, pat, match in leaks_found:
        print(f"  - {code}: matched '{pat}' -> '{match}'")
else:
    print("[PASSED] 100% Zero Competitor Brand Leaks Found across all 62 packages, 176 days, 310 tariffs, and 38 darshan slots!")

# 3. Test Quotation Proposal View
print("\n--- TESTING LIVE QUOTATION PROPOSAL VIEWS ---")
from django.contrib.auth.models import User
client = Client()
user = User.objects.filter(is_superuser=True).first() or User.objects.filter(is_staff=True).first()
if not user:
    user = User.objects.create_user('testaudituser', 'audit@test.com', 'testpass123')
client.force_login(user)

sample_codes = ['SGT-CTT-001', 'SGT-CTT-009', 'SGT-CTT-028', 'SGT-CTT-055', 'SGT-CTT-058']

for code in sample_codes:
    pkg = Package.objects.get(package_code=code)
    url = f"/packages/quote/{pkg.id}/"
    resp = client.get(url)
    print(f"Testing Quote URL: {url} ({pkg.package_code} - {pkg.name[:45]}...)")
    print(f"  Status Code: {resp.status_code}")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    content = resp.content.decode('utf-8', errors='ignore')
    has_company = "Siva Gayathri" in content or "SIVA GAYATHRI" in content
    has_contact = "98425" in content or "94381" in content
    has_tariffs = "Tariff" in content or "Rate" in content or "₹" in content
    print(f"  Contains Company Branding: {has_company}")
    print(f"  Contains Helpline Contact:  {has_contact}")
    print(f"  Contains Vehicle Tariffs:   {has_tariffs}")
    assert has_company, "Missing Siva Gayathri company branding in quote view"

print("\n[PASSED] All sample quotation proposals render perfectly with HTTP 200!")

# 4. Master Inventory by Prefix Across Whole Platform
print("\n" + "="*85)
print("PLATFORM-WIDE MASTER TOUR INVENTORY SUMMARY (ALL DATA SOURCES)")
print("="*85)

sources = [
    ('SGT-HOL-', 'Holidify Tourism Circuits (Pan-India & International)'),
    ('SGT-TRW-', 'Trawell.in Multi-Destination Itineraries'),
    ('SGT-CT-',  'Chennai Travels (Pilgrimage & Hill Stations)'),
    ('SGT-SM-',  'Sri Murugan Travels (South Special Tours)'),
    ('SGT-PRB-', 'Prabu Tours & Travels (Coimbatore Excursions)'),
    ('SGT-BHA-', 'Bharathiyar Travels (South Temple Circuits)'),
    ('SGT-HHH-', 'Hip Hop Holidays (Holiday & IV Packages)'),
    ('SGT-CTT-', 'Chennai Tours & Travels (Ex-Chennai & Temple Circuits)'),
]

grand_total = 0
for prefix, label in sources:
    cnt = Package.objects.filter(package_code__startswith=prefix).count()
    grand_total += cnt
    print(f"  {prefix:9} | {cnt:5} packages | {label}")

other_cnt = Package.objects.exclude(
    package_code__regex=r'^(' + '|'.join([p[0] for p in sources]) + ')'
).count()
grand_total += other_cnt
if other_cnt > 0:
    print(f"  {'OTHER':9} | {other_cnt:5} packages | Core / Custom Bespoke Packages")

print("-" * 85)
print(f"  TOTAL     | {grand_total:5} packages | ENTIRE SIVA GAYATHRI PLATFORM REPOSITORY")
print("="*85)
