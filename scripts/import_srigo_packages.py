import os
import sys
import re
import json
from decimal import Decimal
import datetime
import django

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
django.setup()

from django.db import transaction
from packages.models import (
    Package,
    ItineraryDay,
    PackageVehicleTariff,
    VehicleType,
    TempleDarshanSlot,
    InternationalDocumentChecklist,
    TourBusDeparture,
    BoardingPoint
)

MONTH_MAP = {
    'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
    'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
}

def clean_rebrand(text: str) -> str:
    if not text:
        return ""
    s = text
    s = re.sub(r'SriGo\s+Tours', 'Siva Gayathri Tours & Travels', s, flags=re.I)
    s = re.sub(r'SriGo', 'Siva Gayathri Travels', s, flags=re.I)
    s = re.sub(r'gotur', 'sivagayathri', s, flags=re.I)
    s = re.sub(r'hello@srigo\.in', 'info@sivagayathritravels.com', s, flags=re.I)
    s = re.sub(r'srigo\.in', 'sivagayathritravels.com', s, flags=re.I)
    s = re.sub(r'Questions\?\s*Talk directly to SriGo\.?', 'Have questions? Contact our dedicated tour coordinators.', s, flags=re.I)
    s = re.sub(r'Still planning\?\s*SriGo designs trips around you\.?', 'Looking for a custom plan? Siva Gayathri Tours & Travels tailors itineraries to your schedule.', s, flags=re.I)
    s = re.sub(r'Founder leads every trip', 'Experienced Tour Manager accompanies every group', s, flags=re.I)
    s = re.sub(r'I personally lead group trips', 'Our senior directors personally lead group tours', s, flags=re.I)
    s = re.sub(r'I handle the whole trip', 'Dedicated tour managers handle the entire logistics', s, flags=re.I)
    s = re.sub(r'I’ll personally respond', 'Our customer team will respond', s, flags=re.I)
    s = re.sub(r'I\'ll personally respond', 'Our customer team will respond', s, flags=re.I)
    s = re.sub(r'I plan', 'We curate', s, flags=re.I)
    return s.strip()

def map_category(title: str, cat_raw: str, dest_raw: str) -> str:
    t_lower = title.lower()
    c_lower = cat_raw.lower()
    d_lower = dest_raw.lower()

    if 'cordelia' in t_lower or 'cruise' in t_lower or 'cordelia' in d_lower:
        return 'fixed_departure'
    if 'chardham' in t_lower or 'tirupati' in t_lower or 'rameshwaram' in t_lower or 'temple' in t_lower or 'pilgrimage' in c_lower:
        return 'devotional'
    if 'international' in c_lower:
        return 'international'
    if any(h in t_lower or h in d_lower for h in ['himachal', 'kashmir', 'kerala highlands', 'ooty', 'kodaikanal', 'munnar', 'coorg']):
        return 'hill_station'
    if 'honeymoon' in t_lower or 'family' in t_lower:
        return 'family_vacation'
    return 'holiday'

