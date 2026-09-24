import os
import sys
import re

sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)

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
)

def main():
    print("=" * 70)
    print("SIVA GAYATHRI TOURS & TRAVELS — PRABU TOURS INGESTION & AUDIT REPORT")
    print("=" * 70)

    ptt_pkgs = Package.objects.filter(package_code__startswith='SGT-PTT-')
    count = ptt_pkgs.count()
    print(f"Total Prabu Tours Packages Ingested (SGT-PTT-): {count}")

    if count == 0:
        print("No SGT-PTT- packages found in database.")
        return

    days_count = ItineraryDay.objects.filter(package__package_code__startswith='SGT-PTT-').count()
    tariffs_count = PackageVehicleTariff.objects.filter(package__package_code__startswith='SGT-PTT-').count()
    darshan_count = TempleDarshanSlot.objects.filter(package__package_code__startswith='SGT-PTT-').count()

    print(f"Total Itinerary Days Created           : {days_count}")
    print(f"Total 5-Tier Tariffs Created           : {tariffs_count}")
    print(f"Total Temple Darshan Slots             : {darshan_count}")

    # Category breakdown
    print("\n--- CATEGORY BREAKDOWN ---")
    cats = ptt_pkgs.values('category').annotate(c=Count('id')).order_by('-c')
    for cat in cats:
        print(f"  • {cat['category']:<20}: {cat['c']:>5} packages")

    # Sample listing
    print("\n--- SAMPLE INGESTED PACKAGES ---")
    for p in ptt_pkgs.order_by('id')[:8]:
        print(f"  [{p.package_code}] {p.name:<60} | {p.duration_days}D/{p.duration_nights}N | Rs.{p.base_price}")

    # Zero-tolerance branding leak audit
    print("\n--- ZERO-TOLERANCE BRANDING LEAK SCAN ---")
    banned_patterns = [
        re.compile(r'prabu', re.I),
        re.compile(r'prabutourstravels', re.I),
        re.compile(r'98401-?08069'),
        re.compile(r'82202-?02056'),
    ]

    leaks = 0
    for p in ptt_pkgs:
        for pat in banned_patterns:
            if pat.search(p.name) or pat.search(p.destination):
                print(f"  [LEAK IN PACKAGE] ID={p.id} Code={p.package_code}: {p.name}")
                leaks += 1
                break

    for d in ItineraryDay.objects.filter(package__package_code__startswith='SGT-PTT-'):
        for pat in banned_patterns:
            if pat.search(d.title) or pat.search(d.activities or ''):
                print(f"  [LEAK IN ITINERARY] Day {d.day_number} (Pkg {d.package.package_code}): {d.title}")
                leaks += 1
                break

    if leaks == 0:
        print("  ✓ ZERO BRANDING LEAKS DETECTED! 100% sanitized under Siva Gayathri Tours & Travels.")
    else:
        print(f"  ⚠ FOUND {leaks} POTENTIAL BRANDING LEAKS.")

    # Quotation preview test
    print("\n--- QUOTATION PREVIEW TEST ---")
    from django.contrib.auth import get_user_model
    User = get_user_model()
    u = User.objects.filter(is_superuser=True).first()
    client = Client()
    if u:
        client.force_login(u)
    samples = ptt_pkgs.order_by('?')[:3]
    for sp in samples:
        url = f"/packages/quote/{sp.id}/"
        resp = client.get(url)
        status = "OK (200)" if resp.status_code == 200 else f"FAIL ({resp.status_code})"
        print(f"  GET {url:<25} [{sp.package_code}] -> {status}")

    # Grand total database inventory
    print("\n" + "=" * 70)
    print("GRAND TOTAL DATABASE INVENTORY ACROSS ALL 14 AUDITED WEBSITES")
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
        ('Bharathiyar Travels', 'SGT-BTT-'),
        ('Prabu Tours & Travels', 'SGT-PTT-'),
        ('Kandhan Travels', 'SGT-KT-'),
        ('SriGo Tours', 'SGT-SG-'),
        ('SBLT Travels', 'SGT-SBLT-'),
    ]

    for name, prefix in providers:
        p_cnt = Package.objects.filter(package_code__startswith=prefix).count()
        print(f"  • {name:<25} ({prefix:<9}) : {p_cnt:>5} packages")

    other_cnt = Package.objects.exclude(package_code__regex=r'^SGT-(HOL|TRW|AH|RH|MT|CT|SMT|JT|ER|BTT|PTT|KT|SG|SBLT)-').count()
    print(f"  • Other Custom / College IV Departures       : {other_cnt:>5} packages")
    print("-" * 70)
    print(f"  TOTAL PACKAGES IN DATABASE                   : {all_count:>5}")
    print(f"  TOTAL ITINERARY DAYS                         : {ItineraryDay.objects.count():>5}")
    print(f"  TOTAL 5-TIER VEHICLE TARIFFS                 : {PackageVehicleTariff.objects.count():>5}")
    print("=" * 70)

if __name__ == '__main__':
    main()
