import os
import sys
import re
import json
import ssl
import html
import urllib.request
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
    InternationalDocumentChecklist,
)
from core.models import VehicleType

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*'
}

def clean_rebrand(text):
    if not text:
        return ""
    text = text.replace('\u2013', ' - ').replace('\u2014', ' - ').replace('\u2015', ' - ')
    text = text.replace('\u00a0', ' ').replace('\xa0', ' ').replace('\u2018', "'").replace('\u2019', "'").replace('\u201c', '"').replace('\u201d', '"')
    
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'wa\.link/\S+', '', text)
    text = re.sub(r'(?:www\.)?[a-zA-Z0-9-]+\.(?:com|in|org|net)/\S*', '', text)

    replacements = [
        (re.compile(r'Aspire\s+Holidays\s+(?:Pvt\s+Ltd|Private\s+Limited)?', re.IGNORECASE), 'Siva Gayathri Tours & Travels'),
        (re.compile(r'Aspire\s+Holiday\s+(?:Pvt\s+Ltd|Private\s+Limited)?', re.IGNORECASE), 'Siva Gayathri Tours & Travels'),
        (re.compile(r'Aspire\s+Tours\s+(?:and|&)\s+Travels', re.IGNORECASE), 'Siva Gayathri Tours & Travels'),
        (re.compile(r'Aspire\s+Travels?', re.IGNORECASE), 'Siva Gayathri Tours & Travels'),
        (re.compile(r'\bAspire\b', re.IGNORECASE), 'Siva Gayathri'),
        (re.compile(r'aspireholidays\.in', re.IGNORECASE), 'sivagayathritravels.com'),
        (re.compile(r'info@aspireholidays\.in', re.IGNORECASE), 'info@sivagayathritravels.com'),
        (re.compile(r'\+91[\s\d-]{9,15}'), '+91 98425 33777'),
    ]
    cleaned = text
    for pattern, repl in replacements:
        cleaned = pattern.sub(repl, cleaned)

    cleaned = re.sub(r'\s*,\s*', ', ', cleaned)
    cleaned = re.sub(r'\s*-\s*', ' - ', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned

def detect_country_currency(country_name):
    combined = country_name.lower()
    mapping = [
        (('thailand', 'bangkok'), 'Thailand', 'THB'),
        (('singapore',), 'Singapore', 'SGD'),
        (('malaysia',), 'Malaysia', 'MYR'),
        (('united arab emirates', 'dubai', 'uae'), 'United Arab Emirates', 'AED'),
        (('indonesia', 'bali'), 'Indonesia', 'IDR'),
        (('vietnam',), 'Vietnam', 'VND'),
        (('maldives',), 'Maldives', 'USD'),
        (('sri lanka',), 'Sri Lanka', 'LKR'),
        (('switzerland',), 'Switzerland', 'CHF'),
        (('france', 'italy', 'germany', 'spain', 'austria', 'belgium', 'netherlands', 'finland', 'czech', 'malta', 'cyprus', 'greece', 'schengen'), country_name, 'EUR'),
        (('united kingdom', 'uk', 'england'), 'United Kingdom', 'GBP'),
        (('united states', 'usa', 'america'), 'United States', 'USD'),
        (('australia',), 'Australia', 'AUD'),
        (('new zealand',), 'New Zealand', 'NZD'),
        (('japan',), 'Japan', 'JPY'),
        (('south korea',), 'South Korea', 'KRW'),
        (('mauritius',), 'Mauritius', 'USD'),
        (('seychelles',), 'Seychelles', 'USD'),
        (('egypt',), 'Egypt', 'USD'),
        (('south africa',), 'South Africa', 'ZAR'),
        (('qatar',), 'Qatar', 'QAR'),
        (('oman',), 'Oman', 'OMR'),
        (('saudi arabia',), 'Saudi Arabia', 'SAR'),
        (('philippines',), 'Philippines', 'USD'),
        (('fiji',), 'Fiji', 'FJD'),
    ]
    for keywords, c_name, curr in mapping:
        if any(k in combined for k in keywords):
            return c_name, curr
    return country_name.title(), 'USD'

def main():
    print("=" * 80)
    print("  SIVA GAYATHRI TOURS & TRAVELS — ASPIRE VISA SERVICE PACKAGES EXTRACTOR")
    print("=" * 80)

    out_file = os.path.join(WORKSPACE_ROOT, 'scripts', 'scraped_aspire_visa_packages.json')
    if os.path.exists(out_file) and '--force-scrape' not in sys.argv:
        print(f"Loading cached visa dataset from {out_file}...")
        with open(out_file, 'r', encoding='utf-8') as f:
            cached_data = json.load(f)
            vpkgs = cached_data['packages']
            vguides = cached_data['guides']
        print(f"Loaded {len(vpkgs)} visa packages and {len(vguides)} country guides from cache!")
    else:
        print("Fetching Visa Packages from https://aspireholidays.in/api/visapackage...")
        req1 = urllib.request.Request('https://aspireholidays.in/api/visapackage', headers=HEADERS)
        vpkgs = json.loads(urllib.request.urlopen(req1, context=ctx, timeout=20).read().decode('utf-8')).get('data', [])
        
        print("Fetching Visa Guidelines from https://aspireholidays.in/api/visa...")
        req2 = urllib.request.Request('https://aspireholidays.in/api/visa', headers=HEADERS)
        vguides = json.loads(urllib.request.urlopen(req2, context=ctx, timeout=20).read().decode('utf-8')).get('data', [])

        print(f"Retrieved {len(vpkgs)} Visa Packages and {len(vguides)} Country Guides!")
        with open(out_file, 'w', encoding='utf-8') as f:
            json.dump({'packages': vpkgs, 'guides': vguides}, f, indent=2, ensure_ascii=False)
        print(f"Saved complete raw visa dataset to {out_file} ({os.path.getsize(out_file):,} bytes)!")

    # Build country guide lookup
    guide_map = {}
    for g in vguides:
        c = g.get('country')
        if isinstance(c, dict):
            cname = c.get('country')
            if cname:
                guide_map[cname.lower()] = g

    # Pre-fetch Vehicle types
    vtypes = list(VehicleType.objects.all())
    sedan_vt = next((vt for vt in vtypes if any(k in vt.name.lower() for k in ['sedan', 'dzire', 'etios'])), vtypes[0] if vtypes else None)
    crysta_vt = next((vt for vt in vtypes if any(k in vt.name.lower() for k in ['crysta', 'innova'])), vtypes[1] if len(vtypes) > 1 else sedan_vt)
    urbania_vt = next((vt for vt in vtypes if any(k in vt.name.lower() for k in ['urbania', 'tempo', '17'])), vtypes[2] if len(vtypes) > 2 else sedan_vt)
    bus36_vt = next((vt for vt in vtypes if any(k in vt.name.lower() for k in ['36', 'mini', '40'])), vtypes[3] if len(vtypes) > 3 else sedan_vt)
    coach54_vt = next((vt for vt in vtypes if any(k in vt.name.lower() for k in ['54', 'coach', '52', 'volvo'])), vtypes[4] if len(vtypes) > 4 else sedan_vt)

    tariff_configs = [
        (sedan_vt, '4_sedan', 14.0, 500.0),
        (crysta_vt, '7_crysta', 20.0, 600.0),
        (urbania_vt, '17_tt_urbania', 26.0, 800.0),
        (bus36_vt, '36_mini_bus', 35.0, 1000.0),
        (coach54_vt, '54_luxury_coach', 45.0, 1200.0),
    ]

    print(f"\nImporting {len(vpkgs)} Visa Service Packages into database under prefix SGT-AH-VISA-...")
    with transaction.atomic():
        deleted = Package.objects.filter(package_code__startswith='SGT-AH-VISA-').delete()
        print(f"Cleared previous SGT-AH-VISA- records: {deleted}")

        existing_codes = set(Package.objects.values_list('package_code', flat=True))
        all_pkg_records = []

        for idx, item in enumerate(vpkgs, 1):
            raw_name = item.get('name', 'International Tourist Visa').strip()
            # Country name extraction
            c_data = item.get('country')
            c_name = 'International'
            if isinstance(c_data, dict):
                ci = c_data.get('country')
                if isinstance(ci, dict):
                    c_name = ci.get('country', 'International')
                elif isinstance(ci, str):
                    c_name = ci

            pkg_name = clean_rebrand(raw_name).upper()
            if 'VISA' not in pkg_name:
                pkg_name = f"{pkg_name} VISA ASSISTANCE"

            country_name, currency_code = detect_country_currency(c_name)
            process_time = item.get('process_time') or '5 to 7 Working Days'
            stay_period = item.get('stay_period') or 'Upto 30 Days'
            validity = item.get('validity') or '3 Months'
            v_type = (item.get('type') or 'Tourist').title()

            # Unique slug
            raw_slug = re.sub(r'[^A-Z0-9]+', '-', pkg_name[:25]).strip('-')
            pkg_code = f"SGT-AH-VISA-{raw_slug}"
            if pkg_code in existing_codes:
                pkg_code = f"SGT-AH-VISA-{raw_slug}-{idx}"
            existing_codes.add(pkg_code)

            # Price
            raw_fee = item.get('fees')
            if raw_fee and str(raw_fee).isdigit() and int(raw_fee) > 0:
                base_price = Decimal(str(raw_fee))
            else:
                base_price = Decimal('3500.00')

            # Look up country guide if available
            guide = guide_map.get(c_name.lower())
            guide_desc = ""
            if guide:
                mdes = guide.get('mdes') or ''
                guide_desc = clean_rebrand(mdes)

            if guide_desc and len(guide_desc) > 50:
                description = f"{guide_desc}\n\nVisa Specifications:\n• Processing Time: {process_time}\n• Allowed Stay Period: {stay_period}\n• Visa Validity: {validity}\n• Category: {v_type} Visa"
            else:
                description = (
                    f"Comprehensive {pkg_name} documentation, appointment scheduling, and application filing assistance by Siva Gayathri Tours & Travels.\n\n"
                    f"Visa Specifications:\n"
                    f"• Destination Country: {country_name}\n"
                    f"• Visa Category: {v_type} Visa\n"
                    f"• Processing Turnaround: {process_time}\n"
                    f"• Permitted Stay Duration: {stay_period}\n"
                    f"• Entry Validity: {validity}\n"
                    f"• Expert Consultation & Form Verification Included"
                )

            inclusions_text = (
                "• Complete visa consultation, documentation evaluation, and appointment booking.\n"
                "• Professional review and digitization of passport bio-pages and supporting proofs.\n"
                "• Government consular portal filing and embassy processing fee facilitation.\n"
                "• Cover letter drafting, confirmed flight itinerary reservation, and dummy hotel vouchers.\n"
                "• Real-time application tracking and 24x7 customer support by Siva Gayathri visa desk."
            )

            exclusions_text = (
                "• Consular visa rejection penalties (non-refundable by respective foreign embassies).\n"
                "• VFS / TLS premium lounge or priority biometrics desk charges (optional).\n"
                "• Physical courier dispatch of stamped passports (charged at actuals if required).\n"
                "• Document translation, notary public, or MEA apostille charges (if required)."
            )

            terms_text = (
                "• Final visa issuance and validity are at the sole discretion of the respective embassy/consulate.\n"
                "• Processing turnaround times are government estimates and subject to embassy working days.\n"
                "• All supporting financial proofs, income tax returns, and employer letters must be authentic.\n"
                "• Siva Gayathri Tours & Travels guarantees verified application submission and dedicated guidance."
            )

            pkg = Package(
                package_code=pkg_code,
                name=pkg_name,
                destination=f"{country_name} (Visa Assistance)",
                category='international',
                duration_nights=0,
                duration_days=1,
                base_price=base_price,
                price_with_food=base_price,
                price_without_food=base_price,
                pricing_type='per_person',
                meal_plan='EP',
                room_sharing_type='twin_sharing',
                min_pax=1,
                is_international=True,
                destination_country=country_name,
                currency_code=currency_code,
                visa_required=True,
                visa_guidelines=f"Type: {v_type} | Processing: {process_time} | Stay: {stay_period} | Validity: {validity}",
                passport_validity_months=6,
                flight_inclusive=False,
                flight_details_note=f"Scheduled flight booking reservation vouchers provided for {country_name} visa submission.",
                overseas_dmc_partner=f"Certified Visa Consular Partner for {country_name}",
                is_devotional=False,
                satvik_pure_veg_meals=False,
                senior_citizen_friendly=True,
                inclusions=inclusions_text,
                exclusions=exclusions_text,
                terms_and_conditions=terms_text,
                contact_persons_footer="Rithik CA (+91 98425 33777), Anandh C (+91 94381 7131)",
                description=description,
                is_active=True,
            )
            all_pkg_records.append((pkg, country_name, v_type, process_time, stay_period))

        created_packages = Package.objects.bulk_create([p[0] for p in all_pkg_records])
        print(f"Created {len(created_packages)} Visa Service Package records in database!")

        all_days_records = []
        all_tariff_records = []
        all_doc_records = []

        for pkg, (_, country_name, v_type, process_time, stay_period) in zip(created_packages, all_pkg_records):
            # Day 1
            all_days_records.append(ItineraryDay(
                package=pkg,
                day_number=1,
                title=f"Day 1: Document Auditing, Biometrics & {country_name} Visa Submission",
                route_segment=f"{country_name} Consular Processing",
                activities=(
                    f"Step 1: Submission of original passport scans, photographs, and bank statements. "
                    f"Step 2: Verification and file formatting by Siva Gayathri visa specialists. "
                    f"Step 3: Appointment scheduling, portal submission, and application dispatch for embassy processing."
                ),
                sightseeing_spots=f"{country_name} Visa Desk, Application Portal & Biometrics Centre",
                meals_included="Executive Consultation",
                night_stay_location=f"{country_name} Consular Desk",
            ))

            # Fleet Tariffs
            for vt, tier, km_rate, bata in tariff_configs:
                if not vt:
                    continue
                daily = (100 * km_rate) + bata
                all_tariff_records.append(PackageVehicleTariff(
                    package=pkg,
                    vehicle_type=vt,
                    seating_tier=tier,
                    rate_type='local_1day',
                    package_rate=Decimal(str(round(daily, 2))),
                    per_day_rate=Decimal(str(round(daily, 2))),
                    included_km=100,
                    extra_km_rate=Decimal(str(km_rate)),
                    driver_bata_per_day=Decimal(str(bata)),
                    driver_bata_included=True,
                    toll_parking_included=True,
                    interstate_permit_included=False,
                ))

            # Document Checklist
            docs = [
                ("Original Passport (Min 6 months validity from travel date)", True, 15, "Minimum 2 blank pages required"),
                (f"Passport Size Photographs for {country_name}", True, 10, "White background, matte finish, 80% face view"),
                ("Last 6 Months Bank Statement with Bank Seal", True, 7, "Sufficient funds as per consular norms"),
                ("Employment Proof / Business Registration / College ID", True, 7, "Letter of introduction / Leave sanction"),
                ("Confirmed Round-Trip Flight Reservation & Hotel Voucher", True, 5, "Provided by Siva Gayathri Tours"),
                ("Overseas Travel & Health Insurance Certificate", True, 5, "Minimum $50,000 / €30,000 coverage"),
            ]
            for dname, mand, dline, note in docs:
                all_doc_records.append(InternationalDocumentChecklist(
                    package=pkg,
                    document_name=dname,
                    is_mandatory=mand,
                    submission_deadline_days=dline,
                    notes=note
                ))

        ItineraryDay.objects.bulk_create(all_days_records, batch_size=500)
        print(f"Saved {len(all_days_records)} ItineraryDay records!")

        PackageVehicleTariff.objects.bulk_create(all_tariff_records, batch_size=500)
        print(f"Saved {len(all_tariff_records)} PackageVehicleTariff records!")

        InternationalDocumentChecklist.objects.bulk_create(all_doc_records, batch_size=500)
        print(f"Saved {len(all_doc_records)} InternationalDocumentChecklist records!")

    print("=" * 80)
    print(f"SUCCESS! Imported all {len(created_packages)} Visa Service Packages under prefix SGT-AH-VISA-!")
    print("=" * 80)

if __name__ == '__main__':
    main()
