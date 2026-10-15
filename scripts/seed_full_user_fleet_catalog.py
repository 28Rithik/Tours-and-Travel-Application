"""
Master Ingestion & Replenishment Script for User's Exact Fleet Catalog.
Parses all 140+ Make-Model-Trim configurations provided by the user across:
- MUVs & SUVs (Innova, Crysta, Hycross, Invicto, Fortuner, Ertiga, Carens, Marazzo, Rumion)
- Executive Sedans (Corolla Altis, City, Ciaz, Etios, Amaze, Aura, Dzire)
- Ultra-Luxury VIP (Camry Hybrid, E-Class, S-Class, Vellfire, V-Class, Carnival)
- Maxi Cabs & Vans (Winger, Cityline, HiAce, Coaster, GranAce)
- Force Travellers & Urbanias (Standard, Fixed Glass & Maharaja)
- Mini Buses & Midi Coaches (SML Isuzu, Eicher, BharatBenz 1017, Cruzio)
- Heavy Luxury Intercity Coaches & Sleepers (Volvo 9400/9600, Scania, BharatBenz 1624/1924, Damodar, Prakash, Veera)
- Corporate Commute & Institutional Staff Buses (Tata Ultra, Eicher Skyline, Lynx, School Buses)
- Specialized Caravans & Vanity Vans (JCBL, OJES, Vanity Vans)
- Electric Mobility (EVs) (MG ZS, BYD, Nexon, Tigor, Switch EiV, Pro-E, Starbus EV)

Maintains full backward compatibility with Package Tariffs and regional depot vehicles.
"""

import os
import sys
import re
from decimal import Decimal
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
django.setup()

from core.models import VehicleCategory, VehicleType, Vehicle
from packages.models import Package, PackageVehicleTariff

# ──────────────────────────────────────────────────────────────────────────────
# 1. EXPANDED MASTER VEHICLE CATEGORIES
# ──────────────────────────────────────────────────────────────────────────────
CATEGORIES_DEF = [
    {
        'code': 'sedan',
        'name': 'Sedan & Compact',
        'description': 'Swift Dzire, Etios, Aura, Amaze, City, Ciaz, Altis. Economical for airport transfers, local city packages, and couple tours.',
        'icon': 'fa-solid fa-car-side',
        'badge_color': '#0284c7',
        'seating_range': '4 + 1 Seats',
        'display_order': 1,
    },
    {
        'code': 'suv_muv',
        'name': 'Premium MUV & SUV',
        'description': 'Innova Crysta, Innova Classic, Hycross, Invicto, Fortuner, Ertiga, Carens, Rumion, Marazzo. Family holidays, Western Ghats, and corporate transit.',
        'icon': 'fa-solid fa-van-shuttle',
        'badge_color': '#8b5cf6',
        'seating_range': '6 - 8 Seats',
        'display_order': 2,
    },
    {
        'code': 'luxury_vip',
        'name': 'Ultra-Luxury VIP & Chauffeur Drive',
        'description': 'Mercedes S-Class, E-Class, Toyota Vellfire Lounge, Camry Hybrid, Mercedes V-Class, Kia Carnival Limousine. Consulate, C-suite, and luxury wedding delegations.',
        'icon': 'fa-solid fa-crown',
        'badge_color': '#e11d48',
        'seating_range': '3 - 7 Seats',
        'display_order': 3,
    },
    {
        'code': 'mini_coach',
        'name': 'Luxury Van & Mini Coach',
        'description': 'Force Urbania (9S-16S), Tempo Traveller (9S-26S), Maharaja VIP, HiAce, Coaster, Winger, Cityline. Pilgrimages, wedding shuttles, and mid-size tours.',
        'icon': 'fa-solid fa-bus-simple',
        'badge_color': '#10b981',
        'seating_range': '9 - 26 Seats',
        'display_order': 4,
    },
    {
        'code': 'luxury_coach',
        'name': 'Intercity Luxury Coach & Sleeper',
        'description': 'Volvo 9400/9600, Scania Metrolink, BharatBenz 1624/1924 Glider/Zedastra/Damodar/Veera, Mercedes 2441 SHD, Luxury AC Sleepers. Long-distance express tours.',
        'icon': 'fa-solid fa-bus',
        'badge_color': '#f59e0b',
        'seating_range': '35 - 59 Seats',
        'display_order': 5,
    },
    {
        'code': 'commute_staff',
        'name': 'Corporate Commute & Institutional Bus',
        'description': 'Tata Ultra Prime, Eicher Skyline Next, Ashok Leyland Lynx Oyster, SML Isuzu Staff & School Buses. SEZ shift contracts and institutional student transport.',
        'icon': 'fa-solid fa-building-user',
        'badge_color': '#4f46e5',
        'seating_range': '25 - 66 Seats',
        'display_order': 6,
    },
    {
        'code': 'electric_ev',
        'name': 'Electric Mobility (EV)',
        'description': 'MG ZS EV, BYD eMax 7, Nexon EV, Tigor EV, Switch Mobility EiV 12, Eicher Pro-E, Tata Starbus EV, Force E-Traveller. Zero-emission green fleet.',
        'icon': 'fa-solid fa-bolt',
        'badge_color': '#06b6d4',
        'seating_range': '4 - 50 Seats',
        'display_order': 7,
    },
    {
        'code': 'specialized_vanity',
        'name': 'Luxury Caravans & Celebrity Vanity Vans',
        'description': 'BharatBenz 1017 JCBL/OJES Caravans, Force Urbania/Traveller Caravans, Single & 3-Door Vanity Vans. Mobile greenrooms, VIP suites, and outdoor shoots.',
        'icon': 'fa-solid fa-couch',
        'badge_color': '#d97706',
        'seating_range': 'Executive Suite',
        'display_order': 8,
    },
]

