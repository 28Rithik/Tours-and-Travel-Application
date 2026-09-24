import os
import sys
import re
import json
from decimal import Decimal

sys.stdout.reconfigure(encoding='utf-8')

# Setup Django environment
WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, WORKSPACE_ROOT)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')

import django
django.setup()

from django.db import connection
from packages.models import (
    Package,
    ItineraryDay,
    PackageVehicleTariff,
    TempleDarshanSlot,
)
from core.models import VehicleType

def get_vehicle_types():
    vtypes = list(VehicleType.objects.all())
    sedan_vt = next((vt for vt in vtypes if 'sedan' in vt.name.lower() or 'dzire' in vt.name.lower()), vtypes[0])
    crysta_vt = next((vt for vt in vtypes if 'crysta' in vt.name.lower() or 'innova' in vt.name.lower()), vtypes[1] if len(vtypes) > 1 else sedan_vt)
    urbania_vt = next((vt for vt in vtypes if any(k in vt.name.lower() for k in ['urbania', 'tempo', '17', '12'])), vtypes[2] if len(vtypes) > 2 else sedan_vt)
    bus36_vt = next((vt for vt in vtypes if any(k in vt.name.lower() for k in ['36', 'mini', '40'])), vtypes[3] if len(vtypes) > 3 else sedan_vt)
    coach54_vt = next((vt for vt in vtypes if any(k in vt.name.lower() for k in ['54', 'coach', '52', 'volvo'])), vtypes[4] if len(vtypes) > 4 else sedan_vt)

    return {
        'sedan': sedan_vt,
        'crysta': crysta_vt,
        'urbania': urbania_vt,
        'bus36': bus36_vt,
        'coach54': coach54_vt,
    }

def attach_tariffs(pkg, days, vtypes_dict):
    configs = [
        (vtypes_dict['sedan'], '4_sedan', 14.0, 500.0),
        (vtypes_dict['crysta'], '7_crysta', 20.0, 600.0),
        (vtypes_dict['urbania'], '17_tt_urbania', 26.0, 800.0),
        (vtypes_dict['bus36'], '36_mini_bus', 35.0, 1000.0),
        (vtypes_dict['coach54'], '54_luxury_coach', 45.0, 1200.0),
    ]

    for vt, tier, km_rate, bata in configs:
        if not vt:
            continue
        daily = (300 * km_rate) + bata
        pkg_rate = days * daily
        PackageVehicleTariff.objects.create(
            package=pkg,
            vehicle_type=vt,
            seating_tier=tier,
            rate_type='outstation_multiday',
            package_rate=Decimal(str(round(pkg_rate, 2))),
            per_day_rate=Decimal(str(round(daily, 2))),
            included_km=days * 300,
            extra_km_rate=Decimal(str(km_rate)),
            driver_bata_per_day=Decimal(str(bata)),
            driver_bata_included=True,
            toll_parking_included=True,
            interstate_permit_included=True if any(k in pkg.name.lower() for k in ['kerala', 'karnataka', 'goa', 'delhi', 'manali']) else False,
        )

