import json
import re

with open('scripts/chennaitravels_in_tour_urls.json', 'r', encoding='utf-8') as f:
    urls = json.load(f)

print(f"Total identified tour URLs: {len(urls)}")

# Check against existing packages in database
import os, sys, django
sys.path.append('c:/Users/rithi/Documents/Documents Project Intership and Course/Projects/Rag chatbot/Travels Trip Managment Application')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
django.setup()

from packages.models import Package

ct_packages = Package.objects.filter(package_code__startswith='SGT-CT-')
print(f"Existing SGT-CT packages in database: {ct_packages.count()}")

# Sample existing package codes and names
print("\nSample 10 existing SGT-CT packages:")
for p in ct_packages[:10]:
    print(f"  [{p.package_code}] {p.name} ({p.duration_nights}N/{p.duration_days}D) - Itin days: {p.itinerary_days.count()}, Tariffs: {p.vehicle_tariffs.count()}, Darshan slots: {p.temple_slots.count()}")

# Check what the 54 tour URLs on chennaitravels.in correspond to
print("\nFirst 20 tour URLs from chennaitravels.in:")
for u in urls[:20]:
    slug = u.split('/')[-1].replace('.html', '')
    print(f"  - {slug:45} | {u}")