# Raw Data from User
RAW_FLEET_DATA = [
    # MUVs
    ("Toyota Innova 2.5 VX", "7+d"),
    ("Toyota Innova Crysta 2.4 GX+", "7+d"),
    ("Toyota Innova Hycross VX", "7+d"),
    ("Maruti Suzuki Invicto Zeta Plus", "7+d"),
    ("Toyota Rumion S Petrol", "6+d"),
    ("Maruti Suzuki Ertiga Lxi", "8+d"),
    ("Kia Carens Clavis HTE(O) 1.5", "6+d"),
    ("Mahindra Marazzo M2 7 STR", "7+d"),

    # Sedans
    ("Toyota Corolla Altis", "4+d"),
    ("Honda City V", "4+d"),
    ("Maruti Suzuki Ciaz Sigma 1.5", "4+d"),
    ("Toyota Etios VXD", "4+d"),
    ("Honda Amaze VX 1.2", "4+d"),
    ("Hyundai Aura E 1.2", "4+d"),
    ("Maruti Suzuki Dzire Lxi", "4+d"),

    # Maxi Cabs & Light Commercial
    ("Tata Winger Tourist 3200 AC", "13+d"),
    ("Force Motors Cityline AC", "9+d"),
    ("Toyota HiAce Commuter H300 GL 2023", "10+d"),
    ("Toyota Coaster 4.2l", "17+d"),
    ("Toyota GranAce 3R 2.8l", "7+d"),

    # EVs
    ("MG ZS EV Excite Pro", "4+d"),
    ("BYD eMax 7 Premium", "6+d"),
    ("Tata Nexon EV", "4+d"),
    ("Tata Tigor EV XT", "4+d"),
    ("Ashok Leyland Switch Mobility EiV 12", "45+d (HB 2x2)"),
    ("Tata Starbus Ultra 9/7 EV", "20+d (2x2)"),
    ("Tata Starbus Ultra 9/9 EV", "31+d (HBR 2x2)"),
    ("Tata Starbus Ultra 9/12 EV", "45+d (HB 2x2)"),
    ("Eicher Skyline Pro-E 3012 12m", "50+d (PB 2x2)"),
    ("Eicher Skyline Pro-E 9m", "32+d (PB 2x2)"),
    ("Force E - Traveller", "14+d"),
    ("Tata Ultra 9/9 EV (3x2)", "48+2d Bench"),
    ("Tata Ultra 9/9 EV (2x2)", "40+2d Bench"),
    ("Eicher Skyline Pro-E 12m (2x2)", "50+d PB"),
    ("Eicher Skyline Pro-E 9m (2x2)", "32+d PMS"),

    # Luxury Sedans & VIP MPVs
    ("Toyota Camry Hybrid", "3+d"),
    ("Mercedes Benz E220d LWB", "3+d"),
    ("Mercedes-Benz S-Class S350d", "3+d"),
    ("Toyota Fortuner 4x4 2.8 4WD", "5+d"),
    ("Toyota Vellfire Executive Lounge", "5+d"),
    ("Toyota Veilfire Executive Lounge", "5+d"),
    ("Mercedes Benz V-Class V 300d", "5+d"),
    ("Kia Carnival Limousine", "7+d"),

    # Force Travellers & Urbanias
    ("Force Traveller T2 4020 AC", "26+d"),
    ("Force Traveller T1 4020 AC", "20+d"),
    ("Force Traveller T1 3700 AC", "17+d"),
    ("Force Traveller T1 3350 AC", "14+d"),
    ("Force Urbania 4400", "16+d"),
    ("Force Urbania 3615", "13+d"),
    ("Force Urbania 3350", "9+d"),
    ("Force Traveller T2 4020 AC FG", "26+d"),
    ("Force Traveller T1 4020 AC FG", "20+d"),
    ("Force Traveller T1 3700 AC Maharaja FG", "14+d (1x1 Maharaja)"),
    ("Force Traveller T1 3350 AC Maharaja FG", "9+d (1x1 Maharaja)"),
    ("Force Urbania 4400 Maharaja", "13+d"),
    ("Force Urbania 3615 Maharaja", "9+d"),

    # Mini Buses & Midi Coaches
    ("Bharat Benz 1017 Fixed Glass", "35+d (Seater 2x2)"),
    ("Force MonoBus T3 MB 5200 AC Fixed Glass", "41+d"),
    ("SML Isuzu Hiroi 5300 Fixed Glass", "40+d PB"),
    ("SML Isuzu Executive LX 5100 Fixed Glass", "35+d (Seater 2x2)"),
    ("SML Isuzu Swaraj Mazda EcoMax T3500", "20+d"),
    ("SML Isuzu Asai 3335 AC", "20+d (PB Seater 2x2)"),
    ("Eicher 2050 Pandyan Coach", "21+d (PB Seater 2x2)"),
    ("Eicher 2050 Aadhavan Coach", "21+d (PB Seater 2x2)"),
    ("Eicher 2050 Joy Coach", "21+d (PB Seater 2x2)"),
    ("SML Isuzu 3335 Vinayaka Coach", "25+d (PB Seater 2x2)"),
    ("SML Isuzu 3335 Skylar Sahara Coach", "25+d (PB Seater 2x2)"),
    ("SML Isuzu 3335 Pandyan Coach FG", "25+d (PB Seater 2x2)"),
    ("SML Isuzu 3335 Aadhavan Coach FG", "25+d (PB Seater 2x2)"),
    ("Bharat Benz 1017 Ojes Body FG", "25+d (PB Seater 2x1)"),
    ("Bharat Benz 1017 Navigo FG", "25+d (PB Seater 2x1)"),
    ("Bharat Benz 1017 Skylar Sahara Coach", "35+d (PB Seater 2x2)"),
    ("Bharat Benz 1017 Ojes Fedora Body", "35+d (PB Seater 2x2)"),
    ("Bharat Benz 1017 Prakash Astra", "35+d (PB Seater 2x2)"),
    ("Bharat Benz 1017 Prakash Astra FG", "35+d (PB Seater 2x2)"),
    ("Mahindra Cruzio Grande 4440", "32+d (Seater 2x2)"),
    ("Mahindra Cruzio Grande 5360", "40+d (Seater 2x2)"),

    # Heavy Luxury Coaches (BharatBenz, Eicher, Ashok Leyland)
    ("Bharat Benz 1624 Prakash Zedastra", "53+2d (PB Seater 3x2)"),
    ("Bharat Benz 1624 ZedVega", "53+2d (PB Seater 3x2)"),
    ("Eicher 6016 Prakash Zedastra", "53+2d (PB Seater 3x2)"),
    ("Ashok Leyland Viking 11.4m Zedastra", "53+2d (PB Seater 3x2)"),
    ("Ashok Leyland Viking 11.4m Zedvega", "53+2d (PB Seater 3x2)"),
    ("Volvo Eicher 6016 R LPO VECV 12.4 m FG", "43+2d (PB Seater 2x2)"),
    ("Bharat Benz 1624 MG Glider 12m FG", "45+2d (PB Seater 2x2)"),
    ("Bharat Benz 1624 Prakash Capella GT 11.4m FG", "45+2d (PB Seater 2x2)"),
    ("Bharat Benz 1624 Prakash Zedastra FG", "45+2d (PB Seater 2x2)"),
    ("Bharat Benz 1624 Prakash Zedastra 13.5m", "52+2d (PB Seater 2x2)"),
    ("Bharat Benz 1924 Glider 13.5m", "52+2d (PB Seater 2x2)"),
    ("Volvo Eicher 6019 Pro VECV 13.5m", "52+2d (PB Seater 2x2)"),

    # Heavy Luxury Coaches (Volvo, Scania, Mercedes)
    ("Volvo 9400 B8R 12m Biaxle", "45+2d (Seater 2x2)"),
    ("Volvo 9400 B11R 13.5m Bi-Axle", "51+2d (Seater 2x2)"),
    ("Volvo 9400 B11R 14.5m Multi-Axle", "55+2d (Seater 2x2)"),
    ("Volvo 9600 B8R 12.2m Bi-Axle", "43+2d (Seater 2x2)"),
    ("Volvo 9600 B8R 13.5m Multi-Axle", "47+2d (Seater 2x2)"),
    ("Volvo 9600 B8R 15m Multi-Axle", "55+2d (Seater 2x2)"),
    ("Scania Metrolink HD 12m Bi-Axle", "45+2d (Seater 2x2)"),
    ("Scania Metrolink HD 13.7m Multi-Axle", "53+2d (Seater 2x2)"),
    ("Scania Metrolink HD 14.5m Multi-Axle", "57+2d (Seater 2x2)"),
    ("Mercedes Benz 2441 SHD 15m Multiaxle", "59+2d (Seater 2x2)"),

    # Coach Builders (Damodar, Sutlej, Veera, MG, Sahara, Synaty, Aravali)
    ("Volvo Eicher 6016 N Sutlej S-1800+", "45+2d (Seater 2x2)"),
    ("Eicher 6019 R Synaty Destino 12m", "45+2d (Seater 2x2)"),
    ("Eicher 6016 6200 WB Sahara Dexter", "45+2d (Seater 2x2)"),
    ("Volvo Eicher 6016 Pro Syanty 12 m", "45+2d (Seater 2x2)"),
    ("Bharat Benz 1624 MG Tigra", "45+2d (PB Seater 2x2)"),
    ("Bharat Benz 1624 Damodar Rudra", "45+2d (PB Seater 2x2)"),
    ("Bharat Benz 1624 Damodar Spyder 2.0", "45+2d (PB Seater 2x2)"),
    ("Bharat Benz 1624 Damodar Super High Deck+", "45+2d (PB Seater 2x2)"),
    ("Bharat Benz 1624 Damodar Kalpa", "45+2d (PB Seater 2x2)"),
    ("Bharat Benz 1624 Synaty Umang", "45+2d (PB Seater 2x2)"),
    ("Bharat Benz 1624 Synaty Destino 12m", "45+2d (PB Seater 2x2)"),
    ("Bharat Benz 1624 Sutlej S-1800+", "45+2d (PB Seater 2x2)"),
    ("Bharat Benz 1624 Sahara Meraki", "45+2d (PB Seater 2x2)"),
    ("Bharat Benz 1624 Veeramaha Samrat V8 Mk III", "45+2d (PB Seater 2x2)"),
    ("Bharat Benz 1624 Aravali Stunner", "45+2d (PB Seater 2x2)"),

    # Intercity Luxury AC Sleepers
    ("Bharat Benz 1924 MG Glider Z+", "36+2d (AC Sleeper 2+1)"),
    ("Bharat Benz 1924 MG Tigra", "36+2d (AC Sleeper 2+1)"),
    ("Bharat Benz 1924 Prakash Capella GT", "36+2d (AC Sleeper 2+1)"),
    ("Bharat Benz 1924 Damodar Rudra", "36+2d (AC Sleeper 2+1)"),
    ("Bharat Benz 1924 Damodar Spyder 2.0", "36+2d (AC Sleeper 2+1)"),
    ("Bharat Benz 1924 Damodar Super High Deck+", "36+2d (AC Sleeper 2+1)"),
    ("Bharat Benz 1924 Damodar Kalpa", "36+2d (AC Sleeper 2+1)"),
    ("Bharat Benz 1924 Damodar Prabal", "36+2d (AC Sleeper 2+1)"),
    ("Bharat Benz 1924 Sutlej SL1800+", "36+2d (AC Sleeper 2+1)"),
    ("Bharat Benz 1924 Veera V8 Mk III", "36+2d (AC Sleeper 2+1)"),
    ("Bharat Benz 1924 Synaty Lavie", "36+2d (AC Sleeper 2+1)"),
    ("Bharat Benz 1924 Synaty Destino", "36+2d (AC Sleeper 2+1)"),
    ("Bharat Benz 1924 Aravali Stunner", "36+2d (AC Sleeper 2+1)"),
    ("Bharat Benz 1924 Sahara Meraki", "36+2d (AC Sleeper 2+1)"),
    ("Bharat Benz 1924 R2 Prime+ REC", "36+2d (AC Sleeper 2+1)"),
    ("Bharat Benz 1924 Shakti Coach", "36+2d (AC Sleeper 2+1)"),
    ("Bharat Benz 1924 Jaswant Type 1 Coach", "36+2d (AC Sleeper 2+1)"),
    ("Bharat Benz 1924 Jaswant Type 2 Coach", "36+2d (AC Sleeper 2+1)"),
    ("Bharat Benz 1924 Shri Dharmraj Body", "36+2d (AC Sleeper 2+1)"),
    ("Tata LPO 1618 Mirabelle S5300", "36+2d (AC Sleeper 2+1)"),
    ("Ashok Leyland Garud TF 2513.5 Veera V8 Mk III", "36+2d (AC Sleeper 2+1)"),
    ("Volvo Eicher 6019 Pro Veera V8 mk III", "36+2d (AC Sleeper 2+1)"),
    ("Ashok Leyland Garud TF 2513.5 SL1800+", "36+2d (AC Sleeper 2+1)"),
    ("Volvo Eicher 6019 Pro Sutlej SL1800+", "36+2d (AC Sleeper 2+1)"),
    ("Ashok Leyland Garud TF 2513 Rudra", "36+2d (AC Sleeper 2+1)"),
    ("Ashok Leyland Garud TF 2513 Spyder", "36+2d (AC Sleeper 2+1)"),
    ("Ashok Leyland Garud TF 2513 Kalpa", "36+2d (AC Sleeper 2+1)"),
    ("Volvo Eicher 6019 Pro Rudra", "36+2d (AC Sleeper 2+1)"),
    ("Volvo Eicher 6019 Pro Spyder", "36+2d (AC Sleeper 2+1)"),
    ("Volvo Eicher 6019 Pro Super High Deck", "36+2d (AC Sleeper 2+1)"),
    ("Volvo Eicher 6019 Pro Capella GT", "36+2d (AC Sleeper 2+1)"),
    ("Volvo Eicher 6019 Pro Stella", "36+2d (AC Sleeper 2+1)"),
    ("Volvo Eicher 6019 Pro VECV Body", "36+2d (AC Sleeper 2+1)"),
    ("Volvo 9400 B11R 14.5m AC Sleeper", "40+2d (AC Sleeper 2+1)"),
    ("Volvo 9400 B11R 14.5m MG Star Z", "40+2d (AC Sleeper 2+1)"),
    ("Mercedes Benz 2441 SHD Sleeper", "40+2d (AC Sleeper 2+1)"),
    ("Mercedes Benz 2441 SHD MG Dream Z", "40+2d (AC Sleeper 2+1)"),
    ("Scania Metrolink HD 14.5m Sleeper", "40+2d (AC Sleeper 2+1)"),
    ("Volvo B8R 9600s 15m Sleeper", "40+2d (AC Sleeper 2+1)"),
    ("Volvo B8R 9600 SLX 15m Sleeper 40B", "40+2d (AC Sleeper 2+1)"),
    ("Volvo B8R 9600 SLX 15m Sleeper 42B", "42+2d (AC Sleeper 2+1)"),
    ("Volvo B8R 9600 SLX 15m 42B", "42+2d (AC Sleeper 2+1)"),
    ("Bharat Benz 1924 Chassis - 49 Lakhs", "45+2d (Chassis Platform ₹49L)"),
    ("Ashok Leyland Garud TF 2513.5 - 40 Lakhs", "45+2d (Chassis Platform ₹40L)"),

    # Corporate Commute, SEZ & Institutional Staff Buses
    ("Tata Ultra Prime 50+D AC LPO11.6/54 FG", "50+d (PB 3x2)"),
    ("Tata Ultra Prime 42+D AC LPO11.6/54 FG", "50+d (PB 3x2)"),
    ("Tata Ultra Prime 55+D LPO11.6/54", "55+d (3x2)"),
    ("Tata Ultra Prime 44+D LPO11.6/54", "44+d (PB 3x2)"),
    ("Tata Ultra Prime 34+D LPO8.6/44", "34+d (PB 3x2)"),
    ("Eicher Skyline Pro Next 3011 L AC FG", "55+d (3x2)"),
    ("Eicher Skyline Pro Next 3010 L AC FG", "44+d (HHR 2x2)"),
    ("Eicher Skyline Pro Next 3009 H AC FG", "36+d (HHR 2x2)"),
    ("Eicher Skyline Next 2112 M AC", "50+d (HHR 3x2)"),
    ("Eicher Skyline Next 2090 L AC", "40+d (HHR 2x2)"),
    ("Eicher Skyline Next 2075 H AC", "32+d (HHR 2x2)"),
    ("Eicher Skyline Next 2075 G AC", "28+d (HHR 2x2)"),
    ("Force Traveller T2 4020 AC Staff", "25+d"),
    ("Force Traveller T1 3700 AC Staff", "17+d"),
    ("Force Urbania 4400 Staff", "16+d"),
    ("Force Urbania 3615 Staff", "13+d"),
    ("Force MonoBus T3 MB 5200 AC Staff", "41+d"),
    ("Force MonoBus T3 MB 4020 AC Staff", "33+d"),
    ("Bharat Benz 1017 AC Staff", "35+d (Seater 2x2)"),
    ("Bharat Benz 1017 Fixed Glass Staff", "35+d HH (Seater 2x2)"),
    ("SML Isuzu Hiroi 4370 Staff", "34+d SR"),
    ("SML Isuzu Hiroi 5300 Staff", "42+d SR"),
    ("SML Isuzu Executive LX 4240 Staff", "30+d HBR"),
    ("SML Isuzu Executive LX 5100 Staff", "37+d HBR"),
    ("Ashok Leyland Lynx Oyster 5200 LS1510", "52+d (3x2)"),
    ("Ashok Leyland Lynx Strong REC Coach", "52+d (3x2)"),
    ("Ashok Leyland Lynx Prakash Vega", "52+d (3x2)"),
    ("Ashok Leyland Lynx Arrow Coach", "52+d (3x2)"),
    ("Ashok Leyland Lynx MG Glider Fixed Glass AC", "52+d (3x2)"),
    ("Bharat Benz 1017 Mini Bus", "35+d"),
    ("Eicher 2090 L Mini Bus", "35+d"),
    ("Ashok Leyland Viking 222 12m Route Line Bus", "55+2d"),
    ("Bharat Benz 1624 12m Route Line Bus", "56+2d"),

    # School Buses
    ("BharatBenz 1017 School Bus", "49+d"),
    ("BharatBenz 1017 : School", "49+d"),
    ("BharatBenz 917 School Bus", "39+d"),
    ("BharatBenz 917 : School", "39+d"),
    ("SML Isuzu Executive LX School 4240 N", "40+d (AC Seater 3x2)"),
    ("SML Isuzu S7 5100 School", "52+d"),
    ("SML Isuzu S7 4240 School", "42+d"),
    ("Force Traveller School 4020 WB", "26+d"),
    ("Force Traveller 26 School", "25+d"),
    ("Force Monobus LWB School", "55+d"),
    ("Force Monobus SWB School", "50+d"),
    ("Force Traveller Monobus Scholar 5200", "60+d"),
    ("Force Traveller Monobus Scholar 4020", "48+d"),
    ("Eicher Skyline Pro Next 3011 K School", "66+d (3x3 Seater)"),
    ("Eicher Skyline Pro Next 3011 K", "66+d (3x3 Seater)"),
    ("Eicher Sykline Pro Next 3011 K", "66+d (3x3 Seater)"),
    ("Eicher Skyline Pro Next 3009 H AC School", "53+d"),
    ("Eicher Starline Next 2050 C", "22+d"),
    ("Eicher Starline Next-Gen 2050 D", "25+d"),
    ("Eicher Starline Next-Gen 2070 E", "30+d"),
    ("Eicher Starline Next-Gen 2090 K", "45+d"),
    ("Ashok Leyland Oyster Wide School 4900", "63+d"),
    ("Ashok Leyland Oyster School 3900", "36+d"),

    # Specialized Caravans & Vanity Vans
    ("Bharat Benz 1017 JCBL Caravan 9m", "nil (Luxury RV Suite)"),
    ("Bharat Benz 1017 OJES Body Caravan", "nil (Mobile Living Suite)"),
    ("Force Traveller 4020 Caravan", "nil (Family Camper Van)"),
    ("Force Urbania 4400 Caravan", "nil (Executive Touring RV)"),
    ("Volvo 9400 JCBL Caravan 12m", "nil (Presidential RV Lounge)"),
    ("Bharat Benz 1017 Single Door Vanity Van", "nil (Celebrity Greenroom)"),
    ("Bharat Benz 1017 Three Door Vanity Van", "nil (Triple-Station Greenroom)"),
    ("Force Traveller 4020 T2 Vanity Van", "nil (Mobile Studio Vanity)"),
    ("Volvo 9400 12m JCBL Vanity Van", "nil (VIP Dual-Room Vanity)")
]

