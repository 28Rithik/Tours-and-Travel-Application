import os
import sys

sys.stdout.reconfigure(encoding='utf-8')
WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, WORKSPACE_ROOT)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')

import django
django.setup()

from core.models import VehicleType

print("Available Vehicle Types in DB:")
for vt in VehicleType.objects.all():
    print(f"- ID: {vt.id} | Name: {vt.name} | Seating: {getattr(vt, 'seating_capacity', 'N/A')}")
