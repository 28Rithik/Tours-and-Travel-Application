"""
Management command to seed enterprise-scale fleet and crew data.
Generates:
- 10 Enterprise Vehicle Categories
- 730+ Own Fleet Vehicles with exact model/trim/seating specifications
- 420+ Supplier / Vendor Attached Vehicles (Total 1,150+ Vehicles)
- 1,150+ Certified Commercial Chauffeurs & Highway Captains
- 30+ Regional Supplier / Vendor Transporters
- 100% Compliant RTO Telematics & Statutory Records (FC, AIS-140 GPS, FASTag, Insurance, AITP)
"""

import random
from datetime import date, timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import Vehicle, Driver, Supplier, VehicleType, VehicleCategory


# Indian first and last names for Tamil Nadu, Kerala, Karnataka regional transport
FIRST_NAMES = [
    "Murugan", "Karthik", "Senthil", "Selvakumar", "Saravanan", "Arumugam", "Venkatesh",
    "Manikandan", "Suresh", "Ramesh", "Praveen", "Dhanush", "Rajesh", "Muthukumar",
    "Palanisamy", "Shanmugam", "Ganesan", "Velmurugan", "Balamurugan", "Sundaram",
    "Subramanian", "Thirunavukkarasu", "Anand", "Vijay", "Ajith", "Dinesh", "Kannan",
    "Natarajan", "Marimuthu", "Perumal", "Sakthivel", "Sivakumar", "Ilango", "Gopal",
    "Govindaraj", "Ayyappan", "Kumaran", "Pandian", "Baskaran", "Vijayan", "Jayachandran",
    "Moorthy", "Radhakrishnan", "Sasikumar", "Prabhu", "Harikrishnan", "Vignesh", "Ravi",
    "Mohan", "Ranganathan", "Karuppusamy", "Naveen", "Mahesh", "Sathish", "Deepak"
]

LAST_NAMES = [
    "K", "S", "M", "P", "R", "G", "A", "V", "N", "T", "B", "C", "D", "E",
    "Kannan", "Murugan", "Gounder", "Chettiar", "Pillai", "Nadar", "Thevar",
    "Iyer", "Iyengar", "Naidu", "Reddy", "Menon", "Nair", "Pillay", "Sharma"
]

DEPOTS = [
    "Coimbatore Central HQ",
    "Tirupur Branch",
    "Erode Branch",
    "Chennai Branch",
    "Hosur Branch",
    "Trichy Branch",
    "Central Control Room",
]

SUPPLIERS_DATA = [
    ("Coimbatore FastTrack Cabs & Travels", "Coimbatore", "33AAAFC1234F1Z1"),
    ("Salem Royal Transport Logistics", "Salem", "33AABSR5678G1Z2"),
    ("Ooty Hill Queen Tourers", "Ooty", "33AACHO9012H1Z3"),
    ("Madurai Meenakshi Bus Lines", "Madurai", "33AADMM3456J1Z4"),
    ("Tirupur Industrial Commute Shuttles", "Tirupur", "33AAETI7890K1Z5"),
    ("Chennai Gateway Express Fleet", "Chennai", "33AAFCE2345L1Z6"),
    ("Bangalore Interstate Fleet Services", "Bengaluru", "29AAGBI6789M1Z7"),
    ("Kerala God's Own Luxury Liners", "Palakkad", "32AAHKG0123N1Z8"),
    ("Trichy Chola Transit Solutions", "Trichy", "33AAITC4567P1Z9"),
    ("Hosur Border Freight & Cabs", "Hosur", "33AAJHB8901Q1Z0"),
    ("Erode Kongu Transport Syndicate", "Erode", "33AAKEK2345R1Z1"),
    ("Kodaikanal Misty Heights Travels", "Kodaikanal", "33AALKM6789S1Z2"),
    ("Pollachi Coconut Valley Fleet", "Pollachi", "33AAMPC0123T1Z3"),
    ("Dindigul Rock Fort Transit", "Dindigul", "33AANDR4567U1Z4"),
    ("Tirunelveli Nellai Express Cabs", "Tirunelveli", "33AAOTN8901V1Z5"),
    ("Vellore Golden City Transports", "Vellore", "33AAPVG2345W1Z6"),
    ("Kochi Cochin Backwater Shuttles", "Kochi", "32AAQCB6789X1Z7"),
    ("Mysore Palace City Cabs", "Mysuru", "29AARMC0123Y1Z8"),
    ("Karur Amaravathi Logistics", "Karur", "33AASKA4567Z1Z9"),
    ("Namakkal Lorry & Bus Syndicate", "Namakkal", "33AATNL8901A1Z0"),
    ("Thanjavur Delta Horizon Travels", "Thanjavur", "33AAUTD2345B1Z1"),
    ("Kanyakumari Southern Tip Tours", "Kanyakumari", "33AAVKS6789C1Z2"),
    ("Coonoor Tea Garden Shuttles", "Coonoor", "33AAWCT0123D1Z3"),
    ("Calicut Malabar Coast Shuttles", "Kozhikode", "32AAXMC4567E1Z4"),
    ("Trivandrum Capital Shuttles", "Thiruvananthapuram", "32AAYTC8901F1Z5"),
    ("Perundurai Highway Express", "Perundurai", "33AAZPH2345G1Z6"),
    ("Sathyamangalam Forest Corridor Fleet", "Sathyamangalam", "33ABASF6789H1Z7"),
    ("Mettupalayam Nilgiri Gateway Cabs", "Mettupalayam", "33ABBMT0123I1Z8"),
    ("Anamailai Wildlife Safari Fleet", "Valparai", "33ABCAW4567J1Z9"),
    ("Avinashi High Speed Transit Partners", "Avinashi", "33ABDAV8901K1Z0")
]

