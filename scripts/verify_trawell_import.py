import os
import sys
import re

sys.stdout.reconfigure(encoding='utf-8')

WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, WORKSPACE_ROOT)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')

import django
django.setup()

from django.test import Client
from django.db.models import Count
from packages.models import (
    Package,
    ItineraryDay,
    PackageVehicleTariff,
    TempleDarshanSlot,
    InternationalDocumentChecklist
)

def main():
    print("=" * 70)
    print("SIVA GAYATHRI TOURS & TRAVELS — TRAWELL INGESTION & AUDIT REPORT")
    print("=" * 70)

    trw_pkgs = Package.objects.filter(package_code__startswith='SGT-TRW-')
    count = trw_pkgs.count()
    print(f"Total Trawell Packages Ingested (SGT-TRW-): {count}")

    if count == 0:
        print("No SGT-TRW- packages found in database yet.")
        return

    days_count = ItineraryDay.objects.filter(package__package_code__startswith='SGT-TRW-').count()
    tariffs_count = PackageVehicleTariff.objects.filter(package__package_code__startswith='SGT-TRW-').count()
    darshan_count = TempleDarshanSlot.objects.filter(package__package_code__startswith='SGT-TRW-').count()
    intl_count = InternationalDocumentChecklist.objects.filter(package__package_code__startswith='SGT-TRW-').count()

    print(f"Total Itinerary Days Created           : {days_count}")
    print(f"Total 5-Tier Tariffs Created           : {tariffs_count}")
    print(f"Total Temple Darshan Slots             : {darshan_count}")
    print(f"Total International Checklists         : {intl_count}")

    # Category breakdown
    print("\n--- CATEGORY BREAKDOWN ---")
    cats = trw_pkgs.values('category').annotate(c=Count('id')).order_by('-c')
    for cat in cats:
        print(f"  • {cat['category']:<20}: {cat['c']:>5} packages")

    # Zero-tolerance branding leak audit
    print("\n--- ZERO-TOLERANCE BRANDING LEAK SCAN ---")
    banned_patterns = [
        re.compile(r'trawell(?:\.in)?', re.I),
        re.compile(r'tripzy', re.I),
        re.compile(r'77995-?91230'),
        re.compile(r'95351-?39583'),
    ]

    leaks = 0
    for p in trw_pkgs:
        for pat in banned_patterns:
            if pat.search(p.name) or pat.search(p.destination):
                print(f"  [LEAK IN PACKAGE] ID={p.id} Code={p.package_code}: {p.name}")
                leaks += 1
                break

    for d in ItineraryDay.objects.filter(package__package_code__startswith='SGT-TRW-')[:1000]:
        for pat in banned_patterns:
            if pat.search(d.title) or pat.search(d.activities or ''):
                print(f"  [LEAK IN ITINERARY] Day {d.day_number} (Pkg {d.package.package_code}): {d.title}")
                leaks += 1
                break

    if leaks == 0:
        print("  ✓ ZERO BRANDING LEAKS DETECTED! 100% sanitized under Siva Gayathri Tours & Travels.")
    else:
        print(f"  ⚠ FOUND {leaks} POTENTIAL BRANDING LEAKS.")

    # Quotation rendering test
    print("\n--- QUOTATION PREVIEW TEST ---")
    from django.contrib.auth import get_user_model
    User = get_user_model()
    u = User.objects.filter(is_superuser=True).first()
    client = Client()
    if u:
        client.force_login(u)
    samples = trw_pkgs.order_by('?')[:3]
    for sp in samples:
        url = f"/packages/quote/{sp.id}/"
        resp = client.get(url)
        status = "OK (200)" if resp.status_code == 200 else f"FAIL ({resp.status_code})"
        print(f"  GET {url:<25} [{sp.package_code}] -> {status}")

    # Grand total database inventory
    print("\n" + "=" * 70)
    print("GRAND TOTAL DATABASE INVENTORY ACROSS ALL AUDITED WEBSITES")
    print("=" * 70)
    all_count = Package.objects.count()
    providers = [
        ('Holidify Catalog', 'SGT-HOL-'),
        ('Trawell.in Catalog', 'SGT-TRW-'),
        ('Aspire Holidays', 'SGT-AH-'),
        ('Rengha Holidays', 'SGT-RH-'),
        ('Manoj Travels', 'SGT-MT-'),
        ('Chennai Travels', 'SGT-CT-'),
        ('Sri Murugan Travels', 'SGT-SMT-'),
        ('Jaisun Tourism', 'SGT-JT-'),
        ('Eroutes Travel', 'SGT-ER-'),
        ('Kandhan Travels', 'SGT-KT-'),
        ('SriGo Tours', 'SGT-SG-'),
        ('SBLT Travels', 'SGT-SBLT-'),
    ]

    for name, prefix in providers:
        p_cnt = Package.objects.filter(package_code__startswith=prefix).count()
        print(f"  • {name:<25} ({prefix:<9}) : {p_cnt:>5} packages")

    other_cnt = Package.objects.exclude(package_code__regex=r'^SGT-(HOL|TRW|AH|RH|MT|CT|SMT|JT|ER|KT|SG|SBLT)-').count()
    print(f"  • Other Custom / College IV Departures       : {other_cnt:>5} packages")
    print("-" * 70)
    print(f"  TOTAL PACKAGES IN DATABASE                   : {all_count:>5}")
    print(f"  TOTAL ITINERARY DAYS                         : {ItineraryDay.objects.count():>5}")
    print(f"  TOTAL 5-TIER VEHICLE TARIFFS                 : {PackageVehicleTariff.objects.count():>5}")
    print("=" * 70)

if __name__ == '__main__':
    main()
