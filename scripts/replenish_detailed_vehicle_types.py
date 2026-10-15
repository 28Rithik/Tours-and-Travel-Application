"""
Comprehensive Vehicle Type Reset and Replenishment Script.
Cleans up legacy/duplicate vehicle types while safely preserving Package Tariffs & Vehicle integrity.
Creates a complete, detailed format for all 29 standard Indian commercial fleet vehicle types:
- Toyota Fortuner 4x4 Luxury SUV
- Toyota Innova Crysta 2.4D
- Toyota Innova (Classic 2.5D)
- Toyota Innova Hycross Hybrid
- Maruti Suzuki Swift Dzire Tour S
- Toyota Etios GD Platinum
- Hyundai Aura Prime
- Honda City Executive Sedan
- Maruti Suzuki Ertiga Smart Hybrid
- Kia Carens Luxury Plus
- Mahindra Scorpio-N 4x4
- Force Urbania Luxury Van (10S, 13S, 17S)
- Force Tempo Traveller (12S, 17S, 20S, 26S, 9S Maharaja)
- BharatBenz Glider, Ashok Leyland Viking, Tata Starbus Ultra
- Volvo B11R 9600 Multi-Axle, Volvo 9600 Sleeper, Scania Metrolink HD
- 54-Seater Deluxe Pushback Coach
- Electric Mobility (Tata Tigor EV, BYD E6, Olectra Electric Bus)
"""

import os
import sys
from decimal import Decimal
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
django.setup()

from core.models import VehicleType, VehicleCategory, Vehicle
from packages.models import Package, PackageVehicleTariff
from operations.models import Booking