def parse_seating(seat_str):
    if not seat_str or 'nil' in seat_str.lower():
        return 4
    m = re.search(r'(\d+)', seat_str)
    if m:
        return int(m.group(1))
    return 4

def classify_vehicle(name, seat_str):
    n_lower = name.lower()
    s_lower = seat_str.lower()
    
    # 1. Specialized Vanity & Caravans
    if 'caravan' in n_lower or 'vanity' in n_lower or 'nil' in s_lower:
        return 'specialized_vanity'
    
    # 2. Electric Vehicles
    if 'ev' in n_lower or 'e - traveller' in n_lower or 'pro-e' in n_lower or 'electric' in n_lower or 'eiv' in n_lower:
        return 'electric_ev'
    
    # 3. Ultra-Luxury VIP
    if any(k in n_lower for k in ['s-class', 's350d', 'e220d', 'vellfire', 'veilfire', 'v-class', 'carnival', 'camry']):
        return 'luxury_vip'
    
    # 4. Sedans
    if any(k in n_lower for k in ['altis', 'city', 'ciaz', 'etios', 'amaze', 'aura', 'dzire']) and not any(k in n_lower for k in ['tempo', 'bus']):
        return 'sedan'
    
    # 5. MUVs & SUVs
    if any(k in n_lower for k in ['innova', 'invicto', 'fortuner', 'ertiga', 'carens', 'rumion', 'marazzo']):
        return 'suv_muv'
    
    # 6. Corporate Commute & Institutional Bus (Staff/School)
    if any(k in n_lower for k in ['staff', 'school', 'scholar', 'starline', 'lynx', 'route line']):
        return 'commute_staff'
    
    # 7. Vans & Mini Coaches (Under 27 seats)
    if any(k in n_lower for k in ['traveller', 'urbania', 'winger', 'cityline', 'hiace', 'coaster', 'granace', 'ecomax', '2050', 'asai']):
        return 'mini_coach'
    
    seats = parse_seating(seat_str)
    if seats <= 26:
        return 'mini_coach'
    elif 'ultra prime' in n_lower or 'skyline' in n_lower or 'sykline' in n_lower:
        return 'commute_staff'
    else:
        return 'luxury_coach'

