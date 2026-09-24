import os
import sys
import django

sys.path.append('c:/Users/rithi/Documents/Documents Project Intership and Course/Projects/Rag chatbot/Travels Trip Managment Application')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
django.setup()

from packages.models import Package

slugs_to_check = [
    'kolli-hills',
    'valparai',
    'thirunallar',
    'outside-city',
    'thiruthani',
    'tiruchendur',
    'narasimhar',
    'wayanad'
]

for s in slugs_to_check:
    matches = Package.objects.filter(package_code__startswith='SGT-CT-').filter(name__icontains=s)
    print(f"Slug query: '{s}' -> {matches.count()} matches")
    for m in matches:
        print(f"   [{m.package_code}] {m.name}")
