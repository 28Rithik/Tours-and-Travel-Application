import datetime
from decimal import Decimal
import json
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.utils import timezone
from django.urls import reverse

from core.models import Client as CoreClient, VehicleType
from crm.models import Inquiry, InquiryFollowUp
from operations.models import Booking, Trip


class CRMKanbanBoardTests(TestCase):
    """
    Automated regression and functional test suite for Phase 6:
    Visual Drag-and-Drop CRM Kanban Board & Lead Follow-Up Hub.
    """

    def setUp(self):
        self.user = User.objects.create_superuser(
            username='admin_tester',
            email='admin@travelerp.com',
            password='password123'
        )
        self.client = Client()
        self.client.force_login(self.user)

        self.party = CoreClient.objects.create(
            name='Acme Corp Travels',
            phone='9840012345',
            email='trips@acmecorp.com'
        )

        self.vehicle_type = VehicleType.objects.create(
            name='Toyota Innova Crysta',
            seating_capacity=7
        )

        self.inquiry = Inquiry.objects.create(
            inquiry_number='INQ-TEST-601',
            party=self.party,
            guest_name='Rajesh Sundaram',
            guest_phone='9842511223',
            guest_email='rajesh@example.com',
            pickup_location='Chennai Central',
            destination='Pondicherry Heritage Tour',
            pickup_date=datetime.date(2026, 10, 15),
            pickup_time=datetime.time(7, 30),
            adult_count=4,
            child_count=1,
            vehicle_type=self.vehicle_type,
            status='new',
            priority='high',
            source='phone',
            estimated_deal_value=Decimal('28500.00'),
            assigned_to=self.user
        )

    def test_kanban_board_view_status_code_and_render(self):
        """Kanban board returns 200 OK and renders the 6 stage columns."""
        response = self.client.get('/crm/kanban/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'crm/kanban_board.html')
        self.assertIn('columns', response.context)
        self.assertIn('total_pipeline_value', response.context)
        self.assertContains(response, 'Rajesh Sundaram')
        self.assertContains(response, 'Pondicherry Heritage Tour')

    def test_kanban_admin_url_alias(self):
        """Kanban board accessible via admin aliases /admin/crm/kanban/ and /admin/kanban/."""
        resp1 = self.client.get('/admin/crm/kanban/')
        self.assertEqual(resp1.status_code, 200)
        resp2 = self.client.get('/admin/kanban/')
        self.assertEqual(resp2.status_code, 200)

    def test_api_inquiry_update_stage(self):
        """Drag-and-drop endpoint updates stage and creates an audit follow-up log."""
        url = reverse('crm:api_inquiry_update_stage', kwargs={'inquiry_id': self.inquiry.id})
        
        # Move from 'new' to 'in_progress'
        payload = {'new_status': 'in_progress', 'kanban_order': 1}
        response = self.client.post(
            url,
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        res_data = response.json()
        self.assertEqual(res_data['status'], 'success')
        self.assertEqual(res_data['new_status'], 'in_progress')

        self.inquiry.refresh_from_db()
        self.assertEqual(self.inquiry.status, 'in_progress')

        # Check follow-up transition log
        follow_up = InquiryFollowUp.objects.filter(inquiry=self.inquiry).latest('id')
        self.assertIn('Under Review', follow_up.notes)

    def test_api_inquiry_quick_followup(self):
        """Quick follow-up logs interaction and updates last_followup_at and next_followup_at."""
        url = reverse('crm:api_inquiry_quick_followup', kwargs={'inquiry_id': self.inquiry.id})
        payload = {
            'interaction_type': 'phone',
            'notes': 'Spoke with guest. Agreed on 3-day itinerary, awaiting budget approval.',
            'next_action': 'Send revised cost sheet with French Quarter hotel included.',
            'next_followup_days': 2
        }
        response = self.client.post(
            url,
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')

        self.inquiry.refresh_from_db()
        self.assertIsNotNone(self.inquiry.last_followup_at)
        self.assertIsNotNone(self.inquiry.next_followup_at)

        follow_up = InquiryFollowUp.objects.filter(inquiry=self.inquiry, interaction_type='phone').first()
        self.assertIsNotNone(follow_up)
        self.assertIn('French Quarter hotel', follow_up.next_action)

    def test_api_inquiry_convert_to_booking_and_trip(self):
        """1-click conversion creates Booking & Trip, marks Inquiry as 'won', and links them."""
        url = reverse('crm:api_inquiry_convert_to_booking', kwargs={'inquiry_id': self.inquiry.id})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertIn('trip_id', data)
        self.assertIn('booking_id', data)

        self.inquiry.refresh_from_db()
        self.assertEqual(self.inquiry.status, 'won')
        self.assertIsNotNone(self.inquiry.converted_booking)
        self.assertIsNotNone(self.inquiry.converted_trip)

        # Verify created booking
        booking = self.inquiry.converted_booking
        self.assertEqual(booking.guest_name, 'Rajesh Sundaram')
        self.assertEqual(booking.status, 'confirmed')
        self.assertEqual(booking.quoted_price, Decimal('28500.00'))

        # Verify created trip
        trip = self.inquiry.converted_trip
        self.assertEqual(trip.booking, booking)
        self.assertEqual(trip.status, 'booked')
        self.assertEqual(trip.fixed_amount, Decimal('28500.00'))
        self.assertIn('Pondicherry Heritage Tour', trip.notes)

    def test_api_inquiry_dispatch_whatsapp(self):
        """Generates tailored WhatsApp quotation link and logs follow-up interaction."""
        url = reverse('crm:api_inquiry_dispatch_whatsapp', kwargs={'inquiry_id': self.inquiry.id})
        payload = {
            'custom_note': 'Special weekend package includes beachside resort stay.'
        }
        response = self.client.post(
            url,
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertIn('wa.me/919842511223', data['wa_url'])
        self.assertIn('Pondicherry Heritage Tour', data['message_text'])
        self.assertIn('Special weekend package', data['message_text'])

        self.inquiry.refresh_from_db()
        self.assertIsNotNone(self.inquiry.last_followup_at)

    def test_api_crm_kanban_data(self):
        """api_crm_kanban_data returns JSON state with all pipeline stages."""
        url = reverse('crm:api_crm_kanban_data')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertIn('board', data)
        board = data['board']
        self.assertIn('new', board)
        self.assertIn('in_progress', board)
        self.assertIn('quoted', board)
        self.assertIn('negotiating', board)
        self.assertIn('won', board)
        self.assertIn('lost', board)
        self.assertGreaterEqual(board['new']['count'], 1)
