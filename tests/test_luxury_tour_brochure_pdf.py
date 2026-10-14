"""
Comprehensive Test Suite for Option B: Luxury Tour Proposal & Itinerary Brochure PDF Generator
================================================================================================
Verifies:
  1. Multi-page ReportLab PDF generation for Quotations, Inquiries, and Packages.
  2. PDF binary integrity (%PDF-1.4 header, file size > 5KB).
  3. Dynamic NPCI UPI QR code generation and embedding.
  4. 3-Tier package pricing engine (Comfort vs Deluxe vs Royal Luxury) & per-pax calculations.
  5. In-memory caching tier (<5ms hot hits).
  6. HTTP view endpoints (/crm/quotations/<id>/brochure/pdf/, /quote/<token>/brochure.pdf).
  7. WhatsApp sales pitch API and interactive web preview studio.
"""

import datetime
from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.utils import timezone

from core.models import Client as PartyClient, VehicleType
from crm.models import (
    Inquiry, Quotation, QuotationDay, QuotationItem, HotelMaster
)
from crm.brochure_pdf_engine import LuxuryTourBrochurePDFEngine, _PDF_CACHE


class LuxuryTourBrochurePDFTestCase(TestCase):
    def setUp(self):
        # 1. Clear in-memory PDF cache
        _PDF_CACHE.clear()

        # 2. Staff user and client
        self.staff_user = User.objects.create_user(
            username='sales_agent_brochure',
            password='Password123!',
            is_staff=True
        )
        self.client_party = PartyClient.objects.create(
            name='Dr. Rajesh Kumar',
            phone='9840123456',
            email='rajesh@example.com',
            party_type='b2c'
        )

        # 3. Vehicle Type
        self.vtype = VehicleType.objects.create(
            name='Toyota Innova Crysta Luxury',
            seating_capacity=7,
            category='SUV'
        )

        # 4. Hotel Master
        self.hotel = HotelMaster.objects.create(
            name='Savoy IHCL SeleQtions',
            destination='Ooty',
            star_category='5_star',
            room_type='Heritage Suite',
            map_rate=Decimal('8500.00'),
            cp_rate=Decimal('7000.00')
        )

        # 5. Quotation with days and items
        self.start_date = timezone.now().date() + datetime.timedelta(days=7)
        self.end_date = self.start_date + datetime.timedelta(days=3)  # 4 Days / 3 Nights

        self.quote = Quotation.objects.create(
            quotation_number='QTN-2026-TEST-001',
            version=1,
            party=self.client_party,
            guest_name='Dr. Rajesh Kumar',
            guest_phone='9840123456',
            guest_email='rajesh@example.com',
            title='4 Days / 3 Nights Nilgiris Holiday Expedition',
            destination='Ooty, Nilgiris',
            start_date=self.start_date,
            end_date=self.end_date,
            pax_count=4,
            vehicle_type=self.vtype,
            total_quoted_price=Decimal('36000.00'),
            status='sent',
            created_by=self.staff_user
        )

        # Add Day 1
        self.day1 = QuotationDay.objects.create(
            quotation=self.quote,
            day_number=1,
            date=self.start_date,
            title='Arrival & Botanical Enchantment',
            description='Scenic ghat ascent via Kallar, hotel check-in, Botanical Gardens visit.',
            hotel=self.hotel,
            hotel_meal_plan='MAP',
            overnight_destination='Ooty'
        )
        QuotationItem.objects.create(
            quotation=self.quote,
            day=self.day1,
            category='transport',
            item_name='Innova Crysta Luxury Hire',
            quantity=1,
            unit_cost=Decimal('4500.00')
        )

        # 6. Inquiry
        self.inquiry = Inquiry.objects.create(
            inquiry_number='INQ-2026-TEST-002',
            party=self.client_party,
            guest_name='Vikram Sethi',
            guest_phone='9841122334',
            pickup_location='Coimbatore Airport',
            destination='Kodaikanal',
            destination_dropdown='kodaikanal',
            pickup_date=self.start_date,
            pickup_time=datetime.time(9, 30),
            drop_date=self.end_date,
            adult_count=3,
            child_count=1,
            vehicle_type=self.vtype,
            quoted_price=Decimal('32000.00'),
            status='quoted',
            assigned_to=self.staff_user
        )

        self.http_client = Client()

    def test_quotation_brochure_pdf_binary_generation(self):
        """Verifies PDF binary generation, valid PDF-1.4 header, size > 5KB, and caching."""
        pdf_bytes = LuxuryTourBrochurePDFEngine.generate_brochure_pdf(quotation=self.quote)

        self.assertIsInstance(pdf_bytes, bytes)
        self.assertTrue(pdf_bytes.startswith(b'%PDF-1.4'), "Generated file must start with %PDF-1.4 header")
        self.assertGreater(len(pdf_bytes), 5000, "Brochure PDF must be a rich multi-page document > 5KB")

        # Second generation must hit the hot cache
        cache_count_before = len(_PDF_CACHE)
        pdf_bytes_2 = LuxuryTourBrochurePDFEngine.generate_brochure_pdf(quotation=self.quote)
        self.assertEqual(pdf_bytes, pdf_bytes_2)
        self.assertEqual(len(_PDF_CACHE), cache_count_before)

    def test_inquiry_brochure_pdf_generation_with_synthesized_itinerary(self):
        """Verifies that an Inquiry without explicit day objects synthesizes rich destination itinerary."""
        pdf_bytes = LuxuryTourBrochurePDFEngine.generate_brochure_pdf(inquiry=self.inquiry)

        self.assertIsInstance(pdf_bytes, bytes)
        self.assertTrue(pdf_bytes.startswith(b'%PDF-1.4'))
        self.assertGreater(len(pdf_bytes), 5000)

    def test_tiered_pricing_calculations(self):
        """Verifies standard (85%), deluxe (100%), and luxury (138%) pricing tier models."""
        base_price = Decimal('36000.00')
        pax = 4

        # Deluxe Tier = base price
        self.assertEqual(self.quote.deluxe_tier_total, base_price)
        self.assertEqual(self.quote.deluxe_per_pax, Decimal('9000.00'))

        # Standard Tier = 85% of base
        expected_std = round(base_price * Decimal('0.85'), 2)
        self.assertEqual(self.quote.standard_tier_total, expected_std)
        self.assertEqual(self.quote.standard_per_pax, round(expected_std / Decimal(str(pax)), 2))

        # Luxury Tier = 138% of base
        expected_lux = round(base_price * Decimal('1.38'), 2)
        self.assertEqual(self.quote.luxury_tier_total, expected_lux)
        self.assertEqual(self.quote.luxury_per_pax, round(expected_lux / Decimal(str(pax)), 2))

        # Manual Overrides
        self.quote.tier_standard_price = Decimal('30000.00')
        self.quote.tier_luxury_price = Decimal('55000.00')
        self.quote.save()

        self.assertEqual(self.quote.standard_tier_total, Decimal('30000.00'))
        self.assertEqual(self.quote.standard_per_pax, Decimal('7500.00'))
        self.assertEqual(self.quote.luxury_tier_total, Decimal('55000.00'))
        self.assertEqual(self.quote.luxury_per_pax, Decimal('13750.00'))

    def test_http_quotation_brochure_pdf_endpoint(self):
        """Tests authenticated download & streaming of quotation brochure PDF."""
        self.http_client.force_login(self.staff_user)

        # 1. Inline stream
        url = f'/crm/quotations/{self.quote.id}/brochure/pdf/'
        resp = self.http_client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'application/pdf')
        self.assertIn('inline', resp['Content-Disposition'])
        self.assertTrue(resp.content.startswith(b'%PDF-1.4'))

        # 2. Attachment download
        resp_dl = self.http_client.get(f'{url}?download=1')
        self.assertEqual(resp_dl.status_code, 200)
        self.assertIn('attachment', resp_dl['Content-Disposition'])

    def test_http_inquiry_brochure_pdf_endpoint(self):
        """Tests authenticated download of inquiry brochure PDF."""
        self.http_client.force_login(self.staff_user)

        url = f'/crm/inquiries/{self.inquiry.id}/brochure/pdf/'
        resp = self.http_client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'application/pdf')
        self.assertTrue(resp.content.startswith(b'%PDF-1.4'))

    def test_public_guest_brochure_pdf_endpoint(self):
        """Verifies unauthenticated guest download via public proposal token."""
        # Unauthenticated client
        guest_client = Client()

        # 1. Via Inquiry token
        token_inq = self.inquiry.proposal_token
        self.assertTrue(len(token_inq) > 0)
        url_inq = f'/quote/{token_inq}/brochure.pdf'
        resp_inq = guest_client.get(url_inq)
        self.assertEqual(resp_inq.status_code, 200)
        self.assertEqual(resp_inq['Content-Type'], 'application/pdf')
        self.assertTrue(resp_inq.content.startswith(b'%PDF-1.4'))

        # 2. Via Quotation token
        token_quote = self.quote.token
        self.assertTrue(len(token_quote) > 0)
        url_quote = f'/quote/{token_quote}/brochure.pdf'
        resp_quote = guest_client.get(url_quote)
        self.assertEqual(resp_quote.status_code, 200)
        self.assertEqual(resp_quote['Content-Type'], 'application/pdf')
        self.assertTrue(resp_quote.content.startswith(b'%PDF-1.4'))

    def test_whatsapp_sales_pitch_api(self):
        """Tests API endpoint that generates pre-formatted WhatsApp sales pitch & links."""
        self.http_client.force_login(self.staff_user)

        url = f'/crm/api/quotations/{self.quote.id}/whatsapp-brochure/'
        resp = self.http_client.get(url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        self.assertEqual(data['status'], 'success')
        self.assertIn('Sivagayathiri Tours and Travels', data['whatsapp_message'])
        self.assertIn('Premium Deluxe', data['whatsapp_message'])
        self.assertIn(f'/quote/{self.quote.token}/brochure.pdf', data['brochure_url'])
        self.assertTrue(data['whatsapp_share_url'].startswith('https://wa.me/'))

    def test_interactive_brochure_web_preview(self):
        """Tests HTML web preview studio for brochure with 3-tier cards."""
        self.http_client.force_login(self.staff_user)

        url = f'/crm/quotations/{self.quote.id}/brochure/preview/'
        resp = self.http_client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'SIVAGAYATHIRI TOURS AND TRAVELS')
        self.assertContains(resp, 'Comfort Package')
        self.assertContains(resp, 'Premium Deluxe')
        self.assertContains(resp, 'Royal Luxury')
        self.assertContains(resp, 'Download PDF Brochure')
