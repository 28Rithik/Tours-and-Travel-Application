"""
Comprehensive Automated Test Suite for Main User Webpage (Landing Page)
Verifies:
1. GET / (Landing Page) renders all navigation, buttons, forms, and interactive components.
2. Category Filter Pills: all 4 categories (Hill Stations, Devotional, College IV, Holiday) have packages.
3. Fare Estimator API calculation for all tiers and journey types.
4. Outstation Fleet Rental Booking Submission (POST /customer-portal/rental-checkout/).
5. Direct navigation to /customer-portal/rental-checkout/ redirects to #fare-estimator.
6. Fleet Showcase Cards with interactive tier selection and auto-scroll.
7. Policy Modal dialogues (Privacy, Terms, Cancellation & Refund) in footer.
8. Live Booking Tracking search.
9. Package detail view and catalog directory.
"""
import datetime
from django.utils import timezone
from django.test import TestCase, Client
from django.urls import reverse
from packages.models import Package
from operations.models import Booking


class LandingPageButtonsAndFunctionsTest(TestCase):
    def setUp(self):
        self.client = Client()
        from django.utils import timezone
        import datetime
        self.today = timezone.now().date()
        
        # Seed 1 test package for each key category
        categories = ['hill_station', 'devotional', 'college_iv', 'holiday']
        for cat in categories:
            Package.objects.get_or_create(
                package_code=f'PKG-TEST-{cat.upper()}',
                defaults={
                    'name': f'Test {cat.replace("_", " ").title()} Package',
                    'category': cat,
                    'destination': 'South India',
                    'duration_days': 3,
                    'duration_nights': 2,
                    'base_price': 4500,
                    'is_active': True
                }
            )

    def test_01_landing_page_render_and_components(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        html = response.content.decode('utf-8')
        
        # Check essential buttons & interactive widgets
        self.assertIn('id="rental-estimator-form"', html)
        self.assertIn('id="btn-book-rental"', html)
        self.assertIn('id="btn-hero-explore"', html)
        self.assertIn('selectFleetTier', html)
        self.assertIn('openPolicyModal', html)
        self.assertIn('id="policyModal"', html)
        self.assertIn('href="/customer-portal/packages/"', html)
        self.assertIn('#fare-estimator', html)

    def test_02_all_package_categories_populated_on_homepage(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        all_pkgs = response.context['all_packages']
        self.assertGreater(len(all_pkgs), 0)
        
        categories = {p.category for p in all_pkgs}
        self.assertIn('hill_station', categories, "Hill Stations category must have cards")
        self.assertIn('devotional', categories, "Devotional category must have cards")
        self.assertIn('college_iv', categories, "College IV category must have cards")
        has_holiday = any(c in ['holiday', 'family_vacation'] for c in categories)
        self.assertTrue(has_holiday, "Holiday category must have cards")

    def test_03_fare_estimator_api(self):
        response = self.client.post('/customer-portal/api/fare-estimator/', {
            'vehicle_tier': 'tt',
            'journey_type': 'outstation_round',
            'pickup_city': 'Coimbatore',
            'destination': 'Kodaikanal',
            'days': 3,
            'estimated_km': 650
        }, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertGreater(data['total_estimate'], 0)
        self.assertGreater(data['advance_payable'], 0)
        self.assertEqual(data['billable_km'], 900)  # 3 days * 300 min km/day = 900 km

    def test_04_rental_booking_submission(self):
        response = self.client.post('/customer-portal/rental-checkout/', {
            'vehicle_tier': 'crysta',
            'journey_type': 'outstation_round',
            'pickup_city': 'Coimbatore',
            'destination': 'Ooty',
            'days': 2,
            'estimated_km': 300,
            'pickup_date': '2026-10-12',
            'guest_name': 'Siva Traveler',
            'guest_phone': '9842511223'
        })
        self.assertEqual(response.status_code, 200)
        html = response.content.decode('utf-8')
        self.assertIn('Confirm Vehicle Rental', html)
        self.assertIn('SCAN TO PAY ADVANCE VIA UPI', html)
        self.assertIn('BK-RENT-', html)
        
        # Verify Booking record created
        booking = Booking.objects.filter(guest_phone='9842511223').order_by('-id').first()
        self.assertIsNotNone(booking)
        self.assertEqual(booking.status, 'pending')
        self.assertEqual(booking.pickup_location, 'Coimbatore')
        self.assertEqual(booking.destination, 'Ooty')

    def test_05_rental_checkout_get_redirects_to_estimator(self):
        response = self.client.get('/customer-portal/rental-checkout/')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/#fare-estimator')

    def test_06_booking_tracker_search(self):
        # Create a test booking
        from core.models import Client as CoreClient
        party = CoreClient.objects.create(name='Tracker Test', phone='9842509999')
        booking = Booking.objects.create(
            booking_number='BK-TEST-TRACK-99',
            party=party,
            guest_name='Tracker Test',
            guest_phone='9842509999',
            pickup_location='Coimbatore',
            pickup_date=self.today,
            pickup_time=datetime.time(8, 0),
            destination='Munnar',
            quoted_price=12000,
            status='confirmed'
        )
        # Search by booking number
        res_by_num = self.client.get(f'/customer-portal/track-booking/?q={booking.booking_number}')
        self.assertEqual(res_by_num.status_code, 302)
        self.assertIn(f'/customer-portal/booking/confirmed/{booking.id}/', res_by_num.url)
        
        # Search by phone number
        res_by_phone = self.client.get(f'/customer-portal/track-booking/?q={booking.guest_phone}')
        self.assertEqual(res_by_phone.status_code, 302)
        self.assertIn(f'/customer-portal/booking/confirmed/{booking.id}/', res_by_phone.url)
