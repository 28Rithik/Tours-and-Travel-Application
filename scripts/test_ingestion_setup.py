import os
import sys
import re
import json
import decimal
import django

# Setup Django environment
sys.path.append('c:/Users/rithi/Documents/Documents Project Intership and Course/Projects/Rag chatbot/Travels Trip Managment Application')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
django.setup()

from packages.models import Package, PackageTemplate, ItineraryDay, PackageVehicleTariff, TempleDarshanSlot
from core.models import VehicleType

sys.stdout.reconfigure(encoding='utf-8')

print("Starting Chennai Tours & Travels Ingestion & Rebranding...")

# Load crawled dataset
with open('scripts/crawled_chennaitourstravels_packages.json', 'r', encoding='utf-8') as f:
    crawled_items = json.load(f)

print(f"Loaded {len(crawled_items)} crawled pages.")

# Get vehicle types
v_sedan = VehicleType.objects.filter(name__icontains='Sedan').first() or VehicleType.objects.get(id=3)
v_crysta = VehicleType.objects.filter(name__icontains='Crysta').first() or VehicleType.objects.get(id=1)
v_tt = VehicleType.objects.filter(name__icontains='Urbania').first() or VehicleType.objects.filter(name__icontains='Tempo').first() or VehicleType.objects.get(id=4)
v_minibus = VehicleType.objects.filter(name__icontains='36').first() or VehicleType.objects.get(id=13)
v_coach = VehicleType.objects.filter(name__icontains='54').first() or VehicleType.objects.filter(name__icontains='52').first() or VehicleType.objects.get(id=8)

print(f"Assigned Vehicle Types: Sedan({v_sedan.id}), Crysta({v_crysta.id}), TT({v_tt.id}), MiniBus({v_minibus.id}), Coach({v_coach.id})")

def clean_rebrand(text):
    if not text:
        return ""
    text = re.sub(r'Content on this page requires a newer version of Adobe Flash Player\.?', '', text, flags=re.I)
    text = re.sub(r'HAPPY TIME AHEAD WITH (?:OUR )?TRAVEL AHEAD(?:\s*TOURS)?\.?', 'Happy Journey with Siva Gayathri Tours & Travels!', text, flags=re.I)
    text = re.sub(r'Travel Ahead(?:\s*Tours)?', 'Siva Gayathri Tours & Travels', text, flags=re.I)
    text = re.sub(r'Chennai Tours\s*(?:and|&)?\s*Travels(?:\s*-\s*Direct Tour Operators)?', 'Siva Gayathri Tours & Travels', text, flags=re.I)
    text = re.sub(r'chennaitourstravels\.com', 'sivagayathritravels.com', text, flags=re.I)
    text = re.sub(r'travelahead\.[a-z]+', 'sivagayathritravels.com', text, flags=re.I)
    text = re.sub(r'\+?91[\s-]?[0-9]{10}', '+91 98425 33777', text)
    text = re.sub(r'[a-zA-Z0-9_.+-]+@(?:chennaitourstravels|travelahead)\.[a-zA-Z0-9-.]+', 'booking@sivagayathritravels.com', text, flags=re.I)
    return text.strip()

def to_title_case(text):
    if not text:
        return ""
    # Clean text from pipe splits
    if '|' in text:
        parts = [p.strip() for p in text.split('|') if len(p.strip()) > 3]
        text = parts[0] if parts else text
    words = text.split()
    clean_words = []
    minor_words = {'and', 'or', 'the', 'in', 'on', 'at', 'to', 'for', 'of', 'by', 'with', 'a', 'an'}
    for i, w in enumerate(words):
        lw = w.lower()
        if i == 0 or lw not in minor_words:
            clean_words.append(w.capitalize())
        else:
            clean_words.append(lw)
    return ' '.join(clean_words)

print("Setup completed successfully.")