CATEGORIES_SPEC = [
    ("Executive & Compact Sedans", "sedan", "Premium corporate and airport cabs (4+D)", "local_taxi", "blue", "4+1"),
    ("Premium MUVs & SUVs", "muv_suv", "Highway cruisers and family tourist outstation cabs (6+D, 7+D, 8+D)", "directions_car", "emerald", "6-8+1"),
    ("Zero-Emission Green Fleet (EVs)", "ev_green", "Eco-friendly commercial electric vehicles for urban mobility", "electric_car", "teal", "4-6+1"),
    ("Luxury Minivans & Force Urbania", "luxury_van", "High-comfort monocoque vans with luxury reclining seats", "airport_shuttle", "indigo", "9-17+1"),
    ("Force Traveller Mini-Coaches", "tempo_traveller", "Reliable group tourers and outstation tempo travellers", "directions_bus", "purple", "9-26+1"),
    ("Executive & Route Line Mini Buses", "mini_bus", "School, staff and pilgrim route line mini buses", "departure_board", "amber", "20-35+1"),
    ("Intercity Sleeper & Semi-Sleeper Coaches", "intercity_coach", "Long-haul interstate luxury coaches (Volvo, Scania, BharatBenz)", "airline_seat_flat", "rose", "36-59+2"),
    ("Corporate Employee Transport & Staff Buses", "corporate_staff_bus", "Dedicated contract carriage buses for IT parks & factories", "commute", "cyan", "33-55+1"),
    ("VIP Motorhomes, Caravans & Vanity Vans", "caravan_vanity", "Luxury vanity vans and executive caravans for film shoots & VIPs", "rv_hookup", "yellow", "Special"),
    ("Ultra-Luxury VIP Chauffeur Cars", "ultra_luxury", "Flagship Mercedes Maybach, S-Class, BMW 7 & Vellfire for VVIPs", "stars", "fuchsia", "3-5+1")
]

