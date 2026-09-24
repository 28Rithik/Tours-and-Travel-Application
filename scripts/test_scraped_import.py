import os
import sys
import json
import re
from decimal import Decimal

# Setup Django environment
WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, WORKSPACE_ROOT)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')

import django
django.setup()

from packages.models import Package, ItineraryDay, PackageVehicleTariff
from fleet.models import VehicleType

def test_import():
    with open('scripts/scraped_manoj_packages.json', encoding='utf-8') as f:
        data = json.load(f)

    print(f"Loaded {len(data)} packages from JSON.")
    sample = data[:3]
    for p in sample:
        print("Sample:", p['title'], "| Cat:", p['category_name'], "| Days:", p['days_count'])

if __name__ == '__main__':
    test_import()
