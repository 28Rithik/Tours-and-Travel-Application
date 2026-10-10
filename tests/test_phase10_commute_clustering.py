"""
tests/test_phase10_commute_clustering.py

Automated Test Suite for Phase 10:
Corporate Commute Roster Optimization & Route Clustering Engine.
Validates:
1. Spatial Geohash / Haversine Distance & Density Clustering
2. Fleet Capacity Matching (Sedan 4S, MPV 7S, Tempo 14S, Bus 32S)
3. TSP 2-Opt Waypoint Route Sequencing
4. Statutory Night Commute Female Safety Guardrails & Mandatory Escort Assignment
5. Atomic Roster Commitment (ContractTripLog, CommuterBoardingPass, NightSafetyEscortLog)
6. REST API Endpoints (/commute/api/clusters/optimize/ & /commute/api/clusters/commit/)
"""

import json
from decimal import Decimal
from datetime import time, timedelta
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.utils import timezone

from core.models import Vehicle, Driver, VehicleType, Client as CoreClient
from fleet_contracts.models import (
    TransportContract,
    Route,
    RouteStop,
    Shift,
    ContractTripLog,
    CommuterManifest,
    NightSafetyEscortLog,
)
from fleet_commute.models import CommuterBoardingPass, ESGCarbonMetric
from fleet_commute.clustering_engine import CommuteRouteClusteringEngine


