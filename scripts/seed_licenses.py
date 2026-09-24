import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
django.setup()

from core.models import LicenseClass

licenses = [
    {"code": "MCWOG", "name": "Motorcycle Without Gear", "example_vehicles": "Scooty, Activa"},
    {"code": "MCWG", "name": "Motorcycle With Gear", "example_vehicles": "KTM, Royal Enfield, BMW bike"},
    {"code": "LMV", "name": "Light Motor Vehicle", "example_vehicles": "Car, SUV, small van"},
    {"code": "LMV-NT", "name": "LMV – Non-Transport", "example_vehicles": "Private car/SUV"},
    {"code": "LMV-TR", "name": "LMV – Transport", "example_vehicles": "Taxi, small commercial vehicle"},
    {"code": "HMV/HGV", "name": "Heavy Motor Vehicle / Heavy Goods Vehicle", "example_vehicles": "Heavy truck"},
    {"code": "HPMV/HGMV", "name": "Heavy Passenger/Goods Motor Vehicle", "example_vehicles": "Bus, large truck"},
    {"code": "Transport", "name": "Commercial passenger/goods vehicle", "example_vehicles": "Bus, taxi, truck"},
    {"code": "Tractor", "name": "Agricultural tractor", "example_vehicles": "Farm tractor"},
    {"code": "E-rickshaw", "name": "Electric rickshaw", "example_vehicles": "E-rickshaw"},
    {"code": "Three-wheeler", "name": "Auto/3-wheeler", "example_vehicles": "Auto-rickshaw"},
]

for lic in licenses:
    obj, created = LicenseClass.objects.get_or_create(code=lic["code"], defaults=lic)
    if not created:
        obj.name = lic["name"]
        obj.example_vehicles = lic["example_vehicles"]
        obj.save()

print("Licenses seeded successfully!")
