import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, WORKSPACE_ROOT)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')

import django
django.setup()

from packages.models import Package

print("Short or generic names check (< 12 chars):")
short_names = Package.objects.filter(name__regex=r'^.{1,12}$')
print(f"Total: {short_names.count()}")
for p in short_names:
    print(f"  [{p.package_code}] ID: {p.id} | Name: {p.name!r} | Dest: {p.destination!r}")

print("\nShort destinations check (< 3 chars):")
short_dest = Package.objects.filter(destination__regex=r'^.{0,2}$')
print(f"Total: {short_dest.count()}")
for p in short_dest:
    print(f"  [{p.package_code}] ID: {p.id} | Name: {p.name!r} | Dest: {p.destination!r}")
