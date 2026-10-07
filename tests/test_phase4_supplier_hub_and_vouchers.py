import json
from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.utils import timezone

from core.models import Party, Vehicle, VehicleType, Driver
from operations.models import Booking, Trip, TripHotel
from packages.models import Package
from suppliers.models import (
    OutsourcedTripSettlement,
    HotelConfirmationVoucher,
    HotelVoucherGuest
)
from suppliers.settlement_engine import (
    determine_tds_rate,
    calculate_and_create_settlement,
    approve_and_post_settlement_ledger,
    generate_settlement_number
)
from suppliers.voucher_service import (
    create_hotel_voucher,
    generate_hotel_whatsapp_link,
    generate_voucher_number
)
from marketing.models import PromotionCampaign, Coupon
from marketing.campaign_engine import (
    get_audience_recipients,
    generate_campaign_dispatches
)
from finance.models import SupplierTripCost


class Phase4SupplierHubAndVouchersTestCase(TestCase):
    """
    Comprehensive test suite for Phase 10 (Part 4):
    1. Outsourced fleet settlements & Sec 194C TDS calculation engine.
    2. General Ledger approval & SupplierTripCost synchronization.
    3. Hotel confirmation vouchers, rooming manifests, and WhatsApp dispatch.
    4. Driver duty slip & settlement voucher printing.
    5. Marketing promotional campaign broadcast studio.
    """

    def setUp(self):
        # 1. Staff User
        self.staff_user = User.objects.create_user(
            username='ops_manager',
            password='Password@123',
            is_staff=True,
            is_superuser=True
        )
        self.client = Client()
        self.client.force_login(self.staff_user)

        # 2. Master Data: Customer & Supplier Parties
        self.customer = Party.objects.create(
            name='Cognizant Technologies Ltd',
            party_type='corporate',
            phone='9842299887',
            email='facilities@cognizant.com',
            address='CHIL SEZ IT Park, Saravanampatti, Coimbatore',
            gstin='33AAACC1234F1Z1'
        )

        self.supplier = Party.objects.create(
            name='Kovai Royal Cabs & Travels',
            party_type='supplier',
            phone='9842211223',
            email='ops@kovairoyalcabs.com',
            address='Gandhipuram, Coimbatore',
            gstin='33ABCDE1234P1Z5'  # 4th char 'P' -> Individual
        )

        self.corporate_supplier = Party.objects.create(
            name='Sri Krishna Transport Pvt Ltd',
            party_type='supplier',
            phone='9443212345',
            email='info@srikrishnatransport.com',
            address='Peelamedu, Coimbatore',
            gstin='33AAACC9988C1Z8'  # 4th char 'C' -> Company
        )

        # 3. Vehicle Type & Outsourced Vehicles
        self.vtype = VehicleType.objects.create(
            name='Force Urbania 17S',
            category='mini_bus',
            default_day_rate=Decimal('6500.00'),
            default_km_rate=Decimal('22.00'),
            driver_bata=Decimal('600.00')
        )

        self.vehicle = Vehicle.objects.create(
            registration_number='TN38BZ9988',
            vehicle_type=self.vtype,
            ownership_type='outsourced',
            owner_party=self.supplier,
            supplier_driver_name='M. Murugan',
            supplier_driver_phone='9842255443',
            supplier_daily_rate=Decimal('5000.00'),
            supplier_driver_bata=Decimal('500.00'),
            status='available'
        )

        # 4. Booking & Trip
        self.today = timezone.now().date()
        self.booking = Booking.objects.create(
            party=self.customer,
            guest_name='Cognizant Facilities Group',
            guest_phone='9842299887',
            journey_type='outstation',
            pickup_location='Saravanampatti, Coimbatore',
            destination='Ooty, Nilgiris',
            pickup_date=self.today,
            pickup_time='06:00',
            quoted_price=Decimal('18500.00')
        )

        self.trip = Trip.objects.create(
            booking=self.booking,
            vehicle=self.vehicle,
            start_date=self.today,
            end_date=self.today + timedelta(days=2),
            start_time='06:00',
            end_time='20:00',
            billing_model='fixed',
            fixed_amount=Decimal('18500.00'),
            status='dispatched'
        )

        # 5. Trip Hotel
        self.trip_hotel = TripHotel.objects.create(
            trip=self.trip,
            hotel_name='Sterling Ooty Elk Hill',
            hotel_room_type='Deluxe Valley View',
            check_in_date=self.today,
            check_out_date=self.today + timedelta(days=2),
            confirmation_status='pending',
            notes='Driver accommodation required'
        )

    def test_01_tds_rate_determination_pan_matrix(self):
        """Tests Indian Income Tax Section 194C / 206AA TDS rate determination."""
        # 1. Individual Proprietor (4th character 'P') -> 1.00%
        sec, rate = determine_tds_rate('ABCDE1234F', party=self.supplier)
        self.assertEqual(sec, '194C_INDIVIDUAL')
        self.assertEqual(rate, Decimal('1.00'))

        # 2. Company / Firm (4th character 'C') -> 2.00%
        sec, rate = determine_tds_rate('AAACC9988C', party=self.corporate_supplier)
        self.assertEqual(sec, '194C_COMPANY')
        self.assertEqual(rate, Decimal('2.00'))

        # 3. Missing / Invalid PAN -> Sec 206AA penalty 20.00%
        sec, rate = determine_tds_rate('INVALID123', party=None)
        self.assertEqual(sec, '206AA_NO_PAN')
        self.assertEqual(rate, Decimal('20.00'))

        # 4. Form 194C(6) Exemption -> 0.00%
        sec, rate = determine_tds_rate('ABCDE1234F', force_section='EXEMPT_DECLARATION')
        self.assertEqual(sec, 'EXEMPT_DECLARATION')
        self.assertEqual(rate, Decimal('0.00'))

    def test_02_calculate_outsourced_settlement_math(self):
        """Tests mathematical accuracy of partner settlement, TDS, and deductions."""
        settlement = calculate_and_create_settlement(
            supplier=self.supplier,
            vehicle=self.vehicle,
            agreed_buy_rate=Decimal('10000.00'),
            trip=self.trip,
            toll_parking_allowance=Decimal('800.00'),
            driver_bata_payable=Decimal('1000.00'),
            advance_paid=Decimal('2000.00'),
            fuel_deducted=Decimal('1500.00'),
            damage_penalty=Decimal('0.00'),
            pan_number='ABCDE1234P',
            tds_applicable=True
        )

        # Gross = Buy (10,000) + Toll (800) + Bata (1,000) = 11,800
        self.assertEqual(settlement.gross_supplier_payable, Decimal('11800.00'))
        # TDS = 1% on 10,000 = 100
        self.assertEqual(settlement.tds_amount, Decimal('100.00'))
        # Total Deductions = Advance (2000) + Fuel (1500) + TDS (100) = 3600
        self.assertEqual(settlement.total_deductions, Decimal('3600.00'))
        # Net Payable = Gross (11,800) - Deductions (3,600) = 8,200
        self.assertEqual(settlement.net_payable_amount, Decimal('8200.00'))
        # Gross Margin = Customer Sell (18,500) - Gross Supplier (11,800) = 6,700
        self.assertEqual(settlement.gross_margin_earned, Decimal('6700.00'))
        self.assertEqual(settlement.status, 'draft')
        self.assertTrue(settlement.settlement_number.startswith('ST-'))

    def test_03_approve_settlement_and_post_ledger(self):
        """Tests that approving a settlement creates a SupplierTripCost record and updates status."""
        settlement = calculate_and_create_settlement(
            supplier=self.supplier,
            vehicle=self.vehicle,
            agreed_buy_rate=Decimal('9500.00'),
            trip=self.trip,
            advance_paid=Decimal('1000.00')
        )

        approved = approve_and_post_settlement_ledger(settlement, approved_by_user=self.staff_user)
        self.assertEqual(approved.status, 'approved')
        self.assertEqual(approved.approved_by, self.staff_user)

        # Check that finance.SupplierTripCost exists for this trip
        cost = SupplierTripCost.objects.filter(trip=self.trip, supplier=self.supplier).first()
        self.assertIsNotNone(cost)
        self.assertEqual(cost.amount, Decimal('9500.00'))
        self.assertIn(settlement.settlement_number, cost.description)

    def test_04_create_hotel_voucher_and_guest_manifest(self):
        """Tests creation of Hotel Confirmation Voucher with nights calculation and guest manifest."""
        voucher = create_hotel_voucher(
            trip=self.trip,
            trip_hotel=self.trip_hotel,
            hotel_name='Sterling Ooty Elk Hill',
            hotel_city='Ooty',
            hotel_phone='9443299881',
            lead_guest_name='Mr. Anbarasan',
            total_adults=4,
            total_children=2,
            total_rooms=2,
            room_category='deluxe',
            meal_plan='MAP',
            agreed_tariff=Decimal('14000.00'),
            advance_paid=Decimal('5000.00'),
            billing_instruction='bill_to_company',
            special_requests='Free driver accommodation requested'
        )

        self.assertTrue(voucher.voucher_number.startswith('HCV-'))
        self.assertEqual(voucher.total_nights, 2)
        self.assertEqual(voucher.balance_payable_to_hotel, Decimal('9000.00'))
        self.assertEqual(voucher.meal_plan, 'MAP')
        self.assertEqual(voucher.guest_manifest.count(), 1)
        self.assertEqual(self.trip_hotel.confirmation_status, 'confirmed')

        # Test WhatsApp link formatting
        wa_data = generate_hotel_whatsapp_link(voucher)
        self.assertIn('HCV-', wa_data['message_text'])
        self.assertIn('Sterling Ooty Elk Hill', wa_data['message_text'])
        self.assertIn('MAP', wa_data['message_text'])
        self.assertIn('wa.me', wa_data['whatsapp_url'])

    def test_05_views_and_rest_api_endpoints(self):
        """Tests web view responses and REST endpoints for settlements and vouchers."""
        # 1. Settlement Hub Studio
        res = self.client.get('/suppliers/settlement-hub/')
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Outsourced Fleet &amp; Partner Settlement Hub')

        # 2. Hotel Vouchers Hub Studio
        res = self.client.get('/suppliers/hotel-vouchers/')
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Hotel Confirmation Vouchers &amp; Rooming Hub')

        # 3. REST API: Calculate Settlement
        payload = {
            'trip_id': self.trip.id,
            'supplier_id': self.supplier.id,
            'vehicle_id': self.vehicle.id,
            'agreed_buy_rate': 8500.00,
            'toll_parking_allowance': 400.00,
            'advance_paid': 1500.00
        }
        res = self.client.post(
            '/suppliers/api/settlement/calculate/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data['success'])
        settlement_id = data['settlement_id']

        # 4. REST API: Approve Settlement
        res = self.client.post(f'/suppliers/api/settlement/{settlement_id}/approve/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['status'], 'approved')

        # 5. Duty Slip & Settlement Print Views
        res = self.client.get(f'/suppliers/duty-slip/{settlement_id}/print/')
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'DRIVER DUTY SLIP')

        res = self.client.get(f'/suppliers/settlement/{settlement_id}/print/')
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'VENDOR PAYMENT CLEARANCE VOUCHER')

        # 6. REST API: Create Hotel Voucher
        hotel_payload = {
            'trip_id': self.trip.id,
            'hotel_name': 'Club Mahindra Munnar',
            'hotel_city': 'Munnar',
            'check_in_date': str(self.today),
            'check_out_date': str(self.today + timedelta(days=2)),
            'lead_guest_name': 'Dr. Suresh Babu',
            'meal_plan': 'AP'
        }
        res = self.client.post(
            '/suppliers/api/hotel-voucher/create/',
            data=json.dumps(hotel_payload),
            content_type='application/json'
        )
        self.assertEqual(res.status_code, 200)
        v_data = res.json()
        self.assertTrue(v_data['success'])
        voucher_id = v_data['voucher_id']

        # 7. Hotel Voucher Print View & WhatsApp API
        res = self.client.get(f'/suppliers/hotel-voucher/{voucher_id}/print/')
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Club Mahindra Munnar')

        res = self.client.get(f'/suppliers/api/hotel-voucher/{voucher_id}/whatsapp/')
        self.assertEqual(res.status_code, 200)
        self.assertIn('whatsapp_url', res.json())

    def test_06_marketing_campaign_studio_and_reengagement(self):
        """Tests marketing campaign studio, audience counting, and promotional broadcast creation."""
        # Create a promo coupon
        coupon = Coupon.objects.create(
            code='DIWALI2026',
            discount_percent=Decimal('10.00'),
            is_active=True
        )

        # 1. Campaign Studio View
        res = self.client.get('/marketing/campaign-studio/')
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Marketing &amp; Customer Re-Engagement Studio')

        # 2. Audience Count API
        res = self.client.get('/marketing/api/audience-count/?audience=all_tourists')
        self.assertEqual(res.status_code, 200)
        self.assertIn('count', res.json())

        # 3. Create Campaign API
        payload = {
            'name': 'Diwali Outstation Bonanza',
            'headline': 'Diwali Outstation Bonanza',
            'message_body': 'Vanakkam {name}! Book with code *{coupon_code}* for exclusive travel discounts!',
            'channel': 'whatsapp',
            'target_audience': 'all_tourists',
            'coupon_id': coupon.id
        }
        res = self.client.post(
            '/marketing/api/campaign/create/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(res.status_code, 200)
        c_data = res.json()
        self.assertTrue(c_data['success'])
        self.assertEqual(c_data['campaign_name'], 'Diwali Outstation Bonanza')
        self.assertGreaterEqual(c_data['target_count'], 1)
        self.assertIn('dispatches', c_data)
