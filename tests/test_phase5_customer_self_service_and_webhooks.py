import json
import hmac
import hashlib
from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase, Client as HttpClient
from django.utils import timezone
from django.contrib.auth.models import User

from core.models import Client as CoreClient, VehicleType, Vehicle, Driver
from operations.models import Booking, Trip
from finance.models import Payment, Account, JournalEntry
from payments_gateway.models import PaymentGatewayConfig, GatewayTransaction, PaymentWebhookEvent
from customer_portal.models import CustomerAccount, CustomerOTP


class Phase5CustomerSelfServiceAndWebhooksTestCase(TestCase):
    """
    Automated test suite for Phase 5 / Phase 11:
    1. Mobile Phone Passwordless OTP Generation & Throttling
    2. OTP Verification & Instant Guest Account Provisioning
    3. Customer Self-Service Dashboard & Financial Balance Calculations
    4. Live Telematics Radar View & AIS-140 GPS Telemetry
    5. Official Rule 46 GST Tax Invoice Generation & SAC Code Reconciliation
    6. Razorpay HMAC-SHA256 Webhook Ingestion, Auto-Confirmation & Double-Entry GL Posting
    """

    def setUp(self):
        self.client = HttpClient()

        # Provision Vehicle Type & Vehicle
        self.vtype = VehicleType.objects.create(
            name="Innova Crysta Luxury",
            seating_capacity=7,
            default_km_rate=Decimal('22.00'),
            default_day_rate=Decimal('3500.00')
        )

        self.vehicle = Vehicle.objects.create(
            registration_number="TN 38 BX 8899",
            vehicle_type=self.vtype,
            brand="Toyota",
            model="Innova Crysta",
            current_km=64280,
            status="available"
        )


        # Provision Driver
        self.driver = Driver.objects.create(
            name="Murugan K",
            phone="9842533888",
            license_number="TN38-2015-004812",
            status="active"
        )

        # Provision Customer Party / Client
        self.cust_client = CoreClient.objects.create(
            name="Kavitha Senthil",
            phone="9842533777",
            email="kavitha.s@example.com",
            party_type="individual",
            is_active=True
        )


        # Provision Customer User & Profile
        self.user = User.objects.create_user(
            username="cust_9842533777",
            first_name="Kavitha",
            password="testpassword123"
        )
        self.account = CustomerAccount.objects.create(
            user=self.user,
            client_record=self.cust_client,
            is_email_verified=True
        )

        # Provision Booking
        self.booking = Booking.objects.create(
            booking_number="BK-2026-TEST01",
            party=self.cust_client,
            guest_name="Kavitha Senthil",
            guest_phone="9842533777",
            destination="Ooty & Coonoor Hills",
            pickup_date=date(2026, 10, 15),
            pickup_time="06:00:00",
            drop_date=date(2026, 10, 18),
            pax_count=4,
            quoted_price=Decimal('24500.00'),
            status='draft'
        )


        # Provision Trip linked to Booking
        self.trip = Trip.objects.create(
            booking=self.booking,
            party=self.cust_client,
            vehicle=self.vehicle,
            driver=self.driver,
            start_date=date(2026, 10, 15),
            end_date=date(2026, 10, 18),
            status="started",
            billing_model="fixed",
            fixed_amount=Decimal('24500.00')
        )


    def test_01_request_otp_api_validation_and_generation(self):
        """
        Verify POST /customer-portal/api/request-otp/ generates a 6-digit code,
        persists to DB with 10-minute expiry, and handles phone validations.
        """
        # 1. Invalid phone number (too short)
        res_invalid = self.client.post(
            '/customer-portal/api/request-otp/',
            json.dumps({'phone': '12345'}),
            content_type='application/json'
        )
        self.assertEqual(res_invalid.status_code, 400)
        self.assertIn('valid 10-digit', res_invalid.json().get('message', ''))

        # 2. Valid 10-digit phone
        res_valid = self.client.post(
            '/customer-portal/api/request-otp/',
            json.dumps({'phone': '9842533777'}),
            content_type='application/json'
        )
        self.assertEqual(res_valid.status_code, 200)
        data = res_valid.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['phone'], '9842533777')
        self.assertTrue(len(data['dev_otp']) == 6)

        # 3. Check DB persistence
        otp_obj = CustomerOTP.objects.filter(phone='9842533777', is_verified=False).first()
        self.assertIsNotNone(otp_obj)
        self.assertEqual(otp_obj.otp_code, data['dev_otp'])
        self.assertTrue(otp_obj.is_valid())

        # 4. Successive request invalidates prior code
        res_second = self.client.post(
            '/customer-portal/api/request-otp/',
            json.dumps({'phone': '9842533777'}),
            content_type='application/json'
        )
        self.assertEqual(res_second.status_code, 200)
        otp_obj.refresh_from_db()
        self.assertTrue(otp_obj.is_verified)  # marked invalid by next request

    def test_02_verify_otp_api_and_instant_account_provisioning(self):
        """
        Verify POST /customer-portal/api/verify-otp/ authenticates user,
        auto-provisions Client and User if new, and logs in session.
        """
        phone = "9842599000"
        # Seed a provisional booking with this guest phone
        temp_party = CoreClient.objects.create(name="Initial Party", phone="9000000000", party_type="individual")
        Booking.objects.create(
            booking_number="BK-GUEST-99000",
            party=temp_party,
            guest_name="Ravi Kumar",
            guest_phone=phone,
            destination="Kodaikanal Lake",
            pickup_date=date(2026, 11, 1),
            pickup_time="07:30:00",
            quoted_price=Decimal('15000.00'),
            status='draft'
        )



        # Generate OTP
        res_req = self.client.post(
            '/customer-portal/api/request-otp/',
            json.dumps({'phone': phone}),
            content_type='application/json'
        )
        dev_otp = res_req.json()['dev_otp']

        # 1. Invalid OTP verification fails
        res_fail = self.client.post(
            '/customer-portal/api/verify-otp/',
            json.dumps({'phone': phone, 'otp': '000000'}),
            content_type='application/json'
        )
        self.assertEqual(res_fail.status_code, 400)

        # 2. Valid OTP verification succeeds
        res_success = self.client.post(
            '/customer-portal/api/verify-otp/',
            json.dumps({'phone': phone, 'otp': dev_otp}),
            content_type='application/json'
        )
        self.assertEqual(res_success.status_code, 200)
        data = res_success.json()
        self.assertEqual(data['status'], 'success')
        self.assertIn('/customer-portal/bookings/', data['redirect_url'])

        # 3. Verify auto-provisioning
        prov_client = CoreClient.objects.filter(phone=phone).first()
        self.assertIsNotNone(prov_client)
        self.assertEqual(prov_client.name, "Ravi Kumar")

        prov_user = User.objects.filter(username=f"cust_{phone}").first()
        self.assertIsNotNone(prov_user)

        prov_account = CustomerAccount.objects.filter(client_record=prov_client).first()
        self.assertIsNotNone(prov_account)
        self.assertEqual(prov_account.user, prov_user)

        # 4. Verify past unassigned bookings were re-linked to prov_client
        linked_booking = Booking.objects.get(booking_number="BK-GUEST-99000")
        self.assertEqual(linked_booking.party, prov_client)

    def test_03_customer_bookings_dashboard_and_balance_calculations(self):
        """
        Verify GET /customer-portal/bookings/ renders customer dashboard,
        accurately calculates total_paid and balance_due, and displays KPIs.
        """
        # Create an advance payment for self.booking
        Payment.objects.create(
            party=self.cust_client,
            booking=self.booking,
            date=date.today(),
            amount=Decimal('10000.00'),
            payment_type='customer_receipt',
            payment_mode='upi',
            collected_by='company',
            reference_number='UPI-TXN-10000'
        )

        self.client.force_login(self.user)
        response = self.client.get('/customer-portal/bookings/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Kavitha")
        self.assertContains(response, "BK-2026-TEST01")
        self.assertContains(response, "Ooty &amp; Coonoor Hills")
        self.assertContains(response, "TN 38 BX 8899")


        # Verify context calculation
        bookings = response.context['bookings']
        self.assertEqual(len(bookings), 1)
        b = bookings[0]
        self.assertEqual(b.total_paid, Decimal('10000.00'))
        self.assertEqual(b.balance_due, Decimal('14500.00'))  # 24,500 - 10,000
        self.assertEqual(response.context['total_spent'], Decimal('10000.00'))
        self.assertEqual(response.context['total_balance_due'], Decimal('14500.00'))

    def test_04_live_telematics_radar_tracking(self):
        """
        Verify GET /customer-portal/booking/<id>/live/ renders telematics cockpit,
        Leaflet map container, assigned vehicle & driver details, and speed gauges.
        """
        self.client.force_login(self.user)
        response = self.client.get(f'/customer-portal/booking/{self.booking.id}/live/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "radarMap")
        self.assertContains(response, "TN 38 BX 8899")
        self.assertContains(response, "Murugan K")
        self.assertContains(response, "EMERGENCY SOS")
        self.assertContains(response, "Live Speedometer")

        # Verify access control: unauthenticated user without phone is redirected
        anon_client = HttpClient()
        res_anon = anon_client.get(f'/customer-portal/booking/{self.booking.id}/live/')
        self.assertEqual(res_anon.status_code, 302)

        # Phone-based token access (e.g. from SMS tracking link)
        res_phone_link = anon_client.get(f'/customer-portal/booking/{self.booking.id}/live/?phone=9842533777')
        self.assertEqual(res_phone_link.status_code, 200)

    def test_05_official_gst_tax_invoice_generation(self):
        """
        Verify GET /customer-portal/booking/<id>/invoice/ renders Rule 46 GST Tax Invoice,
        accurate SAC code 9964, CGST/SGST 2.5% breakdown, and corporate GSTIN.
        """
        self.client.force_login(self.user)
        response = self.client.get(f'/customer-portal/booking/{self.booking.id}/invoice/')
        self.assertEqual(response.status_code, 200)

        # Statutory Invoice Checks
        self.assertContains(response, "TAX INVOICE")
        self.assertContains(response, "33AAAAA0000A1Z5")  # Sivagayathiri GSTIN
        self.assertContains(response, "9964")             # SAC code for passenger road transport
        self.assertContains(response, "CGST (2.50%)")
        self.assertContains(response, "SGST (2.50%)")
        self.assertContains(response, "Kavitha Senthil")
        self.assertContains(response, f"INV-2026-{self.booking.id:05d}")

    def test_06_razorpay_hmac_webhook_booking_confirmation_and_gl_entry(self):
        """
        Verify POST /payments/webhook/razorpay/ with valid HMAC-SHA256 signature
        auto-confirms Booking status, generates Payment receipt, records GatewayTransaction,
        and posts balanced Double-Entry General Ledger journal entries.
        """
        # Configure Razorpay Gateway with webhook secret
        rzp_config, _ = PaymentGatewayConfig.objects.get_or_create(
            provider='razorpay',
            defaults={
                'name': 'Razorpay Test Gateway',
                'is_active': True,
                'api_key': 'rzp_test_key123',
                'api_secret': 'rzp_test_secret123',
                'webhook_secret': 'rzp_sec_travels_2026',
                'gateway_fee_percent': Decimal('1.75'),
                'gst_on_fee_percent': Decimal('18.00'),

            }
        )
        rzp_config.webhook_secret = 'rzp_sec_travels_2026'
        rzp_config.is_active = True
        rzp_config.save()

        # Target Booking to confirm
        target_booking = Booking.objects.create(
            booking_number="BK-RZP-CONFIRM-99",
            party=self.cust_client,
            guest_name="Kavitha Senthil",
            guest_phone="9842533777",
            destination="Kodaikanal Weekend",
            pickup_date=date(2026, 11, 20),
            pickup_time="08:00:00",
            quoted_price=Decimal('18500.00'),
            status='draft'
        )


        # Razorpay payload for payment.captured
        event_id = "evt_rzp_test_998877"
        payload_dict = {
            "entity": "event",
            "account_id": "acc_test123",
            "event": "payment.captured",
            "id": event_id,
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_TEST_99887766",
                        "amount": 1850000, # paise = ₹18,500.00
                        "currency": "INR",
                        "status": "captured",
                        "order_id": "order_TEST_443322",
                        "method": "card",
                        "fee": 32375,      # paise = ₹323.75
                        "tax": 5827,       # paise = ₹58.27
                        "description": f"Settlement for {target_booking.booking_number}",
                        "notes": {
                            "reference_id": target_booking.booking_number,
                            "booking_id": str(target_booking.id)
                        }
                    }
                }
            }
        }
        body_bytes = json.dumps(payload_dict).encode('utf-8')

        # Generate HMAC-SHA256 signature
        signature = hmac.new(
            b'rzp_sec_travels_2026',
            body_bytes,
            hashlib.sha256
        ).hexdigest()

        # Send Webhook POST request
        response = self.client.post(
            '/payments/webhook/razorpay/',
            body_bytes,
            content_type='application/json',
            HTTP_X_RAZORPAY_SIGNATURE=signature
        )

        self.assertEqual(response.status_code, 200)
        res_data = response.json()
        self.assertEqual(res_data['status'], 'success')
        self.assertEqual(res_data['booking_number'], target_booking.booking_number)
        self.assertEqual(res_data['gross_amount'], 18500.00)

        # 1. Verify Booking was auto-confirmed
        target_booking.refresh_from_db()
        self.assertEqual(target_booking.status, 'confirmed')

        # 2. Verify Payment record was generated
        pmt = Payment.objects.filter(reference_number="pay_TEST_99887766").first()
        self.assertIsNotNone(pmt)
        self.assertEqual(pmt.booking, target_booking)
        self.assertEqual(pmt.amount, Decimal('18500.00'))

        # 3. Verify GatewayTransaction recorded
        txn = GatewayTransaction.objects.filter(gateway_payment_id="pay_TEST_99887766").first()
        self.assertIsNotNone(txn)
        self.assertEqual(txn.status, 'captured')
        self.assertEqual(txn.gross_amount, Decimal('18500.00'))

        # 4. Verify Double-Entry General Ledger journal entry created and balanced
        je_number = res_data.get('journal_entry')
        self.assertIsNotNone(je_number)
        je = JournalEntry.objects.get(entry_number=je_number)
        self.assertTrue(je.is_posted)
        self.assertTrue(je.is_balanced)
