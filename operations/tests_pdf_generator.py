from datetime import date, timedelta
from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.urls import reverse

from core.models import Vehicle, Driver, VehicleType, Client as PartyClient
from operations.models import Trip, Booking
from finance.models import CorporateGSTInvoice
from operations.pdf_generator import (
    render_trip_sheet_pdf,
    render_tax_invoice_pdf,
    render_booking_voucher_pdf,
    amount_in_words_inr
)

User = get_user_model()


class PDFGeneratorTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser('pdf_admin', 'pdf@example.com', 'pass123')
        self.client = Client()
        self.client.force_login(self.user)

        self.party = PartyClient.objects.create(
            name="Sathyam Technologies Private Limited",
            phone="9876543210",
            party_type="corporate",
            address="Tech Park, Saravanampatti, Coimbatore - 641035",
            gstin="33AAECS5432F1ZA",
            state_code="33"
        )

        self.vtype = VehicleType.objects.create(name="Prime SUV", seating_capacity=7)
        today = timezone.localdate()

        self.vehicle = Vehicle.objects.create(
            registration_number="TN 38 BX 7788",
            brand="Toyota",
            model="Innova Hycross",
            vehicle_type=self.vtype,
            seating_capacity=7,
            ownership_type="owned",
            status="available",
            current_km=14200,
            insurance_expiry=today + timedelta(days=180),
            fc_expiry=today + timedelta(days=250),
            pollution_expiry=today + timedelta(days=60),
        )

        self.driver = Driver.objects.create(
            name="R. Senthil Kumar",
            phone="9887766554",
            license_number="TN38-2016-8877",
            badge_number="BDG-CBE-102",
            license_validity_tr=today + timedelta(days=400),
            status="active",
            hill_station_experience=True
        )

        self.booking = Booking.objects.create(
            party=self.party,
            guest_name="Dr. Vikram Sarabhai",
            guest_phone="9876543210",
            pickup_location="Coimbatore Junction",
            destination="Munnar Tea Country Resort",
            pickup_date=today + timedelta(days=2),
            pickup_time="07:30:00",
            drop_date=today + timedelta(days=4),
            journey_type="outstation",
            vehicle_type=self.vtype,
            pax_count=4,
            quoted_price=Decimal("18500.00"),
            status="confirmed"
        )

        self.trip = Trip.objects.create(
            booking=self.booking,
            party=self.party,
            guest_name=self.booking.guest_name,
            start_date=self.booking.pickup_date,
            end_date=self.booking.drop_date,
            vehicle=self.vehicle,
            driver=self.driver,
            opening_km=14200,
            closing_km=14850,
            days_count=3,
            fixed_amount=Decimal("18500.00"),
            driver_bata=Decimal("1500.00"),
            status="assigned"
        )

        # Corporate GST Invoice
        self.invoice = CorporateGSTInvoice.objects.create(
            invoice_number="INV-2026-0042",
            invoice_date=today,
            party=self.party,
            trip=self.trip,
            supplier_legal_name="Sivagayathiri Tours and Travels",
            supplier_gstin="33AABCS1234F1Z8",
            supplier_state_code="33",
            recipient_legal_name=self.party.name,
            recipient_gstin=self.party.gstin,
            recipient_state_code="33",
            taxable_value=Decimal("18500.00"),
            cgst_amount=Decimal("462.50"),
            sgst_amount=Decimal("462.50"),
            igst_amount=Decimal("0.00"),
            total_tax=Decimal("925.00"),
            total_invoice_value=Decimal("19425.00"),
            payment_status="unpaid"
        )

    def test_amount_in_words_inr_formatting(self):
        """Test Indian Lakhs/Crores conversion."""
        self.assertEqual(amount_in_words_inr(0), "Rupees Zero Only")
        self.assertEqual(amount_in_words_inr(500), "Rupees Five Hundred Only")
        self.assertEqual(amount_in_words_inr(18500), "Rupees Eighteen Thousand Five Hundred Only")
        self.assertEqual(amount_in_words_inr(19425), "Rupees Nineteen Thousand Four Hundred Twenty Five Only")
        self.assertEqual(amount_in_words_inr(1250000), "Rupees Twelve Lakh Fifty Thousand Only")

    def test_render_trip_sheet_pdf_bytes(self):
        """Verify render_trip_sheet_pdf returns valid PDF binary starting with %PDF-."""
        pdf_bytes = render_trip_sheet_pdf(self.trip)
        self.assertIsInstance(pdf_bytes, bytes)
        self.assertGreater(len(pdf_bytes), 1000)
        self.assertTrue(pdf_bytes.startswith(b'%PDF-'))

    def test_render_tax_invoice_pdf_from_trip(self):
        """Verify render_tax_invoice_pdf directly from Trip object."""
        pdf_bytes = render_tax_invoice_pdf(self.trip)
        self.assertIsInstance(pdf_bytes, bytes)
        self.assertGreater(len(pdf_bytes), 1000)
        self.assertTrue(pdf_bytes.startswith(b'%PDF-'))

    def test_render_tax_invoice_pdf_from_invoice(self):
        """Verify render_tax_invoice_pdf directly from CorporateGSTInvoice object."""
        pdf_bytes = render_tax_invoice_pdf(self.invoice)
        self.assertIsInstance(pdf_bytes, bytes)
        self.assertGreater(len(pdf_bytes), 1000)
        self.assertTrue(pdf_bytes.startswith(b'%PDF-'))

    def test_render_booking_voucher_pdf_bytes(self):
        """Verify render_booking_voucher_pdf returns valid PDF binary starting with %PDF-."""
        pdf_bytes = render_booking_voucher_pdf(self.booking)
        self.assertIsInstance(pdf_bytes, bytes)
        self.assertGreater(len(pdf_bytes), 1000)
        self.assertTrue(pdf_bytes.startswith(b'%PDF-'))

    def test_trip_sheet_pdf_http_endpoint(self):
        """Verify GET /trips/<id>/pdf/trip-sheet/ returns HTTP 200 with application/pdf MIME type."""
        url = reverse('trip-sheet-pdf', args=[self.trip.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertIn('TripSheet-', response['Content-Disposition'])
        self.assertTrue(response.content.startswith(b'%PDF-'))

    def test_trip_invoice_pdf_http_endpoint(self):
        """Verify GET /trips/<id>/pdf/invoice/ returns HTTP 200 with application/pdf MIME type."""
        url = reverse('trip-invoice-pdf', args=[self.trip.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertIn('TaxInvoice-', response['Content-Disposition'])
        self.assertTrue(response.content.startswith(b'%PDF-'))

    def test_booking_voucher_pdf_http_endpoint(self):
        """Verify GET /bookings/<id>/pdf/voucher/ returns HTTP 200 with application/pdf MIME type."""
        url = reverse('booking-voucher-pdf', args=[self.booking.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertIn('BookingVoucher-', response['Content-Disposition'])
        self.assertTrue(response.content.startswith(b'%PDF-'))

    def test_corporate_invoice_pdf_http_endpoint(self):
        """Verify GET /finance/invoice/<id>/pdf/ returns HTTP 200 with application/pdf MIME type."""
        url = reverse('corporate-invoice-pdf', args=[self.invoice.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertIn(self.invoice.invoice_number, response['Content-Disposition'])
        self.assertTrue(response.content.startswith(b'%PDF-'))