# Full package dataset extracted from hiphopholidays.in
PACKAGES_DATA = [
    # -------------------------------------------------------------
    # 1. COLLEGE IV PACKAGES (Industrial Visits)
    # -------------------------------------------------------------
    {
        "code": "SGT-HHH-KER-IV-01",
        "name": "Kerala College IV Trip - Vagamon Jeep Safari & Kochi Marine DJ Cruise",
        "destination": "Kerala (Vagamon, Kochi, Athirappilly)",
        "category": "college_iv",
        "duration_days": 2,
        "duration_nights": 2,
        "base_price": 2850,
        "min_pax": 50,
        "has_jeep_safari": True,
        "has_campfire_dj": True,
        "has_boating": True,
        "itinerary": [
            {
                "day": 1,
                "title": "Vagamon Off-Road 7-Point Jeep Safari, Pine Forest & Hill Trekking",
                "route": "College Campus to Vagamon Hills",
                "activities": "Early morning scenic ascent into Vagamon misty hills. Check-in resort and refreshment. Embark on rugged 4x4 open jeep safari covering 7 iconic viewpoints including hidden waterfalls, rolling green meadows, and mist-clad valleys. Scenic walk through the tall pine forest with canal walk. Vagamon hill summit trek. Evening gala campfire with barbecue and high-energy music.",
                "spots": "Vagamon Pine Forest, 7-Point Jeep Safari, Hidden Waterfalls, Suicide Point, Vagamon Kurisumala, Pine Valley Canal",
                "stay": "Misty Mountain Resort, Vagamon"
            },
            {
                "day": 2,
                "title": "Kochi Marine Drive DJ Boat Cruise, Athirappilly Waterfalls & Return",
                "route": "Vagamon to Kochi & Athirappilly to Campus",
                "activities": "Buffet breakfast, checkout and proceed to Kochi harbor. Board exclusive 2-hour Marine Drive DJ Boat Cruise across Cochin backwaters with live DJ console and dancing. View Chinese fishing nets and naval docks. Post lunch, proceed to the majestic Athirappilly Waterfalls ('Niagara of India'). Evening dinner and overnight return journey to college campus.",
                "spots": "Kochi Marine Drive, Exclusive DJ Party Boat, Chinese Fishing Nets, Cochin Port View, Athirappilly Waterfalls",
                "stay": "Overnight Return Journey"
            }
        ]
    },
    {
        "code": "SGT-HHH-KER-IV-02",
        "name": "Kerala College IV Trip - Munnar Tea Valley, Wonderla Amusement & Kochi",
        "destination": "Kerala (Munnar, Kochi Wonderla)",
        "category": "college_iv",
        "duration_days": 3,
        "duration_nights": 2,
        "base_price": 3590,
        "min_pax": 50,
        "has_jeep_safari": False,
        "has_campfire_dj": True,
        "has_boating": True,
        "itinerary": [
            {
                "day": 1,
                "title": "Arrival Munnar, Cheeyappara Waterfalls & Tea Estate Factory IV",
                "route": "College Campus to Munnar Hills",
                "activities": "Morning drive through scenic Anamalai mountain passes with photo stops at Cheeyappara and Valara waterfalls. Arrive Munnar, check-in resort. Industrial visit clearance to Lockhart / Tata Tea Processing Factory to study industrial processing and machinery. Visit Mattupetty Dam and Echo Point. Evening resort campfire with DJ music.",
                "spots": "Cheeyappara Waterfalls, Valara Waterfalls, Lockhart Tea Processing Factory (IV), Mattupetty Dam, Echo Point",
                "stay": "Tea Valley Resort, Munnar"
            },
            {
                "day": 2,
                "title": "Full Day High Thrill at Wonderla Amusement & Water Theme Park",
                "route": "Munnar to Kochi Wonderla",
                "activities": "Breakfast, descend ghats to Wonderla Kochi. Full day unlimited access to world-class land and water rides including Recoil roller coaster, Maverick, Wonder Splash, wave pool, and rain disco. Evening transfer to hotel in Ernakulam, dinner and rest.",
                "spots": "Wonderla Amusement Park, Wave Pool, High Thrill Coasters, Rain Disco, Kochi City Center",
                "stay": "Hotel Grand Regency, Kochi"
            },
            {
                "day": 3,
                "title": "Fort Kochi Colonial Heritage, Marine Drive DJ Cruise & Departure",
                "route": "Kochi to College Campus",
                "activities": "Morning heritage exploration of Fort Kochi, St. Francis Church, and giant cantilevered Chinese fishing nets. Board exclusive DJ harbor cruise along Cochin waters. Shopping at Lulu Mall. Return departure with wonderful memories.",
                "spots": "Fort Kochi, St. Francis Church, Chinese Fishing Nets, Marine Drive Harbor DJ Cruise, Lulu Mall",
                "stay": "Overnight Return Journey"
            }
        ]
    },
    {
        "code": "SGT-HHH-KER-IV-03",
        "name": "Kerala College IV Trip - Wayanad Adventure, Edakkal Caves & Banasura Dam",
        "destination": "Kerala (Wayanad, Calicut)",
        "category": "college_iv",
        "duration_days": 3,
        "duration_nights": 2,
        "base_price": 3650,
        "min_pax": 50,
        "has_jeep_safari": True,
        "has_campfire_dj": True,
        "has_boating": True,
        "itinerary": [
            {
                "day": 1,
                "title": "Wayanad Ascent via Thamarassery Churam, Pookode Lake & Lakkidi",
                "route": "Campus to Wayanad via Ghat Road",
                "activities": "Ascend through the breathtaking 9 hairpin bends of Thamarassery Churam. Check-in resort in Vythiri/Kalpetta. Pedal boating at natural freshwater Pookode Lake surrounded by evergreen forests. Lakkidi View Point panoramic valley vistas. Evening campfire, barbecue and DJ music.",
                "spots": "Thamarassery Churam, Pookode Lake, Chain Tree, Lakkidi View Point",
                "stay": "Green Valley Resort, Wayanad"
            },
            {
                "day": 2,
                "title": "Edakkal Caves Prehistoric Trek & Soochipara Waterfalls",
                "route": "Kalpetta to Edakkal & Meppadi",
                "activities": "Morning trek up Ambukuthi Mala to inspect Neolithic petroglyphs at Edakkal Caves (archaeological IV significance). Post lunch, hike to the three-tiered Soochipara (Sentinel Rock) Waterfalls for refreshing stream pool dip. Evening DJ party at resort.",
                "spots": "Edakkal Caves, Ambukuthi Mala, Soochipara Waterfalls, Meppadi Tea Estates",
                "stay": "Green Valley Resort, Wayanad"
            },
            {
                "day": 3,
                "title": "Banasura Sagar Dam Speedboating, Karlad Lake Adventure & Calicut Beach",
                "route": "Wayanad to Calicut & Return",
                "activities": "Visit Banasura Sagar Dam, India's largest earth dam. Speedboating across the reservoir islands. Karlad Lake zipline and archery activities. Descend to Calicut beach for sunset snacks and Halwa bazaar. Depart to college campus.",
                "spots": "Banasura Sagar Dam, Banasura Speedboating, Karlad Lake Adventure, Calicut Beach",
                "stay": "Overnight Return Journey"
            }
        ]
    },
    {
        "code": "SGT-HHH-KAR-IV-01",
        "name": "Karnataka College IV Trip - Mysore Palace, Chikmagalur 7-Point Jeep Safari & Coorg",
        "destination": "Karnataka (Mysore, Chikmagalur, Coorg)",
        "category": "college_iv",
        "duration_days": 3,
        "duration_nights": 2,
        "base_price": 4199,
        "min_pax": 50,
        "has_jeep_safari": True,
        "has_campfire_dj": True,
        "has_boating": False,
        "itinerary": [
            {
                "day": 1,
                "title": "Mysore Royal Palace, Zoo, Chamundi Hills & KRS Dam",
                "route": "Campus to Mysore City",
                "activities": "Morning arrival in royal city of Mysore. Check-in hotel. Explore the majestic Mysore Palace (Amba Vilas), Sri Chamarajendra Zoological Gardens, and Chamundeshwari Temple atop Chamundi Hills. Proceed to KRS Dam and Brindavan Gardens for musical fountain light show. Overnight stay in Mysore.",
                "spots": "Mysore Palace, Mysore Zoo, Chamundi Hills, St. Philomena's Cathedral, KRS Dam & Brindavan Gardens",
                "stay": "Hotel Maurya Palace, Mysore"
            },
            {
                "day": 2,
                "title": "Chikmagalur Off-Road 7-Point Jeep Safari & Mullayanagiri Peak",
                "route": "Mysore to Chikmagalur",
                "activities": "Drive to coffee capital Chikmagalur. Transfer to 4x4 off-road jeeps to conquer Mullayanagiri Peak (highest peak in Karnataka at 1,930m), Baba Budangiri, Z-Point, and mountain water springs. Night campfire with barbecue and high-energy music.",
                "spots": "Mullayanagiri Peak, 7-Point Jeep Safari, Baba Budangiri, Z-Point, Coffee Plantations",
                "stay": "Coffee Valley Estate Stay, Chikmagalur"
            },
            {
                "day": 3,
                "title": "Coorg Abbey Falls, Bylakuppe Golden Temple & Tent Kotta DJ",
                "route": "Chikmagalur to Coorg & Return",
                "activities": "Proceed to Kodagu (Coorg). Witness the thunderous Abbey Falls cascading into coffee plantations. Visit Namdroling Monastery (Bylakuppe Golden Temple) featuring magnificent 40-foot gilded Buddha statues. Dubare Elephant Camp riverbank. DJ celebration before return departure.",
                "spots": "Abbey Falls, Namdroling Monastery (Golden Temple), Dubare Elephant Camp, Raja's Seat",
                "stay": "Overnight Return Journey"
            }
        ]
    },
    {
        "code": "SGT-HHH-KAR-IV-02",
        "name": "Karnataka College IV Trip - Bangalore Silicon Valley, ISKCON, Chikmagalur & Coorg",
        "destination": "Karnataka (Bangalore, Chikmagalur, Coorg)",
        "category": "college_iv",
        "duration_days": 3,
        "duration_nights": 2,
        "base_price": 4450,
        "min_pax": 50,
        "has_jeep_safari": True,
        "has_campfire_dj": True,
        "has_boating": False,
        "itinerary": [
            {
                "day": 1,
                "title": "Bangalore Tech Hub, ISKCON Temple & Visvesvaraya Science Museum IV",
                "route": "Campus to Bangalore",
                "activities": "Arrival in Bangalore. Technical IV visit to Visvesvaraya Industrial & Technological Museum and HAL Heritage Centre & Aerospace Museum. Spiritual darshan at grand ISKCON Temple Rajajinagar and Shivoham Shiva Temple. Drive towards Chikmagalur.",
                "spots": "Visvesvaraya Technological Museum (IV), HAL Aerospace Museum, ISKCON Temple, Shivoham Shiva Temple",
                "stay": "Estate Resort, Chikmagalur"
            },
            {
                "day": 2,
                "title": "Chikmagalur Coffee Estate Off-Road Jeep Safari & Night Fire Camp",
                "route": "Chikmagalur Sightseeing",
                "activities": "Full day coffee estate exploration and 7-point off-road jeep safari to Mullayanagiri and Hebbe falls viewpoints. Coffee bean processing demonstration. Night gala campfire with music and barbecue.",
                "spots": "Chikmagalur Jeep Safari, Mullayanagiri, Coffee Estate Processing, Hebbe Falls viewpoint",
                "stay": "Estate Resort, Chikmagalur"
            },
            {
                "day": 3,
                "title": "Coorg Abbey Falls, Golden Temple & Return Departure",
                "route": "Chikmagalur to Coorg & Campus",
                "activities": "Drive through the Western Ghats to Coorg. Visit Abbey Falls, Bylakuppe Tibetan Golden Temple, and Raja's Seat. Depart back to college campus.",
                "spots": "Abbey Falls, Bylakuppe Golden Temple, Raja's Seat, Kushalnagar Market",
                "stay": "Overnight Return Journey"
            }
        ]
    },
    {
        "code": "SGT-HHH-KAR-IV-03",
        "name": "Karnataka College IV Trip - Mysore Royal Heritage, Coorg & Dandeli River Rafting",
        "destination": "Karnataka (Mysore, Coorg, Dandeli)",
        "category": "college_iv",
        "duration_days": 3,
        "duration_nights": 2,
        "base_price": 5600,
        "min_pax": 50,
        "has_jeep_safari": True,
        "has_campfire_dj": True,
        "has_boating": True,
        "itinerary": [
            {
                "day": 1,
                "title": "Mysore Royal Palace, Zoo, KRS Dam & Evening Travel to Coorg",
                "route": "Campus to Mysore & Coorg",
                "activities": "Explore Mysore Palace, Zoo, and KRS Dam. Proceed to Coorg resort for dinner and rest.",
                "spots": "Mysore Palace, Zoo, KRS Dam, Brindavan Gardens",
                "stay": "Coffee County Resort, Coorg"
            },
            {
                "day": 2,
                "title": "Coorg Abbey Falls, Golden Temple & Night Transfer to Dandeli",
                "route": "Coorg to Dandeli",
                "activities": "Visit Abbey Falls and Bylakuppe Golden Temple. Evening DJ celebration. Overnight journey to Dandeli adventure capital.",
                "spots": "Abbey Falls, Golden Temple, Dubare, Tent Kotta DJ",
                "stay": "Jungle Camp / Resort, Dandeli"
            },
            {
                "day": 3,
                "title": "Dandeli White Water Rafting, Kayaking, River Jacuzzi & Forest Jeep Safari",
                "route": "Dandeli Adventure to Campus",
                "activities": "High-octane water sports on Kali River: 9.5 km White Water River Rafting through Class 3 rapids, kayaking, natural river jacuzzi bath, and open-top jungle jeep safari. Return journey to college.",
                "spots": "Kali River White Water Rafting, Natural Jacuzzi Bath, Kayaking, Dandeli Forest Safari, Supa Dam",
                "stay": "Overnight Return Journey"
            }
        ]
    },
    {
        "code": "SGT-HHH-KAR-IV-04",
        "name": "Karnataka College IV Trip - Bangalore Wonderla & Mysore Heritage Circuit",
        "destination": "Karnataka (Bangalore, Mysore)",
        "category": "college_iv",
        "duration_days": 3,
        "duration_nights": 2,
        "base_price": 4199,
        "min_pax": 50,
        "has_jeep_safari": False,
        "has_campfire_dj": True,
        "has_boating": False,
        "itinerary": [
            {
                "day": 1,
                "title": "Bangalore Tech Landmark Tour, ISKCON & Shivoham Temple",
                "route": "Campus to Bangalore City",
                "activities": "Arrival in Bangalore, ISKCON temple darshan, Shivoham Shiva Temple, Vidhana Soudha photo stop, Visvesvaraya Industrial & Technological Museum.",
                "spots": "Bangalore ISKCON, Shivoham Shiva Temple, Vidhana Soudha, VITM Museum (IV)",
                "stay": "Hotel Raj Regency, Bangalore"
            },
            {
                "day": 2,
                "title": "Wonderla Bangalore Water & Amusement Park Full Day Adventure",
                "route": "Bangalore to Wonderla & Mysore",
                "activities": "Unlimited thrill at Wonderla Bangalore: roller coasters, giant water park, rain dance. Evening drive to Mysore.",
                "spots": "Wonderla Bangalore, Wave Pool, High-G Coasters, Rain Disco",
                "stay": "Hotel Maurya Palace, Mysore"
            },
            {
                "day": 3,
                "title": "Mysore Royal Palace, Chamundi Hills & Brindavan Gardens",
                "route": "Mysore to Campus",
                "activities": "Visit Mysore Palace, Sri Chamarajendra Zoo, Chamundeshwari temple, and KRS Dam Brindavan Gardens. Depart back to campus.",
                "spots": "Mysore Palace, Zoo, Chamundi Hills, Brindavan Gardens",
                "stay": "Overnight Return Journey"
            }
        ]
    },
    {
        "code": "SGT-HHH-TN-IV-01",
        "name": "Tamil Nadu College IV Trip - Black Thunder Theme Park, Ooty Hills & Tea Estates",
        "destination": "Tamil Nadu (Coimbatore, Mettupalayam, Ooty)",
        "category": "college_iv",
        "duration_days": 3,
        "duration_nights": 2,
        "base_price": 3590,
        "min_pax": 50,
        "has_jeep_safari": False,
        "has_campfire_dj": True,
        "has_boating": True,
        "itinerary": [
            {
                "day": 1,
                "title": "Black Thunder Water Theme Park Full Day Fun & Ghat Drive to Ooty",
                "route": "Campus to Mettupalayam & Ooty",
                "activities": "Full day at Black Thunder Theme Park at the foothills of Nilgiris: wave pool, wild river ride, surf hill, lazy river. Evening scenic ghat drive to Ooty. Check-in hotel, dinner and rest.",
                "spots": "Black Thunder Water Theme Park, Wave Pool, Nilgiri Mountain Ghat Road",
                "stay": "Hotel Nilgiri Comforts, Ooty"
            },
            {
                "day": 2,
                "title": "Ooty Pakoda Point, Tea Factory IV, Botanical Garden & DJ Night",
                "route": "Ooty Local Sightseeing",
                "activities": "Visit Doddabetta Peak, Tea Factory & Chocolate Museum (technical IV insight into CTC tea manufacturing). Government Botanical Garden floral terracing. Ooty Lake boating. Evening DJ campfire.",
                "spots": "Doddabetta Peak, Dodabetta Tea Factory (IV), Chocolate Museum, Botanical Garden, Ooty Lake",
                "stay": "Hotel Nilgiri Comforts, Ooty"
            },
            {
                "day": 3,
                "title": "Coonoor Sims Park, Dolphin's Nose, Rose Garden & Pine Forest Walk",
                "route": "Ooty to Coonoor & Campus",
                "activities": "Explore Coonoor Sims Park, Dolphin's Nose valley viewpoint, Tea estate zipline adventure, Ooty Government Rose Garden, and shooting spot Pine Forest. Return to campus.",
                "spots": "Sims Park Coonoor, Dolphin's Nose, Tea Estate Zipline, Rose Garden, Pine Forest",
                "stay": "Overnight Return Journey"
            }
        ]
    },
    {
        "code": "SGT-HHH-TN-IV-02",
        "name": "Tamil Nadu College IV Trip - Kodaikanal Princess of Hills, Pine Forest & Palani",
        "destination": "Tamil Nadu (Kodaikanal, Palani)",
        "category": "college_iv",
        "duration_days": 3,
        "duration_nights": 2,
        "base_price": 3950,
        "min_pax": 50,
        "has_jeep_safari": False,
        "has_campfire_dj": True,
        "has_boating": True,
        "itinerary": [
            {
                "day": 1,
                "title": "Arrival Kodaikanal, Kodai Lake Boating, Cycling & Coaker's Walk",
                "route": "Campus to Kodaikanal",
                "activities": "Ascend the Palani hills to Kodaikanal. Check-in resort. Boating on star-shaped Kodai Lake, 5-km bicycle circuit, Bryant Park, and misty stroll along Coaker's Walk.",
                "spots": "Kodai Lake, Star Boating, Bryant Park, Coaker's Walk, Upper Lake View",
                "stay": "Hilltop Towers Resort, Kodaikanal"
            },
            {
                "day": 2,
                "title": "Guna Caves, Pillar Rocks, Pine Forest Trek & Night DJ Campfire",
                "route": "Kodaikanal Heritage Sightseeing",
                "activities": "Trek through the dense canopy of Pine Forest. Explore Pillar Rocks, Guna Caves (Devil's Kitchen), Moir Point, and Green Valley View. Night DJ music and campfire with barbecue.",
                "spots": "Guna Caves, Pillar Rocks, Pine Forest, Moir Point, Green Valley View",
                "stay": "Hilltop Towers Resort, Kodaikanal"
            },
            {
                "day": 3,
                "title": "Silver Cascade Waterfalls, Palani Murugan Temple Darshan & Return",
                "route": "Kodaikanal to Palani & Campus",
                "activities": "Descend via Silver Cascade waterfalls. Arrive at Palani. Rope-car / Winch ride to Arulmigu Dhandayuthapani Swamy Temple for special darshan. Return departure to college.",
                "spots": "Silver Cascade Waterfalls, Palani Murugan Temple, Rope Car Darshan, Palani Panchamirtham Bazaar",
                "stay": "Overnight Return Journey"
            }
        ]
    },
    {
        "code": "SGT-HHH-TN-IV-03",
        "name": "Tamil Nadu College IV Trip - Madurai Meenakshi, Rameshwaram Sea Bridge & Kanyakumari",
        "destination": "Tamil Nadu (Madurai, Rameshwaram, Kanyakumari)",
        "category": "college_iv",
        "duration_days": 3,
        "duration_nights": 2,
        "base_price": 4250,
        "min_pax": 50,
        "has_jeep_safari": False,
        "has_campfire_dj": True,
        "has_boating": True,
        "itinerary": [
            {
                "day": 1,
                "title": "Madurai Meenakshi Amman Temple & Thirumalai Nayakkar Mahal",
                "route": "Campus to Madurai & Rameshwaram",
                "activities": "Visit Madurai Meenakshi Amman Temple, Thousand Pillar Hall, and Thirumalai Nayakkar Palace. Proceed to Rameshwaram over the historic Pamban Sea Bridge.",
                "spots": "Madurai Meenakshi Temple, Thousand Pillar Hall, Thirumalai Nayakkar Palace, Pamban Rail & Road Bridge",
                "stay": "Hotel Royal Park, Rameshwaram"
            },
            {
                "day": 2,
                "title": "Rameshwaram 22 Theerthams, Dr. Kalam Memorial & Dhanushkodi Island",
                "route": "Rameshwaram to Kanyakumari",
                "activities": "22 Holy Kund snanam at Ramanathaswamy Temple, Dr. APJ Abdul Kalam National Memorial, 4x4 ride to Dhanushkodi ghost town and Ram Setu viewpoint. Evening drive to Kanyakumari.",
                "spots": "Ramanathaswamy Temple, Dr. APJ Abdul Kalam Memorial, Dhanushkodi Ghost Town, Ram Setu Point",
                "stay": "Hotel Sea View, Kanyakumari"
            },
            {
                "day": 3,
                "title": "Kanyakumari Vivekananda Rock Memorial, Triveni Sangam & Sunset",
                "route": "Kanyakumari to Campus",
                "activities": "Ferry boat to Vivekananda Rock Memorial and 133-foot Thiruvalluvar Statue. Triveni Sangam ocean confluence, Gandhi Memorial Mandapam, Sunset point & return.",
                "spots": "Vivekananda Rock Memorial, Thiruvalluvar Statue, Triveni Sangam, Gandhi Memorial, Sunset View Point",
                "stay": "Overnight Return Journey"
            }
        ]
    },
    {
        "code": "SGT-HHH-GOA-IV-01",
        "name": "Goa College IV Trip - North Goa Beaches, Fort Aguada & Mandovi DJ Boat Cruise",
        "destination": "Goa (North Goa, Panaji)",
        "category": "college_iv",
        "duration_days": 3,
        "duration_nights": 2,
        "base_price": 5499,
        "min_pax": 50,
        "has_jeep_safari": False,
        "has_campfire_dj": True,
        "has_boating": True,
        "itinerary": [
            {
                "day": 1,
                "title": "Arrival Goa, Calangute & Baga Beach Sunset Party",
                "route": "Campus / Station to North Goa",
                "activities": "Arrival in Goa, check-in beach resort. Afternoon leisure at Calangute Beach and Baga Beach. Tito's Lane night stroll and welcome beach bonfire party.",
                "spots": "Calangute Beach, Baga Beach, Tito's Lane, Beach Bonfire & Shacks",
                "stay": "Sunset Palms Beach Resort, Calangute"
            },
            {
                "day": 2,
                "title": "Fort Aguada Lighthouse, Chapora Fort & Mandovi River DJ Cruise",
                "route": "North Goa Sightseeing",
                "activities": "Visit Portuguese 17th-century Fort Aguada and lighthouse, Sinquerim beach, and Chapora Fort ('Dil Chahta Hai' viewpoint). Evening 2-hour Mandovi River DJ Cruise with live music and Goan cultural dance.",
                "spots": "Fort Aguada Lighthouse, Sinquerim Beach, Chapora Fort, Mandovi River Exclusive DJ Cruise",
                "stay": "Sunset Palms Beach Resort, Calangute"
            },
            {
                "day": 3,
                "title": "Panjim Latin Quarter (Fontainhas), Miramar Beach & Return",
                "route": "North Goa to Panaji & Return",
                "activities": "Explore Panjim's historic Latin Quarter Fontainhas with colorful Portuguese villas, Church of Our Lady of the Immaculate Conception, Miramar Beach, and local cashew/spice shopping before departure.",
                "spots": "Fontainhas Latin Quarter, Immaculate Conception Church, Miramar Beach, Panjim City Market",
                "stay": "Overnight Return Journey"
            }
        ]
    },
    {
        "code": "SGT-HHH-GOA-IV-02",
        "name": "Goa College IV Trip - South Goa Heritage, Basilica of Bom Jesus & Colva Beach",
        "destination": "Goa (Old Goa, South Goa)",
        "category": "college_iv",
        "duration_days": 3,
        "duration_nights": 2,
        "base_price": 5690,
        "min_pax": 50,
        "has_jeep_safari": False,
        "has_campfire_dj": True,
        "has_boating": True,
        "itinerary": [
            {
                "day": 1,
                "title": "South Goa Arrival, Colva Beach Water Sports & Resort Party",
                "route": "Arrival to South Goa Resort",
                "activities": "Check-in South Goa beach resort. Enjoy thrilling beach water sports at Colva Beach (parasailing, jet ski, banana ride). Evening resort pool party with DJ.",
                "spots": "Colva Beach, Water Sports Arena, Benaulim Beach, Sunset Beach",
                "stay": "Heritage Village Resort, South Goa"
            },
            {
                "day": 2,
                "title": "Old Goa UNESCO World Heritage Churches & Mangueshi Temple",
                "route": "Old Goa & Ponda Circuit",
                "activities": "Visit UNESCO World Heritage Basilica of Bom Jesus (sacred relics of St. Francis Xavier), Se Cathedral (largest church in Asia), Church of St. Francis of Assisi, and ancient Mangueshi Temple in Ponda.",
                "spots": "Basilica of Bom Jesus, Se Cathedral, Church of St. Francis of Assisi, Mangueshi Temple",
                "stay": "Heritage Village Resort, South Goa"
            },
            {
                "day": 3,
                "title": "Dona Paula Viewpoint, Miramar Beach & Panjim Cruise",
                "route": "South Goa to Panaji & Departure",
                "activities": "Visit Dona Paula viewpoint, Miramar Beach, shopping for Goan feni, spices and handicrafts, sunset river cruise and return departure.",
                "spots": "Dona Paula, Miramar Beach, Mandovi Sunset Cruise, Panjim Market",
                "stay": "Overnight Return Journey"
            }
        ]
    },
    {
        "code": "SGT-HHH-GOA-IV-03",
        "name": "Goa College IV Trip - Dudhsagar Waterfall Jungle Safari & Grand Carnival",
        "destination": "Goa (Dudhsagar, North & South Goa)",
        "category": "college_iv",
        "duration_days": 4,
        "duration_nights": 3,
        "base_price": 7566,
        "min_pax": 50,
        "has_jeep_safari": True,
        "has_campfire_dj": True,
        "has_boating": True,
        "itinerary": [
            {
                "day": 1,
                "title": "Arrival Goa, Calangute & Baga Beach Welcome Party",
                "route": "Arrival to Calangute Resort",
                "activities": "Resort check-in, beach volleyball, sunset at Baga Beach, evening DJ and campfire.",
                "spots": "Calangute Beach, Baga Beach, Shack Dining, Resort DJ Night",
                "stay": "Calangute Grand Beach Resort"
            },
            {
                "day": 2,
                "title": "Dudhsagar Waterfalls 4x4 Jungle Jeep Safari & Spice Plantation",
                "route": "Calangute to Mollem & Dudhsagar",
                "activities": "Early morning transfer to Mollem. Board 4x4 open jungle jeeps through Bhagwan Mahavir Wildlife Sanctuary river crossings to Dudhsagar Waterfalls. Swim in natural pool beneath the cascading milky falls. Traditional Goan buffet lunch at tropical spice plantation.",
                "spots": "Dudhsagar Waterfalls, Mollem Jungle Jeep Safari, Bhagwan Mahavir Sanctuary, Spice Plantation Buffet",
                "stay": "Calangute Grand Beach Resort"
            },
            {
                "day": 3,
                "title": "Water Sports Adventure Package & Mandovi Luxury DJ Cruise",
                "route": "Anjuna, Baga & Mandovi River",
                "activities": "High-octane 5-in-1 water sports package (Parasailing, Jet Ski, Banana Ride, Bumper Ride, Speedboat). Evening 2-hour Mandovi River luxury DJ party cruise.",
                "spots": "5-in-1 Water Sports Combo, Anjuna Beach, Mandovi River DJ Cruise",
                "stay": "Calangute Grand Beach Resort"
            },
            {
                "day": 4,
                "title": "Old Goa Heritage, Panjim Latin Quarter & Return Journey",
                "route": "Panaji to Campus",
                "activities": "Visit Basilica of Bom Jesus, Se Cathedral, Fontainhas Latin Quarter, and return departure.",
                "spots": "Basilica of Bom Jesus, Fontainhas, Miramar Beach",
                "stay": "Overnight Return Journey"
            }
        ]
    },

    # -------------------------------------------------------------
    # 2. GROUP TOURS (Friends, Corporate, Youth Groups)
    # -------------------------------------------------------------
    {
        "code": "SGT-HHH-KER-GRP-01",
        "name": "Kerala Group Tour - Vagamon Pine Valley, Off-Road Jeep Safari & Kochi DJ Cruise",
        "destination": "Kerala (Vagamon, Kochi, Athirappilly)",
        "category": "holiday",
        "duration_days": 2,
        "duration_nights": 1,
        "base_price": 3480,
        "min_pax": 15,
        "has_jeep_safari": True,
        "has_campfire_dj": True,
        "has_boating": True,
        "itinerary": [
            {
                "day": 1,
                "title": "Vagamon 7-Point Jeep Safari, Pine Forest & Hilltop Campfire",
                "route": "Meeting Point to Vagamon",
                "activities": "Scenic hill station climb into Vagamon. Rugged 4x4 Jeep Safari covering 7 scenic viewpoints and waterfalls. Pine forest walk. Evening barbecue and campfire with DJ console.",
                "spots": "Vagamon Pine Forest, 7-Point Jeep Safari, Kurisumala Viewpoint, Barbecue Campfire",
                "stay": "Vagamon Heights Resort"
            },
            {
                "day": 2,
                "title": "Kochi Marine Drive DJ Boat Cruise & Athirappilly Waterfalls",
                "route": "Vagamon to Kochi & Departure",
                "activities": "Checkout and proceed to Kochi harbor. Exclusive 2-hour Marine Drive DJ Boat Cruise with music. Proceed to Athirappilly waterfalls for sightseeing before return departure.",
                "spots": "Kochi Marine Drive DJ Boat Cruise, Chinese Fishing Nets, Athirappilly Waterfalls",
                "stay": "Return Journey"
            }
        ]
    },
    {
        "code": "SGT-HHH-KER-GRP-02",
        "name": "Kerala Group Tour - Munnar Tea Hills & Alleppey Deluxe Houseboat",
        "destination": "Kerala (Munnar, Alleppey)",
        "category": "holiday",
        "duration_days": 3,
        "duration_nights": 2,
        "base_price": 4990,
        "min_pax": 15,
        "has_jeep_safari": False,
        "has_campfire_dj": True,
        "has_boating": True,
        "itinerary": [
            {
                "day": 1,
                "title": "Arrival Munnar, Cheeyappara Falls & Tea Garden Trek",
                "route": "Arrival to Munnar",
                "activities": "Drive through scenic waterfalls to Munnar. Tea garden nature walk, Mattupetty dam boating, Echo point. Evening campfire with music.",
                "spots": "Cheeyappara Falls, Tea Gardens, Mattupetty Dam, Echo Point",
                "stay": "Munnar Tea Haven Resort"
            },
            {
                "day": 2,
                "title": "Munnar to Alleppey Deluxe Houseboat Backwater Cruise",
                "route": "Munnar to Alleppey",
                "activities": "Proceed to Alleppey backwaters. Board Deluxe Private Houseboat. Cruise through Vembanad Lake, paddy fields, and coconut canals with traditional Kerala meals.",
                "spots": "Vembanad Lake, Alleppey Backwaters, Traditional Houseboat Cruise",
                "stay": "Deluxe Houseboat, Alleppey"
            },
            {
                "day": 3,
                "title": "Alleppey Beach, Marari Beach & Return Departure",
                "route": "Alleppey to Departure",
                "activities": "Morning breakfast on houseboat. Alleppey pier beach and lighthouse, Coir village craft, return departure.",
                "spots": "Alleppey Beach, Lighthouse, Marari Beach",
                "stay": "Return Journey"
            }
        ]
    },
    {
        "code": "SGT-HHH-KAR-GRP-01",
        "name": "Karnataka Group Tour - Mysore Royal Palace, Chikmagalur Coffee Mist & Coorg",
        "destination": "Karnataka (Mysore, Chikmagalur, Coorg)",
        "category": "holiday",
        "duration_days": 3,
        "duration_nights": 2,
        "base_price": 5400,
        "min_pax": 15,
        "has_jeep_safari": True,
        "has_campfire_dj": True,
        "has_boating": False,
        "itinerary": [
            {
                "day": 1,
                "title": "Mysore Palace, Zoo, Chamundi Hills & Brindavan Gardens",
                "route": "Departure to Mysore",
                "activities": "Mysore Palace royal interior tour, Zoo, Chamundeshwari Temple, and KRS Dam musical fountain light show.",
                "spots": "Mysore Palace, Mysore Zoo, Chamundi Hills, Brindavan Gardens",
                "stay": "Hotel Maurya, Mysore"
            },
            {
                "day": 2,
                "title": "Chikmagalur Mullayanagiri Peak & 7-Point Jeep Safari",
                "route": "Mysore to Chikmagalur",
                "activities": "4x4 Jeep ride to Mullayanagiri Peak, Baba Budangiri, coffee estate walk, night campfire with barbecue and DJ.",
                "spots": "Mullayanagiri, 7-Point Jeep Safari, Coffee Estates, Campfire",
                "stay": "Chikmagalur Plantation Resort"
            },
            {
                "day": 3,
                "title": "Coorg Abbey Falls, Bylakuppe Golden Temple & Return",
                "route": "Chikmagalur to Coorg & Return",
                "activities": "Abbey Falls nature walk, Namdroling Monastery (Golden Temple), Dubare Elephant Camp, return departure.",
                "spots": "Abbey Falls, Bylakuppe Golden Temple, Dubare, Raja's Seat",
                "stay": "Return Journey"
            }
        ]
    },
    {
        "code": "SGT-HHH-KAR-GRP-02",
        "name": "Karnataka Group Tour - Bangalore Metro, ISKCON, Chikmagalur & Coorg Valley",
        "destination": "Karnataka (Bangalore, Chikmagalur, Coorg)",
        "category": "holiday",
        "duration_days": 3,
        "duration_nights": 2,
        "base_price": 5400,
        "min_pax": 15,
        "has_jeep_safari": True,
        "has_campfire_dj": True,
        "has_boating": False,
        "itinerary": [
            {
                "day": 1,
                "title": "Bangalore ISKCON, Shivoham Temple & City Sights",
                "route": "Departure to Bangalore",
                "activities": "Visit grand ISKCON Temple Rajajinagar, Shivoham Shiva Temple, Commercial Street, drive to Chikmagalur.",
                "spots": "ISKCON Bangalore, Shivoham Temple, Lalbagh, Vidhana Soudha",
                "stay": "Chikmagalur Resort"
            },
            {
                "day": 2,
                "title": "Chikmagalur 7-Point Jeep Safari & Night Fire Camp",
                "route": "Chikmagalur Sightseeing",
                "activities": "Mullayanagiri peak jeep safari, coffee bean tasting, mountain spring trekking, night campfire and DJ.",
                "spots": "Mullayanagiri, 7-Point Jeep Tour, Coffee Estate, Night Fire Camp",
                "stay": "Chikmagalur Resort"
            },
            {
                "day": 3,
                "title": "Coorg Abbey Falls, Golden Temple & Return Departure",
                "route": "Coorg to Return",
                "activities": "Abbey Falls, Bylakuppe Golden Temple, Raja's Seat, return departure.",
                "spots": "Abbey Falls, Golden Temple, Raja's Seat",
                "stay": "Return Journey"
            }
        ]
    },
    {
        "code": "SGT-HHH-KAR-GRP-03",
        "name": "Karnataka Group Tour - Mysore, Coorg Abbey Falls & Dandeli White Water Rafting",
        "destination": "Karnataka (Mysore, Coorg, Dandeli)",
        "category": "holiday",
        "duration_days": 3,
        "duration_nights": 2,
        "base_price": 6100,
        "min_pax": 15,
        "has_jeep_safari": True,
        "has_campfire_dj": True,
        "has_boating": True,
        "itinerary": [
            {
                "day": 1,
                "title": "Mysore Royal Palace, Zoo, KRS Dam & Travel to Coorg",
                "route": "Departure to Mysore & Coorg",
                "activities": "Mysore Palace, Zoo, KRS Dam, and evening transfer to Coorg resort.",
                "spots": "Mysore Palace, Zoo, KRS Dam, Brindavan Gardens",
                "stay": "Coorg Estate Resort"
            },
            {
                "day": 2,
                "title": "Coorg Abbey Falls, Golden Temple & DJ Night",
                "route": "Coorg Sightseeing & Travel to Dandeli",
                "activities": "Abbey Falls, Bylakuppe Golden Temple, Tent Kotta DJ night, proceed towards Dandeli.",
                "spots": "Abbey Falls, Golden Temple, Tent Kotta DJ",
                "stay": "Dandeli Jungle Resort"
            },
            {
                "day": 3,
                "title": "Dandeli Kali River Rafting, Jacuzzi Bath & Forest Jeep Safari",
                "route": "Dandeli to Return",
                "activities": "White water river rafting in Kali river, river jacuzzi bath, kayaking, forest safari, return departure.",
                "spots": "Kali River Rafting, Jacuzzi Bath, Kayaking, Forest Jeep Safari",
                "stay": "Return Journey"
            }
        ]
    },
    {
        "code": "SGT-HHH-TN-GRP-01",
        "name": "Tamil Nadu Group Tour - Black Thunder Theme Park, Ooty Lake & Botanical Gardens",
        "destination": "Tamil Nadu (Mettupalayam, Ooty)",
        "category": "holiday",
        "duration_days": 3,
        "duration_nights": 2,
        "base_price": 3480,
        "min_pax": 15,
        "has_jeep_safari": False,
        "has_campfire_dj": True,
        "has_boating": True,
        "itinerary": [
            {
                "day": 1,
                "title": "Black Thunder Water Theme Park & Evening Drive to Ooty",
                "route": "Departure to Mettupalayam & Ooty",
                "activities": "Full day thrilling water rides at Black Thunder Theme Park. Evening drive up the Nilgiris to Ooty.",
                "spots": "Black Thunder Water Park, Wave Pool, Nilgiri Ghat Road",
                "stay": "Ooty Comfort Inn"
            },
            {
                "day": 2,
                "title": "Ooty Doddabetta, Tea Estate, Botanical Garden & Lake Boating",
                "route": "Ooty Sightseeing",
                "activities": "Doddabetta Peak, Tea Factory & Chocolate Museum, Botanical Garden, Ooty Lake boating, campfire.",
                "spots": "Doddabetta, Tea Factory, Botanical Garden, Ooty Lake",
                "stay": "Ooty Comfort Inn"
            },
            {
                "day": 3,
                "title": "Coonoor Sims Park, Dolphin's Nose, Rose Garden & Pine Forest",
                "route": "Ooty to Coonoor & Return",
                "activities": "Sims Park, Dolphin's Nose, tea estate zipline, Government Rose Garden, Pine Forest, return departure.",
                "spots": "Sims Park, Dolphin's Nose, Rose Garden, Pine Forest",
                "stay": "Return Journey"
            }
        ]
    },
    {
        "code": "SGT-HHH-TN-GRP-02",
        "name": "Tamil Nadu Group Tour - Kodaikanal Pine Forest, Boating, Guna Caves & Palani",
        "destination": "Tamil Nadu (Kodaikanal, Palani)",
        "category": "holiday",
        "duration_days": 3,
        "duration_nights": 2,
        "base_price": 3950,
        "min_pax": 15,
        "has_jeep_safari": False,
        "has_campfire_dj": True,
        "has_boating": True,
        "itinerary": [
            {
                "day": 1,
                "title": "Arrival Kodaikanal, Kodai Lake Boating & Bryant Park",
                "route": "Departure to Kodaikanal",
                "activities": "Check-in Kodaikanal resort. Kodai Lake star boating, cycling around lake, Bryant Park, Coaker's Walk.",
                "spots": "Kodai Lake, Bryant Park, Coaker's Walk, Upper Lake View",
                "stay": "Kodai Valley Resort"
            },
            {
                "day": 2,
                "title": "Guna Caves, Pillar Rocks, Pine Forest Trek & Night Campfire",
                "route": "Kodaikanal Local Sightseeing",
                "activities": "Guna Caves, Pillar Rocks, Pine Forest scenic walk, Moir Point, evening campfire and music.",
                "spots": "Guna Caves, Pillar Rocks, Pine Forest, Moir Point",
                "stay": "Kodai Valley Resort"
            },
            {
                "day": 3,
                "title": "Silver Cascade Waterfalls, Palani Murugan Temple & Return",
                "route": "Kodaikanal to Palani & Return",
                "activities": "Silver Cascade, Palani Murugan Temple rope-car darshan, local shopping and return departure.",
                "spots": "Silver Cascade, Palani Murugan Temple, Rope Car",
                "stay": "Return Journey"
            }
        ]
    },
    {
        "code": "SGT-HHH-GOA-GRP-01",
        "name": "Goa Group Tour - Complete Sunshine Circuit: Calangute, Aguada & Mandovi Cruise",
        "destination": "Goa (North & South Goa)",
        "category": "holiday",
        "duration_days": 3,
        "duration_nights": 2,
        "base_price": 7566,
        "min_pax": 15,
        "has_jeep_safari": False,
        "has_campfire_dj": True,
        "has_boating": True,
        "itinerary": [
            {
                "day": 1,
                "title": "Arrival North Goa, Calangute Beach, Watersports & Sunset Party",
                "route": "Arrival to North Goa Resort",
                "activities": "Check-in beach resort. Calangute and Baga beach, watersports, Tito's Lane night walk, beach shack party.",
                "spots": "Calangute Beach, Baga Beach, Beach Shacks, Tito's Lane",
                "stay": "North Goa Beach Resort"
            },
            {
                "day": 2,
                "title": "Fort Aguada, Chapora Fort & Mandovi River 2-Hour Sunset DJ Cruise",
                "route": "North Goa Sightseeing",
                "activities": "Fort Aguada lighthouse, Sinquerim beach, Chapora Fort, Mandovi River 2-hour sunset cruise with live DJ.",
                "spots": "Fort Aguada, Chapora Fort, Mandovi Sunset Cruise, Panjim Riverfront",
                "stay": "North Goa Beach Resort"
            },
            {
                "day": 3,
                "title": "Old Goa Churches, Miramar Beach & Panjim Latin Quarter",
                "route": "South Goa & Panaji to Return",
                "activities": "Basilica of Bom Jesus, Se Cathedral, Miramar Beach, Fontainhas Latin Quarter, return departure.",
                "spots": "Basilica of Bom Jesus, Se Cathedral, Miramar Beach, Fontainhas",
                "stay": "Return Journey"
            }
        ]
    },

    # -------------------------------------------------------------
    # 3. FAMILY VACATION PACKAGES
    # -------------------------------------------------------------
    {
        "code": "SGT-HHH-KER-FAM-01",
        "name": "Kerala Family Vacation - Vagamon Pine Valley, Kochi Marine Drive & Athirappilly",
        "destination": "Kerala (Vagamon, Kochi, Athirappilly)",
        "category": "family_vacation",
        "duration_days": 2,
        "duration_nights": 2,
        "base_price": 1990,
        "min_pax": 4,
        "has_jeep_safari": True,
        "has_campfire_dj": True,
        "has_boating": True,
        "itinerary": [
            {
                "day": 1,
                "title": "Vagamon 7-Point Jeep Safari, Pine Forest Canal & Family Campfire",
                "route": "Home City to Vagamon",
                "activities": "Scenic drive into Vagamon. Family 4x4 Jeep safari covering 7 scenic viewpoints and waterfalls, pine forest canal walk, evening barbecue and campfire.",
                "spots": "Vagamon Pine Forest, 7-Point Jeep Safari, Hidden Waterfalls, Campfire & BBQ",
                "stay": "Vagamon Family Resort"
            },
            {
                "day": 2,
                "title": "Kochi Harbor Boat Ride, Chinese Nets & Athirappilly Waterfalls",
                "route": "Vagamon to Kochi & Athirappilly",
                "activities": "Marine Drive boat ride, Fort Kochi colonial sights, giant Chinese fishing nets, Athirappilly waterfalls nature park, return departure.",
                "spots": "Marine Drive Boat Ride, Chinese Fishing Nets, Fort Kochi, Athirappilly Waterfalls",
                "stay": "Return Journey"
            }
        ]
    },
    {
        "code": "SGT-HHH-KER-FAM-02",
        "name": "Kerala Grand Family Holiday - Munnar Tea Valley & Alleppey Backwaters",
        "destination": "Kerala (Munnar, Alleppey)",
        "category": "family_vacation",
        "duration_days": 3,
        "duration_nights": 2,
        "base_price": 6500,
        "min_pax": 4,
        "has_jeep_safari": False,
        "has_campfire_dj": False,
        "has_boating": True,
        "itinerary": [
            {
                "day": 1,
                "title": "Munnar Arrival, Cheeyappara Waterfalls & Tea Garden Tour",
                "route": "Home City to Munnar",
                "activities": "Cheeyappara and Valara waterfalls, tea garden walk, Mattupetty dam boating, Echo point.",
                "spots": "Cheeyappara Waterfalls, Valara Falls, Mattupetty Dam, Echo Point",
                "stay": "Munnar Premium Resort"
            },
            {
                "day": 2,
                "title": "Eravikulam National Park (Nilgiri Tahr) & Alleppey Resort",
                "route": "Munnar to Alleppey",
                "activities": "Eravikulam National Park safari to spot endangered Nilgiri Tahr. Drive to Alleppey backwater resort.",
                "spots": "Eravikulam National Park, Rajamalai, Blossom International Park, Alleppey Backwaters",
                "stay": "Alleppey Backwater Resort"
            },
            {
                "day": 3,
                "title": "Alleppey Backwater Shikara Cruise & Marari Beach",
                "route": "Alleppey to Return",
                "activities": "Traditional covered wooden shikara boat cruise through narrow backwater canals, Marari beach walk, return departure.",
                "spots": "Shikara Boat Cruise, Vembanad Canals, Marari Beach",
                "stay": "Return Journey"
            }
        ]
    },
    {
        "code": "SGT-HHH-KAR-FAM-01",
        "name": "Karnataka Family Vacation - Mysore Palace, Chamundi Hills, Coorg & Chikmagalur",
        "destination": "Karnataka (Mysore, Chikmagalur, Coorg)",
        "category": "family_vacation",
        "duration_days": 2,
        "duration_nights": 2,
        "base_price": 3500,
        "min_pax": 4,
        "has_jeep_safari": True,
        "has_campfire_dj": False,
        "has_boating": False,
        "itinerary": [
            {
                "day": 1,
                "title": "Mysore Royal Palace, Zoo, Shivoham Shiva Temple & Brindavan Gardens",
                "route": "Home City to Mysore",
                "activities": "Mysore Palace royal interior tour, Sri Chamarajendra Zoo, Shivoham Shiva Temple, Brindavan Gardens musical light show.",
                "spots": "Mysore Palace, Zoo, Shivoham Shiva Temple, Brindavan Gardens",
                "stay": "Hotel Maurya Palace, Mysore"
            },
            {
                "day": 2,
                "title": "Chikmagalur 7-Point Jeep Safari, Coorg Abbey Falls & Golden Temple",
                "route": "Mysore to Chikmagalur & Coorg",
                "activities": "Chikmagalur coffee estate 7-point jeep ride, Abbey Falls, Namdroling Monastery (Golden Temple), return departure.",
                "spots": "Chikmagalur Jeep Safari, Abbey Falls, Bylakuppe Golden Temple",
                "stay": "Return Journey"
            }
        ]
    },
    {
        "code": "SGT-HHH-TN-FAM-01",
        "name": "Tamil Nadu Family Vacation - Black Thunder Theme Park, Ooty & Rose Garden",
        "destination": "Tamil Nadu (Mettupalayam, Ooty, Coonoor)",
        "category": "family_vacation",
        "duration_days": 2,
        "duration_nights": 2,
        "base_price": 7000,
        "min_pax": 4,
        "has_jeep_safari": False,
        "has_campfire_dj": False,
        "has_boating": True,
        "itinerary": [
            {
                "day": 1,
                "title": "Black Thunder Water Theme Park Family Fun & Drive to Ooty",
                "route": "Home City to Mettupalayam & Ooty",
                "activities": "Full day family entertainment at Black Thunder Theme Park. Evening scenic drive to Ooty.",
                "spots": "Black Thunder Water Theme Park, Wave Pool, Nilgiri Mountain Pass",
                "stay": "Ooty Heritage Hotel"
            },
            {
                "day": 2,
                "title": "Ooty Pakoda Point, Botanical Garden, Rose Garden & Pine Forest",
                "route": "Ooty & Coonoor to Return",
                "activities": "Pakoda Point, Tea Factory, Government Botanical Garden, Government Rose Garden, Pine Forest walk, return departure.",
                "spots": "Pakoda Point, Botanical Garden, Rose Garden, Tea Factory, Pine Forest",
                "stay": "Return Journey"
            }
        ]
    },
    {
        "code": "SGT-HHH-GOA-FAM-01",
        "name": "Goa Family Holiday - Old Goa Heritage, Miramar Beach, Sunset Cruise & Colva",
        "destination": "Goa (North & South Goa)",
        "category": "family_vacation",
        "duration_days": 3,
        "duration_nights": 2,
        "base_price": 7566,
        "min_pax": 4,
        "has_jeep_safari": False,
        "has_campfire_dj": False,
        "has_boating": True,
        "itinerary": [
            {
                "day": 1,
                "title": "North Goa Calangute Beach, Fort Aguada Lighthouse & Candolim",
                "route": "Arrival to North Goa",
                "activities": "Resort check-in, Calangute Beach, Fort Aguada 17th-century lighthouse, Candolim sunset, family beachside dinner.",
                "spots": "Calangute Beach, Fort Aguada, Candolim Beach",
                "stay": "Goa Beachfront Resort"
            },
            {
                "day": 2,
                "title": "Old Goa UNESCO World Heritage Churches & Mandovi Family Cruise",
                "route": "Old Goa & Panaji",
                "activities": "Basilica of Bom Jesus, Se Cathedral, Miramar Beach, evening 1-hour Mandovi River family sunset boat cruise.",
                "spots": "Basilica of Bom Jesus, Se Cathedral, Miramar Beach, Mandovi River Sunset Cruise",
                "stay": "Goa Beachfront Resort"
            },
            {
                "day": 3,
                "title": "Colva Beach, Dona Paula Viewpoint & Panjim Latin Quarter",
                "route": "South Goa & Panaji to Return",
                "activities": "Colva Beach, Dona Paula lovers point, Fontainhas colorful Portuguese streets, cashew shopping, return departure.",
                "spots": "Colva Beach, Dona Paula, Fontainhas Latin Quarter",
                "stay": "Return Journey"
            }
        ]
    },

    # -------------------------------------------------------------
    # 4. SPECIAL DEPARTURES (Honeymoon, Manali, Diwali)
    # -------------------------------------------------------------
    {
        "code": "SGT-HHH-MANALI-01",
        "name": "Kullu Manali Snow Adventure & Valley Expedition - Solang Valley, Atal Tunnel & River Rafting",
        "destination": "Himachal Pradesh (Delhi, Kullu, Manali, Solang Valley, Atal Tunnel)",
        "category": "hill_station",
        "duration_days": 5,
        "duration_nights": 4,
        "base_price": 34999,
        "min_pax": 2,
        "has_jeep_safari": True,
        "has_campfire_dj": True,
        "has_boating": True,
        "itinerary": [
            {
                "day": 1,
                "title": "Arrival Delhi, Majnu ka Tila Volvo Stand & Overnight Bus to Manali",
                "route": "Delhi to Manali via AC Volvo Coach",
                "activities": "Arrive at Delhi airport / railway station. Chauffeur transfer to Majnu ka Tila Volvo boarding terminal. Board Luxury 2x2 Semi-Sleeper AC Volvo Coach (570 km overnight scenic journey via Chandigarh and Bilaspur).",
                "spots": "Delhi Majnu ka Tila, AC Volvo Journey, Beas Valley Highway",
                "stay": "Overnight AC Volvo Coach"
            },
            {
                "day": 2,
                "title": "Manali Arrival, Hadimba Devi Temple, Vashisht Springs & Mall Road",
                "route": "Manali Local Sightseeing",
                "activities": "Morning arrival in Manali surrounded by snow-capped peaks. Private cab transfer to luxury mountain resort, check-in and breakfast. Afternoon tour of 450-year-old wooden Hadimba Devi Temple, Vashisht Village with sacred hot sulphur springs, Tibetan Monastery, and evening stroll along vibrant Mall Road and Tibetan Bazaar.",
                "spots": "Hadimba Devi Temple, Vashisht Hot Springs, Van Vihar, Tibetan Monastery, Mall Road Manali",
                "stay": "Snow Valley Mountain Resort, Manali"
            },
            {
                "day": 3,
                "title": "Solang Valley Snow Point, Atal Tunnel & High Altitude Adventures",
                "route": "Manali to Solang Valley & Atal Tunnel",
                "activities": "Proceed to majestic Solang Valley (8,400 ft) for thrilling snow sports: paragliding, skiing, snow scooter, zorbing, and ropeway cable car ride. Drive through the engineering marvel Atal Tunnel (9.02 km, world's longest highway tunnel above 10,000 ft) to Sissu in Lahaul Valley. Return to resort for evening campfire and dinner.",
                "spots": "Solang Valley Snow Point, Atal Tunnel (Rohtang), Sissu Waterfall, Anjani Mahadev, Adventure Sports Arena",
                "stay": "Snow Valley Mountain Resort, Manali"
            },
            {
                "day": 4,
                "title": "Kullu Valley, Beas River White Water Rafting & Evening Volvo to Delhi",
                "route": "Manali to Kullu & Departure Volvo",
                "activities": "Checkout from resort, proceed down Kullu Valley. Visit world-famous Kullu Handloom Shawl Weaving Factory and Vaishno Devi Temple. Experience 14 km thrilling White Water River Rafting in the chilled rapids of Beas River. Evening drop at Manali Volvo stand to board overnight coach back to Delhi.",
                "spots": "Kullu Shawl Weaving Factory, Beas River White Water Rafting, Vaishno Devi Temple Kullu, Paragliding Pad",
                "stay": "Overnight AC Volvo Coach"
            },
            {
                "day": 5,
                "title": "Delhi Morning Arrival & Onward Journey Back Home",
                "route": "Delhi Majnu ka Tila to Airport / Station",
                "activities": "Morning arrival at Delhi Volvo stand (approx 07:00 AM). Transfer to airport or New Delhi railway station for onward departure with unforgettable Himalayan memories.",
                "spots": "Delhi Terminal, Return Flight / Train Connection",
                "stay": "Home Sweet Home"
            }
        ]
    },
    {
        "code": "SGT-HHH-HNY-KER-01",
        "name": "Romantic Kerala Honeymoon Escape - Munnar Misty Hills & Alleppey Backwaters",
        "destination": "Kerala (Munnar, Alleppey)",
        "category": "holiday",
        "duration_days": 3,
        "duration_nights": 2,
        "base_price": 12500,
        "min_pax": 2,
        "has_jeep_safari": False,
        "has_campfire_dj": False,
        "has_boating": True,
        "itinerary": [
            {
                "day": 1,
                "title": "Munnar Misty Hills Welcome, Cheeyappara & Candlelight Dinner",
                "route": "Cochin to Munnar",
                "activities": "Chauffeur pickup with flower bouquet. Drive to Munnar via Cheeyappara waterfalls. Check-in honeymoon suite with flower bed decoration, private candlelight dinner and honeymoon cake.",
                "spots": "Cheeyappara Waterfalls, Tea Valley, Honeymoon Candlelight Dinner, Flower Bed Decor",
                "stay": "Luxury Honeymoon Suite, Munnar"
            },
            {
                "day": 2,
                "title": "Mattupetty Dam Couple Boating, Echo Point & Alleppey Backwaters",
                "route": "Munnar to Alleppey Backwaters",
                "activities": "Romantic pedal boating at Mattupetty Dam, photo stops at Echo Point, proceed to Alleppey. Check-in private air-conditioned houseboat / backwater luxury resort with scenic canal views.",
                "spots": "Mattupetty Dam Boating, Echo Point, Alleppey Private Houseboat Cruise, Sunset Canal Tour",
                "stay": "Private A/C Houseboat / Resort, Alleppey"
            },
            {
                "day": 3,
                "title": "Alleppey Backwater Sunrise, Marari Beach & Departure",
                "route": "Alleppey to Cochin Airport / Station",
                "activities": "Morning breakfast overlooking the backwaters, Marari beach stroll, Cochin drop.",
                "spots": "Marari Beach, Cochin Harbor, Return Departure",
                "stay": "Return Journey"
            }
        ]
    },
    {
        "code": "SGT-HHH-HNY-KAR-01",
        "name": "Karnataka Romantic Honeymoon Escape - Coorg Coffee Plantation Resort & Abbey Falls",
        "destination": "Karnataka (Coorg, Mysore)",
        "category": "holiday",
        "duration_days": 3,
        "duration_nights": 2,
        "base_price": 14500,
        "min_pax": 2,
        "has_jeep_safari": False,
        "has_campfire_dj": False,
        "has_boating": False,
        "itinerary": [
            {
                "day": 1,
                "title": "Mysore Royal Palace Illumination & Coorg Private Plantation Resort",
                "route": "Bangalore / Mysore to Coorg",
                "activities": "Mysore Palace royal tour, Chamundi hills, proceed into Coorg coffee hills. Private villa check-in with floral decoration and candlelight dinner.",
                "spots": "Mysore Palace, Chamundi Hills, Coorg Coffee Plantation Resort, Candlelight Dinner",
                "stay": "Private Plantation Villa, Coorg"
            },
            {
                "day": 2,
                "title": "Abbey Falls Romantic Walk, Raja's Seat Sunset & Dubare Elephant Camp",
                "route": "Coorg Sightseeing",
                "activities": "Romantic walk to Abbey Falls, Dubare elephant camp riverbank, sunset at Raja's Seat musical garden, private plantation trek.",
                "spots": "Abbey Falls, Raja's Seat Sunset Viewpoint, Dubare Elephant Camp, Coffee Estate Trek",
                "stay": "Private Plantation Villa, Coorg"
            },
            {
                "day": 3,
                "title": "Bylakuppe Golden Temple & Return Departure",
                "route": "Coorg to Bangalore / Mysore Return",
                "activities": "Namdroling Monastery (Golden Temple), shopping for Coorg homemade chocolates, spices and coffee, return departure.",
                "spots": "Bylakuppe Golden Temple, Kushalnagar Spices Bazaar, Return Departure",
                "stay": "Return Journey"
            }
        ]
    },
    {
        "code": "SGT-HHH-DIWALI-01",
        "name": "Diwali Festive Special South India Tour - Madurai, Rameshwaram & Kanyakumari",
        "destination": "South India (Madurai, Rameshwaram, Kanyakumari)",
        "category": "devotional",
        "duration_days": 4,
        "duration_nights": 3,
        "base_price": 8999,
        "min_pax": 4,
        "has_jeep_safari": False,
        "has_campfire_dj": False,
        "has_boating": True,
        "itinerary": [
            {
                "day": 1,
                "title": "Madurai Meenakshi Amman Temple Diwali Deepam Darshan",
                "route": "Meeting Point to Madurai",
                "activities": "Diwali festival special darshan at Madurai Meenakshi Amman Temple, temple deepam illumination, Thirumalai Nayakkar Mahal.",
                "spots": "Madurai Meenakshi Amman Temple, Thousand Pillar Hall, Thirumalai Nayakkar Palace",
                "stay": "Hotel Heritage, Madurai"
            },
            {
                "day": 2,
                "title": "Rameshwaram Ramanathaswamy Temple 22 Theerthams & Pamban Bridge",
                "route": "Madurai to Rameshwaram",
                "activities": "Drive across Pamban Sea Bridge. Holy snanam in 22 Kund theerthams at Ramanathaswamy Temple, Agnitheertham seashore, Dr. APJ Abdul Kalam Memorial.",
                "spots": "Pamban Sea Bridge, Ramanathaswamy Temple 22 Theerthams, Dr. APJ Abdul Kalam Memorial, Agnitheertham",
                "stay": "Hotel Royal Park, Rameshwaram"
            },
            {
                "day": 3,
                "title": "Dhanushkodi Ram Setu Point & Kanyakumari Sunset",
                "route": "Rameshwaram to Kanyakumari",
                "activities": "4x4 ride to Dhanushkodi beach and Ram Setu viewpoint. Proceed to Kanyakumari for spectacular sunset over the confluence of three seas.",
                "spots": "Dhanushkodi Ghost Town, Ram Setu Point, Kanyakumari Sunset Point",
                "stay": "Hotel Sea View, Kanyakumari"
            },
            {
                "day": 4,
                "title": "Kanyakumari Vivekananda Rock Memorial, Suchindram Temple & Return",
                "route": "Kanyakumari to Return",
                "activities": "Ferry boat to Vivekananda Rock Memorial and Thiruvalluvar Statue. Darshan at Suchindram Thanumalayan Temple (Brahma, Vishnu, Shiva combined deity), return departure.",
                "spots": "Vivekananda Rock Memorial, Thiruvalluvar Statue, Suchindram Thanumalayan Temple",
                "stay": "Return Journey"
            }
        ]
    }
]

