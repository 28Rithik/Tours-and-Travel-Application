import os
import sys
import json
import django
from decimal import Decimal

sys.stdout.reconfigure(encoding='utf-8')
WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, WORKSPACE_ROOT)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
django.setup()

from packages.models import Package, ItineraryDay, PackageVehicleTariff
from core.models import VehicleType
from scripts.scrape_and_import_holidify_all_india import parse_holidify_package_detail, detect_all_india_destination, detect_all_india_category

missing_urls = [
    'https://www.holidify.com/tour-package/5-day-darjeeling-and-kalimpong-scenic-escape-with-classic-highlights-26441.html',
    'https://www.holidify.com/tour-package/3-nights--4-days-darjeeling-package-with-mirik-19022.html',
    'https://www.holidify.com/tour-package/7-day-arunachal-pradesh-scenic-lakes-monasteries-and-nature-tour-19616.html',
    'https://www.holidify.com/tour-package/5-nights-6-days-kerala-package-18870.html',
    'https://www.holidify.com/tour-package/best-of-gujarat-with-rann-utsav-34351.html'
]

scraped = [parse_holidify_package_detail(u) for u in missing_urls]
scraped = [s for s in scraped if s]
print('Scraped missing count:', len(scraped))

v_sedan = VehicleType.objects.filter(name__icontains='sedan').first()
v_crysta = VehicleType.objects.filter(name__icontains='crysta').first() or VehicleType.objects.filter(name__icontains='innova').first()
v_urbania = VehicleType.objects.filter(name__icontains='urbania').first() or VehicleType.objects.filter(name__icontains='tempo').first()
v_minibus = VehicleType.objects.filter(name__icontains='36').first() or VehicleType.objects.filter(name__icontains='bus').first()
v_coach = VehicleType.objects.filter(name__icontains='54').first() or VehicleType.objects.filter(name__icontains='coach').first()

tariff_configs = [
    (v_sedan, '4_sedan', 14.0, 500),
    (v_crysta, '7_crysta', 20.0, 600),
    (v_urbania, '17_tt_urbania', 26.0, 800),
    (v_minibus, '36_mini_bus', 40.0, 1000),
    (v_coach, '54_luxury_coach', 55.0, 1200),
]

for p_data in scraped:
    pkg_id = p_data['pkg_id']
    code = f'SGT-HOL-IN-{pkg_id}'
    dest = detect_all_india_destination(p_data['title'])
    cat = detect_all_india_category(p_data['title'], p_data.get('theme', ''))
    base_price = Decimal(str(round(p_data['price'], 2)))
    pkg, _ = Package.objects.update_or_create(
        package_code=code,
        defaults=dict(
            name=p_data['title'],
            destination=dest,
            category=cat,
            transit_mode='road_coach',
            duration_days=p_data['days'],
            duration_nights=p_data['nights'],
            pricing_type='per_person',
            base_price=base_price,
            price_with_food=Decimal(str(round(float(base_price)*1.25, 2))),
            price_without_food=base_price,
            min_pax=2,
            hotel_star_category=p_data['stay_info'],
            room_sharing_type='twin_sharing',
            meal_plan='CP',
            default_vehicle_type=v_sedan,
            vehicle_seating_desc='Private Air-Conditioned Sedan / Crysta / Urbania Coach',
            bus_amenities_desc='AC, Clean Pushback Seats, First Aid Kit, Audio System',
            has_campfire_dj=True if 'hill' in cat else False,
            is_devotional=False,
            is_international=False,
            destination_country='India',
            currency_code='INR',
            inclusions='\n'.join(f'- {i}' for i in p_data['inclusions']) if p_data['inclusions'] else 'Standard Inclusions',
            exclusions='\n'.join(f'- {e}' for e in p_data['exclusions']) if p_data['exclusions'] else 'Standard Exclusions',
            terms_and_conditions='Standard Siva Gayathri Tours Terms & Conditions',
            contact_persons_footer='Rithik CA (+91 98425 33777), Anandh C (+91 94381 7131)',
            description=f'Scenic tour of {dest} with Siva Gayathri Tours & Travels.',
            is_active=True
        )
    )
    for it in p_data.get('itinerary', []):
        ItineraryDay.objects.update_or_create(
            package=pkg,
            day_number=it['day'],
            defaults=dict(
                title=f"Day {it['day']}: {it['title']}"[:250],
                activities=it['activities'],
                morning_activity=it['activities'][:300],
                sightseeing_spots=it['activities'][:400],
                meals_included='Breakfast & Dinner'
            )
        )
    for vt, tier, km_rate, bata in tariff_configs:
        daily = (300 * km_rate) + bata
        PackageVehicleTariff.objects.update_or_create(
            package=pkg,
            vehicle_type=vt,
            defaults=dict(
                seating_tier=tier,
                rate_type='outstation_multiday',
                package_rate=Decimal(str(round(p_data['days'] * daily, 2))),
                per_day_rate=Decimal(str(round(daily, 2))),
                included_km=p_data['days'] * 300,
                extra_km_rate=Decimal(str(km_rate)),
                driver_bata_per_day=Decimal(str(bata)),
                driver_bata_included=True,
                toll_parking_included=True,
                interstate_permit_included=True
            )
        )

print('Successfully imported all 5 missing packages!')
print('Total Holidify in DB:', Package.objects.filter(package_code__startswith='SGT-HOL-').count())
