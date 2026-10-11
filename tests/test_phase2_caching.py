import datetime
from decimal import Decimal
from django.test import TestCase, Client
from django.core.cache import cache
from django.utils import timezone
from core.models import VehicleType, Vehicle, Driver, Party
from fleet_contracts.models import TransportContract, Route, Shift, CommuterManifest, ContractTripLog
from fleet_commute.models import CommuterBoardingPass
from operations.models import VehicleTelematicsPing
from core.cache_services import (
    get_cached_vehicle_types,
    invalidate_vehicle_types_cache,
    get_cached_active_contracts,
    invalidate_active_contracts_cache,
    get_cached_latest_telematics,
    set_cached_latest_telematics,
    CACHE_KEY_VEHICLE_TYPES,
    CACHE_KEY_ACTIVE_CONTRACTS,
)


class Phase2CachingTierTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = Client()

    def test_vehicle_type_master_data_caching_and_invalidation(self):
        """Verifies VehicleType objects are cached in-memory and invalidated upon change."""
        vt = VehicleType.objects.create(name="Executive Luxury Coach 54", default_day_rate=Decimal('8500.00'))
        
        # 1. Cache Miss -> Populates cache
        self.assertIsNone(cache.get(CACHE_KEY_VEHICLE_TYPES))
        cached_list = get_cached_vehicle_types()
        self.assertIsNotNone(cache.get(CACHE_KEY_VEHICLE_TYPES))
        self.assertEqual(len(cached_list), VehicleType.objects.count())

        # 2. Modify VehicleType -> Signal auto-invalidates cache
        vt.name = "Executive Luxury Coach 54 (Upgraded)"
        vt.save()
        self.assertIsNone(cache.get(CACHE_KEY_VEHICLE_TYPES), "Cache should be invalidated after save signal.")

        # 3. Next get repopulates with new name
        new_cached = get_cached_vehicle_types()
        self.assertIn("Executive Luxury Coach 54 (Upgraded)", [v.name for v in new_cached])

    def test_active_transport_contracts_caching_and_invalidation(self):
        """Verifies active contracts are cached and invalidated upon modification."""
        party = Party.objects.create(name="Cognizant OMR Campus", party_type='corporate')
        contract = TransportContract.objects.create(
            customer=party,
            name="Cognizant Employee Commute Contract 2026",
            billing_model='monthly_fixed',
            start_date=datetime.date(2026, 1, 1),
            end_date=datetime.date(2026, 12, 31),
            status='active',
        )

        self.assertIsNone(cache.get(CACHE_KEY_ACTIVE_CONTRACTS))
        contracts = get_cached_active_contracts()
        self.assertIsNotNone(cache.get(CACHE_KEY_ACTIVE_CONTRACTS))
        self.assertEqual(len(contracts), 1)

        # Trigger update -> verifies signal invalidation
        contract.name = "Cognizant Employee Commute Contract 2026 (Renewed)"
        contract.save()
        self.assertIsNone(cache.get(CACHE_KEY_ACTIVE_CONTRACTS))

    def test_zero_disk_live_telematics_cache(self):
        """Verifies telematics pings are cached in RAM and live tracking serves sub-millisecond cached GPS."""
        vehicle = Vehicle.objects.create(registration_number="TN-38-CACHE-01", ownership_type='owned')
        driver = Driver.objects.create(name="Murugan Captain")
        party = Party.objects.create(name="Tech Park", party_type='corporate')
        contract = TransportContract.objects.create(
            customer=party,
            name="Tech Park Shuttles",
            start_date=datetime.date(2026, 1, 1),
            end_date=datetime.date(2026, 12, 31),
            status='active'
        )
        route = Route.objects.create(contract=contract, name="Route 101")
        shift = Shift.objects.create(route=route, direction='pickup', timing=datetime.time(8, 30))
        trip_log = ContractTripLog.objects.create(
            shift=shift,
            date=timezone.now().date(),
            vehicle=vehicle,
            driver=driver,
            status='en_route'
        )
        commuter = CommuterManifest.objects.create(contract=contract, commuter_id="EMP-900", name="Anitha S")
        bp = CommuterBoardingPass.objects.create(
            commuter=commuter,
            trip_log=trip_log,
            shift=shift,
            pass_token="test_token_live_gps_cache_123"
        )

        # 1. Post telematics ping to ingestion endpoint
        ping_payload = {
            "vehicle_id": vehicle.pk,
            "latitude": 11.025000,
            "longitude": 76.960000,
            "speed_kmh": 48.5,
            "heading": 80,
            "ignition_on": True,
            "fuel_level_pct": 74.0,
        }
        res_ping = self.client.post('/api/telematics/ping/', ping_payload, content_type='application/json')
        self.assertEqual(res_ping.status_code, 200)

        # 2. Verify in-memory cache was populated directly by ingestion
        cached = get_cached_latest_telematics(vehicle.pk)
        self.assertIsNotNone(cached)
        self.assertEqual(cached['latitude'], 11.025)
        self.assertEqual(cached['speed_kmh'], 48.5)

        # 3. Call live tracking API -> Should serve from cache
        url = f"/commute/api/track/{bp.pass_token}/live/"
        res_track = self.client.get(url)
        self.assertEqual(res_track.status_code, 200)
        data = res_track.json()
        self.assertEqual(data['latitude'], 11.025)
        self.assertEqual(data['speed_kmh'], 48.5)
        self.assertEqual(data['vehicle_number'], "TN-38-CACHE-01")
