"""
scripts/test_phase10_clustering_visual_verification.py

Playwright Visual Verification Script for Phase 10:
Corporate Commute Roster Optimization & Route Clustering Engine.
Captures screenshots of:
1. The AI Route Clustering & Multi-Vehicle Roster Optimization Cockpit with active clusters.
2. The Live Dispatch Table updated with committed cluster runs.
"""

import os
import sys
import time
from pathlib import Path
from decimal import Decimal

# Setup Django
WORKSPACE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"

import django
django.setup()

from django.contrib.auth.models import User
import django.contrib.auth
from django.conf import settings
from importlib import import_module
from playwright.sync_api import sync_playwright

from core.models import Vehicle, Driver, VehicleType, Client as CoreClient
from fleet_contracts.models import TransportContract, Route, RouteStop, Shift, CommuterManifest

ARTIFACT_DIR = Path(r"C:\Users\rithi\.gemini\antigravity-ide\brain\3c044726-a75e-47a0-949a-d96c5805a71d")
BASE_URL = "http://127.0.0.1:8000"


def get_session_cookie(user):
    engine = import_module(settings.SESSION_ENGINE)
    session = engine.SessionStore()
    session[django.contrib.auth.SESSION_KEY] = str(user.pk)
    session[django.contrib.auth.BACKEND_SESSION_KEY] = 'django.contrib.auth.backends.ModelBackend'
    session[django.contrib.auth.HASH_SESSION_KEY] = user.get_session_auth_hash()
    session.save()
    return session.session_key


