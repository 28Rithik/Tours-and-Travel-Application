import os
import sys
import re
import django

sys.path.append('c:/Users/rithi/Documents/Documents Project Intership and Course/Projects/Rag chatbot/Travels Trip Managment Application')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
django.setup()

from packages.models import Package, ItineraryDay, PackageVehicleTariff, TempleDarshanSlot

sys.stdout.reconfigure(encoding='utf-8')

ct_pkgs = Package.objects.filter(package_code__startswith='SGT-CT-').order_by('package_code')
print(f"Total SGT-CT packages in database: {ct_pkgs.count()}")

# Check leaks
brand_leaks = []
for p in ct_pkgs:
    corpus = f"{p.name} {p.destination} {p.description} {p.inclusions} {p.exclusions} {p.terms_and_conditions} {p.contact_persons_footer}"
    for itin in p.itinerary_days.all():
        corpus += f" {itin.title} {itin.route_segment} {itin.activities}"
    
    m = re.search(r'chennaitravels|chennai travels|\+?91[\s-]?[0-9]{10}', corpus, re.I)
    if m:
        # Check if it's our official number
        found = m.group(0)
        if found not in ['+91 98425 33777', '+91 94381 7131', '+91 38209 9979', '9842533777', '943817131']:
            brand_leaks.append((p.package_code, p.name, found))

print(f"Brand leaks found: {len(brand_leaks)}")
for c, n, f in brand_leaks[:15]:
    print(f"  - [{c}] {n[:35]} -> leak: '{f}'")

# Check category anomalies
wrong_cats = []
for p in ct_pkgs:
    if p.category == 'international' and any(k in p.name.lower() for k in ['kanchipuram', 'mahabalipuram', 'pondicherry', 'ooty', 'kodaikanal', 'chennai', 'temple', 'tirupati']):
        wrong_cats.append((p.package_code, p.name, p.category))

print(f"\nWrong category anomalies (e.g. TN temple marked as international): {len(wrong_cats)}")
for c, n, cat in wrong_cats[:10]:
    print(f"  - [{c}] {n[:45]} -> {cat}")

# Check missing temple darshan slots on devotional packages
devotional_pkgs = ct_pkgs.filter(is_devotional=True)
missing_darshan = []
for p in devotional_pkgs:
    if p.temple_slots.count() == 0:
        missing_darshan.append((p.package_code, p.name))

print(f"\nDevotional packages in SGT-CT: {devotional_pkgs.count()}")
print(f"Devotional packages missing TempleDarshanSlot: {len(missing_darshan)}")
for c, n in missing_darshan[:10]:
    print(f"  - [{c}] {n[:45]}")