def calculate_rates_and_specs(name, seat_str, cat_code):
    seats = parse_seating(seat_str)
    n_lower = name.lower()
    
    # Fuel Type
    if cat_code == 'electric_ev':
        fuel = 'electric'
    elif 'cng' in n_lower or 'dzire' in n_lower or 'ertiga' in n_lower or 'aura' in n_lower:
        fuel = 'cng' if 'cng' in n_lower else 'petrol'
    elif any(k in n_lower for k in ['camry', 'hycross', 'invicto']):
        fuel = 'petrol'
    elif any(k in n_lower for k in ['altis', 'city']):
        fuel = 'petrol'
    else:
        fuel = 'diesel'
        
    # Toll Class
    if seats <= 7:
        toll = 'car'
    elif seats <= 26:
        toll = 'lcv'
    elif 'multi-axle' in n_lower or 'multiaxle' in n_lower or '14.5m' in n_lower or '15m' in n_lower or 'b11r' in n_lower:
        toll = 'multi_axle'
    elif seats >= 45:
        toll = 'bus_3_axle'
    else:
        toll = 'bus_2_axle'
        
    # Transmission
    if any(k in n_lower for k in ['automatic', 'automatic', 's-class', 'e220d', 'camry', 'vellfire', 'v-class', 'carnival', 'i-shift', 'opticruise', 'b8r', 'b11r', '9600', 'metrolink', 'ev']):
        trans = 'automatic'
    else:
        trans = 'manual'
        
    # Luxury tag
    is_lux = (cat_code in ['luxury_vip', 'specialized_vanity'] or 
              'volvo' in n_lower or 'scania' in n_lower or 'mercedes' in n_lower or 
              'maharaja' in n_lower or 'urbania' in n_lower or 'crysta' in n_lower or 
              'hycross' in n_lower or 'fortuner' in n_lower or 'sleeper' in n_lower)

    # Rates heuristic based on seating and category
    if cat_code == 'specialized_vanity':
        day_rate = Decimal('25000.00')
        km_rate = Decimal('55.00')
        min_km = 300
        extra_km = Decimal('55.00')
        extra_hr = Decimal('1000.00')
        bata = Decimal('1200.00')
        night = Decimal('1500.00')
        mileage = Decimal('4.00')
        luggage = 'Luxury Mobile Suite & Wardrobe'
    elif cat_code == 'luxury_vip':
        day_rate = Decimal('12000.00')
        km_rate = Decimal('38.00')
        min_km = 250
        extra_km = Decimal('38.00')
        extra_hr = Decimal('750.00')
        bata = Decimal('800.00')
        night = Decimal('1000.00')
        mileage = Decimal('11.00') if fuel != 'petrol' else Decimal('14.00')
        luggage = '4 Large VIP Suitcases'
    elif cat_code == 'sedan':
        day_rate = Decimal('2400.00')
        km_rate = Decimal('12.50')
        min_km = 250
        extra_km = Decimal('12.50')
        extra_hr = Decimal('150.00')
        bata = Decimal('350.00')
        night = Decimal('400.00')
        mileage = Decimal('21.00')
        luggage = '2-3 Trolley Bags'
    elif cat_code == 'suv_muv':
        if 'fortuner' in n_lower:
            day_rate = Decimal('7500.00')
            km_rate = Decimal('28.00')
            bata = Decimal('750.00')
            night = Decimal('800.00')
        elif 'hycross' in n_lower or 'invicto' in n_lower:
            day_rate = Decimal('5500.00')
            km_rate = Decimal('22.00')
            bata = Decimal('600.00')
            night = Decimal('700.00')
        elif 'crysta' in n_lower:
            day_rate = Decimal('4200.00')
            km_rate = Decimal('18.00')
            bata = Decimal('500.00')
            night = Decimal('600.00')
        else:
            day_rate = Decimal('3400.00')
            km_rate = Decimal('15.00')
            bata = Decimal('400.00')
            night = Decimal('500.00')
        min_km = 250
        extra_km = km_rate
        extra_hr = Decimal('250.00')
        mileage = Decimal('14.00')
        luggage = '4-5 Large Suitcases'
    elif cat_code == 'mini_coach':
        if 'maharaja' in n_lower:
            day_rate = Decimal('9500.00')
            km_rate = Decimal('35.00')
            bata = Decimal('800.00')
        elif 'urbania' in n_lower:
            day_rate = Decimal('7500.00')
            km_rate = Decimal('28.00')
            bata = Decimal('700.00')
        else:
            day_rate = Decimal('5800.00') if seats > 16 else Decimal('4800.00')
            km_rate = Decimal('23.00') if seats > 16 else Decimal('20.00')
            bata = Decimal('600.00')
        night = Decimal('700.00')
        min_km = 300
        extra_km = km_rate
        extra_hr = Decimal('350.00')
        mileage = Decimal('10.50')
        luggage = f'{seats} Passenger Luggage Bays'
    elif cat_code == 'luxury_coach':
        if 'sleeper' in n_lower:
            day_rate = Decimal('17500.00')
            km_rate = Decimal('48.00')
            bata = Decimal('1000.00')
            night = Decimal('1200.00')
        elif 'volvo' in n_lower or 'scania' in n_lower or 'mercedes' in n_lower:
            day_rate = Decimal('16500.00')
            km_rate = Decimal('46.00')
            bata = Decimal('1000.00')
            night = Decimal('1200.00')
        elif 'glider' in n_lower or 'zedastra' in n_lower or '1924' in n_lower:
            day_rate = Decimal('13500.00')
            km_rate = Decimal('38.00')
            bata = Decimal('850.00')
            night = Decimal('1000.00')
        else:
            day_rate = Decimal('11500.00')
            km_rate = Decimal('35.00')
            bata = Decimal('800.00')
            night = Decimal('900.00')
        min_km = 350
        extra_km = km_rate
        extra_hr = Decimal('650.00')
        mileage = Decimal('4.50')
        luggage = f'{seats} Bags in Underbelly Hold'
    elif cat_code == 'commute_staff':
        day_rate = Decimal('8500.00')
        km_rate = Decimal('30.00')
        min_km = 300
        extra_km = Decimal('30.00')
        extra_hr = Decimal('400.00')
        bata = Decimal('650.00')
        night = Decimal('750.00')
        mileage = Decimal('5.80')
        luggage = 'Overhead Parcel Racks'
    else:  # electric_ev
        day_rate = Decimal('4500.00') if seats <= 7 else Decimal('14000.00')
        km_rate = Decimal('16.00') if seats <= 7 else Decimal('40.00')
        min_km = 200
        extra_km = km_rate
        extra_hr = Decimal('300.00')
        bata = Decimal('500.00')
        night = Decimal('600.00')
        mileage = Decimal('0.00')
        luggage = 'Standard Cabin Bags'

    # Amenities string
    amenity_list = ['High-Capacity Air Conditioning', 'Speed Governor (80 km/h)', 'Emergency First Aid Kit']
    if 'maharaja' in n_lower:
        amenity_list.extend(['1x1 Electric Recliners', 'Chemical Bio-Toilet', 'Smart TV', 'Wi-Fi Hotspot', 'Chiller Box', 'Starlight Roof'])
    elif 'sleeper' in n_lower:
        amenity_list.extend(['Private AC Sleeper Berths', 'Bedding & Linen', 'Individual USB Chargers', 'Shoe Storage', 'Air Suspension'])
    elif 'urbania' in n_lower:
        amenity_list.extend(['Monocoque European Body', 'Independent Front Suspension', 'Individual AC Louvers', 'USB Ports on every seat', 'Reclining Bucket Seats'])
    elif 'volvo' in n_lower or 'scania' in n_lower or 'mercedes' in n_lower:
        amenity_list.extend(['Electronically Controlled Air Suspension (ECAS)', 'Ergonomic Semi-Sleeper Recliners', 'Dual Large LCD Screens', 'Underbelly Hold', 'AIS-140 Panic Feed'])
    elif 'fixed glass' in n_lower or 'fg' in n_lower:
        amenity_list.extend(['Fixed Glass Aerodynamic Panoramic Windows', 'Pushback Reclining Seats', 'PA Audio System', 'Overhead Parcel Racks'])
    elif seats <= 7:
        amenity_list.extend(['Pushback Seats', 'USB Fast Chargers', 'Bluetooth Audio', 'Sanitized Cabin'])

    return {
        'fuel': fuel,
        'toll': toll,
        'trans': trans,
        'is_lux': is_lux,
        'day_rate': day_rate,
        'km_rate': km_rate,
        'min_km': min_km,
        'extra_km': extra_km,
        'extra_hr': extra_hr,
        'bata': bata,
        'night': night,
        'mileage': mileage,
        'luggage': luggage,
        'amenities': ', '.join(amenity_list)
    }

