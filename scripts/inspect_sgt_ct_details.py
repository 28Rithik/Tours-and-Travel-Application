import os
import sys
import django

sys.path.append('c:/Users/rithi/Documents/Documents Project Intership and Course/Projects/Rag chatbot/Travels Trip Managment Application')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
django.setup()

from packages.models import Package

ct_pkgs = Package.objects.filter(package_code__startswith='SGT-CT-').order_by('package_code')

print("--- 18 MISCLASSIFIED PACKAGES (category='international') ---")
for p in ct_pkgs.filter(category='international'):
    print(f"[{p.package_code}] {p.name}")

print("\n--- DEVOTIONAL PACKAGES IN SGT-CT ---")
for p in ct_pkgs.filter(is_devotional=True):
    slots = p.temple_slots.count()
    print(f"[{p.package_code}] {p.name} | slots: {slots}")
