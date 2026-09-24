import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
django.setup()
sys.stdout.reconfigure(encoding='utf-8')

from packages.models import Package

print("=== Inspecting 'devotional' that matched international ===")
from scripts.audit_classification_rules import INTL_COUNTRIES
import re

dev_pkgs = Package.objects.filter(category='devotional')
for p in dev_pkgs:
    title_dest = f"{p.name} {p.destination}".lower()
    matched = [kw for kw in INTL_COUNTRIES if re.search(r'\b' + re.escape(kw) + r'\b', title_dest)]
    if matched:
        print(f"[{p.id}] {p.package_code}: {p.name} | Dest: {p.destination} | Matched: {matched}")
