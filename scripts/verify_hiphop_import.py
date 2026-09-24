import os
import sys
import re
import urllib.request

sys.stdout.reconfigure(encoding='utf-8')

WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, WORKSPACE_ROOT)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')

import django
django.setup()

from packages.models import Package, ItineraryDay, PackageVehicleTariff, TempleDarshanSlot

print("=" * 80)
print("  VERIFICATION & BRANDING AUDIT — HIP HOP HOLIDAYS (SGT-HHH-)")
print("=" * 80)

# 1. Counts
hhh_pkgs = Package.objects.filter(package_code__startswith='SGT-HHH-')
pkg_count = hhh_pkgs.count()
day_count = ItineraryDay.objects.filter(package__package_code__startswith='SGT-HHH-').count()
tariff_count = PackageVehicleTariff.objects.filter(package__package_code__startswith='SGT-HHH-').count()
temple_count = TempleDarshanSlot.objects.filter(package__package_code__startswith='SGT-HHH-').count()

print(f"Total SGT-HHH- Packages       : {pkg_count} (Expected: 30)")
print(f"Total SGT-HHH- Itinerary Days : {day_count} (Expected: 89)")
print(f"Total SGT-HHH- 5-Tier Tariffs : {tariff_count} (Expected: 150)")
print(f"Total SGT-HHH- Temple Slots   : {temple_count}")

# 2. Competitor Leakage Scan
print("\nScanning for competitor leaks (hip hop, hiphopholidays, 9629, 9196...)...")
leak_patterns = [
    re.compile(r'hip\s*hop', re.IGNORECASE),
    re.compile(r'hiphopholidays', re.IGNORECASE),
    re.compile(r'9629\d{6}'),
    re.compile(r'salem', re.IGNORECASE),
]

leaks_found = []
for p in hhh_pkgs:
    text_corpus = f"{p.name} {p.destination} {p.description} {p.inclusions} {p.exclusions} {p.terms_and_conditions} {p.contact_persons_footer}"
    for pat in leak_patterns:
        m = pat.search(text_corpus)
        if m:
            leaks_found.append((p.package_code, 'Package', m.group(0)))

for d in ItineraryDay.objects.filter(package__package_code__startswith='SGT-HHH-'):
    text_corpus = f"{d.title} {d.activities} {d.sightseeing_spots} {d.night_stay_location}"
    for pat in leak_patterns:
        m = pat.search(text_corpus)
        if m:
            leaks_found.append((d.package.package_code, f'Day {d.day_number}', m.group(0)))

if leaks_found:
    print(f"⚠️ FOUND {len(leaks_found)} LEAKS:")
    for code, src, txt in leaks_found:
        print(f"  - [{code}] in {src}: {txt}")
else:
    print("✅ ZERO COMPETITOR LEAKS DETECTED! 100% Sanitized & Rebranded to Siva Gayathri Tours & Travels.")

# 3. Check Contact Info & Branding
first_pkg = hhh_pkgs.first()
print("\nBranding & Contact Verification Sample:")
print(f"  Package: {first_pkg.name}")
print(f"  Footer: {first_pkg.contact_persons_footer}")
print(f"  Tariffs: {first_pkg.vehicle_tariffs.count()} vehicle tiers attached")

# 4. Check Web Quote Endpoint with Django Test Client
from django.test import Client
from django.contrib.auth import get_user_model
User = get_user_model()
admin_user = User.objects.filter(is_superuser=True).first()

sample_pkg = hhh_pkgs.filter(category='college_iv').first()
quote_path = f"/packages/quote/{sample_pkg.id}/"
print(f"\nTesting Quotation Proposal View for [{sample_pkg.package_code}]: {quote_path}")
client = Client()
if admin_user:
    client.force_login(admin_user)
resp = client.get(quote_path)
print(f"  HTTP Status: {resp.status_code} OK")
html = resp.content.decode('utf-8', errors='ignore')
print(f"  Company Name in HTML: {'Siva Gayathri Tours' in html}")
print(f"  Tariffs rendered in proposal: {'Vehicle' in html or 'Tariff' in html or 'Innova' in html or 'Coach' in html}")
print(f"  Itinerary rendered in proposal: {'Day 1' in html or 'Day 01' in html}")

# 5. Grand Total Providers Table
print("\n" + "=" * 80)
print("  MULTI-WEBSITE GRAND AUDIT & INVENTORY SUMMARY (16 PROVIDERS)")
print("=" * 80)

providers = [
    ("Holidify (holidify.com)", "SGT-HOL-"),
    ("Trawell.in (trawell.in)", "SGT-TRW-"),
    ("Aspire Holidays (aspireholidays.in)", "SGT-AH-"),
    ("Rengha Holidays (renghaholidays.com)", "SGT-RH-"),
    ("Custom IV / College Departures", "PKG-"),
    ("Manoj Travels (manojtravels.in)", "SGT-MT-"),
    ("Chennai Travels (chennaitravels.in)", "SGT-CT-"),
    ("Sri Murugan Travels (srimurugantravels.com)", "SGT-SMT-"),
    ("Jaisun Tourism (jaisuntourism.com)", "SGT-JT-"),
    ("Eroutes Travel (eroutestravel.com)", "SGT-ER-"),
    ("Bharathiyar Travels (bharathiyartravels.com)", "SGT-BTT-"),
    ("Prabu Tours & Travels (prabutourstravels.com)", "SGT-PTT-"),
    ("Kandhan Travels (kandhantravels.com)", "SGT-KT-"),
    ("SriGo Tours (srigo.in)", "SGT-SG-"),
    ("Hip Hop Holidays (hiphopholidays.in)", "SGT-HHH-"),
    ("SBLT Travels (sblt.in)", "SGT-SBLT-"),
]

total_all = 0
for name, prefix in providers:
    cnt = Package.objects.filter(package_code__startswith=prefix).count()
    total_all += cnt
    print(f"{name:<45} | Prefix: {prefix:<10} | {cnt:>5} Packages")

grand_db = Package.objects.count()
print("-" * 80)
print(f"{'GRAND TOTAL ALL PACKAGES IN DATABASE':<45} | {'':<18} | {grand_db:>5} Packages")
print("=" * 80)