class Phase10RouteClusteringTests(TestCase):
    def setUp(self):
        # 1. Setup Superuser and Client
        self.user = User.objects.create_superuser(username='testadmin', email='admin@example.com', password='password123')
        self.client = Client()
        self.client.force_login(self.user)

        # 2. Setup Core Client
        self.corp_client = CoreClient.objects.create(
            name="Cognizant IT Solutions (CH-OMR)",
            phone="+91 98401 55667",
            email="transport@cognizant.demo",
            is_active=True
        )

        # 3. Setup TransportContract
        today = timezone.now().date()
        self.contract = TransportContract.objects.create(
            contract_category='corporate',
            name="Cognizant Campus Shuttle 2026",
            customer=self.corp_client,
            start_date=today - timedelta(days=10),
            end_date=today + timedelta(days=350),
            status='active',
            campus_latitude=Decimal("11.016800"),
            campus_longitude=Decimal("76.955800")
        )

        # 4. Setup Route & Shifts
        self.route = Route.objects.create(
            contract=self.contract,
            name="Saravanampatti to Tech Park",
            origin="Saravanampatti Hub",
            destination="Cognizant Tech Park",
            distance_km=18,
            estimated_travel_minutes=42,
            is_active=True
        )

        self.morning_shift = Shift.objects.create(
            route=self.route,
            shift_name="Shift 1 Morning Login",
            direction="pickup",
            timing=time(8, 0),
            days_of_week="Mon-Fri"
        )

        self.night_shift = Shift.objects.create(
            route=self.route,
            shift_name="Shift 3 Night Drop (BPO/Support)",
            direction="drop",
            timing=time(22, 30),  # 10:30 PM Night Shift
            days_of_week="Mon-Fri"
        )

        # 5. Setup Route Stops with GPS coordinates
        self.stop1 = RouteStop.objects.create(
            route=self.route, stop_order=1, name="Saravanampatti Checkpost",
            latitude=Decimal("11.082100"), longitude=Decimal("76.997200")
        )
        self.stop2 = RouteStop.objects.create(
            route=self.route, stop_order=2, name="Chil SEZ Main Gate",
            latitude=Decimal("11.074500"), longitude=Decimal("76.992100")
        )
        self.stop3 = RouteStop.objects.create(
            route=self.route, stop_order=3, name="Ganapathy Bus Stand",
            latitude=Decimal("11.041200"), longitude=Decimal("76.978500")
        )

        # 6. Setup Fleet Vehicles of various capacities
        self.driver1 = Driver.objects.create(name="Ramesh Kannan", phone="+91 98421 11001", status='active')
        self.driver2 = Driver.objects.create(name="Suresh Kumar", phone="+91 98421 11002", status='active')

        vtype_sedan = VehicleType.objects.create(name="Sedan Cab", seating_capacity=4)
        vtype_mpv = VehicleType.objects.create(name="Innova MPV", seating_capacity=7)
        vtype_tempo = VehicleType.objects.create(name="Tempo Traveller", seating_capacity=14)

        self.veh_sedan = Vehicle.objects.create(
            registration_number="TN-38-SEDAN-01",
            vehicle_type=vtype_sedan,
            seating_capacity=4,
            default_driver=self.driver1,
            status='available'
        )
        self.veh_innova = Vehicle.objects.create(
            registration_number="TN-38-INNOVA-01",
            vehicle_type=vtype_mpv,
            seating_capacity=7,
            default_driver=self.driver2,
            status='available'
        )
        self.veh_tempo = Vehicle.objects.create(
            registration_number="TN-38-TEMPO-01",
            vehicle_type=vtype_tempo,
            seating_capacity=14,
            status='available'
        )

        # 7. Seed 9 Commuters with varied genders and stops
        self.commuters = []
        commuter_seed = [
            ("EMP101", "Ananya Krishnan", "female", self.stop1, Decimal("11.0825"), Decimal("76.9975")),
            ("EMP102", "Priya Sundaram", "female", self.stop1, Decimal("11.0821"), Decimal("76.9971")),
            ("EMP103", "Karthik Subramanian", "male", self.stop2, Decimal("11.0750"), Decimal("76.9925")),
            ("EMP104", "Deepa Natarajan", "female", self.stop2, Decimal("11.0740"), Decimal("76.9918")),
            ("EMP105", "Vignesh Murugan", "male", self.stop3, Decimal("11.0415"), Decimal("76.9789")),
            ("EMP106", "Sangeetha Raman", "female", self.stop3, Decimal("11.0408"), Decimal("76.9782")),
            ("EMP107", "Dinesh Babu", "male", self.stop3, Decimal("11.0410"), Decimal("76.9780")),
            ("EMP108", "Kavitha Rajan", "female", self.stop1, Decimal("11.0830"), Decimal("76.9980")),
            ("EMP109", "Manoj Prabhakar", "male", self.stop2, Decimal("11.0742"), Decimal("76.9920")),
        ]

        for emp_id, name, gender, stop, lat, lng in commuter_seed:
            c = CommuterManifest.objects.create(
                contract=self.contract,
                commuter_id=emp_id,
                name=name,
                gender=gender,
                boarding_stop=stop,
                latitude=lat,
                longitude=lng,
                phone="+91 98401 99000",
                is_active=True
            )
            self.commuters.append(c)

    def test_haversine_and_spatial_clustering(self):
        """Verifies Haversine great-circle calculation and spatial clustering grouping."""
        dist = CommuteRouteClusteringEngine.haversine_distance_km(11.0168, 76.9558, 11.0821, 76.9972)
        # Distance between Coimbatore center and Saravanampatti is ~8.5 to 10 km
        self.assertGreater(dist, 7.0)
        self.assertLess(dist, 12.0)

        # Run clustering
        result = CommuteRouteClusteringEngine.cluster_manifest(
            contract_id=self.contract.id,
            shift_id=self.morning_shift.id,
            vehicle_preference='auto'
        )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["summary"]["total_commuters"], 9)
        self.assertGreater(result["summary"]["total_clusters"], 0)
        self.assertGreater(result["summary"]["total_circuit_km"], 0.0)

    def test_capacity_matched_vehicle_allocation(self):
        """Validates capacity matching for varying group sizes."""
        # 3 passengers -> Sedan
        m3 = CommuteRouteClusteringEngine.match_fleet_vehicle(3)
        self.assertEqual(m3["profile"]["code"], "sedan")

        # 6 passengers -> MPV
        m6 = CommuteRouteClusteringEngine.match_fleet_vehicle(6)
        self.assertEqual(m6["profile"]["code"], "mpv")

        # 12 passengers -> Tempo
        m12 = CommuteRouteClusteringEngine.match_fleet_vehicle(12)
        self.assertEqual(m12["profile"]["code"], "tempo")

    def test_tsp_2opt_waypoint_sequencing(self):
        """Validates TSP sequencing for both pickup and drop directions."""
        nodes = [
            {"name": "Stop Near", "latitude": 11.0250, "longitude": 76.9600},
            {"name": "Stop Far", "latitude": 11.0950, "longitude": 77.0100},
            {"name": "Stop Mid", "latitude": 11.0600, "longitude": 76.9800},
        ]

        # Pickup: farthest stop from campus should be visited first
        pickup_seq = CommuteRouteClusteringEngine.solve_tsp_sequence(
            nodes=nodes,
            direction="pickup",
            campus_lat=11.0168,
            campus_lng=76.9558
        )
        self.assertEqual(pickup_seq[0]["name"], "Stop Far")
        self.assertEqual(pickup_seq[-1]["name"], "Stop Near")

        # Drop: closest stop to campus should be visited first
        drop_seq = CommuteRouteClusteringEngine.solve_tsp_sequence(
            nodes=nodes,
            direction="drop",
            campus_lat=11.0168,
            campus_lng=76.9558
        )
        self.assertEqual(drop_seq[0]["name"], "Stop Near")
        self.assertEqual(drop_seq[-1]["name"], "Stop Far")

    def test_statutory_night_female_safety_guardrails(self):
        """Validates mandatory escort guard assignment when female is last drop on night shift."""
        # Run clustering on the night drop shift (22:30 PM)
        result = CommuteRouteClusteringEngine.cluster_manifest(
            contract_id=self.contract.id,
            shift_id=self.night_shift.id,
            vehicle_preference='sedan_mpv'
        )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["shift_direction"], "drop")

        # Check clusters for night safety flag
        clusters = result["clusters"]
        has_night_escort_flagged = any(c["night_safety"]["requires_escort"] for c in clusters)
        self.assertTrue(has_night_escort_flagged, "Statutory escort guard should be flagged for night female drops.")

    def test_atomic_cluster_commitment_to_roster(self):
        """Validates committing clusters creates ContractTripLog, BoardingPasses, and NightSafetyEscortLog."""
        # 1. Generate clusters
        plan = CommuteRouteClusteringEngine.cluster_manifest(
            contract_id=self.contract.id,
            shift_id=self.night_shift.id,
            vehicle_preference='auto'
        )
        self.assertEqual(plan["status"], "success")

        # 2. Commit clusters
        commit_res = CommuteRouteClusteringEngine.commit_clusters_to_roster(
            contract_id=self.contract.id,
            clusters_data=plan["clusters"],
            shift_id=self.night_shift.id
        )

        self.assertEqual(commit_res["status"], "success")
        self.assertGreater(commit_res["trips_committed"], 0)
        self.assertGreater(commit_res["boarding_passes_provisioned"], 0)

        # 3. Verify ContractTripLog exists in DB
        trip = ContractTripLog.objects.filter(id__in=commit_res["trip_ids"]).first()
        self.assertIsNotNone(trip)
        self.assertTrue(trip.cluster_code.startswith("CLUS-"))
        self.assertEqual(trip.status, 'scheduled')

        # 4. Verify CommuterBoardingPass records exist with 4-digit OTPs
        passes = CommuterBoardingPass.objects.filter(trip_log=trip)
        self.assertGreater(passes.count(), 0)
        first_pass = passes.first()
        self.assertEqual(len(first_pass.boarding_otp), 4)

        # 5. Verify NightSafetyEscortLog created if escort was flagged
        if commit_res["escort_logs_created"] > 0:
            escort = NightSafetyEscortLog.objects.filter(trip_log=trip).first()
            self.assertIsNotNone(escort)
            self.assertEqual(escort.last_drop_verification_status, 'pending')

    def test_api_optimize_commute_clusters(self):
        """Tests POST /commute/api/clusters/optimize/ endpoint."""
        payload = {
            "contract_id": self.contract.id,
            "shift_id": self.morning_shift.id,
            "vehicle_preference": "auto"
        }
        response = self.client.post(
            "/commute/api/clusters/optimize/",
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("clusters", data)
        self.assertIn("summary", data)

    def test_api_commit_commute_clusters(self):
        """Tests POST /commute/api/clusters/commit/ endpoint."""
        # Optimize first
        plan = CommuteRouteClusteringEngine.cluster_manifest(
            contract_id=self.contract.id,
            shift_id=self.morning_shift.id
        )

        commit_payload = {
            "contract_id": self.contract.id,
            "shift_id": self.morning_shift.id,
            "clusters": plan["clusters"]
        }
        response = self.client.post(
            "/commute/api/clusters/commit/",
            data=json.dumps(commit_payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertGreater(data["trips_committed"], 0)

    def test_api_commute_cluster_stats(self):
        """Tests GET /commute/api/clusters/stats/ endpoint."""
        response = self.client.get("/commute/api/clusters/stats/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertGreaterEqual(data["active_contracts_count"], 1)
        self.assertGreaterEqual(data["total_registered_commuters"], 9)