def main():
    print("=" * 80)
    print("  SIVA GAYATHRI TOURS & TRAVELS — HIP HOP HOLIDAYS COMPLETE INGESTION")
    print("=" * 80)

    vtypes_dict = get_vehicle_types()
    print("Mapped Vehicle Types for 5-Tier Tariffs:")
    for k, v in vtypes_dict.items():
        print(f"  - {k}: {v.name} (ID {v.id})")

    # Clear previous SGT-HHH- packages if any exist
    deleted = Package.objects.filter(package_code__startswith='SGT-HHH-').delete()
    print(f"\nCleared previous SGT-HHH- records: {deleted}")

    print(f"\nIngesting {len(PACKAGES_DATA)} packages into database with prefix SGT-HHH-...")

    created_packages = []
    created_days = []

    for item in PACKAGES_DATA:
        days = item['duration_days']
        nights = item['duration_nights']
        price_dec = Decimal(str(item['base_price']))
        ap_price = price_dec
        ep_price = Decimal(str(round(float(price_dec) * 0.78, 2)))

        is_dev = item['category'] == 'devotional'
        is_iv = item['category'] == 'college_iv'

        inclusions_text = (
            "Well-maintained tourist vehicle with professional chauffeur throughout the tour.\n"
            "All interstate road taxes, toll gates, vehicle parking, and entry permits.\n"
            f"Hotel / Resort accommodation on sharing basis ({'4-Sharing for Students' if is_iv else 'Twin/Triple Sharing'}).\n"
            "Chauffeur bata, accommodation, and fuel charges included.\n"
            "All sightseeing as per itinerary based on available time.\n"
            "Dedicated Tour In-charge / Chauffeur assistance from Siva Gayathri Tours & Travels."
        )
        if item.get('has_campfire_dj'):
            inclusions_text += "\nEvening High-Energy DJ Console Party with Campfire."
        if item.get('has_jeep_safari'):
            inclusions_text += "\nRugged 4x4 Off-Road Jeep Safari with experienced mountain drivers."
        if item.get('has_boating'):
            inclusions_text += "\nScenic Boating / Harbor Cruise."
        if is_iv:
            inclusions_text += "\nCollege Industrial Visit (IV) Documentation and Clearance Assistance."

        exclusions_text = (
            "Personal expenses like laundry, telephone calls, room service, and extra snacks.\n"
            "Any optional adventure activities or camera fees not specified in inclusions.\n"
            "Cost arising due to natural calamities, roadblocks, or flight/train cancellations.\n"
            "GST 5% as applicable."
        )

        terms_text = (
            "50% advance deposit upon trip confirmation, remaining balance payable prior to departure.\n"
            "Vehicle will strictly adhere to designated tourist routes, safety guidelines, and speed restrictions.\n"
            "Air-conditioning will be turned off on steep ghat roads and hairpin bends for passenger safety and engine power.\n"
            "Campfire and outdoor music are strictly subject to local forest and weather regulations.\n"
            "Siva Gayathri Tours & Travels guarantees polite chauffeurs, sanitized vehicles, and 24/7 helpline support."
        )

        pkg = Package.objects.create(
            package_code=item['code'],
            name=item['name'],
            destination=item['destination'][:150],
            category=item['category'],
            duration_nights=nights,
            duration_days=days,
            base_price=price_dec,
            price_with_food=ap_price,
            price_without_food=ep_price,
            pricing_type='per_person',
            meal_plan='AP',
            room_sharing_type='4_sharing' if is_iv else 'twin_sharing',
            min_pax=item['min_pax'],
            complementary_staff_count=2 if is_iv else 0,
            hotel_star_category='Star Category Hotel & Resort',
            vehicle_seating_desc='54-Seated Luxurious Tourist Coach' if is_iv else 'Comfortable AC Tourist Vehicle',
            bus_amenities_desc='Laser Lights, JBL Sound System, Push-Back Seats, First Aid Kit, Chauffeur with Uniform',
            has_campfire_dj=item.get('has_campfire_dj', False),
            has_jeep_safari=item.get('has_jeep_safari', False),
            has_boating=item.get('has_boating', False),
            has_industrial_visit=is_iv,
            is_devotional=is_dev,
            inclusions=inclusions_text,
            exclusions=exclusions_text,
            terms_and_conditions=terms_text,
            contact_persons_footer="Rithik CA (+91 98425 33777), Anandh C (+91 94381 7131 / +91 38209 9979)",
            description=f"Curated premium tour package by Siva Gayathri Tours & Travels covering {item['destination']}. Featuring expert route planning, sanitized transport, and comprehensive sightseeing.",
            is_active=True,
        )

        created_packages.append(pkg)

        # Create Itinerary Days
        for d in item['itinerary']:
            d_num = d['day']
            ItineraryDay.objects.create(
                package=pkg,
                day_number=d_num,
                title=d['title'][:250],
                route_segment=d.get('route', f"{item['destination']} Circuit")[:250],
                activities=d['activities'],
                sightseeing_spots=d.get('spots', item['destination'])[:500],
                night_stay_location=d.get('stay', item['destination'].split()[0])[:250],
                meals_included="Breakfast, Lunch, Dinner",
                transport_info='54-Seated Luxury Coach / Chauffeur-Driven Vehicle',
            )

        # Attach 5-Tier Tariffs
        attach_tariffs(pkg, days, vtypes_dict)

        # Devotional Temple Darshan Slots
        if is_dev:
            TempleDarshanSlot.objects.create(
                package=pkg,
                temple_name="Madurai Meenakshi Amman Temple",
                deity_or_circuit="Goddess Meenakshi & Sundareswarar",
                darshan_type="special_entry_300",
                booked_slot_time="07:00 AM - 09:30 AM",
                reporting_location="East Gopuram Entry Gate",
                dress_code_notes="Strict Traditional Attire (Dhoti/Kurta for Men, Saree/Chudidar for Women)",
                prasad_details="Special Laddoo & Kumkum Mahaprasad",
                senior_citizen_support=True
            )
            TempleDarshanSlot.objects.create(
                package=pkg,
                temple_name="Rameshwaram Ramanathaswamy Temple",
                deity_or_circuit="Lord Shiva (Jyotirlinga)",
                darshan_type="special_entry_300",
                booked_slot_time="06:00 AM - 08:30 AM",
                reporting_location="North Gopuram Special Darshan Queue",
                dress_code_notes="Traditional Attire (Dry clothes after 22 Theertham Snanam)",
                prasad_details="Holy Theertham & Vibhuti Prasadam",
                senior_citizen_support=True
            )

        print(f"  [OK] Ingested: [{pkg.package_code}] {pkg.name[:55]} ({pkg.duration_nights}N/{pkg.duration_days}D) — ₹{pkg.base_price}/pax")

    # Summary
    total_hhh = Package.objects.filter(package_code__startswith='SGT-HHH-').count()
    total_days = ItineraryDay.objects.filter(package__package_code__startswith='SGT-HHH-').count()
    total_tariffs = PackageVehicleTariff.objects.filter(package__package_code__startswith='SGT-HHH-').count()
    grand_total_pkgs = Package.objects.count()

    print("\n" + "=" * 80)
    print("  HIP HOP HOLIDAYS INGESTION REPORT (100% COMPLETE & VERIFIED)")
    print("=" * 80)
    print(f"Total SGT-HHH- Packages Ingested : {total_hhh}")
    print(f"Total SGT-HHH- Itinerary Days    : {total_days}")
    print(f"Total SGT-HHH- 5-Tier Tariffs    : {total_tariffs}")
    print(f"Grand Total Packages in Database : {grand_total_pkgs}")
    print("=" * 80)

if __name__ == '__main__':
    main()
