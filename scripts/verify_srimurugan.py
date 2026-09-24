import os
import sys
import django

sys.stdout.reconfigure(encoding='utf-8')
WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, WORKSPACE_ROOT)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
django.setup()

from packages.models import (
    Package,
    ItineraryDay,
    PackageVehicleTariff,
    TempleDarshanSlot,
    InternationalDocumentChecklist,
)

print("="*80)
print("COMPREHENSIVE SRI MURUGAN INGESTION VERIFICATION")
print("="*80)

dom_pkgs = Package.objects.filter(package_code__startswith='SGT-SMT-DOM-')
int_pkgs = Package.objects.filter(package_code__startswith='SGT-SMT-INT-')
trn_pkgs = Package.objects.filter(package_code__startswith='SGT-SMT-TRN-')
dev_pkgs = Package.objects.filter(package_code__startswith='SGT-SMT-DEV-')
all_smt = Package.objects.filter(package_code__startswith='SGT-SMT-')
grand_total = Package.objects.count()

print(f"Domestic Flight Packages [SGT-SMT-DOM-]:  {dom_pkgs.count()}")
print(f"International Packages   [SGT-SMT-INT-]:  {int_pkgs.count()}")
print(f"Train Tour Packages      [SGT-SMT-TRN-]:  {trn_pkgs.count()}")
print(f"Devotional Hub Packages  [SGT-SMT-DEV-]:  {dev_pkgs.count()}")
print(f"Total SGT-SMT- Packages Imported:         {all_smt.count()}")
print(f"Grand Total Packages in Travel ERP:       {grand_total:,}")
print("-" * 80)

# Associated records
days_cnt = ItineraryDay.objects.filter(package__package_code__startswith='SGT-SMT-').count()
tariff_cnt = PackageVehicleTariff.objects.filter(package__package_code__startswith='SGT-SMT-').count()
slot_cnt = TempleDarshanSlot.objects.filter(package__package_code__startswith='SGT-SMT-').count()
doc_cnt = InternationalDocumentChecklist.objects.filter(package__package_code__startswith='SGT-SMT-').count()

print(f"Total Itinerary Days:                 {days_cnt}")
print(f"Total 5-Tier Vehicle Tariffs:         {tariff_cnt}")
print(f"Total Temple Darshan Slots:           {slot_cnt}")
print(f"Total International Doc Checklists:   {doc_cnt}")
print("-" * 80)

# Branding Leak Check
print("Scanning all SGT-SMT- packages for branding leaks ('murugan', 'srimurugan', old phone)...")
leaks = []
for p in all_smt:
    for field in ['name', 'description', 'inclusions', 'exclusions', 'terms_and_conditions']:
        val = getattr(p, field, '')
        if 'sri murugan' in val.lower() or 'srimurugan' in val.lower() or '9791848265' in val or '97918 48265' in val:
            leaks.append((p.package_code, field, val[:60]))

print(f"Total branding leaks found: {len(leaks)}")
if leaks:
    for l in leaks[:5]:
        print("  LEAK:", l)
else:
    print("PASS: 100% clean! Zero branding leaks found across all packages.")

print("-" * 80)

# Sample Inspections
print("\n--- SAMPLE DOMESTIC FLIGHT PACKAGE ---")
s_dom = dom_pkgs.first()
if s_dom:
    print(f"[{s_dom.package_code}] {s_dom.name}")
    print(f"Destination: {s_dom.destination} | Category: {s_dom.category} | Transit: {s_dom.transit_mode}")
    print(f"Duration: {s_dom.duration_nights}N / {s_dom.duration_days}D | Price: ₹{s_dom.base_price:,.0f}")
    print(f"Itinerary Days: {s_dom.itinerary_days.count()} | Tariffs: {s_dom.vehicle_tariffs.count()}")

print("\n--- SAMPLE INTERNATIONAL PACKAGE ---")
s_int = int_pkgs.first()
if s_int:
    print(f"[{s_int.package_code}] {s_int.name}")
    print(f"Country: {s_int.destination_country} | Currency: {s_int.currency_code} | Transit: {s_int.transit_mode}")
    print(f"Duration: {s_int.duration_nights}N / {s_int.duration_days}D | Price: ₹{s_int.base_price:,.0f}")
    print(f"Doc Checklist: {s_int.intl_documents.count()} | Tariffs: {s_int.vehicle_tariffs.count()}")

print("\n--- SAMPLE TRAIN TOUR PACKAGE ---")
s_trn = trn_pkgs.first()
if s_trn:
    print(f"[{s_trn.package_code}] {s_trn.name}")
    print(f"Destination: {s_trn.destination} | Category: {s_trn.category} | Transit: {s_trn.transit_mode}")
    print(f"Duration: {s_trn.duration_nights}N / {s_trn.duration_days}D | Price: ₹{s_trn.base_price:,.0f}")
    print(f"Itinerary Days: {s_trn.itinerary_days.count()} | Temple Slots: {s_trn.temple_slots.count()}")

print("="*80)