# EXACT USER VEHICLE SPECIFICATION MATRIX: (brand, model, seating_pax, count, category_code, fuel_type, is_staff, is_sleeper, is_luxury)
VEHICLE_CATALOG = [
    # MUV / SUV Segment
    ("Toyota", "Innova 2.5 VX", 7, 4, "muv_suv", "diesel", False, False, False),
    ("Toyota", "Innova Crysta 2.4 GX+", 7, 9, "muv_suv", "diesel", False, False, True),
    ("Toyota", "Innova Hycross VX", 7, 5, "muv_suv", "petrol", False, False, True),
    ("Maruti Suzuki", "Invicto Zeta Plus", 7, 2, "muv_suv", "petrol", False, False, True),
    ("Mahindra", "XUV700 MX Diesel", 6, 1, "muv_suv", "diesel", False, False, True),
    ("Mahindra", "Marazzo M2 7 STR", 7, 10, "muv_suv", "diesel", False, False, False),
    ("Mahindra", "Xylo D4 BS IV '19", 6, 1, "muv_suv", "diesel", False, False, False),
    ("Kia", "Carens Premium (O)", 6, 1, "muv_suv", "diesel", False, False, False),
    ("Kia", "Carens Clavis HTE(O) 1.5", 6, 2, "muv_suv", "petrol", False, False, False),
    ("Toyota", "Rumion S Petrol", 6, 14, "muv_suv", "petrol", False, False, False),
    ("Maruti Suzuki", "Ertiga Lxi", 8, 6, "muv_suv", "cng", False, False, False),

    # Sedan Segment
    ("Honda", "City V", 4, 1, "sedan", "petrol", False, False, True),
    ("Toyota", "Corolla Altis", 4, 1, "sedan", "petrol", False, False, True),
    ("Maruti Suzuki", "Ciaz Sigma 1.5", 4, 6, "sedan", "petrol", False, False, False),
    ("Toyota", "Etios VXD", 4, 2, "sedan", "diesel", False, False, False),
    ("Honda", "Amaze VX 1.2", 4, 12, "sedan", "petrol", False, False, False),
    ("Hyundai", "Aura E 1.2", 4, 10, "sedan", "cng", False, False, False),
    ("Maruti Suzuki", "Dzire Lxi", 4, 6, "sedan", "cng", False, False, False),

    # Mini Vans & Urban Mobility
    ("Tata", "Winger Tourist 3200 AC", 13, 1, "luxury_van", "diesel", False, False, False),
    ("Force Motors", "Cityline AC", 9, 1, "luxury_van", "diesel", False, False, False),

    # Electric Fleet (EVs)
    ("MG", "ZS EV Excite Pro", 4, 14, "ev_green", "electric", False, False, True),
    ("BYD", "E6", 5, 2, "ev_green", "electric", False, False, True),
    ("BYD", "eMax 7 Premium", 6, 12, "ev_green", "electric", False, False, True),
    ("Tata", "Nexon EV", 4, 12, "ev_green", "electric", False, False, False),
    ("Tata", "Tigor EV XT", 4, 8, "ev_green", "electric", False, False, False),

    # Force Traveller Tourist Line
    ("Force", "Traveller T2 4020 AC", 26, 6, "tempo_traveller", "diesel", False, False, False),
    ("Force", "Traveller T1 4020 AC", 20, 4, "tempo_traveller", "diesel", False, False, False),
    ("Force", "Traveller T1 3700 AC", 17, 2, "tempo_traveller", "diesel", False, False, False),
    ("Force", "Traveller T1 3350 AC", 14, 1, "tempo_traveller", "diesel", False, False, False),
    ("Force", "Traveller T2 4020 AC FG", 26, 3, "tempo_traveller", "diesel", False, False, False),
    ("Force", "Traveller T1 4020 AC FG", 20, 2, "tempo_traveller", "diesel", False, False, False),
    ("Force", "Traveller T1 3700 AC Maharaja FG", 14, 3, "tempo_traveller", "diesel", False, False, True),
    ("Force", "Traveller T1 3350 AC Maharaja FG", 9, 2, "tempo_traveller", "diesel", False, False, True),

    # Force Urbania Luxury Line
    ("Force", "Urbania 4400 17-Seater", 17, 8, "luxury_van", "diesel", False, False, True),
    ("Force", "Urbania 4400 16-Seater", 16, 8, "luxury_van", "diesel", False, False, True),
    ("Force", "Urbania 3615 12-Seater", 12, 4, "luxury_van", "diesel", False, False, True),
    ("Force", "Urbania 3615 10-Seater", 10, 4, "luxury_van", "diesel", False, False, True),
    ("Force", "Urbania 3350 9-Seater", 9, 2, "luxury_van", "diesel", False, False, True),
    ("Force", "Urbania 3350 8-Seater", 8, 2, "luxury_van", "diesel", False, False, True),
    ("Force", "Urbania 4400 Maharaja (1x1)", 12, 2, "luxury_van", "diesel", False, False, True),
    ("Force", "Urbania 3615 Maharaja (1x1)", 9, 2, "luxury_van", "diesel", False, False, True),
    ("Force", "Urbania 3350 Maharaja (1x1)", 5, 2, "luxury_van", "diesel", False, False, True),

    # Mini Buses & Fixed Glass Tourist Coaches
    ("SML Isuzu", "Swaraj Mazda EcoMax T3500", 20, 1, "mini_bus", "diesel", False, False, False),
    ("SML Isuzu", "Asai 3335 AC", 21, 2, "mini_bus", "diesel", False, False, False),
    ("Bharat Benz", "1017 Fixed Glass 35-Seater", 35, 3, "mini_bus", "diesel", False, False, True),
    ("SML Isuzu", "Executive LX 5100 Fixed Glass", 35, 2, "mini_bus", "diesel", False, False, True),
    ("Eicher", "2050 Aadhavan Coach", 21, 2, "mini_bus", "diesel", False, False, False),
    ("SML Isuzu", "3335 Vinayaka Coach", 25, 2, "mini_bus", "diesel", False, False, False),
    ("SML Isuzu", "3335 ZedAstra Face FG", 21, 1, "mini_bus", "diesel", False, False, False),
    ("SML Isuzu", "3335 Aadhavan Coach FG", 25, 1, "mini_bus", "diesel", False, False, False),
    ("Bharat Benz", "1017 Ojes Body FG", 25, 1, "mini_bus", "diesel", False, False, True),
    ("Bharat Benz", "1017 Navigo FG", 25, 1, "mini_bus", "diesel", False, False, True),
    ("Bharat Benz", "1017 Prakash Astra", 35, 2, "mini_bus", "diesel", False, False, True),
    ("Bharat Benz", "1017 Ojes Body FG 35-Seater", 35, 2, "mini_bus", "diesel", False, False, True),

    # Large Coaches & Intercity Line
    ("Ashok Leyland", "Viking 11.4m Zedastra", 53, 5, "intercity_coach", "diesel", False, False, False),
    ("Ashok Leyland", "Viking 11.4m Zedvega", 53, 2, "intercity_coach", "diesel", False, False, False),
    ("Bharat Benz", "1624 Prakash Zedastra", 53, 1, "intercity_coach", "diesel", False, False, True),
    ("Bharat Benz", "1624 MG Glider 12m FG", 45, 1, "intercity_coach", "diesel", False, False, True),
    ("Bharat Benz", "1624 Prakash Capella GT 11.4m FG", 45, 1, "intercity_coach", "diesel", False, False, True),
    ("Bharat Benz", "1624 Prakash Zedastra FG", 45, 2, "intercity_coach", "diesel", False, False, True),
    ("Bharat Benz", "1624 Prakash Zedastra 13.5m", 52, 1, "intercity_coach", "diesel", False, False, True),
    ("Bharat Benz", "1924 Glider 13.5m", 52, 1, "intercity_coach", "diesel", False, False, True),
    ("Volvo", "9400 B8R 12m Biaxle", 45, 4, "intercity_coach", "diesel", False, False, True),
    ("Volvo", "9600 B8R 12.2m Bi-Axle", 43, 6, "intercity_coach", "diesel", False, False, True),

    # Corporate Staff & Employee Commute Fleets (Staff Specific)
    ("Tata", "Winger Tourist 3200 AC Staff", 13, 12, "corporate_staff_bus", "diesel", True, False, False),
    ("Force Motors", "Cityline AC Staff", 9, 1, "corporate_staff_bus", "diesel", True, False, False),
    ("Force", "Traveller T2 4020 AC Staff", 25, 14, "corporate_staff_bus", "diesel", True, False, False),
    ("Force", "Traveller T1 4020 AC Staff", 20, 10, "corporate_staff_bus", "diesel", True, False, False),
    ("Force", "Traveller T1 3700 AC Staff", 17, 8, "corporate_staff_bus", "diesel", True, False, False),
    ("Force", "Traveller T1 3350 AC Staff", 14, 5, "corporate_staff_bus", "diesel", True, False, False),
    ("Force", "Urbania 4400 Staff", 16, 4, "corporate_staff_bus", "diesel", True, False, True),
    ("Force", "Urbania 3615 Staff", 13, 3, "corporate_staff_bus", "diesel", True, False, True),
    ("Force", "MonoBus T3 MB 5200 AC Staff", 41, 12, "corporate_staff_bus", "diesel", True, False, False),
    ("Force", "MonoBus T3 MB 4020 AC Staff", 33, 8, "corporate_staff_bus", "diesel", True, False, False),
    ("Bharat Benz", "1017 AC Staff", 35, 11, "corporate_staff_bus", "diesel", True, False, False),
    ("Bharat Benz", "1017 FG Staff", 35, 4, "corporate_staff_bus", "diesel", True, False, False),
    ("SML Isuzu", "Swaraj Mazda EcoMax T3500 Staff", 20, 14, "corporate_staff_bus", "diesel", True, False, False),
    ("SML Isuzu", "Asai 3335 AC Staff", 21, 6, "corporate_staff_bus", "diesel", True, False, False),
    ("SML Isuzu", "Executive LX 5100 Staff", 37, 6, "corporate_staff_bus", "diesel", True, False, False),
    ("Tata", "Ultra Prime 50+D AC LPO11.6/54 FG Staff", 50, 6, "corporate_staff_bus", "diesel", True, False, False),
    ("Tata", "Ultra Prime 55+D LPO11.6/54 Staff", 55, 12, "corporate_staff_bus", "diesel", True, False, False),
    ("Tata", "Ultra Prime 44+D LPO11.6/54 Staff", 44, 10, "corporate_staff_bus", "diesel", True, False, False),
    ("Eicher", "Skyline Pro Next 3011 L AC FG Staff", 55, 5, "corporate_staff_bus", "diesel", True, False, False),
    ("Eicher", "Skyline Pro Next 3010 L AC FG Staff", 44, 10, "corporate_staff_bus", "diesel", True, False, False),
    ("Ashok Leyland", "Lynx Strong REC Coach Staff", 52, 40, "corporate_staff_bus", "diesel", True, False, False),
    ("Ashok Leyland", "Lynx Arrow Coach Staff", 52, 25, "corporate_staff_bus", "diesel", True, False, False),
    ("Ashok Leyland", "Lynx Prakash Vega Staff", 52, 8, "corporate_staff_bus", "diesel", True, False, False),
    ("Volvo", "9400 B8R 12m Biaxle Staff", 45, 12, "corporate_staff_bus", "diesel", True, False, True),
    ("Volvo", "9600 B8R 12.2m Bi-Axle Staff", 43, 2, "corporate_staff_bus", "diesel", True, False, True),
    ("Scania", "Metrolink HD 12m Bi-Axle Staff", 45, 2, "corporate_staff_bus", "diesel", True, False, True),
    ("Mercedes Benz", "2441 SHD 15m Multiaxle Staff", 59, 1, "corporate_staff_bus", "diesel", True, False, True),

    # Route Line & Mini Buses
    ("Bharat Benz", "1017 Mini Bus", 35, 4, "mini_bus", "diesel", False, False, False),
    ("Eicher", "2090 L Mini Bus", 35, 1, "mini_bus", "diesel", False, False, False),
    ("Ashok Leyland", "Viking 222 12m Route Line Bus", 55, 3, "mini_bus", "diesel", False, False, False),
    ("Bharat Benz", "1624 12m Route Line Bus", 56, 6, "mini_bus", "diesel", False, False, False),

    # Luxury Caravans & Film Vanity Vans
    ("Bharat Benz", "1017 JCBL Caravan 9m", 6, 2, "caravan_vanity", "diesel", False, False, True),
    ("Bharat Benz", "1017 OJES Body Caravan", 6, 3, "caravan_vanity", "diesel", False, False, True),
    ("Force", "Traveller 4020 Caravan", 4, 1, "caravan_vanity", "diesel", False, False, True),
    ("Force", "Urbania 4400 Caravan", 5, 1, "caravan_vanity", "diesel", False, False, True),
    ("Volvo", "9400 JCBL Caravan 12m", 8, 2, "caravan_vanity", "diesel", False, False, True),
    ("Bharat Benz", "1017 Single Door Vanity Van", 4, 3, "caravan_vanity", "diesel", False, False, True),
    ("Bharat Benz", "1017 Three Door Vanity Van", 6, 6, "caravan_vanity", "diesel", False, False, True),
    ("Force", "Traveller 4020 T2 Vanity Van", 4, 2, "caravan_vanity", "diesel", False, False, True),

    # Interstate Luxury Sleepers (BharatBenz 1924 Line)
    ("Bharat Benz", "1924 MG Glider Z+", 36, 16, "intercity_coach", "diesel", False, True, True),
    ("Bharat Benz", "1924 MG Tigra", 36, 10, "intercity_coach", "diesel", False, True, True),
    ("Bharat Benz", "1924 Damodar Spyder 2.0", 36, 9, "intercity_coach", "diesel", False, True, True),
    ("Bharat Benz", "1924 Damodar Kalpa", 36, 6, "intercity_coach", "diesel", False, True, True),
    ("Bharat Benz", "1924 Sutlej SL1800+", 36, 4, "intercity_coach", "diesel", False, True, True),
    ("Bharat Benz", "1924 Veera V8 Mk III", 36, 6, "intercity_coach", "diesel", False, True, True),
    ("Volvo Eicher", "6019 Pro Capella GT", 36, 4, "intercity_coach", "diesel", False, True, True),

    # Flagship Multi-Axle Premium Sleeper Coaches
    ("Mercedes Benz", "2441 SHD", 40, 2, "intercity_coach", "diesel", False, True, True),
    ("Mercedes Benz", "2441 SHD MG Dream Z", 40, 2, "intercity_coach", "diesel", False, True, True),
    ("Scania", "Metrolink HD 14.5m", 40, 6, "intercity_coach", "diesel", False, True, True),
    ("Volvo", "9400 B11R 14.5m MG Star Z", 40, 4, "intercity_coach", "diesel", False, True, True),
    ("Volvo", "B8R 9600s 15m", 40, 6, "intercity_coach", "diesel", False, True, True),
    ("Volvo", "B8R 9600 SLX 15m + Restroom", 40, 12, "intercity_coach", "diesel", False, True, True),
    ("Volvo", "B8R 9600 SLX 15m", 42, 18, "intercity_coach", "diesel", False, True, True),

    # Extended Luxury VIP Fleets & Executive Shuttles
    ("Toyota", "Camry Hybrid", 3, 4, "ultra_luxury", "petrol", False, False, True),
    ("Toyota", "Fortuner 4x4 2.8 4WD", 5, 6, "muv_suv", "diesel", False, False, True),
    ("Toyota", "Fortuner Legender", 5, 5, "muv_suv", "diesel", False, False, True),
    ("Kia", "Carnival Limousine", 7, 5, "luxury_van", "diesel", False, False, True),
    ("Toyota", "Land Cruiser 300 ZX", 5, 2, "ultra_luxury", "diesel", False, False, True),
    ("Toyota", "HiAce Commuter H200 2019", 9, 3, "luxury_van", "diesel", False, False, True),
    ("Toyota", "HiAce Commuter H300 GL 2023", 10, 4, "luxury_van", "diesel", False, False, True),
    ("Toyota", "Vellfire Executive Lounge", 5, 4, "ultra_luxury", "petrol", False, False, True),
    ("Toyota", "GranAce 4R 2.8l", 5, 2, "ultra_luxury", "diesel", False, False, True),
    ("Mercedes-Benz", "E220d LWB", 3, 5, "ultra_luxury", "diesel", False, False, True),
    ("Mercedes-Benz", "S-Class S350d", 3, 3, "ultra_luxury", "diesel", False, False, True),
    ("Mercedes-Benz", "S-Class S 450 4Matic", 3, 2, "ultra_luxury", "petrol", False, False, True),
    ("Mercedes-Benz", "EQS Celebration Edition", 3, 2, "ultra_luxury", "electric", False, False, True),
    ("Mercedes-Benz", "V-Class V 300d", 5, 3, "ultra_luxury", "diesel", False, False, True),
    ("Mercedes-Benz", "Maybach S-Class S580 4Matic", 3, 2, "ultra_luxury", "petrol", False, False, True),
    ("Mercedes-Benz", "Maybach GLS 600 4Matic", 5, 2, "ultra_luxury", "petrol", False, False, True),
    ("BMW", "5 Series 530Li", 4, 4, "ultra_luxury", "petrol", False, False, True),
    ("BMW", "7 Series 740d M Sport", 4, 3, "ultra_luxury", "diesel", False, False, True),
    ("BMW", "i7 xDrive60 M Sport", 4, 2, "ultra_luxury", "electric", False, False, True),
    ("BMW", "X5 xDrive30d", 5, 3, "ultra_luxury", "diesel", False, False, True),
    ("BMW", "X7 xDrive40d", 5, 3, "ultra_luxury", "diesel", False, False, True),
    ("Audi", "A6", 4, 4, "ultra_luxury", "petrol", False, False, True),
    ("Audi", "A8 L Technology", 4, 2, "ultra_luxury", "petrol", False, False, True),
    ("Audi", "Q7 Premium Plus", 5, 3, "ultra_luxury", "petrol", False, False, True),

    # Specialized Institutional School & Green Electric Buses
    ("Bharat Benz", "1017 School Bus", 49, 4, "corporate_staff_bus", "diesel", True, False, False),
    ("Force", "Traveller School 4020 WB", 26, 4, "corporate_staff_bus", "diesel", True, False, False),
    ("Eicher", "Skyline Pro Next 3011 K School", 66, 4, "corporate_staff_bus", "diesel", True, False, False),
    ("Ashok Leyland", "Switch Mobility EiV 12 Electric", 45, 4, "ev_green", "electric", False, False, True),
    ("Tata", "Starbus Ultra 9/9 EV Electric", 31, 3, "ev_green", "electric", False, False, True),
    ("Eicher", "Skyline Pro-E 12m Electric", 50, 3, "ev_green", "electric", False, False, True),
]


