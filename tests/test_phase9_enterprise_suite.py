import datetime
from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.utils import timezone

from core.models import Driver, Vehicle, VehicleType, Party, Client as ClientModel, StaffProfile
from operations.models import Trip, Booking, TrafficFine, TripCashAdvanceEnvelope, EmptyLegTripOffer
from maintenance.models import ComplianceDocument

from operations.cash_advance_settlement import (
    get_cash_envelope_metrics,
    issue_cash_advance_envelope,
    log_onroad_expenses_to_envelope,
    settle_cash_advance_envelope,
    check_driver_pending_advances,
)
from operations.statutory_compliance_sentry import (
    get_compliance_dashboard_metrics,
    get_fleet_compliance_matrix,
    is_vehicle_legally_clear_for_dispatch,
    renew_compliance_document,
)
from operations.echallan_sentry import (
    get_echallan_dashboard_metrics,
    update_echallan_liability,
    mark_echallan_paid,
)
from operations.empty_leg_optimizer import (
    get_empty_leg_dashboard_metrics,
    calculate_empty_leg_pricing,
    generate_whatsapp_broadcast_text,
    SOUTH_INDIA_ONE_WAY_CORRIDORS,
)


class Phase9EnterpriseSuiteTestCase(TestCase):
    """
    Comprehensive test suite verifying Phase 9 operational and statutory capabilities:
    1. Trip Cash Advance & Settlement Envelope Studio
    2. RTO Fitness (FC) & Statutory Compliance Sentry
    3. Parivahan Traffic E-Challan Sentry Studio
    4. Empty-Leg Return Deadhead Trip Marketplace & Optimizer
    """

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_superuser(
            username='ops_director',
            email='ops@sivagayathiritravels.com',
            password='Password@123'
        )
        self.profile = StaffProfile.objects.create(
            user=self.user,
            role='fleet_manager',
            branch='Coimbatore Central HQ'
        )
        self.client.force_login(self.user)

        self.party = Party.objects.create(
            name='Roots Industries India Ltd',
            party_type='customer',
            phone='9842100000',
            billing_cycle='monthly'
        )

        self.v_type = VehicleType.objects.create(
            name='Toyota Innova Crysta',
            seating_capacity=7,
            driver_bata=Decimal('600.00')
        )

        self.vehicle = Vehicle.objects.create(
            registration_number='TN 38 CH 2026',
            vehicle_type=self.v_type,
            seating_capacity=7,
            ownership_type='owned',
            status='available',
            brand='Toyota',
            model='Innova Crysta 2.4 VX',
            current_km=84500,
            base_depot='Coimbatore Hub'
        )

        self.driver = Driver.objects.create(
            name='Muthusamy R',
            phone='9842211223',
            driver_type='owned',
            status='active',
            base_depot='Coimbatore Hub'
        )

        self.booking = Booking.objects.create(
            booking_number='BKG-TEST-9001',
            party=self.party,
            guest_name='Dr. K. Ramasamy',
            guest_phone='9842100000',
            pickup_location='Coimbatore HQ',
            destination='Munnar Tea Sanctuary',
            pickup_date=timezone.now().date(),
            pickup_time=datetime.time(6, 0),
            journey_type='outstation',
            vehicle_type=self.v_type,
            quoted_price=Decimal('18500.00')
        )

        self.trip = Trip.objects.create(
            booking=self.booking,
            vehicle=self.vehicle,
            driver=self.driver,
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + datetime.timedelta(days=3),
            opening_km=84500,
            status='started'
        )

    # --------------------------------------------------------------------------
    # 1. Trip Cash Advance Envelope Tests
    # --------------------------------------------------------------------------
    def test_cash_advance_lifecycle_and_reconciliation(self):
        # 1. Issue cash envelope
        env = issue_cash_advance_envelope(
            trip=self.trip,
            driver=self.driver,
            fuel=7500,
            toll=1400,
            permit=950,
            bata=1800,
            contingency=1000,
            notes='Munnar Outstation Tour Cash Advance'
        )
        self.assertEqual(env.total_advance_disbursed, Decimal('12650.00'))
        self.assertEqual(env.status, 'disbursed')

        # Check driver has pending advance
        has_pending, pending_env = check_driver_pending_advances(self.driver.id)
        self.assertTrue(has_pending)
        self.assertEqual(pending_env.id, env.id)

        # 2. Driver submits return expenses with receipts
        updated_env = log_onroad_expenses_to_envelope(
            envelope_id=env.id,
            fuel=7100,
            tolls=1400,
            permits=950,
            parking=300,
            repairs=0,
            bata=1800,
            submit_for_audit=True
        )
        self.assertEqual(updated_env.total_expenses_verified, Decimal('11550.00'))
        # Driver spent 11,550 out of 12,650 advance => Surplus of 1,100 to return to Cashier
        self.assertEqual(updated_env.net_balance, Decimal('1100.00'))
        self.assertEqual(updated_env.status, 'submitted_for_audit')

        # 3. Cashier settles and closes envelope
        settled = settle_cash_advance_envelope(
            envelope_id=env.id,
            notes='Cashier received ₹1,100 physical cash surplus at Coimbatore gate.',
            signature_ack=True
        )
        self.assertEqual(settled.status, 'reconciled_settled')
        self.assertTrue(settled.driver_signature_acknowledged)
        self.assertIsNotNone(settled.settled_at)

        # Metrics check
        metrics = get_cash_envelope_metrics()
        self.assertGreaterEqual(metrics['total_envelopes'], 1)
        self.assertEqual(metrics['settled_count'], 1)

    # --------------------------------------------------------------------------
    # 2. Statutory Compliance Sentry Tests
    # --------------------------------------------------------------------------
    def test_statutory_compliance_radar_and_renewal(self):
        from django.core.cache import cache
        cache.clear()
        today = timezone.now().date()

        # Create FC document expiring in 5 days (Critical)
        fc_doc = ComplianceDocument.objects.create(
            vehicle=self.vehicle,
            document_type='fc',
            document_number='FC/TN38/2026/001',
            issue_date=today - datetime.timedelta(days=360),
            expiry_date=today + datetime.timedelta(days=5),
            notes='RTO Fitness due for annual inspection'
        )

        # Create Speed Governor certificate valid for 180 days
        sg_doc = ComplianceDocument.objects.create(
            vehicle=self.vehicle,
            document_type='speed_governor',
            document_number='SG-80-TN-2026',
            issue_date=today - datetime.timedelta(days=185),
            expiry_date=today + datetime.timedelta(days=180),
            notes='80 km/h Limiter certified'
        )

        metrics = get_compliance_dashboard_metrics()
        self.assertGreaterEqual(metrics['critical_docs'], 1)

        matrix = get_fleet_compliance_matrix()
        v_entry = next((item for item in matrix if item['vehicle_id'] == self.vehicle.id), None)
        self.assertIsNotNone(v_entry)
        self.assertEqual(v_entry['docs']['fc']['status'], 'critical')

        # Renew FC document
        renewed = renew_compliance_document(
            doc_id=fc_doc.id,
            new_expiry_date=today + datetime.timedelta(days=365),
            new_doc_number='FC/TN38/2027/994',
            notes='Passed roller brake test and speed governor test at Coimbatore North RTO.'
        )
        self.assertEqual(renewed.expiry_date, today + datetime.timedelta(days=365))
        self.assertEqual(renewed.document_number, 'FC/TN38/2027/994')

    # --------------------------------------------------------------------------
    # 3. Traffic E-Challan Sentry Tests
    # --------------------------------------------------------------------------
    def test_echallan_liability_routing_and_payment(self):
        fine = TrafficFine.objects.create(
            challan_number='TN-ECH-TEST-001',
            vehicle=self.vehicle,
            driver=self.driver,
            trip=self.trip,
            date_of_offence=timezone.now(),
            violation_type='speeding',
            fine_amount=Decimal('1000.00'),
            paid_by='unpaid',
            financial_responsibility='driver',
            notes='Overspeeding 94 km/h in 80 km/h radar zone near Salem bypass.'
        )

        metrics = get_echallan_dashboard_metrics()
        self.assertGreaterEqual(metrics['unpaid_count'], 1)
        self.assertGreaterEqual(metrics['driver_liability_amt'], Decimal('1000.00'))

        # Route liability to company (e.g. dispute won by driver)
        updated_fine = update_echallan_liability(
            fine_id=fine.id,
            responsibility='company',
            notes='Disputed: Sensor miscalibration verified by NHAI.'
        )
        self.assertEqual(updated_fine.financial_responsibility, 'company')

        # Mark paid by company
        paid_fine = mark_echallan_paid(
            fine_id=fine.id,
            paid_by='company',
            transaction_ref='PARIVAHAN-TXN-88219'
        )
        self.assertEqual(paid_fine.paid_by, 'company')
        self.assertIn('PARIVAHAN-TXN-88219', paid_fine.notes)

    # --------------------------------------------------------------------------
    # 4. Empty-Leg Return Deadhead Optimizer Tests
    # --------------------------------------------------------------------------
    def test_empty_leg_pricing_and_booking(self):
        corridor = SOUTH_INDIA_ONE_WAY_CORRIDORS[0]  # BLR -> CJB
        pricing = calculate_empty_leg_pricing(corridor, 'suv')

        self.assertGreater(pricing['std_tariff'], pricing['discounted_rate'])
        self.assertGreater(pricing['net_margin'], Decimal('0.00'))

        now = timezone.now()
        offer = EmptyLegTripOffer.objects.create(
            offer_code='EL-TEST-001',
            parent_trip=self.trip,
            vehicle=self.vehicle,
            driver=self.driver,
            origin_city=corridor['origin'],
            destination_city=corridor['dest'],
            available_from=now,
            available_until=now + datetime.timedelta(hours=24),
            standard_tariff=pricing['std_tariff'],
            discounted_empty_leg_rate=pricing['discounted_rate'],
            estimated_fuel_cost=pricing['fuel_cost'],
            estimated_toll_cost=pricing['toll_cost'],
            net_margin_generated=pricing['net_margin'],
            status='available',
            notes='Drop at BLR Airport completed. Available for discounted return.'
        )

        # Generate WhatsApp broadcast text
        wa_text = generate_whatsapp_broadcast_text(offer)
        self.assertIn('SIVAGAYATHIRI EMPTY-LEG DEAL', wa_text)
        self.assertIn(self.vehicle.registration_number, wa_text)

        # API publish
        res_pub = self.client.post('/api/operations/empty-legs/publish/', {
            'offer_id': offer.id
        }, content_type='application/json')
        self.assertEqual(res_pub.status_code, 200)

        # API book
        res_book = self.client.post('/api/operations/empty-legs/book/', {
            'offer_id': offer.id
        }, content_type='application/json')
        self.assertEqual(res_book.status_code, 200)
        offer.refresh_from_db()
        self.assertEqual(offer.status, 'booked')

    # --------------------------------------------------------------------------
    # 5. HTTP Views Render & Light Mode Readiness Tests
    # --------------------------------------------------------------------------
    def test_all_studios_http_render_200(self):
        urls = [
            '/operations/cash-envelopes/',
            '/operations/statutory-compliance/',
            '/operations/echallan-sentry/',
            '/operations/empty-legs/',
            '/operations/border-permits/',
            '/operations/driver-fatigue-sentry/',
            '/operations/breakdown-sos/',
            '/operations/pnr-arrivals/',
            '/suppliers/vendor-bill-audit/',
            '/crm/feedback-reviews/',
            '/crm/followup-cadence/',
            '/finance/tds-194c/',
            '/finance/fastag-reconciliation/',
            '/maintenance/parts-inventory/',
        ]

        for u in urls:
            res = self.client.get(u)
            self.assertEqual(
                res.status_code, 200,
                f"Failed to render studio view: {u} (Got status {res.status_code})"
            )

    # --------------------------------------------------------------------------
    # 6. Global Search Studio Keyword Matches
    # --------------------------------------------------------------------------
    def test_global_search_studio_matches(self):
        queries = ['cash', 'compliance', 'challan', 'empty']
        for q in queries:
            res = self.client.get(f'/api/operations/global-search/?q={q}')
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertEqual(data['status'], 'success')
            self.assertGreater(data['count'], 0)
            studio_matches = [r for r in data['results'] if r['category'] == 'Operations Studios']
            self.assertGreater(len(studio_matches), 0, f"Expected studio match for keyword: '{q}'")
