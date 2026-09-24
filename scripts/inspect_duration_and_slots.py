import os
import sys
import re
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
django.setup()
sys.stdout.reconfigure(encoding='utf-8')

from packages.models import Package

print("=== 1. Inspecting all 20 1-day packages in 'holiday' ===")
for p in Package.objects.filter(category='holiday', duration_days=1):
    print(f"[{p.id}] {p.package_code}: {p.name} | Dest: {p.destination}")

print("\n=== 2. Checking Title vs Duration mismatches ===")
mismatches = []
pattern = re.compile(r'(\d+)\s*(?:nights?|n)\s*(?:/|-|&)?\s*(\d+)\s*(?:days?|d)', re.IGNORECASE)
for p in Package.objects.all():
    match = pattern.search(p.name)
    if match:
        nights_in_title = int(match.group(1))
        days_in_title = int(match.group(2))
        if p.duration_nights != nights_in_title or p.duration_days != days_in_title:
            mismatches.append((p.id, p.package_code, p.name, p.duration_nights, p.duration_days, nights_in_title, days_in_title))

print(f"Total packages with Title vs Duration mismatch: {len(mismatches)}")
for m in mismatches[:20]:
    print(f"[{m[0]}] {m[1]}: '{m[2]}' -> DB: {m[3]}N/{m[4]}D vs Title: {m[5]}N/{m[6]}D")

print("\n=== 3. Inspecting the 230 devotional packages without TempleDarshanSlot ===")
dev_without_slots = Package.objects.filter(category='devotional', temple_slots__isnull=True)
print(f"Total: {dev_without_slots.count()}")
for p in dev_without_slots[:15]:
    print(f"[{p.id}] {p.package_code}: {p.name} | Dest: {p.destination}")
