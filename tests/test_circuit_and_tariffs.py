from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from packages.models import Package, ItineraryDay, PackageVehicleTariff
from core.models import VehicleType


class CircuitAndTariffsTestCase(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_superuser('test_admin_circuit', 'admin_circuit@example.com', 'adminpass')
        self.client = Client()
        self.client.force_login(self.user)

    def test_circuit_and_fleet_tariffs_pipeline(self):
        # 1. Create a test Package simulating Kerala IV 5D
        pkg, _ = Package.objects.get_or_create(
            package_code="TEST-KL-4N5D-CASE",
            defaults={
                'name': "4 NIGHTS 5 DAYS KERALA COLLEGE IV (KOCHI-ALLEPPEY-VAGAMON)",
                'destination': "Kochi, Alleppey, Vagamon (Kerala)",
                'category': "college_iv",
                'duration_nights': 4,
                'duration_days': 5,
                'pricing_type': "per_person",
                'base_price': Decimal('4800.00'),
                'price_with_food': Decimal('6850.00'),
                'price_without_food': Decimal('4750.00'),
                'min_pax': 45,
                'complementary_staff_count': 2,
                'has_campfire_dj': True,
                'has_jeep_safari': True,
                'has_industrial_visit': True,
            }
        )

        kerala_days = [
            (1, "Arrival Kochi - InfoPark IT Hub - Marine Drive & Fort Kochi", "Coimbatore to Kochi Coach", "Kochi", "Breakfast, Lunch, Dinner"),
            (2, "Proceed to Alleppey - Backwater Houseboat Cruise & Beach", "Kochi to Alleppey", "Alleppey", "Breakfast, Lunch, Dinner"),
            (3, "Proceed to Vagamon Hills - Pine Forest & Off-Road Jeep Safari", "Alleppey to Vagamon", "Vagamon", "Breakfast, Lunch, Dinner"),
            (4, "Athirappilly & Vazhachal Waterfalls - Return Transit", "Vagamon to Athirappilly", "Transit", "Breakfast, Lunch, Dinner"),
            (5, "Safe Campus Arrival & Tour Completion", "Highway to Campus", "Campus", "Morning Refreshment"),
        ]

        for day_num, title, route, halt, meals in kerala_days:
            ItineraryDay.objects.create(
                package=pkg,
                day_number=day_num,
                title=title,
                route_segment=route,
                night_stay_location=halt,
                meals_included=meals,
                sightseeing_spots=f"Highlights for Day {day_num}",
                activities="Full tour activities"
            )

        self.assertEqual(ItineraryDay.objects.filter(package=pkg).count(), 5)

        # Map available VehicleTypes
        vt, _ = VehicleType.objects.get_or_create(name='Sedan 4-Seater', defaults={'seating_capacity': 4})
        PackageVehicleTariff.objects.create(
            package=pkg,
            vehicle_type=vt,
            seating_tier='4_sedan',
            rate_type='outstation_multiday',
            package_rate=Decimal('23500.00'),
            per_day_rate=Decimal('4700.00'),
            included_km=1500,
            extra_km_rate=Decimal('14.00'),
            driver_bata_per_day=Decimal('500.00'),
            driver_bata_included=True,
            toll_parking_included=True,
        )

        quote_resp = self.client.get(f'/packages/quote/{pkg.id}/')
        self.assertEqual(quote_resp.status_code, 200)
        html = quote_resp.content.decode('utf-8')
        self.assertTrue("Athirappilly" in html)
        self.assertTrue("Day 01" in html or "Day 1" in html)
