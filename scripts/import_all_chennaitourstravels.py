import os
import sys
import re
import decimal
import django

# Add project root to path and setup Django
sys.path.append('c:/Users/rithi/Documents/Documents Project Intership and Course/Projects/Rag chatbot/Travels Trip Managment Application')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
django.setup()

from packages.models import Package, PackageTemplate, ItineraryDay, PackageVehicleTariff, TempleDarshanSlot
from core.models import VehicleType

sys.stdout.reconfigure(encoding='utf-8')

# Import package data
from ctt_catalog_data import OUTSTATION_PACKAGES
from ctt_pilgrimage_data import PILGRIMAGE_PACKAGES
from ctt_pilgrimage_part2 import PILGRIMAGE_PACKAGES_PART2
from ctt_vacations_data import VACATION_PACKAGES
from ctt_vacations_part2 import VACATION_PACKAGES_PART2
from ctt_specialized_data import SPECIALIZED_PACKAGES

all_packages_to_import = (
    OUTSTATION_PACKAGES +
    PILGRIMAGE_PACKAGES +
    PILGRIMAGE_PACKAGES_PART2 +
    VACATION_PACKAGES +
    VACATION_PACKAGES_PART2 +
    SPECIALIZED_PACKAGES
)

print("="*85)
print(f"IMPORTING {len(all_packages_to_import)} CHENNAI TOURS & TRAVELS PACKAGES INTO TRAVELERP")
print("100% REBRANDED UNDER SIVA GAYATHRI TOURS & TRAVELS (+91 98425 33777)")
print("="*85)

# Fetch vehicle types
v_sedan = VehicleType.objects.filter(name__icontains='Sedan').first() or VehicleType.objects.get(id=3)
v_crysta = VehicleType.objects.filter(name__icontains='Crysta').first() or VehicleType.objects.get(id=1)
v_tt = VehicleType.objects.filter(name__icontains='Urbania').first() or VehicleType.objects.filter(name__icontains='Tempo').first() or VehicleType.objects.get(id=4)
v_minibus = VehicleType.objects.filter(name__icontains='36').first() or VehicleType.objects.get(id=13)
v_coach = VehicleType.objects.filter(name__icontains='54').first() or VehicleType.objects.filter(name__icontains='52').first() or VehicleType.objects.get(id=8)

print(f"Vehicle Types: Sedan({v_sedan.name}), Crysta({v_crysta.name}), TT({v_tt.name}), MiniBus({v_minibus.name}), Coach({v_coach.name})")

# Vehicle pricing tiers helper
def generate_tariffs(package, days, nights, base_price):
    tariffs = []
    days = max(1, days)
    is_1day = (days == 1)

    if is_1day:
        # 1-day pricing based on distance/duration
        rates = {
            v_sedan: (decimal.Decimal('2800.00') if base_price < 600 else decimal.Decimal('3800.00'), '4_sedan', 250, 14.0, 10),
            v_crysta: (decimal.Decimal('4200.00') if base_price < 600 else decimal.Decimal('5800.00'), '7_crysta', 250, 18.0, 10),
            v_tt: (decimal.Decimal('5800.00') if base_price < 600 else decimal.Decimal('7500.00'), '17_tt_urbania', 250, 24.0, 10),
            v_minibus: (decimal.Decimal('9500.00') if base_price < 600 else decimal.Decimal('12500.00'), '36_mini_bus', 250, 36.0, 10),
            v_coach: (decimal.Decimal('14000.00') if base_price < 600 else decimal.Decimal('18500.00'), '54_luxury_coach', 250, 48.0, 10)
        }
        for vt, (pkg_rate, tier, inc_km, extra_km, hrs) in rates.items():
            tariffs.append(PackageVehicleTariff(
                package=package,
                vehicle_type=vt,
                rate_type='local_1day',
                seating_tier=tier,
                package_rate=pkg_rate,
                per_day_rate=pkg_rate,
                included_km=inc_km,
                extra_km_rate=decimal.Decimal(str(extra_km)),
                local_package_hours=hrs,
                extra_hour_rate=decimal.Decimal('250.00'),
                driver_bata_included=True,
                driver_bata_per_day=decimal.Decimal('500.00'),
                toll_parking_included=True
            ))
    else:
        # Multi-day pricing per vehicle
        # Base daily rates
        daily_rates = {
            v_sedan: (decimal.Decimal('2600.00'), '4_sedan', 300, 13.0),
            v_crysta: (decimal.Decimal('3900.00'), '7_crysta', 300, 18.0),
            v_tt: (decimal.Decimal('5200.00'), '17_tt_urbania', 300, 23.0),
            v_minibus: (decimal.Decimal('8500.00'), '36_mini_bus', 300, 35.0),
            v_coach: (decimal.Decimal('13500.00'), '54_luxury_coach', 300, 45.0)
        }
        for vt, (d_rate, tier, inc_km, extra_km) in daily_rates.items():
            total_rate = d_rate * days
            tariffs.append(PackageVehicleTariff(
                package=package,
                vehicle_type=vt,
                rate_type='outstation_multiday',
                seating_tier=tier,
                package_rate=total_rate,
                per_day_rate=d_rate,
                included_km=inc_km * days,
                extra_km_rate=decimal.Decimal(str(extra_km)),
                driver_bata_included=True,
                driver_bata_per_day=decimal.Decimal('600.00'),
                night_halt_charge=decimal.Decimal('500.00') if nights > 0 else decimal.Decimal('0.00'),
                toll_parking_included=True
            ))
    return tariffs

