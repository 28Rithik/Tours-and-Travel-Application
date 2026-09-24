import os
import sys
import django

sys.path.append('c:/Users/rithi/Documents/Documents Project Intership and Course/Projects/Rag chatbot/Travels Trip Managment Application')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
django.setup()

from packages.models import Package, TempleDarshanSlot

ct_pkgs = Package.objects.filter(package_code__startswith='SGT-CT-').order_by('package_code')
print(f"Total SGT-CT packages in database: {ct_pkgs.count()}")

darshan_count = TempleDarshanSlot.objects.filter(package__package_code__startswith='SGT-CT-').count()
print(f"Total TempleDarshanSlot in SGT-CT: {darshan_count}")

# Check sample package details
print("\n--- SAMPLE SGT-CT PACKAGES ---")
for p in ct_pkgs[:15]:
    itin_days = p.itinerary_days.count()
    tariffs = p.vehicle_tariffs.count()
    print(f"[{p.package_code}] {p.name[:45]:45} | cat: {p.category:12} | {p.duration_nights}N/{p.duration_days}D | itin: {itin_days} | tariffs: {tariffs}")
