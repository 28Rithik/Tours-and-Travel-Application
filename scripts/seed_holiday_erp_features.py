import os
import django
import datetime
from decimal import Decimal

import sys
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
django.setup()

from packages.models import (
    Package,
    PackageSeasonalRate,
    PackageHotelAllotment,
    PackageAddon,
    PackageB2BMargin,
    TourFeedbackLog,
    PackageInventory,
    CollegeIVExpedition
)
from core.models import Party

def run_seed():
    print("🚀 Seeding Holiday Package ERP Data...")

    # 1. Update Unit Economics on Packages
    pkgs = Package.objects.all()
    print(f"Found {pkgs.count()} packages. Updating unit economics P&L costs...")

    for pkg in pkgs:
        price = pkg.price_with_food or pkg.base_price or Decimal('5000')
        # Realistic cost modeling: ~80% COGS, ~20% Gross Margin
        pkg.cost_hotel_per_pax = round(price * Decimal('0.35'), 2)      # 35% Hotel Stay
        pkg.cost_coach_per_pax = round(price * Decimal('0.22'), 2)      # 22% Coach & Fuel
        pkg.cost_meals_per_pax = round(price * Decimal('0.18'), 2)      # 18% Meals (AP/MAP)
        pkg.cost_activities_per_pax = round(price * Decimal('0.06'), 2) # 6% Entry & Safari
        pkg.cost_misc_per_pax = round(price * Decimal('0.03'), 2)       # 3% Tolls & Guide
        pkg.save(update_fields=[
            'cost_hotel_per_pax',
            'cost_coach_per_pax',
            'cost_meals_per_pax',
            'cost_activities_per_pax',
            'cost_misc_per_pax',
        ])
    print("✅ Package unit economics P&L costs configured!")

    # 2. Seed Seasonal Rates on primary packages
    sample_pkg = pkgs.first()
    if sample_pkg:
        PackageSeasonalRate.objects.get_or_create(
            package=sample_pkg,
            season_name="Summer Vacation Peak Surge 2025",
            defaults={
                'season_type': 'peak',
                'start_date': datetime.date(2025, 5, 1),
                'end_date': datetime.date(2025, 6, 15),
                'surge_percentage': Decimal('20.00'),
                'vehicle_tariff_surge_percent': Decimal('15.00'),
                'notes': 'High demand period; resort room rates increase by 25%.',
                'is_active': True,
            }
        )
        PackageSeasonalRate.objects.get_or_create(
            package=sample_pkg,
            season_name="Diwali & Deepavali Long Weekend Surge",
            defaults={
                'season_type': 'festival',
                'start_date': datetime.date(2025, 10, 18),
                'end_date': datetime.date(2025, 10, 26),
                'surge_percentage': Decimal('15.00'),
                'vehicle_tariff_surge_percent': Decimal('10.00'),
                'notes': 'Peak festival transit window.',
                'is_active': True,
            }
        )
        print("✅ Seasonal rates seeded for", sample_pkg.name)

    # 3. Seed Hotel Room Allotment
    hotel_supplier, _ = Party.objects.get_or_create(
        name="Sterling Resorts & Hospitality Ltd",
        defaults={
            'party_type': 'supplier',
            'phone': '+91 94433 22110',
            'address': 'Fern Hill, Ooty, The Nilgiris',
        }
    )
    if sample_pkg:
        dep = PackageInventory.objects.filter(package=sample_pkg).first()
        PackageHotelAllotment.objects.get_or_create(
            package=sample_pkg,
            hotel_name="Sterling Fern Hill Resort & Spa, Ooty",
            defaults={
                'departure': dep,
                'hotel_partner': hotel_supplier,
                'room_category': 'deluxe_ac',
                'check_in_date': datetime.date(2025, 5, 10),
                'check_out_date': datetime.date(2025, 5, 13),
                'rooms_blocked': 15,
                'rooms_occupied': 12,
                'cost_per_room_night': Decimal('2800.00'),
                'cutoff_release_date': datetime.date(2025, 5, 3),
                'confirmation_voucher_no': 'ST-OOTY-2025-0842',
                'status': 'confirmed',
                'notes': '15 Deluxe AC valley view rooms blocked. Buffet breakfast & dinner included.'
            }
        )
        print("✅ Hotel room allotment seeded!")

    # 4. Seed Experience & Safari Add-ons
    if sample_pkg:
        PackageAddon.objects.get_or_create(
            package=sample_pkg,
            title="Mullayanagiri Peak 4x4 Off-Road Jeep Safari",
            defaults={
                'category': 'safari_adventure',
                'pricing_unit': 'per_person',
                'cost_price': Decimal('350.00'),
                'selling_price': Decimal('550.00'),
                'is_mandatory_inclusion': False,
                'description': 'Thrilling 4x4 Jeep ride up to Mullayanagiri & Bababudangiri mountain peaks.',
                'is_active': True,
            }
        )
        PackageAddon.objects.get_or_create(
            package=sample_pkg,
            title="Pykara Lake High-Speed Motorboat Ride",
            defaults={
                'category': 'boating_water',
                'pricing_unit': 'per_person',
                'cost_price': Decimal('180.00'),
                'selling_price': Decimal('300.00'),
                'is_mandatory_inclusion': False,
                'description': 'Speedboat ride on the pristine Pykara Lake with life jackets provided.',
                'is_active': True,
            }
        )
        PackageAddon.objects.get_or_create(
            package=sample_pkg,
            title="Comprehensive Tour Travel Accident & Medical Insurance",
            defaults={
                'category': 'insurance_health',
                'pricing_unit': 'per_person',
                'cost_price': Decimal('120.00'),
                'selling_price': Decimal('250.00'),
                'is_mandatory_inclusion': False,
                'description': '₹5,00,000 accidental cover + ₹50,000 emergency medical cashless coverage.',
                'is_active': True,
            }
        )
        print("✅ Experience add-ons seeded!")

    # 5. Seed B2B Sub-Agent Margins
    if sample_pkg:
        PackageB2BMargin.objects.get_or_create(
            package=sample_pkg,
            tier_name='silver_agent',
            defaults={
                'commission_percent': Decimal('6.00'),
                'is_active': True,
            }
        )
        PackageB2BMargin.objects.get_or_create(
            package=sample_pkg,
            tier_name='gold_agent',
            defaults={
                'commission_percent': Decimal('10.00'),
                'is_active': True,
            }
        )
        print("✅ B2B sub-agent commission rules seeded!")

    # 6. Seed Post-Trip Customer Feedback & NPS Logs
    if sample_pkg:
        iv = CollegeIVExpedition.objects.filter(package=sample_pkg).first()
        dep = PackageInventory.objects.filter(package=sample_pkg).first()

        TourFeedbackLog.objects.get_or_create(
            package=sample_pkg,
            guest_name="Dr. K. Senthil Kumar (HOD Mechanical)",
            defaults={
                'departure': dep,
                'iv_expedition': iv,
                'guest_phone': '+91 98421 55667',
                'trip_date': datetime.date(2025, 2, 18),
                'overall_rating': 5,
                'coach_driver_rating': 5,
                'hotel_rating': 5,
                'food_rating': 4,
                'schedule_rating': 5,
                'nps_score': 10,
                'customer_review_text': (
                    "Outstanding IV expedition management by Siva Gayathri Tours! "
                    "The 54-seater luxury coach was impeccably clean, driver Murugan was very safe and punctual, "
                    "and the students thoroughly enjoyed the DJ campfire night at the Coorg resort."
                ),
                'flag_status': 'positive',
                'is_verified': True,
            }
        )
        TourFeedbackLog.objects.get_or_create(
            package=sample_pkg,
            guest_name="Prof. M. Malarvizhi (Faculty In-charge)",
            defaults={
                'departure': dep,
                'iv_expedition': iv,
                'guest_phone': '+91 94422 77889',
                'trip_date': datetime.date(2025, 2, 18),
                'overall_rating': 4,
                'coach_driver_rating': 5,
                'hotel_rating': 4,
                'food_rating': 4,
                'schedule_rating': 4,
                'nps_score': 9,
                'customer_review_text': (
                    "Good management and very prompt responses from Rithik CA. "
                    "All industrial visit clearances at the tea factory were seamless."
                ),
                'flag_status': 'positive',
                'is_verified': True,
            }
        )
        print("✅ Customer reviews and NPS governance seeded!")

    print("🎉 All Holiday Package ERP features seeded successfully!")

if __name__ == '__main__':
    run_seed()
