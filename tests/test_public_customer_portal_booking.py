import json
import datetime
from decimal import Decimal

from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from packages.models import Package, PackageInventory, ItineraryDay
from core.models import VehicleType, Party, Client as ClientModel
from operations.models import Booking
from marketing.models import Coupon
from payments_gateway.models import GatewayTransaction


class PublicCustomerPortalBookingTestCase(TestCase):
    """
    Comprehensive test suite for Part 3: Public Customer Booking Portal,
    Packages Showcase, Interactive Fleet Fare Estimator, and Dual Payment Checkout.
    """

    def setUp(self):
        self.client = Client()

        # 1. Create Core Vehicle Types
        self.vtype_crysta = VehicleType.objects.create(
            name="Toyota Innova Crysta Test",
            seating_capacity=7,
            default_km_rate=Decimal('19.00'),
            driver_bata=Decimal('500.00'),
            minimum_km_per_day=300
        )
        self.vtype_coach = VehicleType.objects.create(
            name="54-Seater Luxury AC Coach Test",
            seating_capacity=54,
            default_km_rate=Decimal('48.00'),
            driver_bata=Decimal('1200.00'),
            minimum_km_per_day=350
        )

        # 2. Create Master Package
        self.package = Package.objects.create(
            package_code="PKG-OOTY-03D",
            name="2 Nights 3 Days Ooty & Coonoor Scenic Hill Getaway",
            destination="Ooty & Coonoor (Tamil Nadu)",
            category="hill_station",
            duration_days=3,
            duration_nights=2,
            base_price=Decimal('4500.00'),
            price_with_food=Decimal('5500.00'),
            price_without_food=Decimal('4200.00'),
            hotel_star_category="3-Star Mountain Resort",
            vehicle_seating_desc="54-Seated Luxury Air Suspension Coach",
            inclusions="AC Coach transit\nResort accommodation\nDJ campfire\nBreakfast & Dinner",
            exclusions="Personal laundry\nMonument entry fees",
            terms_and_conditions="50% advance upon booking\nBalance on departure",
            is_active=True
        )

        # 3. Create Itinerary Days
        self.itinerary_day1 = ItineraryDay.objects.create(
            package=self.package,
            day_number=1,
            title="Coimbatore to Ooty - Check-in & Botanical Garden",
            activities="Morning departure from Coimbatore, hill climb via Mettupalayam, check-in to resort, afternoon visit to Government Botanical Garden.",
            meals_included="Lunch, Dinner"
        )
        self.itinerary_day2 = ItineraryDay.objects.create(
            package=self.package,
            day_number=2,
            title="Coonoor Sim's Park & Tea Factory Tour",
            activities="Full day sightseeing in Coonoor: Dolphin's Nose, Lamb's Rock, Highfield Tea Factory, and evening DJ campfire at resort.",
            meals_included="Breakfast, Lunch, Dinner"
        )

        # 4. Create Fixed Departure Inventory Batch
        self.departure_date = timezone.now().date() + datetime.timedelta(days=10)
        self.inventory = PackageInventory.objects.create(
            package=self.package,
            departure_date=self.departure_date,
            total_seats=52,
            available_seats=52,
            booked_seats=0,
            status='open'
        )

        # 5. Create Promotional Coupon
        self.coupon = Coupon.objects.create(
            code="SUMMER10",
            discount_percent=Decimal('10.00'),
            usage_limit=100,
            used_count=0,
            is_active=True
        )

    def test_01_public_landing_page_renders_successfully(self):
        """Verify public homepage / renders with hero banner, packages, and stats without requiring login."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "SIVAGAYATHIRI")
        self.assertContains(response, "Outstation Fleet Rental")
        self.assertContains(response, "Ooty")
        self.assertIn('all_packages', response.context)
        self.assertIn('stats', response.context)
        self.assertGreaterEqual(response.context['stats']['active_vehicles'], 300)

    def test_02_package_catalog_and_detail_views(self):
        """Verify package catalog filtering and day-by-day itinerary detail view."""
        # Catalog list
        response = self.client.get(reverse('customer_portal:package_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "All Tour Packages & Holiday Circuits")
        self.assertContains(response, "Ooty")

        # Filter by category
        res_filtered = self.client.get(reverse('customer_portal:package_list') + '?category=hill_station')
        self.assertEqual(res_filtered.status_code, 200)
        self.assertContains(res_filtered, "Ooty")

        # Package detail
        res_detail = self.client.get(reverse('customer_portal:package_detail', args=[self.package.id]))
        self.assertEqual(res_detail.status_code, 200)
        self.assertContains(res_detail, "DAY 01")
        self.assertContains(res_detail, "Coimbatore to Ooty")
        self.assertContains(res_detail, "52 / 52 Seats Left")

    def test_03_fleet_fare_estimator_api(self):
        """Verify POST /customer-portal/api/fare-estimator/ calculates realistic outstation and local tariffs."""
        # Outstation 3 Days Crysta
        payload = {
            'vehicle_tier': 'crysta',
            'journey_type': 'outstation_round',
            'days': 3,
            'estimated_km': 1000,
            'pickup_city': 'Coimbatore',
            'destination': 'Ooty'
        }
        response = self.client.post(
            reverse('customer_portal:api_fare_estimator'),
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['vehicle_tier'], 'crysta')
        self.assertEqual(data['billable_km'], 1000)
        self.assertEqual(data['km_rate'], 19.0)
        self.assertEqual(data['driver_bata_total'], 1500.0)  # 500 * 3
        # 1000 * 19 = 19000 + 1500 = 20500. GST 5% = 1025. Total = 21525
        self.assertEqual(data['total_estimate'], 21525.0)
        self.assertEqual(data['advance_payable'], 10762.5)

    def test_04_coupon_validation_api(self):
        """Verify coupon validation endpoint applies percentage discount and rejects invalid codes."""
        # Valid coupon
        payload = {'code': 'SUMMER10', 'total_amount': 20000}
        response = self.client.post(
            reverse('customer_portal:api_validate_coupon'),
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['valid'])
        self.assertEqual(data['discount_amount'], 2000.0)
        self.assertEqual(data['new_total'], 18000.0)

        # Invalid coupon
        bad_response = self.client.post(
            reverse('customer_portal:api_validate_coupon'),
            data=json.dumps({'code': 'NONEXISTENT', 'total_amount': 5000}),
            content_type='application/json'
        )
        self.assertFalse(bad_response.json()['valid'])

    def test_05_frictionless_guest_checkout_with_dynamic_upi(self):
        """
        Verify guest user can book a tour without prior account registration,
        submit a 12-digit UPI UTR, confirm the booking, decrement inventory seats,
        and post a balanced GL transaction.
        """
        checkout_url = reverse('customer_portal:checkout', args=[self.inventory.id])
        
        # 1. GET Checkout page (renders dynamic UPI QR preview)
        get_res = self.client.get(checkout_url)
        self.assertEqual(get_res.status_code, 200)
        self.assertContains(get_res, "Complete Your Tour Booking")
        self.assertIn('upi_package', get_res.context)

        # 2. POST Guest Checkout with UPI UTR
        post_data = {
            'guest_name': 'Kavitha Senthil',
            'guest_phone': '9842533888',
            'guest_email': 'kavitha@example.com',
            'pickup_location': 'Gandhipuram Bus Stand',
            'pax': 4,
            'meal_plan': 'AP',
            'coupon': 'SUMMER10',
            'payment_plan': 'advance',
            'payment_method': 'upi',
            'utr_number': '529814723912'
        }
        post_res = self.client.post(checkout_url, data=post_data)
        self.assertEqual(post_res.status_code, 302)
        redirect_url = post_res.headers.get('Location')
        self.assertIn('/customer-portal/booking/confirmed/', redirect_url)

        # 3. Verify created booking in database
        booking = Booking.objects.filter(guest_phone='9842533888').first()
        self.assertIsNotNone(booking)
        self.assertEqual(booking.status, 'confirmed')
        self.assertEqual(booking.pax_count, 4)
        self.assertEqual(booking.package, self.package)
        self.assertEqual(booking.package_inventory, self.inventory)

        # 4. Verify Gateway Transaction & GL posting
        txn = GatewayTransaction.objects.filter(booking=booking, provider='direct_upi').first()
        self.assertIsNotNone(txn)
        self.assertEqual(txn.gateway_payment_id, '529814723912')
        self.assertIn(txn.status, ['authorized', 'captured'])
        self.assertIsNotNone(txn.journal_entry)

        # 5. Verify seat count updated
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.booked_seats, 4)
        self.assertEqual(self.inventory.available_seats, 48)

        # 6. Verify Booking Confirmed Certificate View
        conf_res = self.client.get(redirect_url)
        self.assertEqual(conf_res.status_code, 200)
        self.assertContains(conf_res, "Booking Confirmed!")
        self.assertContains(conf_res, booking.booking_number)
        self.assertContains(conf_res, "Share on WhatsApp")

        # 7. Verify Quick Booking Tracker
        track_res = self.client.get(reverse('customer_portal:track_booking') + f'?q={booking.booking_number}')
        self.assertEqual(track_res.status_code, 302)
        self.assertIn(f'/customer-portal/booking/confirmed/{booking.id}/', track_res.headers.get('Location'))