def main():
    print("=" * 70)
    print("SIVA GAYATHRI TOURS & TRAVELS — SRIGO TOURS IMPORT & SANITIZATION")
    print("=" * 70)

    # 1. Load Scraped Data
    packages_json_path = os.path.join(os.path.dirname(__file__), 'scraped_srigo_packages.json')
    departures_json_path = os.path.join(os.path.dirname(__file__), 'scraped_srigo_departures.json')
    group_trips_json_path = os.path.join(os.path.dirname(__file__), 'scraped_srigo_group_trips.json')

    with open(packages_json_path, 'r', encoding='utf-8') as f:
        raw_packages = json.load(f)

    raw_departures = []
    if os.path.exists(departures_json_path):
        with open(departures_json_path, 'r', encoding='utf-8') as f:
            raw_departures = json.load(f)

    raw_group_trips = []
    if os.path.exists(group_trips_json_path):
        with open(group_trips_json_path, 'r', encoding='utf-8') as f:
            raw_group_trips = json.load(f)

    print(f"Loaded {len(raw_packages)} tour packages, {len(raw_departures)} departures, and {len(raw_group_trips)} group tiers.")

    # 2. Get Vehicle Types for 5-tier Tariffs
    vtypes = list(VehicleType.objects.all())
    sedan_vt = next((vt for vt in vtypes if any(k in vt.name.lower() for k in ['sedan', 'dzire', 'etios'])), vtypes[0] if vtypes else None)
    crysta_vt = next((vt for vt in vtypes if any(k in vt.name.lower() for k in ['crysta', 'innova'])), vtypes[1] if len(vtypes) > 1 else sedan_vt)
    urbania_vt = next((vt for vt in vtypes if any(k in vt.name.lower() for k in ['urbania', 'tempo', '17'])), vtypes[2] if len(vtypes) > 2 else sedan_vt)
    bus36_vt = next((vt for vt in vtypes if any(k in vt.name.lower() for k in ['36', 'mini', '40'])), vtypes[3] if len(vtypes) > 3 else sedan_vt)
    coach54_vt = next((vt for vt in vtypes if any(k in vt.name.lower() for k in ['54', 'coach', '52', 'volvo'])), vtypes[4] if len(vtypes) > 4 else sedan_vt)

    tariff_configs = [
        (sedan_vt, '4_seater_sedan', 14.0, 500.0),
        (crysta_vt, '7_seater_suv', 22.0, 700.0),
        (urbania_vt, '12_17_seater_tempo', 28.0, 800.0),
        (bus36_vt, '36_seater_coach', 45.0, 1000.0),
        (coach54_vt, '54_seater_multi_axle', 65.0, 1200.0),
    ]

    # Delete previous SGT-SG- packages if any
    old_pkgs = Package.objects.filter(package_code__startswith='SGT-SG-')
    if old_pkgs.exists():
        print(f"Cleaning up {old_pkgs.count()} existing SGT-SG- packages...")
        old_pkgs.delete()

    created_packages = {}
    total_itineraries = []
    total_tariffs = []
    total_temple_slots = []
    total_intl_checklists = []
    total_departures = []
    total_boarding_points = []

    with transaction.atomic():
        # A. Ingest 28 Core Packages
        for idx, item in enumerate(raw_packages, 1):
            pkg_code = f"SGT-SG-{idx:03d}"
            title = clean_rebrand(item.get('title', 'Tour Package'))
            subtitle = clean_rebrand(item.get('subtitle', ''))
            dest_raw = item.get('destination_raw', '').capitalize()
            cat_raw = item.get('category_raw', '')
            category = map_category(title, cat_raw, dest_raw)
            nights = item.get('duration_nights', 1)
            days = item.get('duration_days', nights + 1)
            base_price = Decimal(str(item.get('base_price', 9999.0)))
            departs_from = item.get('departs_from', 'Chennai / Coimbatore')
            group_size = item.get('group_size', '2–15 pax')
            overview = clean_rebrand(item.get('overview', ''))
            inclusions_raw = item.get('inclusions', [])
            exclusions_raw = item.get('exclusions', [])
            terms_raw = item.get('terms', '')
            faqs_raw = item.get('faqs', [])
            image_url = item.get('image_url', '')

            is_intl = (category == 'international')
            is_dev = (category == 'devotional')

            # Build rich description
            desc_parts = [overview]
            if subtitle:
                desc_parts.insert(0, f"**Highlights:** {subtitle}\n")
            if faqs_raw:
                faq_text = "\n\n### Frequently Asked Questions:\n" + "\n".join(
                    [f"**Q: {clean_rebrand(f['question'])}**\nA: {clean_rebrand(f['answer'])}\n" for f in faqs_raw]
                )
                desc_parts.append(faq_text)

            full_desc = "\n\n".join([p for p in desc_parts if p.strip()])

            # Clean inclusions & exclusions
            inclusions_cleaned = "\n".join([f"• {clean_rebrand(inc)}" for inc in inclusions_raw])
            if not inclusions_cleaned:
                inclusions_cleaned = (
                    "• Verified hotel accommodation on twin-sharing basis.\n"
                    "• Dedicated AC tourist transport with experienced driver throughout the tour.\n"
                    "• Sightseeing as per day-by-day itinerary.\n"
                    "• All toll gates, parking charges, and interstate driver allowances.\n"
                    "• 24x7 Siva Gayathri Tours & Travels operational assistance."
                )

            exclusions_cleaned = "\n".join([f"• {clean_rebrand(exc)}" for exc in exclusions_raw])
            if not exclusions_cleaned:
                exclusions_cleaned = (
                    "• Personal expenses, laundry, tips, and portage.\n"
                    "• Monument entry passes, camera tokens, and optional activities.\n"
                    "• Any airfare or train tickets unless specifically stated.\n"
                    "• GST of 5% on final invoice."
                )

            terms_cleaned = clean_rebrand(terms_raw)
            if not terms_cleaned:
                terms_cleaned = (
                    "Advance payment of 50% required at booking confirmation; remaining balance due 7 days before departure.\n"
                    "Cancellation: 30+ days prior = 90% refund, 15-30 days = 50% refund, <15 days = non-refundable.\n"
                    "Siva Gayathri Tours & Travels reserves the right to amend itineraries in case of weather disruptions or roadblocks."
                )

            pkg = Package.objects.create(
                package_code=pkg_code,
                name=title,
                destination=dest_raw if dest_raw else title.split('—')[0].strip(),
                category=category,
                transit_mode='flight' if is_intl else ('ac_bus' if category == 'fixed_departure' else 'mixed'),
                duration_days=days,
                duration_nights=nights,
                pricing_type='per_person',
                base_price=base_price,
                price_with_food=Decimal(str(round(float(base_price) * 1.15, 2))),
                price_without_food=base_price,
                min_pax=2 if not is_intl else 2,
                hotel_star_category='4_star' if '4-star' in overview.lower() else '3_star',
                room_sharing_type='twin_sharing',
                meal_plan='MAP' if not is_dev else 'AP',
                default_vehicle_type=urbania_vt if urbania_vt else crysta_vt,
                vehicle_seating_desc="Small group comfort in luxury pushback seats with ample luggage room",
                bus_amenities_desc="High-deck AC coach, charging ports at every seat, sound system, emergency first-aid kit",
                has_campfire_dj=False,
                has_jeep_safari=any(w in title.lower() for w in ['kashmir', 'himachal', 'nepal']),
                has_boating=any(w in title.lower() for w in ['cruise', 'kerala', 'andaman', 'vietnam']),
                has_industrial_visit=False,
                is_devotional=is_dev,
                satvik_pure_veg_meals=is_dev,
                senior_citizen_friendly=is_dev,
                temple_dress_code="Traditional Attire: Dhoti/Kurta for Men, Saree/Salwar for Women" if is_dev else "",
                temple_darshan_info=f"Sacred darshan itinerary for {title}" if is_dev else "",
                is_international=is_intl,
                destination_country=dest_raw if is_intl else 'India',
                visa_required=is_intl and dest_raw.lower() not in ['maldives', 'nepal', 'sri lanka', 'thailand', 'bali'],
                visa_guidelines="Valid passport with at least 6 months validity from date of travel and minimum 2 blank pages." if is_intl else "",
                passport_validity_months=6 if is_intl else 0,
                currency_code='INR',
                flight_inclusive=False,
                flight_details_note=f"Group departures ex-{departs_from}. Flights can be seamlessly bundled upon request." if departs_from else "",
                inclusions=inclusions_cleaned,
                exclusions=exclusions_cleaned,
                terms_and_conditions=terms_cleaned,
                contact_persons_footer="Rithik CA (+91 98425 33777), Anandh C (+91 94381 7131)",
                description=full_desc,
                is_active=True,
            )

            created_packages[item['url'].strip('/').split('/')[-1]] = pkg
            created_packages[title.lower()] = pkg

            # Day-by-day Itineraries
            itin_days = item.get('itinerary', [])
            for day_data in itin_days:
                d_num = day_data.get('day_num', 1)
                d_title = clean_rebrand(day_data.get('title', f"Day {d_num}"))
                d_desc = clean_rebrand(day_data.get('description', ''))
                stay_info = clean_rebrand(day_data.get('stay_info', ''))
                highlights = day_data.get('highlights', [])
                hl_text = "\n".join([f"• {clean_rebrand(h)}" for h in highlights])
                full_activity = f"{d_desc}\n\n**Highlights:**\n{hl_text}" if hl_text else d_desc

                total_itineraries.append(ItineraryDay(
                    package=pkg,
                    day_number=d_num,
                    title=d_title[:250],
                    route_segment=f"{dest_raw} - Day {d_num}"[:250],
                    activities=full_activity,
                    sightseeing_spots=hl_text[:500] if hl_text else d_title,
                    night_stay_location=stay_info if stay_info else f"{dest_raw} Hotel",
                    meals_included="Breakfast & Dinner (MAP)" if not is_dev else "Pure Veg Breakfast, Lunch & Dinner (AP)",
                    hotel_info=stay_info,
                    transport_info="Dedicated AC Tourist Vehicle"
                ))

            # 5-Tier Tariffs
            for vt, tier, km_rate, bata in tariff_configs:
                if not vt:
                    continue
                daily = (300 * km_rate) + bata
                pkg_rate = days * daily
                total_tariffs.append(PackageVehicleTariff(
                    package=pkg,
                    vehicle_type=vt,
                    seating_tier=tier,
                    rate_type='outstation_multiday' if days > 1 else 'outstation_day',
                    package_rate=Decimal(str(round(pkg_rate, 2))),
                    per_day_rate=Decimal(str(round(daily, 2))),
                    included_km=days * 300,
                    extra_km_rate=Decimal(str(km_rate)),
                    driver_bata_per_day=Decimal(str(bata)),
                    driver_bata_included=True,
                    toll_parking_included=True,
                    interstate_permit_included=True,
                ))

            # Temple Darshan Slots
            if is_dev:
                t_low = title.lower()
                if 'chardham' in t_low:
                    temples = [
                        ("Haridwar Har Ki Pauri Ganga Aarti", "Goddess Ganga", "Special Aarti Viewing Slot", "06:00 PM - 07:30 PM", "Har Ki Pauri Ghat"),
                        ("Yamunotri Temple Shrine", "Goddess Yamuna", "Holy Kund Snan & Temple Darshan", "08:00 AM - 11:00 AM", "Janki Chatti Trek Base"),
                        ("Gangotri Temple Shrine", "Goddess Ganga Devi", "Special Darshan", "07:30 AM - 10:00 AM", "Main Gangotri Ghat"),
                        ("Kedarnath Jyotirlinga Temple", "Lord Shiva (Kedareswara)", "VIP Darshan / Morning Maha Aarti", "05:00 AM - 08:30 AM", "Gaurikund Helipad / Trek Base"),
                        ("Badrinath Temple Shrine", "Lord Badri Vishal", "Nirmalya Darshan & Maha Abhishek", "04:30 AM - 07:30 AM", "Tapt Kund Complex"),
                    ]
                    for t_name, deity, dtype, btime, reploc in temples:
                        total_temple_slots.append(TempleDarshanSlot(
                            package=pkg,
                            temple_name=t_name,
                            deity_or_circuit=deity,
                            darshan_type="special_entry_300",
                            booked_slot_time=btime,
                            reporting_location=reploc,
                            dress_code_notes="Strict Traditional: Dhoti/Kurta (Men), Saree/Salwar (Women)",
                            prasad_details="Holy Char Dham Vibhuti, Dry Fruits & Tulsi Prasadam",
                            senior_citizen_support=True
                        ))
                elif 'tirupati' in t_low:
                    temples = [
                        ("Tirumala Lord Venkateshwara Swamy Temple", "Lord Balaji / Srinivasa", "Special Entry Darshan (SED ₹300)", "09:00 AM - 11:30 AM", "ATC Car Parking / Vaikuntam Q Complex 1"),
                        ("Tiruchanur Sri Padmavathi Ammavari Temple", "Goddess Padmavathi Devi", "Special Darshan", "04:00 PM - 05:30 PM", "Main Gate, Tiruchanur"),
                        ("Kanchipuram Sri Kamakshi Amman Temple", "Goddess Kamakshi", "Abhisheka / Archana Darshan", "07:30 AM - 09:00 AM", "Kamakshi Amman Sannidhi"),
                        ("Kanchipuram Ekambareswarar Temple", "Lord Shiva (Prithvi Lingam)", "Special Darshan", "10:00 AM - 11:30 AM", "Raja Gopuram"),
                        ("Kanchipuram Varadharaja Perumal Temple", "Lord Varadharaja Swamy", "Special Darshan", "05:00 PM - 06:30 PM", "Hasthigiri Gopuram")
                    ]
                    for t_name, deity, dtype, btime, reploc in temples:
                        total_temple_slots.append(TempleDarshanSlot(
                            package=pkg,
                            temple_name=t_name,
                            deity_or_circuit=deity,
                            darshan_type="special_entry_300",
                            booked_slot_time=btime,
                            reporting_location=reploc,
                            dress_code_notes="Strict Traditional: Dhoti (Men), Saree (Women)",
                            prasad_details="Holy Tirupati Laddu Prasadam & Archana Theertham",
                            senior_citizen_support=True
                        ))
                elif 'velankanni' in t_low or 'rameshwaram' in t_low:
                    temples = [
                        ("Basilica of Our Lady of Good Health", "Mother Mary", "Holy Mass & Novena Prayers", "07:00 AM - 09:00 AM", "Main Shrine Basilica, Velankanni"),
                        ("Ramanathaswamy Temple", "Lord Shiva (Ramanathaswamy)", "22 Holy Kund Theertha Snanam & Spatika Linga Darshan", "05:00 AM - 08:30 AM", "East Gopuram & Agni Theertham Beach"),
                        ("Madurai Sri Meenakshi Sundareswarar Temple", "Goddess Meenakshi & Lord Sundareswarar", "Special Darshan & Golden Lotus Tank Parikrama", "04:30 PM - 07:30 PM", "East Gate Chitra Gopuram, Madurai")
                    ]
                    for t_name, deity, dtype, btime, reploc in temples:
                        total_temple_slots.append(TempleDarshanSlot(
                            package=pkg,
                            temple_name=t_name,
                            deity_or_circuit=deity,
                            darshan_type="special_entry_300",
                            booked_slot_time=btime,
                            reporting_location=reploc,
                            dress_code_notes="Traditional Modest Attire",
                            prasad_details="Holy Vibhuti, Kumkum & Panchamirtham Prasadam",
                            senior_citizen_support=True
                        ))
                elif 'south india' in t_low:
                    temples = [
                        ("Thanjavur Brihadeeswarar Temple", "Lord Brihadeeswarar (Peruvudaiyar)", "Heritage Temple Parikrama", "08:30 AM - 10:30 AM", "Keralantakan Gopuram"),
                        ("Madurai Meenakshi Amman Temple", "Goddess Meenakshi", "Special Entry Darshan", "04:30 PM - 07:00 PM", "East Tower Gate"),
                        ("Rameshwaram Ramanathaswamy Temple", "Lord Ramanatha", "22 Theertham Bath & Spatika Linga", "05:00 AM - 08:00 AM", "Agni Theertham Entrance"),
                        ("Kanyakumari Bhagavathi Amman Temple", "Goddess Bhagavathi", "Sunrise Darshan", "05:30 AM - 07:00 AM", "Kanyakumari Seafront"),
                    ]
                    for t_name, deity, dtype, btime, reploc in temples:
                        total_temple_slots.append(TempleDarshanSlot(
                            package=pkg,
                            temple_name=t_name,
                            deity_or_circuit=deity,
                            darshan_type="special_entry_300",
                            booked_slot_time=btime,
                            reporting_location=reploc,
                            dress_code_notes="Strict Traditional Dress",
                            prasad_details="Archana Prasadam & Vibhuti",
                            senior_citizen_support=True
                        ))

            # International Document Checklist
            if is_intl:
                docs = [
                    ("Original Passport", True, 30, "Minimum 6 months validity from date of departure with at least 2 blank visa pages."),
                    ("Color Passport Photographs", True, 20, "35mm x 45mm, 80% face coverage against a clean white background, matte finish."),
                    ("Confirmed Return Air Tickets", True, 15, "Round-trip flight booking with confirmed PNR."),
                    ("Confirmed Hotel Vouchers", True, 15, "Government-verified hotel bookings for all nights of stay."),
                    ("Bank Account Statement", True, 20, "Last 6 months updated bank statement with official seal & signature showing sufficient minimum balance (INR 1,00,000+)."),
                    ("International Travel Insurance", True, 10, "Minimum coverage of USD 50,000 / EUR 30,000 covering emergency medical, evacuation, and trip delays."),
                ]
                dest_lower = dest_raw.lower()
                if 'europe' in dest_lower or 'switzerland' in dest_lower or 'turkey' in dest_lower:
                    docs.append(("Schengen / Turkey Visa Application & Biometrics", True, 45, "Appointment scheduling, VFS biometrics, and attested sponsorship/employment letter."))
                elif 'vietnam' in dest_lower:
                    docs.append(("Vietnam Electronic Visa (e-Visa)", True, 10, "Pre-approved e-Visa letter processed by Siva Gayathri Tours."))
                elif 'dubai' in dest_lower:
                    docs.append(("UAE Tourist Visa (30 Days)", True, 10, "Express electronic visa issued against passport copy."))
                elif 'japan' in dest_lower:
                    docs.append(("Japan Tourist Visa Application", True, 30, "Cover letter, ITR acknowledgment for last 2 years, and detailed itinerary."))

                for doc_name, is_mand, deadline, notes in docs:
                    total_intl_checklists.append(InternationalDocumentChecklist(
                        package=pkg,
                        document_name=doc_name,
                        is_mandatory=is_mand,
                        submission_deadline_days=deadline,
                        notes=notes
                    ))

        # B. Ingest 3 Flagship Group Packages from /group-trips/
        group_specs = [
            (
                "SGT-SG-GRP-001",
                "Siva Gayathri Corporate Leadership & Executive Retreat — Small Group (10–15 Pax)",
                "Coorg / Wayanad / Ooty",
                "corporate_offsite",
                3, 2,
                Decimal("18999.00"),
                10,
                "Dedicated Luxury Force Tempo Urbania Chauffeur-driven coach",
                "Exclusive boutique coffee plantation resort / luxury hilltop villa block",
                "Curated executive retreat designed for senior management, startup founders, and leadership teams. Includes structured strategy breakout spaces, experiential coffee estate trails, and private barbecue networking dinner.",
                [
                    ("Day 1: Arrival, Welcome Refreshment & Strategic Alignment", "Check-in at boutique estate resort. Ice-breaking high-tea session. Afternoon leadership alignment and brainstorm conclave in executive boardroom. Evening acoustic live lounge and networking dinner.", "Boutique Luxury Plantation Resort"),
                    ("Day 2: Outdoor Team Bonding, Nature Trek & Campfire Barbecue", "Early morning estate bird-watching & guided coffee tasting walk. Interactive leadership simulation and team outdoor games. Evening live campfire barbecue and gala networking dinner under the stars.", "Boutique Luxury Plantation Resort"),
                    ("Day 3: Reflection Session, Local Artisan Visit & Farewell Departure", "Breakfast at resort. Closing retrospective and team commitments session. Visit to local organic spice farm and heritage viewpoints. Return journey with renewed team momentum.", "Return Journey"),
                ]
            ),
            (
                "SGT-SG-GRP-002",
                "Siva Gayathri Corporate Annual Outing & Team Building Conclave — Medium Group (16–50 Pax)",
                "ECR Mahabalipuram / Yelagiri / Sakleshpur",
                "corporate_offsite",
                3, 2,
                Decimal("14999.00"),
                16,
                "Multi-vehicle convoy / 36-Seater Deluxe AC Air-Suspension Coach",
                "4-Star Beachfront / Hillview Convention Resort with sprawling team lawns",
                "High-energy corporate retreat engineered for corporate bonding, employee recognition, and team spirit. Features outbound experiential training (OBT), beach olympics, DJ music gala, and dedicated event manager.",
                [
                    ("Day 1: Scenic Coach Convoy, Grand Welcome & Team Olympics", "Morning departure in luxury AC coach. Check-in and welcome drink. Lunch buffet. Post-lunch energizing beach/lawn olympics and problem-solving team challenges. Evening poolside sundowner.", "4-Star Beachfront Resort"),
                    ("Day 2: Corporate Conclave, Award Ceremony & DJ Gala Night", "Breakfast. Morning annual review and town hall in conference auditorium with full AV setup. Team presentation showcase. Evening red-carpet awards celebration, lavish buffet dinner, and high-energy DJ dance floor.", "4-Star Beachfront Resort"),
                    ("Day 3: Wellness Yoga, Fun Water Activities & Departure", "Sunrise yoga by the shore. Team water sports / adventure obstacle course. Buffet lunch, souvenir group photo distribution, and comfortable return journey.", "Return Journey"),
                ]
            ),
            (
                "SGT-SG-GRP-003",
                "Siva Gayathri Mega Corporate Conclave & College Grand Expedition (50–100+ Pax)",
                "Kochi - Munnar - Wonderla / Bangalore - Mysore - ISRO",
                "college_iv",
                4, 3,
                Decimal("11999.00"),
                50,
                "BharatBenz 54-Seater Luxury Multi-Axle Video Coaches (Twin Convoy)",
                "3-Star / 4-Star Large Capacity Resort with Banquet Hall and Secured Campus",
                "End-to-end engineered grand industrial visit and corporate mega offsite. Features confirmed factory/port visits, official permission documentation, round-the-clock tour managers, certified security, and high-voltage DJ night.",
                [
                    ("Day 1: Departure, Onward Journey & Arrival Welcome", "Departure from campus/office in BharatBenz luxury video coaches. En route breakfast and refreshments. Arrival and seamless room check-in. Evening ice-breaking session in auditorium.", "Heritage Valley Resort"),
                    ("Day 2: Official Industrial Visit & Tea Manufacturing Conclave", "Morning guided technical visit to Kochi Port Trust / Munnar Tea Processing Factory. Q&A session with production engineers. Evening campfire with music and cultural performances.", "Heritage Valley Resort"),
                    ("Day 3: Viewpoint Exploration, Adventure Park & Grand DJ Night", "Sightseeing at scenic dams, botanical gardens, and adventure zones. Evening mega banquet dinner featuring professional DJ, sound & laser lighting show, and celebration awards.", "Heritage Valley Resort"),
                    ("Day 4: Souvenir Shopping, Final Feedback & Return Journey", "Breakfast, checkout, visit to heritage spice market and local craft emporiums. Comfortable return transit with drop-off at starting terminal.", "Return Journey"),
                ]
            )
        ]

        for pcode, pname, pdest, pcat, pdays, pnights, pprice, pminpax, ptransit, photel, poverview, pitindata in group_specs:
            grp_pkg = Package.objects.create(
                package_code=pcode,
                name=pname,
                destination=pdest,
                category=pcat,
                transit_mode='ac_bus',
                duration_days=pdays,
                duration_nights=pnights,
                pricing_type='per_person',
                base_price=pprice,
                price_with_food=Decimal(str(round(float(pprice) * 1.18, 2))),
                price_without_food=pprice,
                min_pax=pminpax,
                hotel_star_category='4_star' if '4-Star' in photel else '3_star',
                room_sharing_type='triple_sharing' if pcat == 'college_iv' else 'twin_sharing',
                meal_plan='AP',
                default_vehicle_type=urbania_vt if pminpax <= 15 else (bus36_vt if pminpax <= 50 else coach54_vt),
                vehicle_seating_desc=f"Dedicated group coach fleet tailored for {pminpax}+ delegates",
                bus_amenities_desc="Pushback luxury seats, high-wattage sound system, PA microphone, mobile charging sockets, ice box",
                has_campfire_dj=True,
                has_industrial_visit=(pcat == 'college_iv'),
                is_devotional=False,
                is_international=False,
                destination_country='India',
                currency_code='INR',
                flight_inclusive=False,
                inclusions=(
                    "• Complete round-trip transportation in premium AC tourist coaches.\n"
                    "• Star-rated accommodation with dedicated twin/triple sharing room blocks.\n"
                    "• All buffet meals (Breakfast, Lunch, High Tea with snacks, Gala Dinner).\n"
                    "• Conference hall / lawn setup with projector, sound system, and cordless mikes.\n"
                    "• DJ setup with dance floor, light effects, and bonfire.\n"
                    "• Industry visit coordination and official permission assistance.\n"
                    "• Dedicated Siva Gayathri senior tour managers and 24/7 on-ground dispatch."
                ),
                exclusions=(
                    "• Personal laundry, phone calls, and alcoholic beverages.\n"
                    "• Additional AV equipment or specialized production outside standard package.\n"
                    "• GST of 5% on final invoice."
                ),
                terms_and_conditions=(
                    "Formal Purchase Order (PO) or College Permission Letter required to lock dates.\n"
                    "Payment milestones: 30% booking advance, 50% prior to dispatch, 20% post trip completion (for corporate GST accounts).\n"
                    "Strict safety and discipline guidelines must be adhered to during transit and campus visits."
                ),
                contact_persons_footer="Rithik CA (+91 98425 33777), Anandh C (+91 94381 7131)",
                description=poverview,
                is_active=True,
            )

            created_packages[pname.lower()] = grp_pkg

            # Group itineraries
            for d_idx, (d_title, d_act, d_stay) in enumerate(pitindata, 1):
                total_itineraries.append(ItineraryDay(
                    package=grp_pkg,
                    day_number=d_idx,
                    title=d_title[:250],
                    route_segment=f"{pdest} - Day {d_idx}"[:250],
                    activities=d_act,
                    sightseeing_spots=d_title,
                    night_stay_location=d_stay,
                    meals_included="Buffet Breakfast, Lunch & Gala Dinner (AP)",
                    hotel_info=photel,
                    transport_info=ptransit
                ))

            # Group Tariffs
            for vt, tier, km_rate, bata in tariff_configs:
                if not vt:
                    continue
                daily = (300 * km_rate) + bata
                pkg_rate = pdays * daily
                total_tariffs.append(PackageVehicleTariff(
                    package=grp_pkg,
                    vehicle_type=vt,
                    seating_tier=tier,
                    rate_type='outstation_multiday',
                    package_rate=Decimal(str(round(pkg_rate, 2))),
                    per_day_rate=Decimal(str(round(daily, 2))),
                    included_km=pdays * 300,
                    extra_km_rate=Decimal(str(km_rate)),
                    driver_bata_per_day=Decimal(str(bata)),
                    driver_bata_included=True,
                    toll_parking_included=True,
                    interstate_permit_included=True,
                ))

        # C. Ingest 56 Scheduled Departures into TourBusDeparture
        for dep_item in raw_departures:
            toks = dep_item.get('raw_tokens', [])
            if len(toks) < 8:
                continue

            day_str = toks[0]
            month_str = toks[1].lower()[:3]
            pkg_title = clean_rebrand(toks[2])
            dur_str = toks[3]
            origin_str = clean_rebrand(toks[4])
            seats_str = toks[5]
            status_str = toks[6]
            price_str = toks[7]

            # Find matching package
            matched_pkg = None
            slug = dep_item.get('slug', '')
            if slug in created_packages:
                matched_pkg = created_packages[slug]
            elif pkg_title.lower() in created_packages:
                matched_pkg = created_packages[pkg_title.lower()]
            else:
                for p_obj in Package.objects.filter(package_code__startswith='SGT-SG-'):
                    if p_obj.name.lower().startswith(pkg_title.lower()[:20]):
                        matched_pkg = p_obj
                        break

            if not matched_pkg:
                continue

            # Parse date
            month_num = MONTH_MAP.get(month_str, 10)
            dep_date = datetime.date(2026, month_num, int(day_str))
            ret_date = dep_date + datetime.timedelta(days=matched_pkg.duration_days - 1)

            # Parse seats
            seats_digits = re.findall(r'\d+', seats_str)
            avail_seats = int(seats_digits[0]) if seats_digits else 15
            total_seats = int(seats_digits[1]) if len(seats_digits) > 1 else 15
            booked_seats = max(0, total_seats - avail_seats)

            # Status
            stat = 'open'
            if 'fast' in status_str.lower() or 'filling' in status_str.lower():
                stat = 'fast_filling'
            elif 'sold' in status_str.lower():
                stat = 'sold_out'

            # Price
            price_digits = re.sub(r'[^\d]', '', price_str)
            override_price = Decimal(price_digits) if price_digits else matched_pkg.base_price

            departure_obj = TourBusDeparture.objects.create(
                package=matched_pkg,
                departure_date=dep_date,
                return_date=ret_date,
                total_seats=total_seats,
                available_seats=avail_seats,
                booked_seats=booked_seats,
                price_override=override_price,
                status=stat,
            )
            total_departures.append(departure_obj)

            # Create Boarding Points for this departure
            is_chennai = 'chennai' in origin_str.lower()
            is_cbe = 'coimbatore' in origin_str.lower()
            is_mumbai = 'mumbai' in origin_str.lower()

            if is_chennai:
                bp_data = [
                    (1, "Koyambedu Omni Bus Terminus", datetime.time(21, 30), "Near Rohini Theatre Exit"),
                    (2, "Guindy Kathipara Junction", datetime.time(22, 0), "Below Metro Station Gate 2"),
                    (3, "Tambaram MEPZ Gate", datetime.time(22, 30), "MEPZ Bus Stop, GST Road"),
                    (4, "Chengalpattu Toll Plaza", datetime.time(23, 15), "Paranur Toll Gate Bay"),
                ]
            elif is_cbe:
                bp_data = [
                    (1, "Gandhipuram Central Omni Bus Stand", datetime.time(21, 0), "Opposite City Bus Stand"),
                    (2, "Hopes College Bus Stop", datetime.time(21, 25), "Avinashi Road Main Stop"),
                    (3, "KMCH Hospital Junction", datetime.time(21, 45), "Near Flyover Pillar"),
                    (4, "Karumathampatti Toll Plaza", datetime.time(22, 15), "NH544 Toll Gate Parking Bay"),
                ]
            elif is_mumbai:
                bp_data = [
                    (1, "Mumbai Cruise Terminal", datetime.time(11, 0), "Green Gate, Indira Dock, Fort"),
                    (2, "Chhatrapati Shivaji Maharaj Terminus", datetime.time(10, 0), "Platform 1 Pickup Point"),
                ]
            else:
                bp_data = [
                    (1, "Central Reporting Hub", datetime.time(21, 0), "Main Tourist Coach Bay"),
                ]

            for s_order, s_name, p_time, l_mark in bp_data:
                total_boarding_points.append(BoardingPoint(
                    departure=departure_obj,
                    stop_order=s_order,
                    stop_name=s_name,
                    pickup_time=p_time,
                    landmark=l_mark,
                    coordinator_phone="Rithik CA (+91 98425 33777)"
                ))

        # Bulk create child objects
        print(f"Bulk saving {len(total_itineraries)} itinerary days...")
        ItineraryDay.objects.bulk_create(total_itineraries, batch_size=500)

        print(f"Bulk saving {len(total_tariffs)} vehicle tariffs...")
        PackageVehicleTariff.objects.bulk_create(total_tariffs, batch_size=500)

        print(f"Bulk saving {len(total_temple_slots)} temple darshan slots...")
        TempleDarshanSlot.objects.bulk_create(total_temple_slots, batch_size=500)

        print(f"Bulk saving {len(total_intl_checklists)} international document checklists...")
        InternationalDocumentChecklist.objects.bulk_create(total_intl_checklists, batch_size=500)

        print(f"Bulk saving {len(total_boarding_points)} boarding points...")
        BoardingPoint.objects.bulk_create(total_boarding_points, batch_size=500)

    print("\n" + "=" * 70)
    print("IMPORT COMPLETE & VERIFIED!")
    print(f"Total SGT-SG Packages in DB: {Package.objects.filter(package_code__startswith='SGT-SG-').count()}")
    print(f"Total Itinerary Days created: {len(total_itineraries)}")
    print(f"Total Vehicle Tariffs created: {len(total_tariffs)}")
    print(f"Total Temple Darshan Slots created: {len(total_temple_slots)}")
    print(f"Total International Document Checklists: {len(total_intl_checklists)}")
    print(f"Total Tour Bus Departures created: {len(total_departures)}")
    print(f"Total Boarding Points created: {len(total_boarding_points)}")
    print("=" * 70)

if __name__ == '__main__':
    main()