def main():
    print("========================================================================")
    print("[*] PHASE 10: PLAYWRIGHT VISUAL VERIFICATION & AI CLUSTERING AUDIT")
    print("========================================================================")

    user = User.objects.filter(is_superuser=True).first()
    if not user:
        print("[-] Superuser not found.")
        sys.exit(1)

    session_cookie = get_session_cookie(user)
    print(f"[+] Authenticated session generated for {user.username}")

    # Seed demo contract & commuters if needed
    client, _ = CoreClient.objects.get_or_create(
        name="Bosch Global Software Technologies (CH-Campus)",
        defaults={"phone": "+91 98401 22334", "email": "transport@bosch.demo"}
    )
    today = django.utils.timezone.now().date()
    contract, _ = TransportContract.objects.get_or_create(
        name="Bosch Tech Park Corporate ETS 2026",
        defaults={
            "customer": client,
            "contract_category": "corporate",
            "start_date": today - django.utils.timezone.timedelta(days=30),
            "end_date": today + django.utils.timezone.timedelta(days=330),
            "status": "active",
            "campus_latitude": Decimal("11.016800"),
            "campus_longitude": Decimal("76.955800"),
        }
    )
    if contract.status != 'active':
        contract.status = 'active'
        contract.save()

    route, _ = Route.objects.get_or_create(
        contract=contract,
        name="Saravanampatti to Bosch Campus",
        defaults={
            "origin": "Saravanampatti Hub",
            "destination": "Bosch Campus Gate 2",
            "distance_km": 16,
            "estimated_travel_minutes": 38,
            "is_active": True
        }
    )
    shift, _ = Shift.objects.get_or_create(
        route=route,
        shift_name="Evening Shift 2 Drop",
        direction="drop",
        defaults={
            "timing": django.utils.timezone.datetime.strptime("21:00", "%H:%M").time(),
            "days_of_week": "Mon-Fri"
        }
    )

    # Seed 10 commuters with male/female distribution
    sample_commuters = [
        ("BOSCH01", "Swetha Narayanan", "female", "Stop A - KGISL Campus", Decimal("11.0825"), Decimal("76.9975")),
        ("BOSCH02", "Deepak Sundaram", "male", "Stop A - KGISL Campus", Decimal("11.0821"), Decimal("76.9971")),
        ("BOSCH03", "Aishwarya Rajesh", "female", "Stop B - CHIL SEZ", Decimal("11.0750"), Decimal("76.9925")),
        ("BOSCH04", "Gautham Menon", "male", "Stop B - CHIL SEZ", Decimal("11.0740"), Decimal("76.9918")),
        ("BOSCH05", "Nithya Ram", "female", "Stop C - Ganapathy", Decimal("11.0415"), Decimal("76.9789")),
        ("BOSCH06", "Prabhu Deva", "male", "Stop C - Ganapathy", Decimal("11.0408"), Decimal("76.9782")),
        ("BOSCH07", "Lavanya Mani", "female", "Stop D - Peelamedu", Decimal("11.0250"), Decimal("76.9950")),
        ("BOSCH08", "Harish Kalyan", "male", "Stop D - Peelamedu", Decimal("11.0245"), Decimal("76.9940")),
    ]

    for cid, name, gender, stop_name, lat, lng in sample_commuters:
        CommuterManifest.objects.get_or_create(
            contract=contract,
            commuter_id=cid,
            defaults={
                "name": name,
                "gender": gender,
                "latitude": lat,
                "longitude": lng,
                "phone": "+91 98401 22334",
                "department_or_grade": "ADAS Mobility",
                "is_active": True
            }
        )

    print(f"[+] Contract primed: {contract.name} with {contract.commuters.count()} employees")

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        context = browser.new_context(viewport={'width': 1600, 'height': 1200})

        context.add_cookies([{
            'name': settings.SESSION_COOKIE_NAME,
            'value': session_cookie,
            'domain': '127.0.0.1',
            'path': '/',
            'httpOnly': True,
            'sameSite': 'Lax',
        }])

        page = context.new_page()

        print("[*] Navigating to Roster Dispatcher Studio (/commute/roster-dispatcher/)...")
        page.goto(f"{BASE_URL}/commute/roster-dispatcher/", wait_until="networkidle")
        time.sleep(2)

        # 1. Select the Bosch contract in the dropdown
        contract_select = page.locator("#clusterContractSelect")
        if contract_select.is_visible():
            contract_select.select_option(str(contract.id))
            print(f"[+] Selected contract #{contract.id} in clustering cockpit.")

        # 2. Click "Run AI Optimization" button
        opt_btn = page.locator("#btnRunClustering")
        print("[*] Triggering AI Route Optimization button...")
        opt_btn.click()
        time.sleep(3)

        # Verify cluster KPI bar is visible
        kpi_bar = page.locator("#clusterKpiBar")
        is_kpi_visible = kpi_bar.is_visible()
        print(f"[+] Cluster KPI summary bar visible: {is_kpi_visible}")

        # Check clusters count rendered
        cluster_cards = page.locator(".cluster-card")
        cards_count = cluster_cards.count()
        print(f"[+] AI Cluster cards rendered: {cards_count}")

        # 3. Capture high-res screenshot of the AI Optimization Cockpit with clusters
        screenshot1 = ARTIFACT_DIR / "phase10_corporate_roster_optimizer.png"
        page.screenshot(path=str(screenshot1), full_page=True)
        print(f"[OK] Saved AI Route Clustering screenshot: {screenshot1}")

        # 4. Click "Approve & Commit Clusters to Live Dispatch"
        commit_btn = page.locator("#btnCommitClusters")
        if commit_btn.is_visible():
            print("[*] Clicking Approve & Commit Clusters to Live Dispatch...")
            # Set dialog handler to accept alert
            page.on("dialog", lambda dialog: dialog.accept())
            commit_btn.click()
            time.sleep(3)

        # 5. Capture post-commit Live Dispatch schedule table
        screenshot2 = ARTIFACT_DIR / "phase10_roster_dispatched_committed.png"
        page.screenshot(path=str(screenshot2), full_page=True)
        print(f"[OK] Saved Live Dispatch Roster screenshot: {screenshot2}")

        browser.close()

    print("========================================================================")
    print("[OK] PHASE 10 VISUAL VERIFICATION COMPLETE!")
    print("========================================================================")


if __name__ == '__main__':
    main()