DETAILED_VEHICLE_CATALOG = [
    # ──────────────────────────────────────────────────────────────────────────
    # 1. PREMIUM MUV & SUV (suv_muv)
    # ──────────────────────────────────────────────────────────────────────────
    {
        'id_hint': 1,
        'name': 'Toyota Innova Crysta 2.4D',
        'cat_code': 'suv_muv',
        'description': 'The undisputed gold standard of South Indian long-haul tourism and highway comfort. 2.4L Diesel engine, ultra-smooth suspension, dual blower AC, and plush captain seats. Ideal for family getaways, hill stations (Ooty, Kodaikanal, Valparai, Munnar), and corporate executive transit.',
        'default_day_rate': Decimal('4200.00'),
        'default_km_rate': Decimal('18.00'),
        'minimum_km_per_day': 250,
        'extra_km_rate': Decimal('18.00'),
        'extra_hour_rate': Decimal('250.00'),
        'driver_bata': Decimal('500.00'),
        'night_halt_charge': Decimal('600.00'),
        'seating_capacity': 7,
        'luggage_capacity': '4 Large Suitcases + 3 Handbags',
        'fuel_type': 'diesel',
        'expected_mileage_kmpl': Decimal('13.50'),
        'toll_class': 'car',
        'has_ac': True,
        'is_luxury': True,
        'transmission_type': 'manual',
        'is_wheelchair_accessible': False,
        'amenities': 'Dual AC with Rear Blower, Pushback Leather Captain Seats, USB Fast Charging Ports on All Rows, Bluetooth Audio, Reading Lamps, Ambient Cabin Lighting, First Aid Kit, Emergency Glass Breaker, AIS-140 GPS Speed Governor (80 km/h)',
    },
    {
        'id_hint': 2,
        'name': 'Toyota Innova (Classic 2.5D)',
        'cat_code': 'suv_muv',
        'description': 'Legendary proven workhorse for rugged rural tours, pilgrimage circuits, and industrial site shuttles. Robust D-4D diesel powertrain, high ground clearance, and reliable 7/8 seating layout.',
        'default_day_rate': Decimal('3600.00'),
        'default_km_rate': Decimal('16.00'),
        'minimum_km_per_day': 250,
        'extra_km_rate': Decimal('16.00'),
        'extra_hour_rate': Decimal('200.00'),
        'driver_bata': Decimal('450.00'),
        'night_halt_charge': Decimal('500.00'),
        'seating_capacity': 7,
        'luggage_capacity': '4 Large Bags',
        'fuel_type': 'diesel',
        'expected_mileage_kmpl': Decimal('13.00'),
        'toll_class': 'car',
        'has_ac': True,
        'is_luxury': False,
        'transmission_type': 'manual',
        'is_wheelchair_accessible': False,
        'amenities': 'Dual Zone AC, Reclining Fabric Seats, USB Phone Charger, FM/Aux Audio, Spacious Legroom, First Aid Kit',
    },
    {
        'name': 'Toyota Innova Hycross Hybrid',
        'cat_code': 'suv_muv',
        'description': 'Ultra-luxury flagship MPV with advanced self-charging strong hybrid electric powertrain. Features powered ottoman lounge captain seats, panoramic roof, whisper-quiet cabin, and premium VIP ride quality for high-net-worth clients, consulate delegations, and luxury weddings.',
        'default_day_rate': Decimal('5500.00'),
        'default_km_rate': Decimal('22.00'),
        'minimum_km_per_day': 250,
        'extra_km_rate': Decimal('22.00'),
        'extra_hour_rate': Decimal('350.00'),
        'driver_bata': Decimal('600.00'),
        'night_halt_charge': Decimal('700.00'),
        'seating_capacity': 7,
        'luggage_capacity': '4 Large Suitcases + 2 Cabin Bags',
        'fuel_type': 'petrol',
        'expected_mileage_kmpl': Decimal('18.50'),
        'toll_class': 'car',
        'has_ac': True,
        'is_luxury': True,
        'transmission_type': 'automatic',
        'is_wheelchair_accessible': False,
        'amenities': 'Tri-Zone Climate Control with Pollen Filter, Powered Ottoman Reclining Lounge Seats, Panoramic Sunroof, JBL 9-Speaker Audio, Type-C Fast Chargers, Retractable Sunshades, Air Purifier, First Aid Box, VIP Chauffeur Amenities',
    },
    {
        'id_hint': 20,
        'name': 'Toyota Fortuner 4x4 Luxury SUV',
        'cat_code': 'suv_muv',
        'description': 'Premium full-size 4x4 heavy-duty SUV for VIP executive protocol, dignitary escorts, high-profile weddings, and rugged terrain expeditions across the Western Ghats and wildlife sanctuaries (Mudumalai, Topslip, Valparai).',
        'default_day_rate': Decimal('7500.00'),
        'default_km_rate': Decimal('28.00'),
        'minimum_km_per_day': 250,
        'extra_km_rate': Decimal('28.00'),
        'extra_hour_rate': Decimal('500.00'),
        'driver_bata': Decimal('750.00'),
        'night_halt_charge': Decimal('800.00'),
        'seating_capacity': 7,
        'luggage_capacity': '4 Large Suitcases',
        'fuel_type': 'diesel',
        'expected_mileage_kmpl': Decimal('10.50'),
        'toll_class': 'car',
        'has_ac': True,
        'is_luxury': True,
        'transmission_type': 'automatic',
        'is_wheelchair_accessible': False,
        'amenities': 'Dual-Zone Auto Climate Control, Ventilated Front Seats, 4x4 Terrain Management, Premium Leather Upholstery, Touchscreen Navigation, High Ground Clearance (225mm), Emergency SOS Beacon, Bottled Water Console',
    },
    {
        'id_hint': 5,
        'name': 'Maruti Suzuki Ertiga Smart Hybrid',
        'cat_code': 'suv_muv',
        'description': 'Highly fuel-efficient and budget-friendly 6+1 MUV for small family holiday tours, outstation weekend temple trips, and daily airport transfers.',
        'default_day_rate': Decimal('3200.00'),
        'default_km_rate': Decimal('14.00'),
        'minimum_km_per_day': 250,
        'extra_km_rate': Decimal('14.00'),
        'extra_hour_rate': Decimal('180.00'),
        'driver_bata': Decimal('400.00'),
        'night_halt_charge': Decimal('450.00'),
        'seating_capacity': 6,
        'luggage_capacity': '2 Medium Trolleys + 2 Handbags',
        'fuel_type': 'cng',
        'expected_mileage_kmpl': Decimal('18.00'),
        'toll_class': 'car',
        'has_ac': True,
        'is_luxury': False,
        'transmission_type': 'manual',
        'is_wheelchair_accessible': False,
        'amenities': 'Roof-Mounted Rear AC Vents, Sliding & Reclining 2nd Row, USB Charging, Audio System, Compact City Agility',
    },
    {
        'name': 'Kia Carens Luxury Plus',
        'cat_code': 'suv_muv',
        'description': 'Contemporary 6/7 seater recreational MPV featuring ventilated seats, sky-view sunroof, and refined diesel smoothness. Very popular for tech executive commutes and Coimbatore-Bangalore corridor trips.',
        'default_day_rate': Decimal('3800.00'),
        'default_km_rate': Decimal('16.50'),
        'minimum_km_per_day': 250,
        'extra_km_rate': Decimal('16.50'),
        'extra_hour_rate': Decimal('220.00'),
        'driver_bata': Decimal('450.00'),
        'night_halt_charge': Decimal('550.00'),
        'seating_capacity': 6,
        'luggage_capacity': '3 Medium Suitcases',
        'fuel_type': 'diesel',
        'expected_mileage_kmpl': Decimal('16.00'),
        'toll_class': 'car',
        'has_ac': True,
        'is_luxury': True,
        'transmission_type': 'automatic',
        'is_wheelchair_accessible': False,
        'amenities': 'Automatic Climate Control, One-Touch Electric Tumble Seats, BOSE Sound System, Air Purifier, Type-C Fast Chargers on all rows',
    },
    {
        'name': 'Mahindra Scorpio-N 4x4',
        'cat_code': 'suv_muv',
        'description': 'The Big Daddy of SUVs with 4XPLOR terrain modes, commanding seating position, and rugged body-on-frame chassis for high-altitude hill stations and plantation estate visits.',
        'default_day_rate': Decimal('4500.00'),
        'default_km_rate': Decimal('19.00'),
        'minimum_km_per_day': 250,
        'extra_km_rate': Decimal('19.00'),
        'extra_hour_rate': Decimal('280.00'),
        'driver_bata': Decimal('500.00'),
        'night_halt_charge': Decimal('600.00'),
        'seating_capacity': 7,
        'luggage_capacity': '3 Large Suitcases',
        'fuel_type': 'diesel',
        'expected_mileage_kmpl': Decimal('12.00'),
        'toll_class': 'car',
        'has_ac': True,
        'is_luxury': True,
        'transmission_type': 'manual',
        'is_wheelchair_accessible': False,
        'amenities': 'Dual Zone Climate Control, Sony 3D Sound Stage, 4XPLOR Mud/Snow Modes, Leatherette Seats, Roof Rails',
    },

    # ──────────────────────────────────────────────────────────────────────────
    # 2. SEDAN & COMPACT (sedan)
    # ──────────────────────────────────────────────────────────────────────────
    {
        'id_hint': 3,
        'name': 'Maruti Suzuki Swift Dzire Tour S',
        'cat_code': 'sedan',
        'description': 'India premier commercial taxi sedan. Exceptional fuel efficiency, quiet motor, and adequate 378L boot space for 2-3 outstation bags. Prime choice for point-to-point transfers and couple tours.',
        'default_day_rate': Decimal('2400.00'),
        'default_km_rate': Decimal('12.00'),
        'minimum_km_per_day': 250,
        'extra_km_rate': Decimal('12.00'),
        'extra_hour_rate': Decimal('150.00'),
        'driver_bata': Decimal('350.00'),
        'night_halt_charge': Decimal('400.00'),
        'seating_capacity': 4,
        'luggage_capacity': '2 Large Bags + 2 Handbags',
        'fuel_type': 'cng',
        'expected_mileage_kmpl': Decimal('22.50'),
        'toll_class': 'car',
        'has_ac': True,
        'is_luxury': False,
        'transmission_type': 'manual',
        'is_wheelchair_accessible': False,
        'amenities': 'AC with Heater, Rear Armrest, Mobile Charging Socket, Bluetooth Audio, Speed Governor (80 km/h), Clean Sanitized Interior',
    },
    {
        'name': 'Toyota Etios GD Platinum',
        'cat_code': 'sedan',
        'description': 'Renowned for its class-leading 592-liter boot capacity and flat rear floor with exceptional legroom. The outstation commercial workhorse of choice across Tamil Nadu corridors.',
        'default_day_rate': Decimal('2600.00'),
        'default_km_rate': Decimal('13.00'),
        'minimum_km_per_day': 250,
        'extra_km_rate': Decimal('13.00'),
        'extra_hour_rate': Decimal('160.00'),
        'driver_bata': Decimal('350.00'),
        'night_halt_charge': Decimal('400.00'),
        'seating_capacity': 4,
        'luggage_capacity': '3 Large Suitcases + 2 Duffles',
        'fuel_type': 'diesel',
        'expected_mileage_kmpl': Decimal('20.00'),
        'toll_class': 'car',
        'has_ac': True,
        'is_luxury': False,
        'transmission_type': 'manual',
        'is_wheelchair_accessible': False,
        'amenities': 'High-Capacity AC, Flat Floor Comfort, Massive 592L Boot, Power Windows, Central Locking, Dual Airbags',
    },
    {
        'name': 'Hyundai Aura Prime',
        'cat_code': 'sedan',
        'description': 'Modern compact sedan with refined motor, sleek styling, rear AC vents, and comfortable cushioning for corporate airport transfers and city day tours.',
        'default_day_rate': Decimal('2500.00'),
        'default_km_rate': Decimal('12.50'),
        'minimum_km_per_day': 250,
        'extra_km_rate': Decimal('12.50'),
        'extra_hour_rate': Decimal('150.00'),
        'driver_bata': Decimal('350.00'),
        'night_halt_charge': Decimal('400.00'),
        'seating_capacity': 4,
        'luggage_capacity': '2 Medium Trolleys + 2 Bags',
        'fuel_type': 'petrol',
        'expected_mileage_kmpl': Decimal('20.50'),
        'toll_class': 'car',
        'has_ac': True,
        'is_luxury': False,
        'transmission_type': 'manual',
        'is_wheelchair_accessible': False,
        'amenities': 'Rear AC Vents, USB Fast Charger, Touchscreen Infotainment, Steering Controls, ISOFIX Child Seat Anchors',
    },
    {
        'name': 'Honda City Executive Sedan',
        'cat_code': 'sedan',
        'description': 'Premium mid-size luxury sedan for corporate C-suite executives, hotel VIP pick-ups, and luxury intercity business trips between Coimbatore, Hosur, and Chennai.',
        'default_day_rate': Decimal('3500.00'),
        'default_km_rate': Decimal('16.00'),
        'minimum_km_per_day': 250,
        'extra_km_rate': Decimal('16.00'),
        'extra_hour_rate': Decimal('250.00'),
        'driver_bata': Decimal('450.00'),
        'night_halt_charge': Decimal('550.00'),
        'seating_capacity': 4,
        'luggage_capacity': '3 Large Suitcases',
        'fuel_type': 'petrol',
        'expected_mileage_kmpl': Decimal('16.50'),
        'toll_class': 'car',
        'has_ac': True,
        'is_luxury': True,
        'transmission_type': 'automatic',
        'is_wheelchair_accessible': False,
        'amenities': 'Full Leather Upholstery, Sunroof, Automatic Climate Control, Rear Sunshade, Premium 8-Speaker Audio, Whisper-Quiet Highway Cruise',
    },

    # ──────────────────────────────────────────────────────────────────────────
    # 3. LUXURY VAN & MINI COACH (mini_coach)
    # ──────────────────────────────────────────────────────────────────────────
    {
        'name': 'Force Urbania Luxury Van (10-Seater Executive)',
        'cat_code': 'mini_coach',
        'description': 'Next-generation European-styled monocoque luxury van. Independent front suspension, standing headroom (6.5 ft), individual reclining seats, and individual AC vents for executive delegations and high-end luxury group tours.',
        'default_day_rate': Decimal('6000.00'),
        'default_km_rate': Decimal('24.00'),
        'minimum_km_per_day': 300,
        'extra_km_rate': Decimal('24.00'),
        'extra_hour_rate': Decimal('350.00'),
        'driver_bata': Decimal('600.00'),
        'night_halt_charge': Decimal('700.00'),
        'seating_capacity': 10,
        'luggage_capacity': '8 Large Suitcases',
        'fuel_type': 'diesel',
        'expected_mileage_kmpl': Decimal('11.00'),
        'toll_class': 'lcv',
        'has_ac': True,
        'is_luxury': True,
        'transmission_type': 'manual',
        'is_wheelchair_accessible': False,
        'amenities': 'Monocoque European Body, Independent Front Suspension, Individual AC Louvers, USB Ports at Every Seat, LED Reading Lamps, Panoramic Sealed Windows, Reclining Bucket Seats',
    },
    {
        'name': 'Force Urbania Luxury Van (13-Seater Medium)',
        'cat_code': 'mini_coach',
        'description': 'Optimal mid-size luxury commuter with panoramic side windows, German-engineered FM 2.6 CR ED diesel engine, and cavernous rear luggage hold for 12-13 passenger groups.',
        'default_day_rate': Decimal('6800.00'),
        'default_km_rate': Decimal('26.00'),
        'minimum_km_per_day': 300,
        'extra_km_rate': Decimal('26.00'),
        'extra_hour_rate': Decimal('400.00'),
        'driver_bata': Decimal('650.00'),
        'night_halt_charge': Decimal('750.00'),
        'seating_capacity': 13,
        'luggage_capacity': '10 Large Trolley Bags',
        'fuel_type': 'diesel',
        'expected_mileage_kmpl': Decimal('10.50'),
        'toll_class': 'lcv',
        'has_ac': True,
        'is_luxury': True,
        'transmission_type': 'manual',
        'is_wheelchair_accessible': False,
        'amenities': 'Individual AC Vents, Plush Reclining Armchair Seats, Large Under-Floor Luggage Boot, Multi-Speaker Audio, Dual Airbags, ABS with EBD',
    },
    {
        'id_hint': 12,
        'name': 'Force Urbania Luxury Van (17-Seater Long Wheelbase)',
        'cat_code': 'mini_coach',
        'description': 'Flagship long-wheelbase luxury tourer. Full standing height interior, wide center gangway, individual high-comfort recliners, and aircraft-style overhead parcel racks.',
        'default_day_rate': Decimal('7800.00'),
        'default_km_rate': Decimal('28.00'),
        'minimum_km_per_day': 300,
        'extra_km_rate': Decimal('28.00'),
        'extra_hour_rate': Decimal('450.00'),
        'driver_bata': Decimal('700.00'),
        'night_halt_charge': Decimal('800.00'),
        'seating_capacity': 17,
        'luggage_capacity': '14 Large Bags',
        'fuel_type': 'diesel',
        'expected_mileage_kmpl': Decimal('9.50'),
        'toll_class': 'lcv',
        'has_ac': True,
        'is_luxury': True,
        'transmission_type': 'manual',
        'is_wheelchair_accessible': False,
        'amenities': 'Dual Air Conditioning (Front & Roof), Individual USB Fast Charging, LED Mood Lighting, Reclining Velvet Seats, Music System with Mic for Tour Guide, Fire Extinguisher, Emergency Exit',
    },
    {
        'id_hint': 4,
        'name': 'Force Tempo Traveller (12-Seater Standard AC)',
        'cat_code': 'mini_coach',
        'description': 'The standard benchmark for South India group tours, Sabarimala / Palani pilgrimage circuits, and industrial factory visit delegations.',
        'default_day_rate': Decimal('4800.00'),
        'default_km_rate': Decimal('20.00'),
        'minimum_km_per_day': 300,
        'extra_km_rate': Decimal('20.00'),
        'extra_hour_rate': Decimal('300.00'),
        'driver_bata': Decimal('550.00'),
        'night_halt_charge': Decimal('600.00'),
        'seating_capacity': 12,
        'luggage_capacity': '8 Trolley Bags',
        'fuel_type': 'diesel',
        'expected_mileage_kmpl': Decimal('11.50'),
        'toll_class': 'lcv',
        'has_ac': True,
        'is_luxury': False,
        'transmission_type': 'manual',
        'is_wheelchair_accessible': False,
        'amenities': 'Roof-Mounted AC, Pushback Seats (2x1 Layout), Rear Luggage Compartment, Music System, Mic Facility, Clean Curtains',
    },
    {
        'name': 'Force Tempo Traveller (17-Seater Deluxe AC)',
        'cat_code': 'mini_coach',
        'description': 'High-capacity 17-seater Tempo Traveller configured in 2x1 layout for wedding guest shuttles, college faculty delegations, and temple circuits (Trichy-Thanjavur-Madurai).',
        'default_day_rate': Decimal('5800.00'),
        'default_km_rate': Decimal('23.00'),
        'minimum_km_per_day': 300,
        'extra_km_rate': Decimal('23.00'),
        'extra_hour_rate': Decimal('350.00'),
        'driver_bata': Decimal('600.00'),
        'night_halt_charge': Decimal('700.00'),
        'seating_capacity': 17,
        'luggage_capacity': '12 Large Bags',
        'fuel_type': 'diesel',
        'expected_mileage_kmpl': Decimal('10.50'),
        'toll_class': 'lcv',
        'has_ac': True,
        'is_luxury': False,
        'transmission_type': 'manual',
        'is_wheelchair_accessible': False,
        'amenities': '2x1 Pushback Seats, Heavy-Duty Air Conditioning, LED TV with PA System, Overhead Luggage Racks, First Aid Kit',
    },
    {
        'name': 'Force Tempo Traveller (20-Seater Super Deluxe AC)',
        'cat_code': 'mini_coach',
        'description': 'Extended chassis 20-seater for large corporate department outings and multi-family tours across South India.',
        'default_day_rate': Decimal('6600.00'),
        'default_km_rate': Decimal('25.00'),
        'minimum_km_per_day': 300,
        'extra_km_rate': Decimal('25.00'),
        'extra_hour_rate': Decimal('400.00'),
        'driver_bata': Decimal('650.00'),
        'night_halt_charge': Decimal('750.00'),
        'seating_capacity': 20,
        'luggage_capacity': '14 Bags',
        'fuel_type': 'diesel',
        'expected_mileage_kmpl': Decimal('9.80'),
        'toll_class': 'lcv',
        'has_ac': True,
        'is_luxury': False,
        'transmission_type': 'manual',
        'is_wheelchair_accessible': False,
        'amenities': 'Dual High-Tonnage AC, High-Back Pushback Seats, LED Screen, Audio Amplifier, Emergency Hammers',
    },
    {
        'id_hint': 7,
        'name': 'Force Tempo Traveller (26-Seater Mini Bus)',
        'cat_code': 'mini_coach',
        'description': '26-seater midi-coach variant bridging the gap between Tempo Travellers and heavy buses. Perfect for textile mill staff transport in Tirupur/Erode and corporate SEZ shuttles in Hosur.',
        'default_day_rate': Decimal('7500.00'),
        'default_km_rate': Decimal('28.00'),
        'minimum_km_per_day': 300,
        'extra_km_rate': Decimal('28.00'),
        'extra_hour_rate': Decimal('450.00'),
        'driver_bata': Decimal('700.00'),
        'night_halt_charge': Decimal('800.00'),
        'seating_capacity': 26,
        'luggage_capacity': '16 Bags',
        'fuel_type': 'diesel',
        'expected_mileage_kmpl': Decimal('8.50'),
        'toll_class': 'lcv',
        'has_ac': True,
        'is_luxury': False,
        'transmission_type': 'manual',
        'is_wheelchair_accessible': False,
        'amenities': '2x2 Seating, Dual AC Units, Wide Gangway, Overhead Storage, PA Announcement Mic, Speed Limiter (80 km/h)',
    },
    {
        'name': 'Force Maharaja Tempo Traveller (9-Seater Luxury Recliner)',
        'cat_code': 'mini_coach',
        'description': 'VIP Ultra-Luxury conversion with 1x1 Maharaja diamond-quilted electric recliner seats, chemical bio-washroom on board, 32-inch Smart TV, and minibar console for celebrity travel, bridal parties, and VIP spiritual tours.',
        'default_day_rate': Decimal('9500.00'),
        'default_km_rate': Decimal('35.00'),
        'minimum_km_per_day': 300,
        'extra_km_rate': Decimal('35.00'),
        'extra_hour_rate': Decimal('600.00'),
        'driver_bata': Decimal('800.00'),
        'night_halt_charge': Decimal('1000.00'),
        'seating_capacity': 9,
        'luggage_capacity': '8 Large Suitcases',
        'fuel_type': 'diesel',
        'expected_mileage_kmpl': Decimal('10.00'),
        'toll_class': 'lcv',
        'has_ac': True,
        'is_luxury': True,
        'transmission_type': 'manual',
        'is_wheelchair_accessible': False,
        'amenities': '1x1 Electric Maharaja Recliners with Calf Support, Onboard Chemical Bio-Toilet, 32" Android Smart TV, Wi-Fi Hotspot, Refrigerator / Chiller Box, Ambient Starlight Ceiling, Wooden Flooring',
    },

    # ──────────────────────────────────────────────────────────────────────────
    # 4. INTERCITY LUXURY COACH / BUS (luxury_coach)
    # ──────────────────────────────────────────────────────────────────────────
    {
        'id_hint': 13,
        'name': 'BharatBenz Glider AC Luxury Coach (36-Seater Semi-Sleeper)',
        'cat_code': 'luxury_coach',
        'description': 'Premium 36-seater air-suspension coach powered by Mercedes-derived OM 926 engine. Renowned for zero fatigue, smooth gliding ride over highway joints, and high thermal insulation.',
        'default_day_rate': Decimal('11500.00'),
        'default_km_rate': Decimal('36.00'),
        'minimum_km_per_day': 350,
        'extra_km_rate': Decimal('36.00'),
        'extra_hour_rate': Decimal('600.00'),
        'driver_bata': Decimal('800.00'),
        'night_halt_charge': Decimal('1000.00'),
        'seating_capacity': 36,
        'luggage_capacity': '30 Large Bags in Underfloor Hold',
        'fuel_type': 'diesel',
        'expected_mileage_kmpl': Decimal('5.20'),
        'toll_class': 'bus_2_axle',
        'has_ac': True,
        'is_luxury': True,
        'transmission_type': 'manual',
        'is_wheelchair_accessible': False,
        'amenities': 'Full Air Suspension (Front & Rear), 2x2 Semi-Sleeper Seats with Calf Rest, Sub-Zero Roof AC, 2x LED Entertainment Screens, USB Chargers, Vast Luggage Bays',
    },
    {
        'id_hint': 6,
        'name': 'Ashok Leyland Viking AC Deluxe Bus (40-Seater)',
        'cat_code': 'luxury_coach',
        'description': 'The foundational backbone of Tamil Nadu passenger transport. High durability, robust H-series diesel engine, full air brakes, and comfortable 2x2 seating for college IV trips and corporate shift transport.',
        'default_day_rate': Decimal('10500.00'),
        'default_km_rate': Decimal('34.00'),
        'minimum_km_per_day': 350,
        'extra_km_rate': Decimal('34.00'),
        'extra_hour_rate': Decimal('550.00'),
        'driver_bata': Decimal('750.00'),
        'night_halt_charge': Decimal('900.00'),
        'seating_capacity': 40,
        'luggage_capacity': '35 Large Bags',
        'fuel_type': 'diesel',
        'expected_mileage_kmpl': Decimal('5.50'),
        'toll_class': 'bus_2_axle',
        'has_ac': True,
        'is_luxury': False,
        'transmission_type': 'manual',
        'is_wheelchair_accessible': False,
        'amenities': 'High-Capacity AC, 2x2 High-Back Pushback Seats, Heavy Underbelly Luggage Hold, PA System with Wireless Mic, Emergency Exits',
    },
    {
        'name': 'Tata Starbus Ultra AC Coach (32-Seater Executive)',
        'cat_code': 'luxury_coach',
        'description': 'Modern executive midi-coach with sleek aerodynamic styling and parabolic suspension. Ideal for SEZ corporate campus transport in Chennai and Hosur.',
        'default_day_rate': Decimal('9200.00'),
        'default_km_rate': Decimal('32.00'),
        'minimum_km_per_day': 350,
        'extra_km_rate': Decimal('32.00'),
        'extra_hour_rate': Decimal('500.00'),
        'driver_bata': Decimal('700.00'),
        'night_halt_charge': Decimal('850.00'),
        'seating_capacity': 32,
        'luggage_capacity': '25 Bags',
        'fuel_type': 'diesel',
        'expected_mileage_kmpl': Decimal('6.00'),
        'toll_class': 'bus_2_axle',
        'has_ac': True,
        'is_luxury': True,
        'transmission_type': 'manual',
        'is_wheelchair_accessible': False,
        'amenities': 'Executive Pushback Recliners, Low Noise Cabin, LED Destination Board, Individual AC Blowers, Fire Detection & Suppression System (FDSS)',
    },
    {
        'id_hint': 14,
        'name': 'Volvo B11R / 9600 Multi-Axle AC Luxury Coach (49-Seater)',
        'cat_code': 'luxury_coach',
        'description': 'Pinnacle of Indian luxury highway mobility. 430 HP D11K engine, electronically controlled air suspension (ECAS), I-Shift automated transmission, and theater-style seating for long-distance luxury tours and interstate express corridors.',
        'default_day_rate': Decimal('16500.00'),
        'default_km_rate': Decimal('46.00'),
        'minimum_km_per_day': 400,
        'extra_km_rate': Decimal('46.00'),
        'extra_hour_rate': Decimal('900.00'),
        'driver_bata': Decimal('1000.00'),
        'night_halt_charge': Decimal('1200.00'),
        'seating_capacity': 49,
        'luggage_capacity': '50 Large Suitcases (Massive Belly)',
        'fuel_type': 'diesel',
        'expected_mileage_kmpl': Decimal('4.20'),
        'toll_class': 'multi_axle',
        'has_ac': True,
        'is_luxury': True,
        'transmission_type': 'automatic',
        'is_wheelchair_accessible': False,
        'amenities': 'Electronically Controlled Air Suspension (ECAS), Luxury Ergonomic Leather Pushback Seats, Dual Large LCD Screens with Surround Sound, Individual USB Charging & Reading Lights, 430 HP Whisper Drive, Aircraft Style Hat-Racks',
    },
    {
        'name': 'Volvo 9600 AC Sleeper Coach (36-Berth Intercity Sleeper)',
        'cat_code': 'luxury_coach',
        'description': 'India premier factory-built luxury sleeper coach. Features 36 private single and double berths with panoramic personal windows, plush mattresses, reading lights, and air suspension for overnight intercity tours (e.g. Coimbatore-Chennai, Bangalore-Ooty).',
        'default_day_rate': Decimal('17500.00'),
        'default_km_rate': Decimal('48.00'),
        'minimum_km_per_day': 400,
        'extra_km_rate': Decimal('48.00'),
        'extra_hour_rate': Decimal('950.00'),
        'driver_bata': Decimal('1000.00'),
        'night_halt_charge': Decimal('1200.00'),
        'seating_capacity': 36,
        'luggage_capacity': '40 Large Bags',
        'fuel_type': 'diesel',
        'expected_mileage_kmpl': Decimal('4.00'),
        'toll_class': 'multi_axle',
        'has_ac': True,
        'is_luxury': True,
        'transmission_type': 'automatic',
        'is_wheelchair_accessible': False,
        'amenities': '36 Individual Luxury Sleep Pods with Curtains, Foam Mattresses with Linen, Individual AC Controls & USB Sockets, Dedicated Shoe Storage, Air Suspension, AIS-140 Panic Feed',
    },
    {
        'name': 'Scania Metrolink HD Multi-Axle Coach (53-Seater)',
        'cat_code': 'luxury_coach',
        'description': 'Swedish engineering with 410 HP powertrain, 14.5-meter coach chassis, and generous 53 pushback seats for large corporate conferences, wedding entourages, and high-capacity interstate travel.',
        'default_day_rate': Decimal('16000.00'),
        'default_km_rate': Decimal('45.00'),
        'minimum_km_per_day': 400,
        'extra_km_rate': Decimal('45.00'),
        'extra_hour_rate': Decimal('850.00'),
        'driver_bata': Decimal('1000.00'),
        'night_halt_charge': Decimal('1200.00'),
        'seating_capacity': 53,
        'luggage_capacity': '50 Large Bags',
        'fuel_type': 'diesel',
        'expected_mileage_kmpl': Decimal('4.20'),
        'toll_class': 'multi_axle',
        'has_ac': True,
        'is_luxury': True,
        'transmission_type': 'automatic',
        'is_wheelchair_accessible': False,
        'amenities': 'Opticruise Transmission, Semi-Active Air Suspension, 2x2 Luxury Pushback Seats, Central Air Conditioning, Heavy Luggage Hold, Emergency Glass Breakers',
    },
    {
        'id_hint': 8,
        'name': '54-Seater Deluxe Pushback Air Suspension Coach',
        'cat_code': 'luxury_coach',
        'description': 'Maximum capacity heavy tourist coach configured with 54 pushback seats, air suspension, and powerful engine for large college industrial visit (IV) batches and major industrial worker shifts.',
        'default_day_rate': Decimal('13000.00'),
        'default_km_rate': Decimal('38.00'),
        'minimum_km_per_day': 350,
        'extra_km_rate': Decimal('38.00'),
        'extra_hour_rate': Decimal('650.00'),
        'driver_bata': Decimal('850.00'),
        'night_halt_charge': Decimal('1000.00'),
        'seating_capacity': 54,
        'luggage_capacity': '45 Large Bags',
        'fuel_type': 'diesel',
        'expected_mileage_kmpl': Decimal('4.80'),
        'toll_class': 'bus_2_axle',
        'has_ac': True,
        'is_luxury': False,
        'transmission_type': 'manual',
        'is_wheelchair_accessible': False,
        'amenities': '2x2 High-Back Pushback Seats, Dual Roof AC Units, PA Amplifier with Wireless Microphone, Underbody Storage Bays, First Aid Equipment',
    },

    # ──────────────────────────────────────────────────────────────────────────
    # 5. ELECTRIC MOBILITY (electric_ev)
    # ──────────────────────────────────────────────────────────────────────────
    {
        'name': 'Tata Tigor EV / XPRES-T (Electric Sedan - 4 Seater)',
        'cat_code': 'electric_ev',
        'description': 'Zero-emission electric sedan with 315 km ARAI certified range. Quiet, eco-friendly urban mobility for green corporate clients, airport transit, and local Coimbatore/Chennai campus commutes.',
        'default_day_rate': Decimal('2800.00'),
        'default_km_rate': Decimal('13.50'),
        'minimum_km_per_day': 200,
        'extra_km_rate': Decimal('13.50'),
        'extra_hour_rate': Decimal('180.00'),
        'driver_bata': Decimal('350.00'),
        'night_halt_charge': Decimal('400.00'),
        'seating_capacity': 4,
        'luggage_capacity': '2 Medium Trolleys',
        'fuel_type': 'electric',
        'expected_mileage_kmpl': Decimal('0.00'),
        'toll_class': 'car',
        'has_ac': True,
        'is_luxury': False,
        'transmission_type': 'automatic',
        'is_wheelchair_accessible': False,
        'amenities': 'Zero Emissions, Automatic Silent Drive, Climate Control AC, Fast CCS2 Charging Compatible, Digital Instrument Cluster, Telematics Battery Tracking',
    },
    {
        'name': 'BYD E6 / Atto 3 (Electric MPV - 5 Seater)',
        'cat_code': 'electric_ev',
        'description': 'Premium electric MPV with Blade Battery technology, delivering 520 km real-world city range, opulent rear legroom, and whisper-silent travel for executive green transport.',
        'default_day_rate': Decimal('4800.00'),
        'default_km_rate': Decimal('20.00'),
        'minimum_km_per_day': 200,
        'extra_km_rate': Decimal('20.00'),
        'extra_hour_rate': Decimal('300.00'),
        'driver_bata': Decimal('500.00'),
        'night_halt_charge': Decimal('600.00'),
        'seating_capacity': 5,
        'luggage_capacity': '4 Large Suitcases (Massive 580L Boot)',
        'fuel_type': 'electric',
        'expected_mileage_kmpl': Decimal('0.00'),
        'toll_class': 'car',
        'has_ac': True,
        'is_luxury': True,
        'transmission_type': 'automatic',
        'is_wheelchair_accessible': False,
        'amenities': 'Blade Battery Safety, CN95 Medical-Grade Cabin Air Filtration, 10.1" Rotating Touchscreen, Regenerative Braking, Leatherette Upholstery, Type-C Fast Charging',
    },
    {
        'name': 'Olectra / JBM Electric AC City & SEZ Shuttle (32-Seater)',
        'cat_code': 'electric_ev',
        'description': 'Heavy commercial electric bus for large IT parks and manufacturing SEZ employee shuttle contracts in Chennai and Hosur. Zero carbon footprint, regenerative braking, and low noise pollution.',
        'default_day_rate': Decimal('14000.00'),
        'default_km_rate': Decimal('40.00'),
        'minimum_km_per_day': 250,
        'extra_km_rate': Decimal('40.00'),
        'extra_hour_rate': Decimal('750.00'),
        'driver_bata': Decimal('850.00'),
        'night_halt_charge': Decimal('1000.00'),
        'seating_capacity': 32,
        'luggage_capacity': '20 Bags',
        'fuel_type': 'electric',
        'expected_mileage_kmpl': Decimal('0.00'),
        'toll_class': 'bus_2_axle',
        'has_ac': True,
        'is_luxury': True,
        'transmission_type': 'automatic',
        'is_wheelchair_accessible': True,
        'amenities': 'Zero Emission Electric Drivetrain, Full Air Suspension, High Capacity AC, Low Floor Ingress, CCTV Surveillance, USB Charging on Every Row, Wheelchair Ramp',
    },
]