created_packages_count = 0
created_itinerary_days_count = 0
created_tariffs_count = 0
created_darshan_slots_count = 0

for p_data in all_packages_to_import:
    code = p_data['code']
    name = p_data['name']
    dest = p_data['destination']
    cat = p_data['category']
    days = p_data['duration_days']
    nights = p_data['duration_nights']
    b_price = p_data['base_price']
    p_food = p_data['price_with_food']
    p_nofood = p_data['price_without_food']
    is_devotional = p_data.get('is_devotional', False)
    desc = p_data.get('description', '')

    # Standard Inclusions
    if is_devotional:
        inclusions = (
            "Round-trip AC transportation by dedicated vehicle.\n"
            "All toll gate, interstate permit, parking, and driver bata charges included.\n"
            "Star category hotel accommodation on twin / triple sharing basis.\n"
            "100% Pure Vegetarian South Indian Satvik meals (Breakfast, Lunch, Dinner).\n"
            "Dedicated Tour Manager & Temple Darshan Coordinator from Siva Gayathri Tours.\n"
            "Special Entry Darshan ticket assistance at all major shrines.\n"
            "Special Laddu / Temple Prasadam and holy theertham included.\n"
            "Senior citizen wheelchair / battery car assistance at temple complexes."
        )
        exclusions = (
            "Special individual pooja / archanai / abhishekam tickets.\n"
            "Personal expenses like tonsuring (mottai), ear boring, laundry, and camera fees.\n"
            "Any additional food / room service ordered outside the fixed package menu."
        )
    elif cat == 'college_iv':
        inclusions = (
            "All-way luxury air-suspension coach (JBL sound system, laser lights, charging ports).\n"
            "All toll, parking, driver day bata, and interstate permits covered.\n"
            "Resort / 3-star hotel stay on 4-sharing basis.\n"
            "Full AP meal plan (South/North Indian buffet breakfast, lunch, and dinner).\n"
            "Complimentary travel for faculty / accompanying staff (50 + 2 ratio).\n"
            "Official industrial visit clearance coordination.\n"
            "DJ night with musical campfire at resort.\n"
            "Tour Manager from Siva Gayathri Tours & Travels."
        )
        exclusions = (
            "Individual room service, laundry, telephone charges.\n"
            "Optional boating / theme park game tokens beyond itinerary.\n"
            "Any breakages / damages caused to vehicle or resort properties."
        )
    else:
        inclusions = (
            "Comfortable AC vehicle transfer and sightseeing as per itinerary.\n"
            "All toll gate, state permit, parking fees, and driver day allowance covered.\n"
            "Selected resort / deluxe hotel accommodation on sharing basis.\n"
            "Daily breakfast and dinner (MAP plan).\n"
            "Experienced chauffeur with local route expertise.\n"
            "Assistance on arrival and departure."
        )
        exclusions = (
            "Monument / museum entry tickets and camera fees.\n"
            "Optional watersports, speedboating, or adventure activities.\n"
            "Personal expenses, tips, and additional meals."
        )

    terms = (
        "Camp Fire & Boating Subject to weather Conditions.\n"
        "Playing in Sea / Pool is at Customers Own risk.\n"
        "Payment - 50% advance while confirming the Trip & rest 50% before starting the trip.\n"
        "Any damages caused by the tour members to the vehicle or to any of the properties should be paid before trip end.\n"
        "All sightseeing can be seen only according to road and traffic conditions.\n"
        "ITINERARY can be customized to customer's interest and comfort.\n"
        "Tour members are requested to co-operate with our crew to maintain timings."
    )

    contact_footer = "Rithik CA (+91 98425 33777), Anandh C (+91 94381 7131 / +91 38209 9979)"

    # Create or update Package
    pkg, created = Package.objects.update_or_create(
        package_code=code,
        defaults={
            'name': name,
            'destination': dest,
            'category': cat,
            'duration_days': days,
            'duration_nights': nights,
            'pricing_type': 'per_person',
            'base_price': b_price,
            'price_with_food': p_food,
            'price_without_food': p_nofood,
            'is_devotional': is_devotional,
            'satvik_pure_veg_meals': is_devotional,
            'senior_citizen_friendly': is_devotional,
            'hotel_star_category': 'Deluxe AC Hotel / Premium Resort' if nights > 0 else 'Same Day Excursion',
            'room_sharing_type': 'twin_sharing' if cat != 'college_iv' else '4_sharing',
            'meal_plan': 'AP' if is_devotional or cat == 'college_iv' else 'MAP',
            'has_campfire_dj': True if nights > 1 else False,
            'inclusions': inclusions,
            'exclusions': exclusions,
            'terms_and_conditions': terms,
            'contact_persons_footer': contact_footer,
            'description': desc,
            'is_active': True
        }
    )

    if created:
        created_packages_count += 1

    # Clear existing child records for clean idempotent reload
    pkg.itinerary_days.all().delete()
    pkg.vehicle_tariffs.all().delete()
    pkg.temple_slots.all().delete()

    # 1. Create Itinerary Days
    for itin in p_data.get('itinerary', []):
        day_obj = ItineraryDay.objects.create(
            package=pkg,
            day_number=itin.get('day', 1),
            title=itin.get('title', f"Day {itin.get('day', 1)} Sightseeing"),
            route_segment=itin.get('route', ''),
            activities=itin.get('activities', ''),
            morning_activity=itin.get('morning', ''),
            sightseeing_spots=itin.get('sightseeing', ''),
            evening_night_activity=itin.get('evening', ''),
            night_stay_location=itin.get('night_stay', ''),
            meals_included=itin.get('meals', 'Breakfast, Lunch, Dinner')
        )
        created_itinerary_days_count += 1

    # 2. Create 5-Tier Vehicle Tariffs
    tariffs = generate_tariffs(pkg, days, nights, b_price)
    for t in tariffs:
        t.save()
        created_tariffs_count += 1

    # 3. Create Temple Darshan Slots
    for d_slot in p_data.get('darshan_slots', []):
        TempleDarshanSlot.objects.create(
            package=pkg,
            temple_name=d_slot.get('temple_name', ''),
            deity_or_circuit=d_slot.get('deity', ''),
            darshan_type=d_slot.get('darshan_type', 'special_entry_300'),
            booked_slot_time=d_slot.get('slot_time', 'Morning Slot'),
            reporting_location=d_slot.get('location', 'Main Temple Entrance'),
            dress_code_notes=d_slot.get('dress_code', 'Strict Traditional Attire'),
            prasad_details=d_slot.get('prasad', 'Sacred Temple Prasadam'),
            senior_citizen_support=d_slot.get('senior_citizen', True)
        )
        created_darshan_slots_count += 1

print("\n" + "="*85)
print("CHENNAI TOURS & TRAVELS INGESTION SUMMARY")
print("="*85)
print(f"Total Packages Ingested:        {len(all_packages_to_import)} (All SGT-CTT-001 to SGT-CTT-{len(all_packages_to_import):03d})")
print(f"Total Itinerary Days Created:   {created_itinerary_days_count}")
print(f"Total 5-Tier Tariffs Created:   {created_tariffs_count} (5 tiers per package)")
print(f"Total Temple Darshan Slots:     {created_darshan_slots_count}")
print("Rebranding Status:              100% Siva Gayathri Tours & Travels (+91 98425 33777)")
print("="*85)