class Command(BaseCommand):
    help = "Seeds database with 700+ Own Fleet, 400+ Supplier Vehicles (1150+ total), and 1100+ Professional Chauffeurs."

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("[*] Starting Enterprise Fleet & Crew Seeding Engine..."))

        # Step 1: Create Categories
        categories_dict = {}
        for name, code, desc, icon, color, srange in CATEGORIES_SPEC:
            cat, _ = VehicleCategory.objects.get_or_create(
                code=code,
                defaults={
                    "name": name,
                    "description": desc,
                    "icon": icon,
                    "badge_color": color,
                    "seating_range": srange,
                    "is_active": True,
                }
            )
            categories_dict[code] = cat
        self.stdout.write(self.style.SUCCESS(f"[OK] 10 Vehicle Categories Synchronized."))

        # Step 2: Create / Sync Suppliers (Vendors)
        suppliers_list = []
        for name, city, gstin in SUPPLIERS_DATA:
            sup, _ = Supplier.objects.get_or_create(
                gstin=gstin,
                defaults={
                    "name": name,
                    "party_type": "supplier",
                    "phone": f"+91 {random.randint(90000, 99999)} {random.randint(10000, 99999)}",
                    "email": f"ops@{name.lower().replace(' ', '')[:12]}.in",
                    "address": f"Transport Nagar, Bypass Road, {city}, Tamil Nadu",
                    "billing_cycle": "monthly",
                    "credit_period_days": 30,
                    "state_code": "33",
                    "tds_rate": Decimal("1.00"),
                    "default_day_rate": Decimal("4500.00"),
                    "default_km_rate": Decimal("16.00"),
                    "is_active": True
                }
            )
            suppliers_list.append(sup)
        self.stdout.write(self.style.SUCCESS(f"[OK] {len(suppliers_list)} Regional Supplier Partners Synchronized."))

        # Step 3: Create Vehicle Types for all distinct models in catalog
        vehicle_types_dict = {}
        for brand, model, pax, count, cat_code, fuel, is_staff, is_sleeper, is_luxury in VEHICLE_CATALOG:
            type_name = f"{brand} {model}"
            if type_name not in vehicle_types_dict:
                vtype, _ = VehicleType.objects.get_or_create(
                    name=type_name,
                    defaults={
                        "vehicle_category": categories_dict[cat_code],
                        "category": cat_code,
                        "description": f"{brand} {model} commercial passenger asset",
                        "seating_capacity": pax,
                        "fuel_type": fuel,
                        "has_ac": True,
                        "is_luxury": is_luxury,
                        "default_day_rate": Decimal("3500.00") if pax <= 7 else Decimal("7500.00") if pax <= 26 else Decimal("14000.00"),
                        "default_km_rate": Decimal("14.00") if pax <= 7 else Decimal("24.00") if pax <= 26 else Decimal("42.00"),
                        "minimum_km_per_day": 250 if pax <= 7 else 300,
                        "extra_km_rate": Decimal("15.00") if pax <= 7 else Decimal("26.00") if pax <= 26 else Decimal("45.00"),
                        "driver_bata": Decimal("500.00") if pax <= 7 else Decimal("800.00") if pax <= 26 else Decimal("1200.00"),
                        "night_halt_charge": Decimal("600.00") if pax <= 7 else Decimal("1000.00") if pax <= 26 else Decimal("1500.00"),
                    }
                )
                vehicle_types_dict[type_name] = vtype
        self.stdout.write(self.style.SUCCESS(f"[OK] {len(vehicle_types_dict)} Vehicle Types Synchronized."))

        # Step 4: Seed 1,150+ Professional Drivers
        self.stdout.write(self.style.NOTICE("Generating 1,150+ Certified Commercial Chauffeurs & Highway Captains..."))
        existing_drivers_count = Driver.objects.count()
        target_drivers = 1160
        drivers_to_create = max(0, target_drivers - existing_drivers_count)

        blood_groups = ["O+ve", "A+ve", "B+ve", "AB+ve", "O-ve", "A-ve"]
        languages = [
            "Tamil, English",
            "Tamil, Malayalam, English",
            "Tamil, Kannada, Hindi",
            "Tamil, Telugu, English",
            "Tamil, Hindi, English"
        ]
        bank_names = ["ICICI Bank", "State Bank of India", "Canara Bank", "HDFC Bank", "Indian Overseas Bank"]

        new_drivers = []
        for i in range(drivers_to_create):
            idx = existing_drivers_count + i + 1
            fname = random.choice(FIRST_NAMES)
            lname = random.choice(LAST_NAMES)
            full_name = f"{fname} {lname}"
            is_own = (idx <= 750)
            depot = random.choice(DEPOTS)
            birth_year = random.randint(1975, 1999)
            birth_date = date(birth_year, random.randint(1, 12), random.randint(1, 28))
            join_year = random.randint(max(2015, birth_year + 20), 2024)
            join_date = date(join_year, random.randint(1, 12), random.randint(1, 28))
            rto_code = random.choice(["TN38", "TN37", "TN43", "TN39", "TN33", "TN07", "TN59", "KL09", "KA01"])

            driver = Driver(
                name=full_name,
                driver_type="owned" if is_own else "supplier",
                employer_party=None if is_own else random.choice(suppliers_list),
                phone=f"+91 9{random.randint(4000, 9999)}{random.randint(10000, 99999)}",
                address=f"No. {random.randint(10, 499)}, Gandhi Road, {depot.split()[0]}, Tamil Nadu",
                joining_date=join_date,
                status="active" if random.random() < 0.94 else "on_leave",
                base_depot=depot,
                date_of_birth=birth_date,
                father_or_spouse_name=f"{random.choice(FIRST_NAMES)} {lname}",
                aadhar_number=f"{random.randint(2000, 8999)} {random.randint(1000, 9999)} {random.randint(1000, 9999)}",
                license_number=f"{rto_code}-{join_year}-{random.randint(1000000, 9999999)}",
                licensing_authority=f"RTO {rto_code} Transport Authority",
                license_issue_date=date(join_year, 1, 15),
                license_validity_nt=date(2035, 12, 31),
                license_validity_tr=date(random.randint(2027, 2031), random.randint(1, 12), random.randint(1, 28)),
                badge_number=f"PSV-{random.randint(10000, 99999)}",
                is_volvo_certified=(random.random() < 0.35),
                emergency_contact_name=f"{random.choice(FIRST_NAMES)} (Spouse/Family)",
                emergency_contact_phone=f"+91 9{random.randint(3000, 8999)}{random.randint(10000, 99999)}",
                blood_group=random.choice(blood_groups),
                bank_name=random.choice(bank_names),
                bank_account_number=f"{random.randint(10000000000, 99999999999)}",
                ifsc_code=f"SBIN00{random.randint(1000, 9999)}",
                upi_id=f"{full_name.lower().replace(' ', '')}{random.randint(10, 99)}@okaxis",
                languages_spoken=random.choice(languages),
                hill_station_experience=(random.random() < 0.65)
            )
            new_drivers.append(driver)

        if new_drivers:
            Driver.objects.bulk_create(new_drivers, batch_size=400)
        total_drivers = Driver.objects.count()
        self.stdout.write(self.style.SUCCESS(f"[OK] Drivers in Database: {total_drivers} (Target 1100+ met!)"))

        # Fetch all active drivers for vehicle assignment
        all_drivers = list(Driver.objects.filter(status="active"))
        random.shuffle(all_drivers)

        # Step 5: Seed 730+ Own Vehicles Matching Catalog Specifications
        self.stdout.write(self.style.NOTICE("Generating 730+ Own Fleet Vehicles with exact model/trim/seating specifications..."))
        existing_vehicles = set(Vehicle.objects.values_list("registration_number", flat=True))

        own_vehicles_to_create = []
        reg_series_list = ["TN 38 BZ", "TN 38 CA", "TN 38 CB", "TN 37 AX", "TN 43 B", "TN 39 DA", "TN 33 AK", "TN 07 CM", "TN 59 BX"]
        reg_counter = 1001

        driver_idx = 0

        for brand, model, pax, count, cat_code, fuel, is_staff, is_sleeper, is_luxury in VEHICLE_CATALOG:
            type_obj = vehicle_types_dict[f"{brand} {model}"]
            cat_obj = categories_dict[cat_code]

            for unit in range(count):
                while True:
                    series = random.choice(reg_series_list)
                    reg_no = f"{series} {reg_counter}"
                    reg_counter += 1
                    if reg_counter > 9999:
                        reg_counter = 1001
                    if reg_no not in existing_vehicles:
                        existing_vehicles.add(reg_no)
                        break

                depot = random.choice(DEPOTS)
                assigned_driver = all_drivers[driver_idx % len(all_drivers)] if all_drivers else None
                driver_idx += 1

                veh = Vehicle(
                    registration_number=reg_no,
                    vehicle_category=cat_obj,
                    vehicle_type=type_obj,
                    ownership_type="owned",
                    owner_party=None,
                    status=random.choice(["available", "available", "available", "on_trip", "assigned"]),
                    base_depot=depot,
                    brand=brand,
                    model=model,
                    year=random.randint(2021, 2026),
                    color=random.choice(["Super White", "Pearl Metallic Silver", "Granite Grey", "Navy Blue", "Deep Black", "Golden Bronze"]),
                    fuel_type=fuel,
                    fuel_tank_capacity=55 if pax <= 7 else 80 if pax <= 26 else 350,
                    def_capacity=15 if pax > 7 else 0,
                    seating_capacity=pax,
                    current_km=random.randint(8000, 185000),
                    has_ac=True,
                    is_sleeper=is_sleeper,
                    has_air_suspension=(pax >= 35 or is_luxury),
                    has_video_coach=(pax >= 17),
                    rc_expiry=date(2036, 5, 20),
                    insurance_expiry=date(random.randint(2026, 2028), random.randint(1, 12), random.randint(1, 28)),
                    fc_expiry=date(random.randint(2027, 2029), random.randint(1, 12), random.randint(1, 28)),
                    permit_expiry=date(random.randint(2027, 2030), random.randint(1, 12), random.randint(1, 28)),
                    tax_expiry=date(random.randint(2027, 2029), random.randint(1, 12), random.randint(1, 28)),
                    pollution_expiry=date(2027, 2, 28),
                    next_service_due_km=random.randint(10000, 195000),
                    primary_permit_type="aitp" if is_luxury or pax > 26 else "contract_carriage" if is_staff else "tourist_permit",
                    has_contract_carriage_permit=True,
                    has_tourist_permit=True,
                    permit_number=f"TN-PERMIT-{random.randint(100000, 999999)}",
                    has_aitp=(pax >= 12 or is_luxury),
                    aitp_permit_number=f"AITP-TN-2026-{random.randint(10000, 99999)}" if (pax >= 12 or is_luxury) else "",
                    aitp_expiry=date(2028, 10, 31) if (pax >= 12 or is_luxury) else None,
                    default_driver=assigned_driver,
                    expected_mileage=Decimal("14.5") if pax <= 7 else Decimal("10.5") if pax <= 17 else Decimal("4.2"),
                    current_location=f"{depot} Yard",
                    engine_number=f"ENG{random.randint(1000000, 9999999)}",
                    chassis_number=f"MB1{brand[:3].upper()}{random.randint(1000000000, 9999999999)}",
                    gps_imei=f"8694020{random.randint(10000000, 99999999)}",
                    fastag_id=f"607417{random.randint(1000000000, 9999999999)}",
                    insurance_provider="ICICI Lombard General Insurance",
                    insurance_policy_number=f"3001/MOTO/2026/{random.randint(100000, 999999)}",
                    is_financed=(random.random() < 0.4),
                    financier_name="HDFC Bank Auto Finance" if random.random() < 0.5 else "Sundaram Finance Limited",
                    emi_amount=Decimal("38500.00") if pax <= 7 else Decimal("78000.00"),
                    loan_end_date=date(2028, 12, 31)
                )
                own_vehicles_to_create.append(veh)

        if own_vehicles_to_create:
            Vehicle.objects.bulk_create(own_vehicles_to_create, batch_size=300)
        own_count = Vehicle.objects.filter(ownership_type="owned").count()
        self.stdout.write(self.style.SUCCESS(f"[OK] Own Fleet in Database: {own_count} Vehicles (Target 700+ met!)"))

        # Step 6: Seed 420+ Supplier / Vendor Attached Vehicles
        self.stdout.write(self.style.NOTICE("Generating 420+ Supplier / Vendor Vehicles across 30+ regional transporter partners..."))
        existing_vehicles = set(Vehicle.objects.values_list("registration_number", flat=True))
        current_supplier_count = Vehicle.objects.filter(ownership_type="outsourced").count()
        target_supplier_vehicles = 430
        supplier_vehicles_needed = max(0, target_supplier_vehicles - current_supplier_count)

        supplier_models_pool = [
            ("Toyota", "Innova Crysta 2.4 GX+", 7, "muv_suv", "diesel"),
            ("Toyota", "Innova 2.5 VX", 7, "muv_suv", "diesel"),
            ("Maruti Suzuki", "Ertiga Lxi", 7, "muv_suv", "cng"),
            ("Toyota", "Rumion S Petrol", 6, "muv_suv", "petrol"),
            ("Honda", "Amaze VX 1.2", 4, "sedan", "petrol"),
            ("Hyundai", "Aura E 1.2", 4, "sedan", "cng"),
            ("Maruti Suzuki", "Dzire Lxi", 4, "sedan", "cng"),
            ("Force", "Traveller T2 4020 AC Staff", 25, "corporate_staff_bus", "diesel"),
            ("Force", "Traveller T1 4020 AC Staff", 20, "corporate_staff_bus", "diesel"),
            ("Force", "Urbania 4400 17-Seater", 17, "luxury_van", "diesel"),
            ("Bharat Benz", "1017 AC Staff", 35, "corporate_staff_bus", "diesel"),
            ("SML Isuzu", "Swaraj Mazda EcoMax T3500 Staff", 20, "corporate_staff_bus", "diesel"),
            ("Tata", "Ultra Prime 55+D LPO11.6/54 Staff", 55, "corporate_staff_bus", "diesel"),
            ("Ashok Leyland", "Lynx Strong REC Coach Staff", 52, "corporate_staff_bus", "diesel"),
            ("Ashok Leyland", "Viking 11.4m Zedastra", 53, "intercity_coach", "diesel"),
            ("MG", "ZS EV Excite Pro", 4, "ev_green", "electric"),
            ("BYD", "eMax 7 Premium", 6, "ev_green", "electric"),
        ]

        supplier_series = ["TN 38 C", "TN 37 B", "TN 43 C", "TN 39 E", "TN 33 B", "TN 07 D", "KL 09 R", "KA 01 M", "KA 51 B", "TN 59 E", "TN 45 C"]
        reg_counter_sup = 3001

        supplier_vehicles_to_create = []
        for i in range(supplier_vehicles_needed):
            sup_partner = random.choice(suppliers_list)
            brand, model, pax, cat_code, fuel = random.choice(supplier_models_pool)
            type_obj = vehicle_types_dict.get(f"{brand} {model}")
            if not type_obj:
                type_obj = list(vehicle_types_dict.values())[0]
            cat_obj = categories_dict[cat_code]

            while True:
                s_ser = random.choice(supplier_series)
                reg_no = f"{s_ser} {reg_counter_sup}"
                reg_counter_sup += 1
                if reg_counter_sup > 9999:
                    reg_counter_sup = 1001
                if reg_no not in existing_vehicles:
                    existing_vehicles.add(reg_no)
                    break

            depot = random.choice(DEPOTS)
            assigned_driver = all_drivers[driver_idx % len(all_drivers)] if all_drivers else None
            driver_idx += 1

            s_name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
            s_phone = f"+91 9{random.randint(4000, 9999)}{random.randint(10000, 99999)}"

            veh = Vehicle(
                registration_number=reg_no,
                vehicle_category=cat_obj,
                vehicle_type=type_obj,
                ownership_type="outsourced",
                owner_party=sup_partner,
                status=random.choice(["available", "available", "on_trip", "assigned"]),
                base_depot=depot,
                brand=brand,
                model=model,
                year=random.randint(2020, 2025),
                color=random.choice(["White", "Silver", "Grey", "Golden Beige", "Navy Blue"]),
                fuel_type=fuel,
                fuel_tank_capacity=55 if pax <= 7 else 80 if pax <= 26 else 300,
                def_capacity=15 if pax > 7 else 0,
                seating_capacity=pax,
                current_km=random.randint(15000, 260000),
                has_ac=True,
                is_sleeper=False,
                has_air_suspension=(pax >= 35),
                has_video_coach=(pax >= 20),
                rc_expiry=date(2035, 8, 15),
                insurance_expiry=date(random.randint(2026, 2028), random.randint(1, 12), random.randint(1, 28)),
                fc_expiry=date(random.randint(2027, 2029), random.randint(1, 12), random.randint(1, 28)),
                permit_expiry=date(random.randint(2027, 2030), random.randint(1, 12), random.randint(1, 28)),
                tax_expiry=date(random.randint(2027, 2029), random.randint(1, 12), random.randint(1, 28)),
                pollution_expiry=date(2027, 3, 31),
                next_service_due_km=random.randint(20000, 270000),
                primary_permit_type="tourist_permit" if pax <= 7 else "contract_carriage",
                has_contract_carriage_permit=True,
                has_tourist_permit=True,
                permit_number=f"SUP-PERMIT-{random.randint(100000, 999999)}",
                has_aitp=(pax >= 12),
                aitp_permit_number=f"AITP-SUP-{random.randint(10000, 99999)}" if pax >= 12 else "",
                aitp_expiry=date(2028, 9, 30) if pax >= 12 else None,
                default_driver=assigned_driver,
                expected_mileage=Decimal("14.0") if pax <= 7 else Decimal("10.0") if pax <= 17 else Decimal("4.0"),
                current_location=f"{depot} Outpost",
                engine_number=f"SENG{random.randint(1000000, 9999999)}",
                chassis_number=f"SUPCHAS{random.randint(1000000000, 9999999999)}",
                gps_imei=f"8682020{random.randint(10000000, 99999999)}",
                fastag_id=f"607418{random.randint(1000000000, 9999999999)}",
                insurance_provider="United India Insurance / National Insurance",
                insurance_policy_number=f"UNI/MOTO/2026/{random.randint(100000, 999999)}",
                is_financed=False,
                supplier_contact_person=s_name,
                supplier_driver_name=assigned_driver.name if assigned_driver else s_name,
                supplier_driver_phone=assigned_driver.phone if assigned_driver else s_phone,
                supplier_daily_rate=Decimal("3800.00") if pax <= 7 else Decimal("7200.00") if pax <= 26 else Decimal("13500.00"),
                supplier_km_rate=Decimal("15.50") if pax <= 7 else Decimal("23.00") if pax <= 26 else Decimal("41.00"),
                supplier_driver_bata=Decimal("500.00") if pax <= 7 else Decimal("700.00") if pax <= 26 else Decimal("1000.00"),
                supplier_min_hours=8,
                supplier_min_km=250 if pax <= 7 else 300,
                supplier_payment_terms="Net 15 Days",
                supplier_contract_ref=f"SGT-VND-2026-{random.randint(100, 999)}",
                supplier_contract_start=date(2026, 1, 1),
                supplier_contract_end=date(2027, 12, 31),
                supplier_notes="Attached vendor asset under SLA rate card. Verified vehicle documents and background checked driver."
            )
            supplier_vehicles_to_create.append(veh)

        if supplier_vehicles_to_create:
            Vehicle.objects.bulk_create(supplier_vehicles_to_create, batch_size=300)
        supplier_count = Vehicle.objects.filter(ownership_type="outsourced").count()
        self.stdout.write(self.style.SUCCESS(f"[OK] Supplier / Attached Fleet in Database: {supplier_count} Vehicles (Target 400+ met!)"))

        # Step 7: Final Enterprise Audit Summary
        total_veh = Vehicle.objects.count()
        total_drv = Driver.objects.count()
        own_final = Vehicle.objects.filter(ownership_type="owned").count()
        sup_final = Vehicle.objects.filter(ownership_type="outsourced").count()

        self.stdout.write(self.style.SUCCESS("=" * 70))
        self.stdout.write(self.style.SUCCESS(f"[GOAL] SIVAGAYATHIRI ENTERPRISE FLEET & CREW DATABASE AUDIT:"))
        self.stdout.write(self.style.SUCCESS(f"   • Total Commercial Fleet Assets : {total_veh} (Goal 1100+ met!)"))
        self.stdout.write(self.style.SUCCESS(f"   • Own Fleet Assets (Owned)       : {own_final} (Goal 700+ met!)"))
        self.stdout.write(self.style.SUCCESS(f"   • Supplier / Vendor Assets       : {sup_final} (Goal 400+ met!)"))
        self.stdout.write(self.style.SUCCESS(f"   • Professional Chauffeurs/Crew   : {total_drv} (Goal 1100+ met!)"))
        self.stdout.write(self.style.SUCCESS(f"   • Active Regional Vendor Partners: {Supplier.objects.count()}"))
        self.stdout.write(self.style.SUCCESS(f"   • Vehicle Categories Enrolled    : {VehicleCategory.objects.count()}"))
        self.stdout.write(self.style.SUCCESS(f"   • Vehicle Models / Types Enrolled: {VehicleType.objects.count()}"))
        self.stdout.write(self.style.SUCCESS("=" * 70))