def run_replenishment():
    print("=" * 80)
    print("REPLENISHING ENTERPRISE VEHICLE TYPES (DETAILED SPECIFICATIONS)")
    print("=" * 80)

    # 1. Fetch Categories
    categories = {cat.code: cat for cat in VehicleCategory.objects.all()}

    # 2. Re-point duplicate / legacy records before removing junk
    for old_id, target_id in [(9, 1), (10, 12), (11, 3)]:
        for pvt in list(PackageVehicleTariff.objects.filter(vehicle_type_id=old_id)):
            if PackageVehicleTariff.objects.filter(package=pvt.package, vehicle_type_id=target_id).exists():
                pvt.delete()
            else:
                pvt.vehicle_type_id = target_id
                pvt.save()
        Vehicle.objects.filter(vehicle_type_id=old_id).update(vehicle_type_id=target_id)
        Package.objects.filter(default_vehicle_type_id=old_id).update(default_vehicle_type_id=target_id)

    # 3. Clean up junk records that have 0 references
    active_hint_ids = {item.get('id_hint') for item in DETAILED_VEHICLE_CATALOG if item.get('id_hint')}
    junk_candidates = VehicleType.objects.exclude(id__in=active_hint_ids)
    
    deleted_cnt = 0
    for j in junk_candidates:
        # Verify no packages or tariffs
        p_c = Package.objects.filter(default_vehicle_type=j).count()
        t_c = PackageVehicleTariff.objects.filter(vehicle_type=j).count()
        v_c = Vehicle.objects.filter(vehicle_type=j).count()
        if p_c == 0 and t_c == 0 and v_c == 0:
            print(f"[REMOVED JUNK] ID {j.id}: {j.name}")
            j.delete()
            deleted_cnt += 1
        else:
            print(f"[RETAINED ACTIVE] ID {j.id}: {j.name} (Pkgs: {p_c}, Tariffs: {t_c}, Vehs: {v_c})")

    print(f"\nTotal Legacy / Junk Records Removed: {deleted_cnt}")
    print("-" * 80)

    # 4. Upsert detailed vehicle types
    created_cnt = 0
    updated_cnt = 0

    for item in DETAILED_VEHICLE_CATALOG:
        cat = categories.get(item['cat_code'])
        id_hint = item.get('id_hint')

        vt = None
        if id_hint and VehicleType.objects.filter(id=id_hint).exists():
            vt = VehicleType.objects.get(id=id_hint)
        else:
            # Check by exact name
            vt = VehicleType.objects.filter(name=item['name']).first()

        if vt:
            # Update in place
            vt.name = item['name']
            vt.vehicle_category = cat
            vt.category = cat.name if cat else ''
            vt.description = item['description']
            vt.default_day_rate = item['default_day_rate']
            vt.default_km_rate = item['default_km_rate']
            vt.minimum_km_per_day = item['minimum_km_per_day']
            vt.extra_km_rate = item['extra_km_rate']
            vt.extra_hour_rate = item['extra_hour_rate']
            vt.driver_bata = item['driver_bata']
            vt.night_halt_charge = item['night_halt_charge']
            vt.seating_capacity = item['seating_capacity']
            vt.luggage_capacity = item['luggage_capacity']
            vt.fuel_type = item['fuel_type']
            vt.expected_mileage_kmpl = item['expected_mileage_kmpl']
            vt.toll_class = item['toll_class']
            vt.has_ac = item['has_ac']
            vt.is_luxury = item['is_luxury']
            vt.transmission_type = item['transmission_type']
            vt.is_wheelchair_accessible = item['is_wheelchair_accessible']
            vt.amenities = item['amenities']
            vt.save()
            updated_cnt += 1
            print(f"[UPDATED] ID {vt.id}: {vt.name} ({vt.seating_capacity} seats) -> {cat.name}")
        else:
            # Create fresh
            vt = VehicleType.objects.create(
                name=item['name'],
                vehicle_category=cat,
                category=cat.name if cat else '',
                description=item['description'],
                default_day_rate=item['default_day_rate'],
                default_km_rate=item['default_km_rate'],
                minimum_km_per_day=item['minimum_km_per_day'],
                extra_km_rate=item['extra_km_rate'],
                extra_hour_rate=item['extra_hour_rate'],
                driver_bata=item['driver_bata'],
                night_halt_charge=item['night_halt_charge'],
                seating_capacity=item['seating_capacity'],
                luggage_capacity=item['luggage_capacity'],
                fuel_type=item['fuel_type'],
                expected_mileage_kmpl=item['expected_mileage_kmpl'],
                toll_class=item['toll_class'],
                has_ac=item['has_ac'],
                is_luxury=item['is_luxury'],
                transmission_type=item['transmission_type'],
                is_wheelchair_accessible=item['is_wheelchair_accessible'],
                amenities=item['amenities']
            )
            created_cnt += 1
            print(f"[CREATED] ID {vt.id}: {vt.name} ({vt.seating_capacity} seats) -> {cat.name}")

    print("=" * 80)
    print(f"REPLENISHMENT COMPLETE: {created_cnt} vehicle types created, {updated_cnt} updated in-place.")
    print(f"Total Active Detailed Vehicle Types in System: {VehicleType.objects.count()}")
    print("=" * 80)

    # 5. Re-link vehicles to their proper vehicle type
    crysta_type = VehicleType.objects.filter(name__icontains='Innova Crysta').first()
    hycross_type = VehicleType.objects.filter(name__icontains='Hycross').first()
    dzire_type = VehicleType.objects.filter(name__icontains='Dzire').first()
    etios_type = VehicleType.objects.filter(name__icontains='Etios').first()
    urbania_type = VehicleType.objects.filter(name__icontains='Urbania (17-Seater').first() or VehicleType.objects.filter(name__icontains='Urbania').first()
    tt12_type = VehicleType.objects.filter(name__icontains='12-Seater Standard').first() or VehicleType.objects.filter(name__icontains='Tempo Traveller').first()
    viking_type = VehicleType.objects.filter(name__icontains='Viking').first() or VehicleType.objects.filter(name__icontains='40-Seater').first()
    glider_type = VehicleType.objects.filter(name__icontains='Glider').first() or VehicleType.objects.filter(name__icontains='36-Seater').first()
    volvo_type = VehicleType.objects.filter(name__icontains='Volvo B11R').first() or VehicleType.objects.filter(name__icontains='Volvo').first()
    scania_type = VehicleType.objects.filter(name__icontains='Scania').first() or volvo_type

    # Precise vehicle updates
    for v in Vehicle.objects.all():
        m_lower = (v.model or '').lower() + ' ' + (v.brand or '').lower()
        if 'hycross' in m_lower and hycross_type:
            v.vehicle_type = hycross_type
        elif 'crysta' in m_lower and crysta_type:
            v.vehicle_type = crysta_type
        elif 'etios' in m_lower and etios_type:
            v.vehicle_type = etios_type
        elif 'dzire' in m_lower and dzire_type:
            v.vehicle_type = dzire_type
        elif 'urbania' in m_lower and urbania_type:
            v.vehicle_type = urbania_type
        elif 'tempo traveller' in m_lower and tt12_type:
            v.vehicle_type = tt12_type
        elif 'glider' in m_lower and glider_type:
            v.vehicle_type = glider_type
        elif 'volvo' in m_lower and volvo_type:
            v.vehicle_type = volvo_type
        elif 'scania' in m_lower and scania_type:
            v.vehicle_type = scania_type
        elif v.seating_capacity >= 40 and viking_type:
            v.vehicle_type = viking_type

        if v.vehicle_type:
            v.vehicle_category = v.vehicle_type.vehicle_category
        v.save()
        print(f"Vehicle {v.registration_number}: Linked to {v.vehicle_type.name} ({v.vehicle_category.name})")

if __name__ == '__main__':
    run_replenishment()
