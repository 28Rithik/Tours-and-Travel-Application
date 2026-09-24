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

from django.db import transaction
from packages.models import (
    Package,
    ItineraryDay,
    PackageVehicleTariff,
    TempleDarshanSlot,
    InternationalDocumentChecklist,
)
from core.models import VehicleType

FULL_CATALOG_FILE = os.path.join(os.path.dirname(__file__), 'scraped_rengha_full_catalog.json')
PREV_FILE = os.path.join(os.path.dirname(__file__), 'scraped_rengha_packages.json')

def clean_rebrand(text):
    if not text:
        return ""
    text = text.replace('\u2013', ' - ').replace('\u2014', ' - ').replace('\u2015', ' - ')
    text = text.replace('\u00a0', ' ').replace('\u2018', "'").replace('\u2019', "'").replace('\u201c', '"').replace('\u201d', '"')
    
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'wa\.link/\S+', '', text)
    text = re.sub(r'(?:www\.)?[a-zA-Z0-9-]+\.(?:com|in|org|net)/\S*', '', text)

    replacements = [
        (re.compile(r'Rengha\s+Holidays\s+(?:and|&)\s+Tourism\s+(?:Pvt\s+Ltd|Private\s+Limited)?', re.IGNORECASE), 'Siva Gayathri Tours & Travels'),
        (re.compile(r'Rengha\s+Holidays\s+(?:Pvt\s+Ltd|Private\s+Limited)?', re.IGNORECASE), 'Siva Gayathri Tours & Travels'),
        (re.compile(r'Rengha\s+Tourism', re.IGNORECASE), 'Siva Gayathri Tours & Travels'),
        (re.compile(r'Rengha', re.IGNORECASE), 'Siva Gayathri'),
        (re.compile(r'(?:Siva\s+)?Gayathriholidays(?:\.com)?', re.IGNORECASE), 'sivagayathritravels.com'),
        (re.compile(r'\+91[\s\d-]{9,15}'), '+91 98425 33777'),
    ]
    cleaned = text
    for pattern, repl in replacements:
        cleaned = pattern.sub(repl, cleaned)
        
    cleaned = re.sub(r'from\s+chennai', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'(\bTOUR PACKAGE\b\s*)+', 'TOUR PACKAGE', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'(\bPACKAGE\b\s*)+', 'PACKAGE', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s*,\s*', ', ', cleaned)
    cleaned = re.sub(r'\s*-\s*', ' - ', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned

def format_package_description(title, destination, days, nights, category, overview=""):
    cleaned_ov = clean_rebrand(overview or '').strip()
    cleaned_ov = re.sub(r'Duration:\s*\d+[^.]*', '', cleaned_ov, flags=re.IGNORECASE)
    cleaned_ov = re.sub(r'From City:[^.]*', '', cleaned_ov, flags=re.IGNORECASE)
    cleaned_ov = re.sub(r'To City:[^.]*', '', cleaned_ov, flags=re.IGNORECASE)
    cleaned_ov = re.sub(r'Place Covered:[^.]*', '', cleaned_ov, flags=re.IGNORECASE)
    cleaned_ov = re.sub(r'Tour Info[^.]*', '', cleaned_ov, flags=re.IGNORECASE)
    cleaned_ov = re.sub(r'About Temple:\s*', '', cleaned_ov, flags=re.IGNORECASE)
    cleaned_ov = re.sub(r'[\?]+', '', cleaned_ov)
    cleaned_ov = re.sub(r'^(?:Best|best)\s+[^:]*:\s*', '', cleaned_ov)
    cleaned_ov = re.sub(r'\s+', ' ', cleaned_ov).strip()
    
    if len(cleaned_ov) < 80:
        cat_desc = {
            'international': f"Embark on an unforgettable overseas journey with our {title} ({nights} Nights / {days} Days). Discover iconic landmarks, world-class attractions, and unique cultural experiences across {destination}. Features premium hotel accommodation, private transfers, daily meals, and comprehensive assistance from Siva Gayathri Tours & Travels.",
            'devotional': f"Attain divine blessings and peace of mind on our sacred {title} ({nights} Nights / {days} Days). Experience seamless darshan at venerated temples across {destination}, complemented by Satvik vegetarian meals, comfortable accommodations, senior citizen support, and dedicated chauffeur service.",
            'hill_station': f"Relax amidst scenic mountain vistas and misty valleys on our {title} ({nights} Nights / {days} Days). Explore famous tea gardens, viewpoints, waterfalls, and natural wonders across {destination} with private tourist vehicle logistics and verified star hotel stays.",
            'family_vacation': f"Create cherished memories with your family on our {title} ({nights} Nights / {days} Days). Enjoy an ideal blend of sightseeing, relaxation, and memorable activities across {destination}, thoughtfully curated by Siva Gayathri Tours & Travels.",
            'holiday': f"Experience the captivating sights, heritage, and landscapes of {destination} on our {title} ({nights} Nights / {days} Days). Complete with chauffeur-driven tourist vehicle, hotel accommodation, and personalized itinerary management."
        }.get(category, f"Experience {title} covering {destination} with Siva Gayathri Tours & Travels.")
        return cat_desc
    return cleaned_ov

def main():
    print("="*80, flush=True)
    print("RENGHA HOLIDAYS HIGH-SPEED DATABASE INGESTION", flush=True)
    print("="*80, flush=True)

    with open(FULL_CATALOG_FILE, 'r', encoding='utf-8') as f:
        catalog = json.load(f)
    print(f"Loaded {len(catalog)} packages from {FULL_CATALOG_FILE}", flush=True)

    # Merge honeymoon packages
    existing_urls = set(p.get('url') for p in catalog if p.get('url'))
    if os.path.exists(PREV_FILE):
        try:
            with open(PREV_FILE, 'r', encoding='utf-8') as f:
                prev_pkgs = json.load(f)
                hm_added = 0
                for p in prev_pkgs:
                    if p.get('url') and p['url'] not in existing_urls:
                        catalog.append(p)
                        existing_urls.add(p['url'])
                        hm_added += 1
                print(f"Merged {hm_added} honeymoon packages from previous catalog! Total: {len(catalog)}", flush=True)
        except Exception as e:
            print(f"Error loading prev pkgs: {e}", flush=True)

    # Clear previous SGT-RH packages
    deleted_count, _ = Package.objects.filter(package_code__startswith='SGT-RH-').delete()
    print(f"Cleared previous SGT-RH- records: {deleted_count}", flush=True)

    # Pre-fetch Vehicle Types
    vtypes = list(VehicleType.objects.all())
    sedan_vt = next((vt for vt in vtypes if any(k in vt.name.lower() for k in ['sedan', 'dzire', 'etios'])), vtypes[0] if vtypes else None)
    crysta_vt = next((vt for vt in vtypes if any(k in vt.name.lower() for k in ['crysta', 'innova'])), vtypes[1] if len(vtypes) > 1 else sedan_vt)
    urbania_vt = next((vt for vt in vtypes if any(k in vt.name.lower() for k in ['urbania', 'tempo', '17'])), vtypes[2] if len(vtypes) > 2 else sedan_vt)
    bus36_vt = next((vt for vt in vtypes if any(k in vt.name.lower() for k in ['36', 'mini', '40'])), vtypes[3] if len(vtypes) > 3 else sedan_vt)
    coach54_vt = next((vt for vt in vtypes if any(k in vt.name.lower() for k in ['54', 'coach', '52', 'volvo'])), vtypes[4] if len(vtypes) > 4 else sedan_vt)

    configs = [
        (sedan_vt, '4_sedan', 14.0, 500.0),
        (crysta_vt, '7_crysta', 20.0, 600.0),
        (urbania_vt, '17_tt_urbania', 26.0, 800.0),
        (bus36_vt, '36_mini_bus', 35.0, 1000.0),
        (coach54_vt, '54_luxury_coach', 45.0, 1200.0),
    ]

    all_itineraries = []
    all_tariffs = []
    all_checklists = []
    all_temple_slots = []
    used_codes = set()

    print("Creating packages and preparing relations in batches...", flush=True)
    with transaction.atomic():
        for idx, item in enumerate(catalog, 1):
            days = item.get('days', 4)
            nights = item.get('nights', max(1, days - 1))
            
            raw_slug = re.sub(r'[^A-Z0-9]+', '-', item['title'][:20]).strip('-')
            pkg_code = f"SGT-RH-{raw_slug}-{days}D"
            if pkg_code in used_codes:
                pkg_code = f"SGT-RH-{raw_slug}-{days}D-{idx}"
            used_codes.add(pkg_code)

            is_intl = item.get('is_international', False)
            is_dev = (item.get('category') == 'devotional')

            if is_intl:
                base_price = Decimal(str(days * 7500))
            elif is_dev:
                base_price = Decimal(str(days * 2200))
            elif item.get('category') == 'family_vacation':
                base_price = Decimal(str(days * 3400))
            elif item.get('category') == 'hill_station':
                base_price = Decimal(str(days * 2500))
            else:
                base_price = Decimal(str(days * 2400))

            ap_price = base_price
            ep_price = Decimal(str(round(float(base_price) * 0.78, 2)))
            meal_plan = 'MAP' if is_intl or item.get('category') == 'family_vacation' else 'AP'

            inclusions_list = item.get('inclusions', [])
            if inclusions_list:
                inclusions_text = "\n".join([f"• {inc}" for inc in inclusions_list])
            else:
                inclusions_text = (
                    "• Well-maintained tourist vehicle with professional chauffeur throughout the tour.\n"
                    "• All route permit charges, interstate road taxes, highway toll gates, and vehicle parking.\n"
                    "• Hotel accommodation on twin-sharing basis with daily breakfast and dinner.\n"
                    f"• Comprehensive sightseeing covering key attractions along {item['destination']}.\n"
                    + ("• 100% Satvik Pure Vegetarian South Indian meals.\n" if is_dev else "")
                    + "• 24x7 Siva Gayathri Tours & Travels dispatch and customer assistance."
                )

            exclusions_list = item.get('exclusions', [])
            if exclusions_list:
                exclusions_text = "\n".join([f"• {exc}" for exc in exclusions_list])
            else:
                exclusions_text = (
                    "• Monument entrance fees, boating charges, camera tokens, and personal expenses.\n"
                    "• Any airfare or train tickets (can be arranged upon request).\n"
                    "• Optional activities, adventure sports, or excursions not explicitly mentioned.\n"
                    "• Any delay or expenses caused by roadblocks, train delays, or natural calamities."
                )

            terms_text = (
                "50% advance deposit upon tour confirmation, remaining balance payable prior to trip departure.\n"
                "Vehicle will strictly adhere to designated routes, safety rules, and permit schedules.\n"
                "AC will be switched off on steep ghat roads and hairpin bends for engine power and passenger safety.\n"
                "Siva Gayathri Tours & Travels guarantees polite chauffeurs, sanitized coaches, and timely support."
            )

            pkg_name = clean_rebrand(item['title']).upper()
            pkg_dest = clean_rebrand(item.get('destination', ''))[:150]
            if not pkg_dest:
                pkg_dest = "Tour Destination"
            pkg_desc = format_package_description(pkg_name, pkg_dest, days, nights, item['category'], item.get('overview', ''))

            pkg = Package.objects.create(
                package_code=pkg_code,
                name=pkg_name,
                destination=pkg_dest,
                category=item['category'],
                duration_nights=nights,
                duration_days=days,
                base_price=base_price,
                price_with_food=ap_price,
                price_without_food=ep_price,
                pricing_type='per_person',
                meal_plan=meal_plan,
                room_sharing_type='twin_sharing',
                min_pax=2 if is_intl else 4,
                is_international=is_intl,
                destination_country=item.get('destination_country', 'India'),
                currency_code=item.get('currency_code', 'INR'),
                visa_required=is_intl,
                visa_guidelines=f"Tourist eVisa / Entry Authorization required for {item.get('destination_country')}." if is_intl else "",
                passport_validity_months=6 if is_intl else 0,
                flight_inclusive=False,
                flight_details_note=f"Scheduled flight booking assistance available Ex-Coimbatore (CJB) / Ex-Chennai (MAA) to {item.get('destination_country')}." if is_intl else "",
                overseas_dmc_partner=f"Certified DMC Destination Partner in {item.get('destination_country')}" if is_intl else "",
                is_devotional=is_dev,
                satvik_pure_veg_meals=is_dev,
                senior_citizen_friendly=is_dev,
                temple_dress_code="Mandatory Traditional Dress: Dhoti/Kurta for Men, Saree/Chudidar for Women" if is_dev else "",
                temple_darshan_info=f"Sacred Pilgrimage Circuit covering prominent shrines along {pkg_dest}." if is_dev else "",
                inclusions=inclusions_text,
                exclusions=exclusions_text,
                terms_and_conditions=terms_text,
                contact_persons_footer="Rithik CA (+91 98425 33777), Anandh C (+91 94381 7131)",
                description=pkg_desc,
                is_active=True,
            )

            # Itinerary Days
            raw_itinerary = item.get('itinerary') or item.get('days_plan') or []
            dest_parts = pkg_dest.split()
            primary_city = dest_parts[0] if dest_parts else "Destination"

            for d_idx in range(1, days + 1):
                if d_idx <= len(raw_itinerary):
                    plan_item = raw_itinerary[d_idx - 1]
                    d_title = plan_item.get('header') or plan_item.get('title') or f"Day {d_idx}: Sightseeing & Exploration"
                    d_desc = plan_item.get('content') or plan_item.get('desc') or f"Sightseeing and activities across {pkg_dest}."
                else:
                    if d_idx == days:
                        d_title = f"Day {d_idx}: Final Sightseeing, Souvenir Shopping & Departure"
                        d_desc = f"Morning leisure, local handicraft shopping, checkout from hotel, and comfortable return journey from {pkg_dest} with pleasant memories."
                    else:
                        d_title = f"Day {d_idx}: In-Depth Exploration of {pkg_dest}"
                        d_desc = f"Guided sightseeing covering major viewpoints, cultural monuments, and scenic landmarks along {pkg_dest}."

                d_title_clean = clean_rebrand(d_title)[:250]
                d_desc_clean = clean_rebrand(d_desc)

                all_itineraries.append(ItineraryDay(
                    package=pkg,
                    day_number=d_idx,
                    title=d_title_clean,
                    route_segment=f"{pkg_dest} Circuit"[:250],
                    activities=d_desc_clean,
                    sightseeing_spots=d_desc_clean[:500],
                    meals_included="Breakfast, Lunch, Dinner" if meal_plan == 'AP' else "Breakfast & Dinner",
                    night_stay_location=primary_city if days > 1 and d_idx < days else "Return Journey",
                ))

            # 5-Tier Tariffs
            for vt, tier, km_rate, bata in configs:
                if not vt:
                    continue
                daily = (300 * km_rate) + bata
                pkg_rate = days * daily
                all_tariffs.append(PackageVehicleTariff(
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
                    interstate_permit_included=True if pkg.is_international or any(k in pkg.name.lower() for k in ['kerala', 'karnataka', 'goa', 'delhi', 'agra', 'jaipur', 'mumbai', 'shirdi', 'puri', 'varanasi', 'char dham', 'do dham']) else False,
                ))

            # International Checklist
            if is_intl:
                docs = [
                    ("Original Passport (Min 6 months validity from return date)", True, 15, "Scan of front & back bio-pages"),
                    ("Passport Size Photograph (35x45mm, White background)", True, 10, "Matte finish, 80% face close up"),
                    ("Tourist eVisa / Entry Authorization Form", True, 7, "Processed via embassy portal"),
                    ("Confirmed Return Air Tickets & Hotel Vouchers", True, 5, "Issued by Siva Gayathri Tours"),
                    ("Overseas Travel & Medical Insurance Certificate", True, 5, "Minimum $50,000 coverage"),
                ]
                for dname, mand, dline, note in docs:
                    all_checklists.append(InternationalDocumentChecklist(
                        package=pkg,
                        document_name=dname,
                        is_mandatory=mand,
                        submission_deadline_days=dline,
                        notes=note
                    ))

            # Devotional Slots
            if is_dev:
                dest_lower = (item['title'] + " " + item['destination']).lower()
                if 'ramanathaswamy' in dest_lower or 'rameshwaram' in dest_lower or 'rameswaram' in dest_lower:
                    all_temple_slots.append(TempleDarshanSlot(
                        package=pkg,
                        temple_name="Arulmigu Ramanathaswamy Temple (22 Theertham & Spatika Lingam)",
                        deity_or_circuit="Lord Ramanathaswamy & Parvathavarthini Amman",
                        darshan_type="special_entry_300",
                        booked_slot_time="05:30 AM - 08:30 AM (Spatika Linga Pooja)",
                        reporting_location="East Gopuram Gate 1",
                        dress_code_notes="Strict Traditional: Dhoti/Kurta (Men), Saree (Women)",
                        prasad_details="Holy 22 Theertha Snanam & Temple Prasadam",
                        senior_citizen_support=True
                    ))
                elif 'puri' in dest_lower or 'jaganath' in dest_lower:
                    all_temple_slots.append(TempleDarshanSlot(
                        package=pkg,
                        temple_name="Puri Jagannath Temple & Konark Sun Temple",
                        deity_or_circuit="Lord Jagannath, Balabhadra & Subhadra",
                        darshan_type="special_entry_300",
                        booked_slot_time="06:30 AM - 09:30 AM",
                        reporting_location="Singhadwara (Lion's Gate)",
                        dress_code_notes="Strict Traditional: Dhoti/Kurta (Men), Saree (Women)",
                        prasad_details="Holy Mahaprasad (Khaja & Bhog)",
                        senior_citizen_support=True
                    ))
                elif 'char dham' in dest_lower or 'do dham' in dest_lower or 'kedarnath' in dest_lower or 'badrinath' in dest_lower:
                    all_temple_slots.append(TempleDarshanSlot(
                        package=pkg,
                        temple_name="Kedarnath Jyotirlinga & Badrinath Vishal Sannidhi",
                        deity_or_circuit="Lord Badri Vishal & Kedarnath Jyotirlinga",
                        darshan_type="special_entry_300",
                        booked_slot_time="06:00 AM - 09:00 AM",
                        reporting_location="Main Temple Complex",
                        dress_code_notes="Strict Traditional Attire (Warm Woolens)",
                        prasad_details="Badrinath Tulsi & Kedar Bhasma Prasadam",
                        senior_citizen_support=True
                    ))
                elif 'shirdi' in dest_lower:
                    all_temple_slots.append(TempleDarshanSlot(
                        package=pkg,
                        temple_name="Shirdi Sai Baba Samadhi Mandir & Shani Shingnapur",
                        deity_or_circuit="Shirdi Sai Baba & Lord Shani Bhagwan",
                        darshan_type="special_entry_300",
                        booked_slot_time="07:00 AM - 09:30 AM (Kakad Aarti / Darshan)",
                        reporting_location="VIP Gate 1 / Shirdi Sansthan Complex",
                        dress_code_notes="Decent Traditional Attire",
                        prasad_details="Sai Baba Udi & Boondi Ladoo Prasadam",
                        senior_citizen_support=True
                    ))
                elif 'kashi' in dest_lower or 'gaya' in dest_lower or 'ayodhya' in dest_lower:
                    all_temple_slots.append(TempleDarshanSlot(
                        package=pkg,
                        temple_name="Kashi Vishwanath Jyotirlinga & Ram Janmabhoomi Ayodhya",
                        deity_or_circuit="Lord Shiva Vishwanath & Sri Ram Lalla",
                        darshan_type="special_entry_300",
                        booked_slot_time="05:30 AM - 08:30 AM",
                        reporting_location="Kashi Vishwanath Corridor Gate 4",
                        dress_code_notes="Strict Traditional Attire",
                        prasad_details="Holy Ganga Jal & Ayodhya Ram Lalla Prasadam",
                        senior_citizen_support=True
                    ))
                elif 'guruvayur' in dest_lower or 'guruvayoor' in dest_lower:
                    all_temple_slots.append(TempleDarshanSlot(
                        package=pkg,
                        temple_name="Guruvayoor Sri Krishna Temple",
                        deity_or_circuit="Lord Guruvayoorappan (Unnikrishnan)",
                        darshan_type="special_entry_300",
                        booked_slot_time="04:30 AM - 07:30 AM",
                        reporting_location="East Nada Entrance",
                        dress_code_notes="Strict Kerala Traditional: Mundu (Men bare chest), Saree/Set Mundu (Women)",
                        prasad_details="Neyyappam & Palpayasam Prasadam",
                        senior_citizen_support=True
                    ))
                elif 'shiva' in dest_lower or 'sthalangal' in dest_lower or 'divya desam' in dest_lower:
                    all_temple_slots.append(TempleDarshanSlot(
                        package=pkg,
                        temple_name=f"{pkg_name.split('TOUR')[0].strip()[:70]}",
                        deity_or_circuit="Lord Shiva / Maha Vishnu Sacred Circuit",
                        darshan_type="special_entry_300",
                        booked_slot_time="06:30 AM - 09:30 AM (Morning Viswaroopa Darshan)",
                        reporting_location="Main Temple Rajagopuram Entrance",
                        dress_code_notes="Strict Traditional: Dhoti (Men), Saree / Chudidar with Dupatta (Women)",
                        prasad_details="Archana Prasadam, Vibhuti & Kumkum",
                        senior_citizen_support=True
                    ))
                else:
                    all_temple_slots.append(TempleDarshanSlot(
                        package=pkg,
                        temple_name=f"{item['destination']} Sacred Temple Circuit",
                        deity_or_circuit="Presiding Deity",
                        darshan_type="special_entry_300",
                        booked_slot_time="06:30 AM - 09:30 AM",
                        reporting_location="Main Temple Entrance",
                        dress_code_notes="Strict Traditional Attire",
                        prasad_details="Temple Archanai & Theertha Prasadam",
                        senior_citizen_support=True
                    ))

            if idx % 50 == 0 or idx == len(catalog):
                print(f"  Prepared {idx}/{len(catalog)} packages...", flush=True)

        print(f"Bulk creating {len(all_itineraries)} Itinerary Days...", flush=True)
        ItineraryDay.objects.bulk_create(all_itineraries, batch_size=500)

        print(f"Bulk creating {len(all_tariffs)} Vehicle Tariffs...", flush=True)
        PackageVehicleTariff.objects.bulk_create(all_tariffs, batch_size=500)

        if all_checklists:
            print(f"Bulk creating {len(all_checklists)} International Checklists...", flush=True)
            InternationalDocumentChecklist.objects.bulk_create(all_checklists, batch_size=500)

        if all_temple_slots:
            print(f"Bulk creating {len(all_temple_slots)} Temple Darshan Slots...", flush=True)
            TempleDarshanSlot.objects.bulk_create(all_temple_slots, batch_size=500)

    print("="*80, flush=True)
    print(f"SUCCESS! Fully imported {len(catalog)} packages under prefix SGT-RH-!", flush=True)
    print("="*80, flush=True)

if __name__ == '__main__':
    main()
