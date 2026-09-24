import os
import sys
import re

sys.stdout.reconfigure(encoding='utf-8')

WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, WORKSPACE_ROOT)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')

import django
django.setup()

from packages.models import (
    Package,
    ItineraryDay,
    PackageVehicleTariff,
    TempleDarshanSlot,
    InternationalDocumentChecklist,
)

def run_verification():
    print("="*80)
    print("AUDIT & VERIFICATION: SIVA GAYATHRI TOURS & TRAVELS (RENGHA EXTRACTION)")
    print("="*80)

    rh_pkgs = Package.objects.filter(package_code__startswith='SGT-RH-')
    count = rh_pkgs.count()
    print(f"Total SGT-RH Packages in DB: {count}")
    assert count == 488, f"Expected 488 packages, got {count}"

    itin_count = ItineraryDay.objects.filter(package__in=rh_pkgs).count()
    tariff_count = PackageVehicleTariff.objects.filter(package__in=rh_pkgs).count()
    intl_count = InternationalDocumentChecklist.objects.filter(package__in=rh_pkgs).count()
    temple_count = TempleDarshanSlot.objects.filter(package__in=rh_pkgs).count()

    print(f"Total Itinerary Days: {itin_count}")
    print(f"Total Vehicle Tariffs: {tariff_count} (5 tiers per package: {tariff_count // count})")
    print(f"Total International Document Checklists: {intl_count}")
    print(f"Total Temple Darshan Slots: {temple_count}")

    # Category breakdown
    cats = {}
    for p in rh_pkgs:
        cats[p.category] = cats.get(p.category, 0) + 1
    print(f"\nCategory Breakdown: {cats}")

    # Zero-tolerance branding leak audit
    print("\nRunning zero-tolerance branding leak audit...")
    leak_regex = re.compile(r'\b(rengha|renghaholidays|renghatravels)\b', re.IGNORECASE)
    leak_count = 0
    checked_fields = 0

    for p in rh_pkgs:
        for field_name in ['name', 'description', 'inclusions', 'exclusions', 'terms_and_conditions', 'contact_persons_footer', 'destination']:
            val = getattr(p, field_name, '')
            checked_fields += 1
            m = leak_regex.search(val)
            if m:
                print(f"  [LEAK] Pkg {p.package_code} in {field_name}: {m.group(0)} -> '{val[:80]}'")
                leak_count += 1

    for d in ItineraryDay.objects.filter(package__in=rh_pkgs):
        for field_name in ['title', 'activities', 'sightseeing_spots']:
            val = getattr(d, field_name, '')
            checked_fields += 1
            m = leak_regex.search(val)
            if m:
                print(f"  [LEAK] ItinDay {d.id} in {field_name}: {m.group(0)} -> '{val[:80]}'")
                leak_count += 1

    print(f"Checked {checked_fields} text fields across all packages and itinerary days.")
    print(f"Total branding leaks found: {leak_count}")
    assert leak_count == 0, f"Found {leak_count} branding leaks!"

    print("\nVerifying sample packages across diverse categories...")
    samples = [
        rh_pkgs.filter(category='devotional').first(),
        rh_pkgs.filter(category='international').first(),
        rh_pkgs.filter(category='hill_station').first(),
        rh_pkgs.filter(category='family_vacation').first(),
    ]
    for s in samples:
        if not s: continue
        print(f"\n  Package Code: {s.package_code}")
        print(f"  Name: {s.name}")
        print(f"  Destination: {s.destination} ({s.destination_country})")
        print(f"  Duration: {s.duration_nights}N / {s.duration_days}D | Category: {s.category}")
        print(f"  Base Price: Rs. {s.base_price} | Food Included: Rs. {s.price_with_food}")
        print(f"  Tariffs attached: {s.vehicle_tariffs.count()} tiers")
        print(f"  Itinerary days: {s.itinerary_days.count()} days")
        print(f"  Contact Footer: {s.contact_persons_footer}")

    print("\n" + "="*80)
    print("ALL VERIFICATIONS PASSED WITH 100% SUCCESS!")
    print("="*80)

if __name__ == '__main__':
    run_verification()
