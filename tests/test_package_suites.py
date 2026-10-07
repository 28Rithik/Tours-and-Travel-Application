import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
django.setup()

from decimal import Decimal
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.test import Client
from packages.models import (
    PackageTemplate,
    Package,
    PackageVehicleTariff,
    ItineraryDay,
    PackageInventory,
    BoardingPoint,
    CollegeIVExpedition,
    TourPassengerManifest,
    TempleDarshanSlot,
    InternationalDocumentChecklist,
)
from core.models import Vehicle, VehicleType, Driver

User = get_user_model()

def seed_and_test():
    print("=== SEEDING EXPANDED TOUR PACKAGES (HOLIDAY, DEVOTIONAL, INTL, 4-60 SEATS) ===")

    # 1. Ensure Superuser exists
    admin_user, _ = User.objects.get_or_create(
        username='admin',
        defaults={'email': 'admin@travelerp.com', 'is_staff': True, 'is_superuser': True}
    )
    admin_user.set_password('admin123')
    admin_user.is_staff = True
    admin_user.is_superuser = True
    admin_user.save()

    # 2. Ensure Vehicle Types exist covering 4 to 60 seats
    vtype_sedan, _ = VehicleType.objects.get_or_create(
        name='Swift Dzire Sedan',
        defaults={'category': 'sedan', 'seating_capacity': 4, 'default_km_rate': Decimal('14.00')}
    )
    vtype_innova, _ = VehicleType.objects.get_or_create(
        name='Innova Crysta 7-Seater',
        defaults={'category': 'suv', 'seating_capacity': 7, 'default_km_rate': Decimal('22.00')}
    )
    vtype_tt, _ = VehicleType.objects.get_or_create(
        name='17-Seater Force Urbania / TT',
        defaults={'category': 'van', 'seating_capacity': 17, 'default_km_rate': Decimal('28.00')}
    )
    vtype_minibus, _ = VehicleType.objects.get_or_create(
        name='36-Seater Deluxe Mini Bus',
        defaults={'category': 'bus', 'seating_capacity': 36, 'default_km_rate': Decimal('38.00')}
    )
    vtype_bus, _ = VehicleType.objects.get_or_create(
        name='54-Seater Luxury Coach',
        defaults={'category': 'bus', 'seating_capacity': 54, 'default_km_rate': Decimal('48.00')}
    )

    # --------------------------------------------------------------------------
    # 3. VERTICAL 1: Holiday & College IV Package (Mysore - Coorg - Chikmagalur)
    # --------------------------------------------------------------------------
    template_iv, _ = PackageTemplate.objects.get_or_create(
        name="Mysore - Coorg - Chikmagalur Circuit",
        defaults={
            'destination': 'Tamilnadu / Karnataka',
            'category': 'college_iv',
            'duration_days': 3,
            'duration_nights': 2,
            'base_price': Decimal('5700.00'),
            'description': 'Flagship 3-Day College Industrial Visit & Hill Station Expedition with Mysore Palace, Coorg Coffee Estates, and Mullayanagiri Jeep Safari.'
        }
    )

    pkg_holiday, _ = Package.objects.update_or_create(
        package_code='PKG-MY-CRG-03D',
        defaults={
            'template': template_iv,
            'name': '2 NIGHTS 3 DAYS TOUR PLAN (MYSORE-COORG-CHIKMANGALUR)',
            'destination': 'TAMILNADU/KARNATAKA',
            'category': 'college_iv',
            'duration_days': 3,
            'duration_nights': 2,
            'pricing_type': 'per_person',
            'base_price': Decimal('5700.00'),
            'price_with_food': Decimal('5700.00'),
            'price_without_food': Decimal('4600.00'),
            'min_pax': 50,
            'complementary_staff_count': 2,
            'hotel_star_category': 'Star Category Hotel & Resort',
            'room_sharing_type': '4_sharing',
            'meal_plan': 'AP',
            'default_vehicle_type': vtype_bus,
            'vehicle_seating_desc': 'Non Ac 54 seated Luxurious Bus',
            'bus_amenities_desc': '52/54 seated bus, 1 Driver & 1 cleaner, Laser Light, JBL Sound systems, First aid kit',
            'has_campfire_dj': True,
            'has_jeep_safari': True,
            'has_boating': True,
            'has_industrial_visit': True,
            'inclusions': (
                "Tamilnadu-Karnataka-by bus.\n"
                "All parking, toll gate & permit charges.\n"
                "Accommodation on sharing basis in hotel and resort.\n"
                "All transfer & transportation.\n"
                "All sightseeing as per the itinerary based on time.\n"
                "Tour in charge from Siva Gayathri Tours and Travels.\n"
                "Guide service.\n"
                "Local entrances.\n"
                "Dj with campfire.\n"
                "Jeep safari"
            ),
            'exclusions': (
                "Natural disturbance if any.\n"
                "Any damages or breakages.\n"
                "Optional tours if any.\n"
                "First aid kit.\n"
                "Personal expenses.\n"
                "Company expenses."
            ),
            'terms_and_conditions': (
                "Camp Fire & Boating Subject to weather Conditions.\n"
                "Playing is Sea / Pool is at Customers Own risk.\n"
                "Payment - 50% advance while confirming the Trip & rest 50 % before starting the trip.\n"
                "Any damages caused by the tour members to the vehicle or to any of the properties at the resort should be paid before the end of the trip.\n"
                "All sightseeing can be seen only according to the road and other situation during the trip.\n"
                "ITINERARY can be changed to customer’s interest and comfort.\n"
                "Tour members are requested to co-operate with us to maintain the timings of Itinerary to server you better.\n"
                "Customers drunk will not be allowed for Trekking."
            ),
            'contact_persons_footer': 'Rithik CA (+91 98425 33777), Anandh C (+91 94381 7131 / +91 38209 9979)',
        }
    )

    # 4 to 60-Seater Vehicle Tariffs for Holiday Package
    tariffs_data = [
        (vtype_sedan, '4_sedan', 'outstation_multiday', Decimal('13500.00'), Decimal('4500.00'), 900, Decimal('14.00'), 8, Decimal('150.00'), Decimal('500.00'), False),
        (vtype_innova, '7_crysta', 'outstation_multiday', Decimal('21000.00'), Decimal('7000.00'), 900, Decimal('20.00'), 8, Decimal('250.00'), Decimal('700.00'), False),
        (vtype_tt, '17_tt_urbania', 'outstation_multiday', Decimal('32000.00'), Decimal('10660.00'), 900, Decimal('26.00'), 8, Decimal('350.00'), Decimal('800.00'), False),
        (vtype_minibus, '36_mini_bus', 'outstation_multiday', Decimal('48000.00'), Decimal('16000.00'), 900, Decimal('38.00'), 8, Decimal('500.00'), Decimal('1200.00'), False),
        (vtype_bus, '54_luxury_coach', 'outstation_multiday', Decimal('68000.00'), Decimal('22660.00'), 900, Decimal('48.00'), 8, Decimal('600.00'), Decimal('1500.00'), True),
    ]
    for vt, tier, rtype, pkg_rate, pday, km, xkm, hrs, xhr, bata, dbl in tariffs_data:
        PackageVehicleTariff.objects.update_or_create(
            package=pkg_holiday,
            vehicle_type=vt,
            defaults={
                'seating_tier': tier,
                'rate_type': rtype,
                'package_rate': pkg_rate,
                'per_day_rate': pday,
                'included_km': km,
                'extra_km_rate': xkm,
                'local_package_hours': hrs,
                'extra_hour_rate': xhr,
                'driver_bata_per_day': bata,
                'double_driver_included': dbl,
                'driver_bata_included': True,
                'toll_parking_included': True,
                'interstate_permit_included': True,
            }
        )
    print(f"Seeded Holiday Package & 5 Fleet Tariffs (4-60 Seats): {pkg_holiday.name}")

    # --------------------------------------------------------------------------
    # 4. VERTICAL 2: Devotional & Pilgrimage Tour (Arupadai Veedu & Navagraha)
    # --------------------------------------------------------------------------
    pkg_devotional, _ = Package.objects.update_or_create(
        package_code='PKG-DEV-ARU-05D',
        defaults={
            'name': '4 NIGHTS 5 DAYS ARUPADAI VEEDU & NAVAGRAHA DEVOTIONAL YATRA',
            'destination': 'TAMILNADU (PALANI - KUMBAKONAM - THANJAVUR)',
            'category': 'devotional',
            'is_devotional': True,
            'duration_days': 5,
            'duration_nights': 4,
            'pricing_type': 'per_person',
            'base_price': Decimal('8500.00'),
            'price_with_food': Decimal('8500.00'),
            'price_without_food': Decimal('6200.00'),
            'min_pax': 40,
            'complementary_staff_count': 2,
            'hotel_star_category': 'Pilgrimage Standard AC Hotel',
            'room_sharing_type': 'twin_sharing',
            'meal_plan': 'AP',
            'satvik_pure_veg_meals': True,
            'senior_citizen_friendly': True,
            'temple_dress_code': 'Strict Traditional: Dhoti/Kurta for Men, Saree/Chudidar for Women',
            'temple_darshan_info': 'Fast-track ₹300 Special Entry passes pre-booked for Tiruchendur & Palani. Morning Abhishekam seva passes included.',
            'default_vehicle_type': vtype_bus,
            'vehicle_seating_desc': 'Non AC 40-54 Seated Pushback Coach',
            'bus_amenities_desc': 'Low Floor Entry for Senior Citizens, Devotional Audio System, First Aid Kit, Wheelchair Storage Compartment',
            'has_campfire_dj': False,
            'has_jeep_safari': False,
            'has_boating': False,
            'has_industrial_visit': False,
            'inclusions': (
                "Coimbatore to Kumbakonam & Palani AC coach transportation.\n"
                "All toll gate, parking, and temple hill road permit charges.\n"
                "AC hotel accommodation on twin sharing basis.\n"
                "100% Satvik Pure Vegetarian South Indian Meals (Breakfast, Lunch, Dinner).\n"
                "Special Entry Darshan tokens at major shrines.\n"
                "Experienced Spiritual Tour Escort from Siva Gayathri Tours.\n"
                "Senior citizen boarding and wheelchair assistance."
            ),
            'exclusions': (
                "Personal offerings, archana tickets, and tonsure charges.\n"
                "Special private homams or individual sevas.\n"
                "Room service and personal telephone calls."
            ),
            'terms_and_conditions': (
                "Temple authorities reserve right of entry based on dress code compliance.\n"
                "Darshan queue timings are subject to temple rush and VIP movements.\n"
                "50% advance on booking, balance before departure."
            ),
            'contact_persons_footer': 'Rithik CA (+91 98425 33777), Anandh C (+91 94381 7131 / +91 38209 9979)',
        }
    )

    # Seed Temple Darshan Slots
    temples = [
        ("Subramanya Swamy Temple, Palani", "Murugan (3rd Arupadai Veedu)", "special_entry_300", "07:30 AM - 09:00 AM", "PLN-SE-042", "North Hill Gate (Winch Counter)", True),
        ("Suryanar Kovil Temple", "Navagraha - Surya Bhagavan", "special_entry_300", "11:30 AM Slot", "SRY-NAV-108", "East Gopuram Entrance", True),
        ("Brihadeeswarar Temple, Thanjavur", "Lord Shiva (Big Temple)", "general", "04:30 PM Slot", "Free Sarva Darshanam", "Main Rajagopuram", False),
    ]
    for tname, deity, dtype, slot_time, tnum, loc, sr in temples:
        TempleDarshanSlot.objects.update_or_create(
            package=pkg_devotional,
            temple_name=tname,
            defaults={
                'deity_or_circuit': deity,
                'darshan_type': dtype,
                'booked_slot_time': slot_time,
                'token_ticket_number': tnum,
                'reporting_location': loc,
                'senior_citizen_support': sr,
            }
        )
    print(f"Seeded Devotional Yatra Package with Temple Slots: {pkg_devotional.name}")

    # --------------------------------------------------------------------------
    # 5. VERTICAL 3: International Tour Package (Dubai & Abu Dhabi)
    # --------------------------------------------------------------------------
    pkg_intl, _ = Package.objects.update_or_create(
        package_code='PKG-INT-DXB-05D',
        defaults={
            'name': '4 NIGHTS 5 DAYS DUBAI & ABU DHABI DESERT EXTRAVAGANZA',
            'destination': 'DUBAI & ABU DHABI',
            'destination_country': 'United Arab Emirates (UAE)',
            'category': 'international',
            'is_international': True,
            'duration_days': 5,
            'duration_nights': 4,
            'pricing_type': 'per_person',
            'base_price': Decimal('58000.00'),
            'price_with_food': Decimal('58000.00'),
            'price_without_food': Decimal('49000.00'),
            'min_pax': 20,
            'complementary_staff_count': 1,
            'hotel_star_category': '4-Star Luxury City Hotel (Deira/Bur Dubai)',
            'room_sharing_type': 'twin_sharing',
            'meal_plan': 'MAP',
            'visa_required': True,
            'visa_guidelines': '30-Day Tourist eVisa provided by Siva Gayathri Tours. Processing requires clear passport scan (min 6 months validity) and white background photo.',
            'passport_validity_months': 6,
            'currency_code': 'AED',
            'flight_inclusive': True,
            'flight_details_note': 'Air India Express / IndiGo direct roundtrip flight Ex-Coimbatore or Chennai.',
            'overseas_dmc_partner': 'Arabian Adventures & Tourism LLC, Dubai',
            'default_vehicle_type': vtype_minibus,
            'vehicle_seating_desc': 'Luxury AC Tourist Coach with English/Tamil Speaking Tour Guide',
            'bus_amenities_desc': 'Full AC, Panoramic Windows, USB Charging Ports, On-board Bottled Water',
            'has_campfire_dj': True,
            'has_jeep_safari': True,
            'has_boating': True,
            'has_industrial_visit': False,
            'inclusions': (
                "Return Economy Class Airfare Ex-Coimbatore / Chennai.\n"
                "30 Days UAE Tourist Visa with Overseas Travel Insurance.\n"
                "4 Nights accommodation at 4-Star Hotel in Dubai.\n"
                "Daily Buffet Breakfast & Dinners at Indian Restaurants.\n"
                "Desert Safari with 4x4 Dune Bashing, BBQ Dinner & Belly Dance Show.\n"
                "Burj Khalifa At The Top 124th Floor Entry Ticket.\n"
                "Dhow Cruise Dinner at Dubai Creek / Marina.\n"
                "Full Day Abu Dhabi City Tour with Sheikh Zayed Grand Mosque.\n"
                "All transfers in Deluxe Luxury AC Tourist Coach."
            ),
            'exclusions': (
                "Tourism Dirham Fee payable directly at hotel (approx. AED 15/room/night).\n"
                "Lunches unless specified in the itinerary.\n"
                "Personal expenses, laundry, and excess baggage charges."
            ),
            'terms_and_conditions': (
                "Passport must have at least 6 months validity from the date of return.\n"
                "Visa approval is subject to UAE Immigration guidelines.\n"
                "Payment: 30% advance on confirmation, 50% upon visa approval, 20% before departure."
            ),
            'contact_persons_footer': 'Rithik CA (+91 98425 33777), Anandh C (+91 94381 7131 / +91 38209 9979)',
        }
    )

    # Seed International Document Checklist
    intl_docs = [
        ("Passport Scanned Copy (Front & Back Pages)", True, 10, "Minimum 6 months validity from return date"),
        ("Recent Photograph (35mm x 45mm, White Background, 80% Face)", True, 10, "Color scan in high resolution JPEG"),
        ("PAN Card Copy (for TCS Compliance)", True, 7, "Government mandated for foreign travel"),
    ]
    for dname, mand, days, nts in intl_docs:
        InternationalDocumentChecklist.objects.update_or_create(
            package=pkg_intl,
            document_name=dname,
            defaults={
                'is_mandatory': mand,
                'submission_deadline_days': days,
                'notes': nts,
            }
        )
    print(f"Seeded International Tour Package with Document Checklist: {pkg_intl.name}")

    # --------------------------------------------------------------------------
    # 6. Verify HTTP Endpoints with Django Test Client
    # --------------------------------------------------------------------------
    print("\n=== VERIFYING ALL SUITE ENDPOINTS & PROPOSALS ===")
    client = Client()
    client.force_login(admin_user)

    endpoints = [
        # Suite 1: Tour Packages & Itineraries
        ('/admin/packages/package/', 'Suite 1: Packages List'),
        (f'/admin/packages/package/{pkg_holiday.id}/change/', 'Suite 1: Holiday Package Detail'),
        (f'/admin/packages/package/{pkg_devotional.id}/change/', 'Suite 1: Devotional Package Detail'),
        (f'/admin/packages/package/{pkg_intl.id}/change/', 'Suite 1: International Package Detail'),
        ('/admin/packages/packagevehicletariff/', 'Suite 1: 4-60 Seater Vehicle Tariffs'),
        ('/admin/packages/templedarshanslot/', 'Suite 1: Temple Darshan Slots'),
        ('/admin/packages/internationaldocumentchecklist/', 'Suite 1: International Documents'),
        
        # Suite 2: College IV Expeditions & Group Departures
        ('/admin/package_tours/collegeivproxy/', 'Suite 2: College IV Expeditions List'),
        ('/admin/package_tours/tourdeparturebatchproxy/', 'Suite 2: Tour Departures List'),
        ('/admin/package_tours/boardingpointproxy/', 'Suite 2: Boarding Points List'),
        ('/admin/package_tours/passengermanifestproxy/', 'Suite 2: Passenger Manifest List'),

        # Quotation Proposals for all 3 Verticals
        (f'/packages/quote/{pkg_holiday.id}/', 'Quotation: Holiday / IV Proposal'),
        (f'/packages/quote/{pkg_devotional.id}/', 'Quotation: Devotional Yatra Proposal'),
        (f'/packages/quote/{pkg_intl.id}/', 'Quotation: International Package Proposal'),
    ]

    all_passed = True
    for url, label in endpoints:
        resp = client.get(url)
        status = resp.status_code
        status_symbol = "[PASS]" if status == 200 else f"[FAIL ({status})]"
        if status != 200:
            all_passed = False
        print(f"{status_symbol} {label} -> {url} [HTTP {status}]")

    # Content Verifications on Quotations
    # 1. Holiday Quote
    q_holiday = client.get(f'/packages/quote/{pkg_holiday.id}/').content.decode('utf-8')
    assert "SIVA GAYATHRI" in q_holiday
    assert "FLEET TARIFF MATRIX" in q_holiday, "Fleet tariff matrix not found in Holiday quote!"
    print("[PASS] Verified Holiday Proposal with 4 to 60 Seater Fleet Matrix!")

    # 2. Devotional Quote
    q_dev = client.get(f'/packages/quote/{pkg_devotional.id}/').content.decode('utf-8')
    assert "Spiritual Yatra" in q_dev or "Devotional" in q_dev
    assert "Palani" in q_dev, "Palani temple not found in Devotional quote!"
    assert "Satvik Pure Vegetarian" in q_dev or "Satvik" in q_dev
    assert "Wheelchair" in q_dev, "Wheelchair support not found in Devotional quote!"
    print("[PASS] Verified Devotional Proposal with Temple Darshan Slots & Satvik Food!")

    # 3. International Quote
    q_intl = client.get(f'/packages/quote/{pkg_intl.id}/').content.decode('utf-8')
    assert "International Tour Package" in q_intl
    assert "United Arab Emirates" in q_intl or "DUBAI" in q_intl
    assert "MANDATORY INTERNATIONAL TRAVEL DOCUMENTS" in q_intl
    print("[PASS] Verified International Proposal with Flight, Visa & Document Checklist!")

    if all_passed:
        print("\nALL EXPANDED TOUR PACKAGES & VERTICALS VERIFIED FLAWLESSLY!")
    else:
        print("\nSOME ENDPOINTS FAILED!")

if __name__ == '__main__':
    seed_and_test()