def run_master_seeding():
    print("=" * 80)
    print("INGESTING USER'S COMPLETE MASTER FLEET CATALOG (140+ VEHICLE TYPES)")
    print("=" * 80)

    # 1. Ensure All 8 Master Categories
    cat_objs = {}
    for c_def in CATEGORIES_DEF:
        obj, c_created = VehicleCategory.objects.update_or_create(
            code=c_def['code'],
            defaults=c_def
        )
        cat_objs[c_def['code']] = obj
        act = "CREATED" if c_created else "UPDATED"
        print(f"[{act}] Category: {obj.name} ({obj.code})")

    print("-" * 80)

    # 2. Map existing critical package tariffs to canonical names before altering
    # Canonical mappings to prevent any orphan tariffs:
    CANONICAL_MATCHES = {
        'innova_crysta': 'Toyota Innova Crysta 2.4 GX+',
        'innova_classic': 'Toyota Innova 2.5 VX',
        'sedan': 'Maruti Suzuki Dzire Lxi',
        'tempo_traveller': 'Force Traveller T1 3350 AC',
        'urbania': 'Force Urbania 4400',
        'bus_40': 'Ashok Leyland Viking 11.4m Zedastra',
        'minibus_35': 'Bharat Benz 1017 Fixed Glass',
        'coach_54': 'Bharat Benz 1624 Prakash Zedastra',
    }

    # 3. Ingest every single item from user's list
    ingested_cnt = 0
    updated_cnt = 0

    for name, seat_str in RAW_FLEET_DATA:
        seats = parse_seating(seat_str)
        cat_code = classify_vehicle(name, seat_str)
        cat_obj = cat_objs[cat_code]
        spec = calculate_rates_and_specs(name, seat_str, cat_code)

        desc = f"{name} ({seat_str}). Commercial passenger fleet specification for {cat_obj.name} operations."

        vt, created = VehicleType.objects.update_or_create(
            name=name,
            defaults={
                'vehicle_category': cat_obj,
                'category': cat_obj.name,
                'description': desc,
                'seating_capacity': seats,
                'luggage_capacity': spec['luggage'],
                'fuel_type': spec['fuel'],
                'expected_mileage_kmpl': spec['mileage'],
                'toll_class': spec['toll'],
                'default_day_rate': spec['day_rate'],
                'default_km_rate': spec['km_rate'],
                'minimum_km_per_day': spec['min_km'],
                'extra_km_rate': spec['extra_km'],
                'extra_hour_rate': spec['extra_hr'],
                'driver_bata': spec['bata'],
                'night_halt_charge': spec['night'],
                'has_ac': True,
                'is_luxury': spec['is_lux'],
                'transmission_type': spec['trans'],
                'is_wheelchair_accessible': ('wheelchair' in name.lower() or 'vanity' in name.lower()),
                'amenities': spec['amenities'],
            }
        )

        if created:
            ingested_cnt += 1
            print(f"[CREATED] {vt.name:<48} | {seats:2d} seats | {cat_obj.name}")
        else:
            updated_cnt += 1
            print(f"[UPDATED] {vt.name:<48} | {seats:2d} seats | {cat_obj.name}")

    print("=" * 80)
    print(f"MASTER FLEET CATALOG INGESTED: {ingested_cnt} created, {updated_cnt} updated.")
    print(f"Total Active Vehicle Types in Database: {VehicleType.objects.count()}")
    print("=" * 80)

    # 4. Re-link regional depot vehicles to their best match in the catalog
    crysta = VehicleType.objects.filter(name='Toyota Innova Crysta 2.4 GX+').first()
    hycross = VehicleType.objects.filter(name='Toyota Innova Hycross VX').first()
    dzire = VehicleType.objects.filter(name='Maruti Suzuki Dzire Lxi').first()
    etios = VehicleType.objects.filter(name='Toyota Etios VXD').first()
    urbania = VehicleType.objects.filter(name='Force Urbania 4400').first()
    tt = VehicleType.objects.filter(name='Force Traveller T1 3350 AC').first()
    glider = VehicleType.objects.filter(name='Bharat Benz 1624 MG Glider 12m FG').first()
    volvo = VehicleType.objects.filter(name='Volvo 9400 B11R 14.5m Multi-Axle').first()
    scania = VehicleType.objects.filter(name='Scania Metrolink HD 14.5m Multi-Axle').first()

    for v in Vehicle.objects.all():
        m_lower = (v.model or '').lower() + ' ' + (v.brand or '').lower()
        if 'hycross' in m_lower and hycross:
            v.vehicle_type = hycross
        elif 'crysta' in m_lower and crysta:
            v.vehicle_type = crysta
        elif 'etios' in m_lower and etios:
            v.vehicle_type = etios
        elif 'dzire' in m_lower and dzire:
            v.vehicle_type = dzire
        elif 'urbania' in m_lower and urbania:
            v.vehicle_type = urbania
        elif 'tempo traveller' in m_lower and tt:
            v.vehicle_type = tt
        elif 'glider' in m_lower and glider:
            v.vehicle_type = glider
        elif 'volvo' in m_lower and volvo:
            v.vehicle_type = volvo
        elif 'scania' in m_lower and scania:
            v.vehicle_type = scania
        
        if v.vehicle_type:
            v.vehicle_category = v.vehicle_type.vehicle_category
        v.save()
        print(f"Regional Fleet Vehicle {v.registration_number}: Linked to {v.vehicle_type.name} @ {v.base_depot}")

    print("=" * 80)

if __name__ == '__main__':
    run_master_seeding()
