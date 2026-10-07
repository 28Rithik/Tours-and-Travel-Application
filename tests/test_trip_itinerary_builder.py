from datetime import date, timedelta
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
import json

from core.models import Vehicle, VehicleType, Driver, Party
from packages.models import Package, ItineraryDay
from operations.models import Trip, TripItineraryDay, Booking


class TripItineraryBuilderTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_superuser(
            username='admin_test',
            email='admin@test.com',
            password='password123'
        )
        self.client.login(username='admin_test', password='password123')

        self.party = Party.objects.create(name='Acme Corp', party_type='customer')
        self.v_type = VehicleType.objects.create(name='Luxury Coach', seating_capacity=54)
        self.vehicle = Vehicle.objects.create(
            registration_number='TN-38-BZ-9090',
            vehicle_type=self.v_type,
            status='available'
        )
        self.driver = Driver.objects.create(
            name='Karthik Murugan',
            phone='9842533777',
            status='active'
        )
        self.package = Package.objects.create(
            name='3 Days Mysore & Coorg Hill Getaway',
            destination='Karnataka',
            duration_days=3,
            duration_nights=2,
            base_price=6500,
        )
        ItineraryDay.objects.create(
            package=self.package,
            day_number=1,
            title='Bangalore to Mysore Heritage & Palace',
            route_segment='Bangalore -> Mysore',
            activities='Depart ex-Bangalore, visit Mysore Palace, evening Brindavan Gardens musical fountain.',
            morning_activity='Pickup from airport/railway station, traditional breakfast stop',
            sightseeing_spots='Mysore Palace, Chamundi Hills, St Philomenas Cathedral, Brindavan Gardens',
            evening_night_activity='Illuminated palace view, dinner buffet at Mysore hotel',
            night_stay_location='Mysore',
            meals_included='Breakfast, Lunch, Dinner',
            hotel_info='Royal Orchid Metropole',
            transport_info='54 Seated Luxury AC Coach'
        )
        ItineraryDay.objects.create(
            package=self.package,
            day_number=2,
            title='Mysore to Coorg Coffee County & Abbey Falls',
            route_segment='Mysore -> Coorg (Madikeri)',
            activities='Scenic transit to Coorg, Golden Temple Bylakuppe, Abbey Falls, Raja Seat sunset.',
            morning_activity='Hotel checkout after breakfast, drive through scenic teak forests',
            sightseeing_spots='Tibetan Monastery Bylakuppe, Dubare Elephant Camp, Abbey Falls, Raja Seat',
            evening_night_activity='Check in to Coorg resort, estate walk, bonfire & BBQ dinner',
            night_stay_location='Coorg',
            meals_included='Breakfast, Lunch, Dinner',
            hotel_info='Coorg Cliffs Resort & Spa',
            transport_info='54 Seated Luxury AC Coach'
        )

        self.booking = Booking.objects.create(
            party=self.party,
            guest_name='Dr. Arvind Swaminathan',
            guest_phone='9840112233',
            pickup_location='Kempegowda International Airport, Bangalore',
            destination='Mysore & Coorg',
            pickup_date=date(2026, 10, 1),
            pickup_time='06:00:00',
            vehicle_type=self.v_type,
            package=self.package,
            quoted_price=125000,
            status='confirmed',
        )

        self.trip = Trip.objects.create(
            trip_id='TR-TEST-0042',
            booking=self.booking,
            party=self.party,
            guest_name='Dr. Arvind Swaminathan',
            vehicle=self.vehicle,
            driver=self.driver,
            package=self.package,
            start_date=date(2026, 10, 1),
            end_date=date(2026, 10, 3),
            days_count=3,
            fixed_amount=125000,
            status='assigned',
        )

    def test_trip_import_package_itinerary(self):
        """Test 1-click import from package template."""
        count = self.trip.import_package_itinerary(self.package)
        self.assertEqual(count, 2)
        self.assertEqual(self.trip.itinerary_days.count(), 2)

        day1 = self.trip.itinerary_days.get(day_number=1)
        self.assertEqual(day1.date, date(2026, 10, 1))
        self.assertIn('Mysore Palace', day1.sightseeing_spots)
        self.assertEqual(len(day1.spots_list), 4)
        self.assertIn('Mysore Palace', day1.spots_list)
        self.assertEqual(day1.hotel_name, 'Royal Orchid Metropole')

        day2 = self.trip.itinerary_days.get(day_number=2)
        self.assertEqual(day2.date, date(2026, 10, 2))
        self.assertIn('Dubare Elephant Camp', day2.spots_list)

    def test_api_trip_itinerary_save(self):
        """Test API endpoint to save/update day-wise stops."""
        payload = {
            'days': [
                {
                    'day_number': 1,
                    'date': '2026-10-01',
                    'title': 'Arrival & Mysore Palace Tour',
                    'route_segment': 'BLR Airport -> Mysore',
                    'morning_plan': 'VIP pickup at airport',
                    'sightseeing_spots': 'Mysore Palace, Chamundi Hill',
                    'evening_plan': 'Brindavan Gardens lights',
                    'night_stay_location': 'Mysore',
                    'hotel_name': 'Grand Mercure Mysore',
                    'hotel_booking_status': 'confirmed',
                    'hotel_voucher_number': 'VCH-MY-7721',
                    'meals_included': 'Breakfast, Dinner',
                    'transport_mode': 'Luxury Coach',
                    'is_active_today': True,
                },
                {
                    'day_number': 2,
                    'date': '2026-10-02',
                    'title': 'Coorg Plantation Safari & Waterfalls',
                    'route_segment': 'Mysore -> Coorg',
                    'morning_plan': 'Breakfast at hotel, drive to Kushalnagar',
                    'sightseeing_spots': 'Namdroling Monastery, Abbey Falls',
                    'evening_plan': 'Resort campfire',
                    'night_stay_location': 'Madikeri, Coorg',
                    'hotel_name': 'Evolve Back Coorg',
                    'hotel_booking_status': 'confirmed',
                    'hotel_voucher_number': 'VCH-CRG-8899',
                    'meals_included': 'Breakfast, Lunch, Dinner',
                    'transport_mode': 'Luxury Coach + Jeep',
                    'is_active_today': False,
                }
            ]
        }
        url = reverse('api-trip-itinerary-save', args=[self.trip.pk])
        response = self.client.post(
            url,
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['days_count'], 2)

        # Verify database record
        self.assertEqual(self.trip.itinerary_days.count(), 2)
        d1 = self.trip.itinerary_days.get(day_number=1)
        self.assertEqual(d1.hotel_name, 'Grand Mercure Mysore')
        self.assertEqual(d1.hotel_voucher_number, 'VCH-MY-7721')
        self.assertTrue(d1.is_active_today)

    def test_api_trip_itinerary_get(self):
        """Test API endpoint to retrieve itinerary stops in JSON."""
        self.trip.import_package_itinerary(self.package)
        url = reverse('api-trip-itinerary-get', args=[self.trip.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['days_count'], 2)
        self.assertEqual(data['days'][0]['title'], 'Bangalore to Mysore Heritage & Palace')

    def test_api_trip_itinerary_import_package(self):
        """Test API endpoint to 1-click import package template."""
        url = reverse('api-trip-itinerary-import-package', args=[self.trip.pk])
        response = self.client.post(
            url,
            data=json.dumps({'package_id': self.package.pk}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['count'], 2)
        self.assertEqual(self.trip.itinerary_days.count(), 2)

    def test_admin_trip_itinerary_builder_view(self):
        """Test dispatcher builder view renders HTTP 200."""
        url = reverse('admin-trip-itinerary-builder', args=[self.trip.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Itinerary Studio')
        self.assertContains(response, 'TR-TEST-0042')
        self.assertContains(response, 'Save Itinerary')

    def test_guest_tour_itinerary_view_by_token_and_id(self):
        """Test Live Guest Experience Portal renders HTTP 200 via token and trip id."""
        self.trip.import_package_itinerary(self.package)
        
        # 1. Access by tracking token
        token_url = reverse('guest-tour-itinerary', args=[self.trip.tracking_token])
        response = self.client.get(token_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Live Tour Companion')
        self.assertContains(response, 'Dr. Arvind Swaminathan')
        self.assertContains(response, 'Karthik Murugan')
        self.assertContains(response, 'Mysore Palace')
        self.assertContains(response, 'Royal Orchid Metropole')

        # 2. Access by trip ID
        id_url = reverse('trip-itinerary-portal', args=[self.trip.pk])
        response2 = self.client.get(id_url)
        self.assertEqual(response2.status_code, 200)
        self.assertContains(response2, 'TR-TEST-0042')
