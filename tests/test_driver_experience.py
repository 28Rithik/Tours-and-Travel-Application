from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.utils import timezone
from core.models import Driver, Vehicle
from fleet_contracts.models import TransportContract, Route, RouteStop, CommuterManifest, Shift, ContractTripLog
from fleet_commute.models import CommuterBoardingPass
from driver_portal.models import DriverPortalAccount, DriverAttendanceLog, RouteIssueReport

User = get_user_model()


class DriverExperienceDomainTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # 1. Driver and Portal Account
        cls.driver = Driver.objects.create(
            name='Captain Senthil Kumar',
            phone='+91 98421 99881',
            license_number='TN-38-2018-0019283',
            status='active'
        )
        cls.user = User.objects.create_user(
            username=f"driver_{cls.driver.pk}",
            password='pass',
            is_staff=True
        )
        cls.portal_acc = DriverPortalAccount.objects.create(
            driver=cls.driver,
            user=cls.user,
            quick_pin='1234'
        )

        # 2. Vehicle
        cls.vehicle = Vehicle.objects.create(
            registration_number='TN 38 AZ 9901',
            brand='Force Motors',
            model='Urbania 4400',
            seating_capacity=17,
            current_km=84500,
            status='active'
        )

        # 3. Customer Party, Contract, Route & Stops
        from core.models import Party
        cls.party = Party.objects.create(
            name='Cognizant Technology Solutions',
            party_type='customer'
        )
        cls.contract = TransportContract.objects.create(
            name='CTS Corporate Staff Mobility SLA',
            customer=cls.party,
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timezone.timedelta(days=365),
            status='active'
        )
        cls.route = Route.objects.create(
            contract=cls.contract,
            name='CTS - Gandhipuram to CHIL SEZ Express',
            origin='Gandhipuram Bus Stand',
            destination='CHIL SEZ IT Park',
            distance_km=22,
            estimated_travel_minutes=45
        )
        cls.stop1 = RouteStop.objects.create(
            route=cls.route,
            stop_order=1,
            name='Cross Cut Signal',
            scheduled_offset_minutes=10,
            pickup_landmark='Opposite Kalyan Jewellers'
        )
        cls.stop2 = RouteStop.objects.create(
            route=cls.route,
            stop_order=2,
            name='Peelamedu Bus Stop',
            scheduled_offset_minutes=25,
            pickup_landmark='Near PSG Tech Signal'
        )

        # 4. Shift & ContractTripLog
        cls.shift = Shift.objects.create(
            route=cls.route,
            shift_name='General Morning Inbound',
            direction='inbound',
            timing=timezone.datetime.strptime('08:00', '%H:%M').time()
        )
        cls.trip_log = ContractTripLog.objects.create(
            driver=cls.driver,
            vehicle=cls.vehicle,
            shift=cls.shift,
            date=timezone.now().date(),
            status='in_progress',
            scheduled_departure_time=cls.shift.timing,
            opening_km=84500,
            passenger_count=2
        )

        # 5. Commuters and Boarding Passes
        cls.commuter1 = CommuterManifest.objects.create(
            contract=cls.contract,
            commuter_type='corporate_employee',
            commuter_id='CTS-EMP-01',
            name='Kavitha Sundar',
            phone='+91 97890 12345',
            boarding_stop=cls.stop1
        )
        cls.pass1 = CommuterBoardingPass.objects.create(
            trip_log=cls.trip_log,
            commuter=cls.commuter1,
            shift=cls.shift,
            boarding_otp='3421',
            is_boarded=False
        )

        cls.commuter2 = CommuterManifest.objects.create(
            contract=cls.contract,
            commuter_type='corporate_employee',
            commuter_id='CTS-EMP-02',
            name='Vignesh Rajan',
            phone='+91 97890 67890',
            boarding_stop=cls.stop2
        )
        cls.pass2 = CommuterBoardingPass.objects.create(
            trip_log=cls.trip_log,
            commuter=cls.commuter2,
            shift=cls.shift,
            boarding_otp='8892',
            is_boarded=False
        )

    def setUp(self):
        self.client = Client()
        self.client.force_login(self.user)

    def test_01_driver_dashboard_renders_with_schedule_and_attendance(self):
        """Driver dashboard renders with active duty cards, assigned schedule, and KPIs."""
        resp = self.client.get(f'/driver/?driver_id={self.driver.id}')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Duty Attendance')
        self.assertContains(resp, 'Today\'s Schedule')
        self.assertContains(resp, 'CTS - Gandhipuram to CHIL SEZ Express')
        self.assertContains(resp, 'TN 38 AZ 9901')

    def test_02_route_navigation_cockpit_renders_sequence_and_commuters(self):
        """Route Navigation Cockpit renders sequential stops, Google Maps link, and commuter actions."""
        resp = self.client.get(f'/driver/commute/{self.trip_log.id}/navigation/?driver_id={self.driver.id}')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Route Pickup Sequence')
        self.assertContains(resp, 'Cross Cut Signal')
        self.assertContains(resp, 'Peelamedu Bus Stop')
        self.assertContains(resp, 'Kavitha Sundar')
        self.assertContains(resp, 'Google Maps Nav')

    def test_03_clock_in_and_clock_out_apis(self):
        """Driver can clock in for duty and clock out with mileage and hours tracked."""
        # Clock in
        resp_in = self.client.post('/driver/api/clock-in/', {
            'shift_name': 'morning',
            'location': 'Coimbatore Depot North Gate',
            'odometer_start': '84500'
        })
        self.assertEqual(resp_in.status_code, 200)
        att = DriverAttendanceLog.objects.filter(driver=self.driver, status='on_duty').first()
        self.assertIsNotNone(att)
        self.assertEqual(att.odometer_start, 84500)

        # Clock out
        resp_out = self.client.post('/driver/api/clock-out/', {
            'odometer_end': '84560',
            'location': 'Coimbatore Depot North Gate',
            'notes': 'All routes on schedule.'
        })
        self.assertEqual(resp_out.status_code, 200)
        att.refresh_from_db()
        self.assertEqual(att.status, 'off_duty')
        self.assertEqual(att.odometer_end, 84560)

    def test_04_commuter_boarding_and_absent_actions(self):
        """Driver can board a passenger with OTP and mark an absent passenger as no-show."""
        # Board commuter 1
        resp_board = self.client.post('/driver/api/board-commuter/', {
            'pass_id': self.pass1.id,
            'otp': '3421'
        })
        self.assertEqual(resp_board.status_code, 200)
        self.pass1.refresh_from_db()
        self.assertTrue(self.pass1.is_boarded)
        self.assertIsNotNone(self.pass1.boarded_at)

        # Mark commuter 2 absent
        resp_absent = self.client.post('/driver/api/absent-commuter/', {
            'pass_id': self.pass2.id,
            'reason': 'Passenger unreachable by phone'
        })
        self.assertEqual(resp_absent.status_code, 200)
        self.pass2.refresh_from_db()
        self.assertTrue(self.pass2.is_no_show)
        self.assertFalse(self.pass2.is_boarded)

    def test_05_route_delay_reporting_api(self):
        """Driver can report traffic delay and it logs RouteIssueReport and updates trip log."""
        resp_delay = self.client.post('/driver/api/report-delay/', {
            'trip_log_id': self.trip_log.id,
            'issue_type': 'traffic_jam',
            'delay_minutes': 25,
            'notes': 'Severe gridlock near Hope College flyover'
        })
        self.assertEqual(resp_delay.status_code, 200)
        self.trip_log.refresh_from_db()
        self.assertEqual(self.trip_log.delay_minutes, 25)
        self.assertIn('Severe gridlock', self.trip_log.delay_reason)
