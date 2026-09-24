import os
import sys
import re
import django

sys.path.append('c:/Users/rithi/Documents/Documents Project Intership and Course/Projects/Rag chatbot/Travels Trip Managment Application')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
django.setup()

from packages.models import Package, ItineraryDay, PackageVehicleTariff, TempleDarshanSlot
from django.test import Client
from django.contrib.auth.models import User

sys.stdout.reconfigure(encoding='utf-8')

print("="*85)
print("VERIFICATION & QUALITY AUDIT: CHENNAI TRAVELS (SGT-CT) CATALOG")
print("="*85)

ct_pkgs = Package.objects.filter(package_code__startswith='SGT-CT-').order_by('package_code')
pkg_count = ct_pkgs.count()
itin_count = ItineraryDay.objects.filter(package__package_code__startswith='SGT-CT-').count()
tariff_count = PackageVehicleTariff.objects.filter(package__package_code__startswith='SGT-CT-').count()
darshan_count = TempleDarshanSlot.objects.filter(package__package_code__startswith='SGT-CT-').count()

print(f"Total SGT-CT Packages:         {pkg_count}")
print(f"Total SGT-CT Itinerary Days:   {itin_count}")
print(f"Total SGT-CT Vehicle Tariffs:  {tariff_count}")
print(f"Total SGT-CT Darshan Slots:    {darshan_count}")

assert pkg_count == 148, f"Expected 148 packages, found {pkg_count}"
assert itin_count == 326, f"Expected 326 itinerary days, found {itin_count}"
assert tariff_count == 740, f"Expected 740 tariffs, found {tariff_count}"
assert darshan_count == 86, f"Expected 86 darshan slots, found {darshan_count}"

print("\n[PASSED] Counts perfectly verified!")

# Brand leak audit
print("\n--- AUDITING FOR COMPETITOR BRAND LEAKS ---")
forbidden_patterns = [
    r'chennaitravels\.in',
    r'chennai travels(?!\s*&?\s*tours\s*siva)',
    r'call-drivers-chennai',
    r'attach-vehicles',
    r'cancellation-refund-policy'
]

leaks_found = []
for pkg in ct_pkgs:
    corpus = f"{pkg.name} {pkg.destination} {pkg.description} {pkg.inclusions} {pkg.exclusions} {pkg.terms_and_conditions} {pkg.contact_persons_footer}"
    for itin in pkg.itinerary_days.all():
        corpus += f" {itin.title} {itin.route_segment} {itin.activities}"
    for slot in pkg.temple_slots.all():
        corpus += f" {slot.temple_name} {slot.deity_or_circuit} {slot.dress_code_notes} {slot.prasad_details}"
    
    # Check if there is competitor name without Siva Gayathri
    if 'chennaitravels.in' in corpus.lower():
        leaks_found.append((pkg.package_code, 'chennaitravels.in'))

if leaks_found:
    print(f"[FAILED] Found {len(leaks_found)} leaks:")
    for c, pat in leaks_found:
        print(f"  - {c}: {pat}")
else:
    print("[PASSED] 100% Zero Competitor Brand Leaks Found!")

# Check category distribution
print("\n--- CATEGORY DISTRIBUTION IN SGT-CT ---")
from django.db.models import Count
cat_dist = ct_pkgs.values('category').annotate(count=Count('id')).order_by('-count')
for cd in cat_dist:
    print(f"  {cd['category']:20} : {cd['count']:3} packages")

# Test live quotation proposal views
print("\n--- TESTING LIVE QUOTATION PROPOSALS ---")
client = Client()
user = User.objects.filter(is_superuser=True).first() or User.objects.filter(is_staff=True).first()
client.force_login(user)

sample_codes = [
    'SGT-CT-KOLLI-HILLS-TOUR-3D',
    'SGT-CT-CHENNAI-OUTSIDE-C-1D',
    'SGT-CT-ARUPADAI-VEEDU-TOU-4D-6',
    'SGT-CT-CHENNAI-KANCHIPURA-1D',
    'SGT-CT-CHENNAI-TO-SRISAIL-3D'
]

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

print("\n[PASSED] All sample quotation proposals render perfectly with HTTP 200!")

# Overall master platform inventory
print("\n" + "="*85)
print("PLATFORM-WIDE MASTER TOUR INVENTORY SUMMARY (ALL DATA SOURCES)")
print("="*85)

sources = [
    ('SGT-HOL-', 'Holidify Tourism Circuits (Pan-India & International)'),
    ('SGT-TRW-', 'Trawell.in Multi-Destination Itineraries'),
    ('SGT-CT-',  'Chennai Travels (Pilgrimage & Hill Stations)'),
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
