import datetime
from decimal import Decimal
import json

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.utils import timezone
from django.urls import reverse

from core.models import Client as CoreClient, VehicleType, Driver, Vehicle
from crm.models import (
    Inquiry, InquiryFollowUp, Quotation, QuotationDay, QuotationItem,
    HotelMaster, MonumentEntranceMaster, ActivityMaster, GuideChargeMaster
)
from packages.models import (
    PackageTemplate, Package, ItineraryDay as PackageItineraryDay,
    PackageVehicleTariff, PackageInventory, BoardingPoint, TourPassengerManifest
)
from operations.models import Booking, Trip, TripItineraryDay


class Phase2CRMPackagesItineraryTests(TestCase):
    """
    End-to-End Master Backend Test Suite for Phase 2:
    CRM Sales Pipeline, Multi-Day Packages & Day-by-Day Tour Studio.
    """

    def setUp(self):
        self.user = User.objects.create_superuser(
            username='phase2_admin',
            email='admin@travelerp.com',
            password='password123'
        )
        self.client = Client()
        self.client.force_login(self.user)

        self.party = CoreClient.objects.create(
            name='Southern Odyssey Travels',
            phone='9840199887',
            email='info@southernodyssey.com'
        )

        self.vehicle_type = VehicleType.objects.create(
            name='Toyota Innova Crysta Phase2',
            seating_capacity=7,
            default_day_rate=Decimal('3500.00'),
            default_km_rate=Decimal('16.00')
        )

        self.vehicle = Vehicle.objects.create(
            registration_number='TN-38-P2-9999',
            vehicle_type=self.vehicle_type,
            status='available'
        )

        self.driver = Driver.objects.create(
            name='Sivakumar R',
            phone='9842511999',
            status='active'
        )

        self.inquiry = Inquiry.objects.create(
            inquiry_number='INQ-P2-001',
            party=self.party,
            guest_name='Dr. Arvind Subramanian',
            guest_phone='9842511223',
            guest_email='arvind@example.com',
            pickup_location='Coimbatore Junction',
            destination='Ooty & Coonoor Hill Tour',
            pickup_date=datetime.date(2026, 11, 10),
            pickup_time=datetime.time(8, 0),
            drop_date=datetime.date(2026, 11, 13),
            adult_count=4,
            child_count=2,
            vehicle_type=self.vehicle_type,
            status='new',
            priority='high',
            source='website',
            estimated_deal_value=Decimal('42000.00'),
            assigned_to=self.user
        )

    # -------------------------------------------------------------------------
    # 1. CRM Inquiries, Priorities & SLA TAT
    # -------------------------------------------------------------------------

    def test_crm_inquiry_lifecycle_and_sla_tat(self):
        """Test Inquiry SLA TAT calculation and overdue detection."""
        self.assertEqual(self.inquiry.priority, 'high')
        self.assertEqual(self.inquiry.status, 'new')
        self.assertIsNotNone(self.inquiry.tat_deadline)
        # Should not be overdue initially when just created with future deadline
        self.assertFalse(self.inquiry.is_overdue)

        # Make overdue by moving tat_deadline to the past
        self.inquiry.tat_deadline = timezone.now() - datetime.timedelta(hours=2)
        self.inquiry.save(update_fields=['tat_deadline'])
        self.assertTrue(self.inquiry.is_overdue)

    def test_inquiry_follow_up_and_communication_logging(self):
        """Test InquiryFollowUp logging and reminder date updates."""
        follow_up = InquiryFollowUp.objects.create(
            inquiry=self.inquiry,
            performed_by=self.user,
            interaction_type='phone',
            notes='Client requested detailed day-by-day plan with 4-star tea estate resort.',
            next_action='Dispatch customized PDF quote and WhatsApp summary.',
            is_done=True,
            completed_at=timezone.now()
        )
        self.assertEqual(str(follow_up), f"Follow-up on {self.inquiry.inquiry_number} (📞 Phone Call)")
        self.assertIn(follow_up, self.inquiry.follow_ups.all())

    # -------------------------------------------------------------------------
    # 2. Drag-and-Drop CRM Kanban Board & APIs
    # -------------------------------------------------------------------------

    def test_kanban_board_view_and_json_api(self):
        """Test Kanban board HTML view and JSON real-time state API."""
        # 1. HTML View
        res = self.client.get('/crm/kanban/')
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, 'crm/kanban_board.html')
        self.assertIn('columns', res.context)
        self.assertContains(res, 'Dr. Arvind Subramanian')

        # 2. JSON Data API
        api_res = self.client.get('/crm/api/kanban-data/')
        self.assertEqual(api_res.status_code, 200)
        data = api_res.json()
        self.assertEqual(data['status'], 'success')
        self.assertIn('board', data)
        self.assertIn('new', data['board'])
        self.assertGreaterEqual(data['board']['new']['count'], 1)

    def test_api_inquiry_stage_update_and_audit(self):
        """Test POST endpoint for drag-and-drop stage progression."""
        url = reverse('crm:api_inquiry_update_stage', kwargs={'inquiry_id': self.inquiry.id})
        payload = {'new_status': 'in_progress', 'kanban_order': 2}
        res = self.client.post(url, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['new_status'], 'in_progress')

        self.inquiry.refresh_from_db()
        self.assertEqual(self.inquiry.status, 'in_progress')

    def test_api_inquiry_quick_followup_modal(self):
        """Test quick follow-up modal interaction submission."""
        url = reverse('crm:api_inquiry_quick_followup', kwargs={'inquiry_id': self.inquiry.id})
        payload = {
            'interaction_type': 'whatsapp',
            'notes': 'Sent photo gallery of Kurumba Village Resort.',
            'next_action': 'Awaiting confirmation on meal preferences.',
            'next_followup_days': 1
        }
        res = self.client.post(url, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data['status'], 'success')

        self.inquiry.refresh_from_db()
        self.assertIsNotNone(self.inquiry.last_followup_at)
        self.assertIsNotNone(self.inquiry.next_followup_at)

    def test_api_inquiry_whatsapp_dispatch(self):
        """Test WhatsApp branded quotation preparation."""
        url = reverse('crm:api_inquiry_dispatch_whatsapp', kwargs={'inquiry_id': self.inquiry.id})
        payload = {'custom_note': 'Includes special toy train joyride booking from Coonoor.'}
        res = self.client.post(url, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data['status'], 'success')
        self.assertIn('wa_url', data)
        self.assertIn('9842511223', data['wa_url'])

    def test_api_inquiry_convert_to_booking_and_trip(self):
        """Test 1-click lead conversion into confirmed Booking and Trip."""
        url = reverse('crm:api_inquiry_convert_to_booking', kwargs={'inquiry_id': self.inquiry.id})
        res = self.client.post(url)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data['status'], 'success')
        self.assertIn('booking_id', data)
        self.assertIn('trip_id', data)

        self.inquiry.refresh_from_db()
        self.assertEqual(self.inquiry.status, 'won')
        self.assertIsNotNone(self.inquiry.converted_booking)
        self.assertIsNotNone(self.inquiry.converted_trip)
        self.assertEqual(self.inquiry.converted_trip.status, 'booked')

    # -------------------------------------------------------------------------
    # 3. Master Quotation Builder & Costing Engine
    # -------------------------------------------------------------------------

    def test_quotation_builder_itemized_costing_and_markup(self):
        """Test Quotation line items costing, 15% markup, and 5% GST calculations."""
        quote = Quotation.objects.create(
            party=self.party,
            inquiry=self.inquiry,
            guest_name='Dr. Arvind Subramanian',
            guest_phone='9842511223',
            title='4 Days Ooty & Coonoor Premium Holiday',
            destination='Ooty, Tamil Nadu',
            start_date=datetime.date(2026, 11, 10),
            end_date=datetime.date(2026, 11, 13),
            pax_count=4,
            vehicle_type=self.vehicle_type,
            markup_percent=Decimal('15.00'),
            gst_rate=Decimal('5.00'),
            created_by=self.user
        )

        day1 = QuotationDay.objects.create(
            quotation=quote,
            day_number=1,
            title='Arrival Coimbatore & Transit to Ooty via Coonoor',
            overnight_destination='Ooty',
            hotel_meal_plan='MAP',
            description='Arrival at Coimbatore junction, scenic drive to Ooty via Coonoor tea estates.'
        )

        # Line Item 1: Transport
        QuotationItem.objects.create(
            quotation=quote,
            day=day1,
            category='transport',
            item_name='Innova Crysta AC (4 Days Disposal)',
            quantity=1,
            unit_cost=Decimal('18000.00')
        )

        # Line Item 2: Hotel Accommodation
        QuotationItem.objects.create(
            quotation=quote,
            day=day1,
            category='hotel',
            item_name='Kurumba Village Resort (2 Rooms x 3 Nights)',
            quantity=1,
            unit_cost=Decimal('30000.00')
        )

        # Line Item 3: Monument / Sightseeing
        QuotationItem.objects.create(
            quotation=quote,
            day=day1,
            category='monument',
            item_name='Botanical Garden & Sim\'s Park Entry',
            quantity=4,
            unit_cost=Decimal('150.00')  # 600.00
        )

        # Recalculate totals
        total_payable = quote.recalculate_totals()
        quote.refresh_from_db()

        # Net Cost: 18000 + 30000 + 600 = 48,600.00
        self.assertEqual(quote.net_cost, Decimal('48600.00'))
        # 15% Markup: 48600 * 0.15 = 7,290.00
        self.assertEqual(quote.markup_amount, Decimal('7290.00'))
        # Gross: 48600 + 7290 = 55,890.00
        self.assertEqual(quote.gross_price, Decimal('55890.00'))
        # 5% GST: 55890 * 0.05 = 2,794.50
        self.assertEqual(quote.gst_amount, Decimal('2794.50'))
        # Total: 55890 + 2794.50 = 58,684.50
        self.assertEqual(quote.total_quoted_price, Decimal('58684.50'))
        self.assertEqual(total_payable, Decimal('58684.50'))

    def test_quotation_versioning_and_revisions(self):
        """Test Quotation.create_revision() clones days and items into V2."""
        quote = Quotation.objects.create(
            party=self.party,
            guest_name='Mr. Balaji',
            destination='Kodaikanal',
            start_date=datetime.date(2026, 12, 1),
            end_date=datetime.date(2026, 12, 3),
            pax_count=2,
            created_by=self.user
        )
        day1 = QuotationDay.objects.create(quotation=quote, day_number=1, title='Kodai Lake & Coakers Walk')
        QuotationItem.objects.create(quotation=quote, day=day1, category='accommodation', item_name='Resort', quantity=1, unit_cost=Decimal('8000.00'))
        quote.recalculate_totals()

        revised_quote = quote.create_revision()
        self.assertEqual(revised_quote.version, 2)
        self.assertIn('-v2', revised_quote.quotation_number)
        self.assertEqual(revised_quote.days.count(), 1)
        self.assertEqual(revised_quote.items.count(), 1)
        self.assertEqual(revised_quote.net_cost, Decimal('8000.00'))

    def test_quotation_convert_to_booking(self):
        """Test Quotation.convert_to_booking() generates operational booking."""
        quote = Quotation.objects.create(
            party=self.party,
            guest_name='Mr. Prakash',
            destination='Munnar',
            start_date=datetime.date(2026, 11, 20),
            end_date=datetime.date(2026, 11, 23),
            pax_count=3,
            vehicle_type=self.vehicle_type,
            total_quoted_price=Decimal('35000.00'),
            created_by=self.user
        )
        booking = quote.convert_to_booking()
        self.assertIsNotNone(booking.id)
        self.assertEqual(booking.guest_name, 'Mr. Prakash')
        self.assertEqual(quote.status, 'converted')

    # -------------------------------------------------------------------------
    # 4. Multi-Day Tour Packages, Tariffs & Departures
    # -------------------------------------------------------------------------

    def test_package_creation_dual_pricing_and_inclusions(self):
        """Test PackageTemplate and Package dual pricing breakdown."""
        template = PackageTemplate.objects.create(
            name='Kerala Backwaters & Hills Circuit',
            destination='Kochi - Munnar - Alleppey',
            category='holiday',
            duration_days=4,
            duration_nights=3,
            base_price=Decimal('12000.00')
        )
        self.assertEqual(str(template), 'Kerala Backwaters & Hills Circuit (3N/4D)')

        pkg = Package.objects.create(
            template=template,
            package_code='PKG-KL-4D',
            name='4 Days Magical Kerala IV Tour',
            destination='Munnar & Alleppey',
            category='college_iv',
            duration_days=4,
            duration_nights=3,
            pricing_type='per_person',
            base_price=Decimal('5500.00'),
            price_with_food=Decimal('7200.00'),
            price_without_food=Decimal('5200.00'),
            has_campfire_dj=True,
            has_jeep_safari=True
        )
        self.assertEqual(str(pkg), '4 Days Magical Kerala IV Tour (3N/4D)')
        self.assertTrue(pkg.has_campfire_dj)
        self.assertEqual(pkg.price_with_food, Decimal('7200.00'))

    def test_package_vehicle_tariff_matrix(self):
        """Test PackageVehicleTariff tier pricing matrix."""
        pkg = Package.objects.create(
            name='Ooty Weekend Gateway',
            destination='Ooty',
            duration_days=2,
            duration_nights=1
        )
        tariff = PackageVehicleTariff.objects.create(
            package=pkg,
            vehicle_type=self.vehicle_type,
            seating_tier='7_crysta',
            package_rate=Decimal('18500.00'),
            per_day_rate=Decimal('4500.00'),
            included_km=500,
            extra_km_rate=Decimal('18.00'),
            driver_bata_per_day=Decimal('500.00')
        )
        self.assertIsNotNone(tariff.id)
        self.assertEqual(tariff.package_rate, Decimal('18500.00'))

    def test_package_inventory_batch_and_seat_depletion(self):
        """Test PackageInventory batch departures and seat calculation."""
        pkg = Package.objects.create(
            name='5 Days Ooty-Mysore Tour Batch',
            destination='Ooty & Mysore',
            duration_days=5,
            duration_nights=4
        )
        batch = PackageInventory.objects.create(
            package=pkg,
            departure_date=datetime.date(2026, 12, 20),
            total_seats=52,
            booked_seats=0,
            assigned_vehicle=self.vehicle,
            assigned_driver=self.driver,
            status='open'
        )
        self.assertEqual(batch.available_seats, 52)

        # Simulate bookings filling up seats
        batch.booked_seats = 48
        batch.save()
        self.assertEqual(batch.available_seats, 4)

        # Completely booked out
        batch.booked_seats = 52
        batch.save()
        self.assertEqual(batch.available_seats, 0)
        self.assertEqual(batch.status, 'sold_out')

    def test_boarding_points_and_manifest(self):
        """Test BoardingPoint routing timetable and TourPassengerManifest."""
        pkg = Package.objects.create(name='Devotional Circuit', destination='Madurai - Rameswaram')
        batch = PackageInventory.objects.create(package=pkg, departure_date=datetime.date(2026, 11, 25), total_seats=36)

        stop1 = BoardingPoint.objects.create(
            departure=batch,
            stop_order=1,
            stop_name='Salem New Bus Stand',
            pickup_time=datetime.time(5, 30),
            coordinator_phone='9842511001'
        )
        self.assertIn('Stop #1', str(stop1))

        manifest_entry = TourPassengerManifest.objects.create(
            departure=batch,
            passenger_name='Sundaram K',
            gender='male',
            age=58,
            phone='9842511222',
            seat_number='12A',
            boarding_point=stop1
        )
        self.assertEqual(manifest_entry.seat_number, '12A')
        self.assertEqual(manifest_entry.phone, '9842511222')

    # -------------------------------------------------------------------------
    # 5. Day-Wise Tour Itinerary Builder & Guest Portal
    # -------------------------------------------------------------------------

    def test_trip_itinerary_builder_apis_and_guest_portal(self):
        """Test Trip multi-day itinerary saving, package import, and guest portal access."""
        booking = Booking.objects.create(
            party=self.party,
            guest_name='Ananya Sen',
            guest_phone='9840199887',
            pickup_location='Bangalore Airport',
            destination='Coorg & Wayanad',
            pickup_date=datetime.date(2026, 12, 10),
            pickup_time=datetime.time(9, 0),
            journey_type='outstation',
            vehicle_type=self.vehicle_type,
            status='confirmed'
        )

        trip = Trip.objects.create(
            booking=booking,
            party=self.party,
            guest_name='Ananya Sen',
            start_date=datetime.date(2026, 12, 10),
            end_date=datetime.date(2026, 12, 13),
            status='booked',
            fixed_amount=Decimal('45000.00'),
            notes='Multi-day family getaway'
        )

        # 1. Save Itinerary Days via API
        save_url = reverse('api-trip-itinerary-save', kwargs={'trip_id': trip.id})
        payload = {
            'days': [
                {
                    'day_number': 1,
                    'title': 'Arrival & Drive to Coorg Coffee County',
                    'route_segment': 'Bangalore -> Madikeri',
                    'morning_plan': 'Pickup from airport, breakfast on highway',
                    'sightseeing_spots': 'Namdroling Golden Temple Bylakuppe, Dubare Elephant Camp',
                    'evening_plan': 'Raja Seat sunset view, dinner at resort',
                    'night_stay_location': 'Madikeri, Coorg',
                    'hotel_name': 'Heritage Resort Coorg',
                    'hotel_booking_status': 'confirmed',
                    'meals_included': 'Breakfast, Dinner',
                    'transport_mode': 'Dedicated Innova Crysta AC'
                },
                {
                    'day_number': 2,
                    'title': 'Abbey Falls, Talacauvery & Brahmagiri Hills',
                    'route_segment': 'Madikeri Local Sightseeing',
                    'morning_plan': 'Early morning coffee plantation walk',
                    'sightseeing_spots': 'Abbey Falls, Talacauvery Holy Origin, Bhagamandala Temple',
                    'evening_plan': 'Resort campfire and Kodava traditional dinner',
                    'night_stay_location': 'Madikeri, Coorg',
                    'hotel_name': 'Heritage Resort Coorg',
                    'hotel_booking_status': 'confirmed',
                    'meals_included': 'Breakfast, Lunch, Dinner',
                    'transport_mode': 'Dedicated Innova Crysta AC'
                }
            ]
        }
        res_save = self.client.post(save_url, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(res_save.status_code, 200)
        data_save = res_save.json()
        self.assertEqual(data_save['status'], 'success')

        # 2. Get Itinerary via API
        get_url = reverse('api-trip-itinerary-get', kwargs={'trip_id': trip.id})
        res_get = self.client.get(get_url)
        self.assertEqual(res_get.status_code, 200)
        data_get = res_get.json()
        self.assertEqual(len(data_get['days']), 2)
        self.assertEqual(data_get['days'][0]['title'], 'Arrival & Drive to Coorg Coffee County')

        # 3. Access Guest Tour Companion Portal
        trip.refresh_from_db()
        self.assertIsNotNone(trip.tracking_token)
        portal_url = reverse('guest-tour-itinerary', kwargs={'token': trip.tracking_token})
        res_portal = self.client.get(portal_url)
        self.assertEqual(res_portal.status_code, 200)
        self.assertContains(res_portal, 'Ananya Sen')
        self.assertContains(res_portal, 'Heritage Resort Coorg')
        self.assertContains(res_portal, 'Namdroling Golden Temple')
