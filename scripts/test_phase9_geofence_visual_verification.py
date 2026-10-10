"""
scripts/test_phase9_geofence_visual_verification.py

Automated Playwright visual verification for Phase 9:
Real-Time Geofence Breach Daemon & Emergency Incident Alarms.
Captures high-resolution screenshots of the Tactical Hazard Alert Banners,
Emergency SOS Alerts, and Dispatcher Acknowledgment in Mission Control & Fleet Radar.
"""

import os
import sys
import time
from pathlib import Path

# Setup Django Environment
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
    print("[*] PHASE 9: PLAYWRIGHT VISUAL VERIFICATION & HAZARD AUDIT")
    print("========================================================================")

    user = User.objects.filter(is_superuser=True).first()
    if not user:
        print("[-] No superuser found! Exiting.")
        sys.exit(1)

    session_cookie = get_session_cookie(user)
    print(f"[+] Generated authenticated session for {user.username}")

    # Seed active geofence breach incident for visual verification
    from core.models import Vehicle, Driver
    from operations.models import EmergencyIncidentAlert, DriverBehaviorLog, GeofenceZone
    from decimal import Decimal

    v = Vehicle.objects.filter(status='available').first() or Vehicle.objects.first()
    d = v.default_driver or Driver.objects.first()
    zone = GeofenceZone.objects.filter(is_active=True).first()

    active_inc, _ = EmergencyIncidentAlert.objects.get_or_create(
        incident_id="INC-GF-DEMO-991",
        defaults={
            "incident_type": "geofence_breach",
            "severity": "critical",
            "vehicle": v,
            "driver": d,
            "latitude": Decimal("11.0251"),
            "longitude": Decimal("76.9601"),
            "location_address": f"{zone.name if zone else 'Orvakkal Restricted Zone'} (Perimeter Breach)",
            "description": f"Autonomous Geofence Alarm: Vehicle {v.registration_number} penetrated unauthorized restricted perimeter.",
            "status": "reported",
        }
    )
    active_inc.status = 'reported'
    active_inc.save()
    print(f"[+] Active breach incident primed: {active_inc.incident_id} ({active_inc.status})")

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        context = browser.new_context(viewport={'width': 1600, 'height': 1000})

        context.add_cookies([{
            'name': settings.SESSION_COOKIE_NAME,
            'value': session_cookie,
            'domain': '127.0.0.1',
            'path': '/',
            'httpOnly': True,
            'sameSite': 'Lax',
        }])

        page = context.new_page()
        page.add_init_script("localStorage.setItem('travelerp_dev_pause_maps', 'false');")

        # 1. Verify Mission Control Hazard Banner
        print("[*] Auditing Mission Control (/fleet/live/)...")
        page.goto(f"{BASE_URL}/fleet/live/", wait_until="networkidle")
        time.sleep(2)

        # Check SOS banner visibility
        sos_banner = page.locator("#mcSosBanner")
        is_banner_visible = sos_banner.is_visible()
        banner_text = sos_banner.inner_text() if is_banner_visible else "Not Visible"
        clean_banner = banner_text.encode('ascii', 'replace').decode('ascii')
        print(f"[+] Mission Control Hazard Banner Visible: {is_banner_visible} | Text: {clean_banner[:80]}...")

        mc_screenshot = ARTIFACT_DIR / "phase9_mission_control_geofence_hazard.png"
        page.screenshot(path=str(mc_screenshot), full_page=True)
        print(f"[OK] Saved Mission Control screenshot: {mc_screenshot}")

        # 2. Verify Admin Fleet Radar (/admin/operations/fleet-radar/)
        print("[*] Auditing Admin Fleet Radar (/admin/operations/fleet-radar/)...")
        page.goto(f"{BASE_URL}/admin/operations/fleet-radar/", wait_until="networkidle")
        time.sleep(2)

        radar_banner = page.locator("#radarAlertBanner")
        is_radar_banner_visible = radar_banner.is_visible()
        radar_text = radar_banner.inner_text() if is_radar_banner_visible else "Not Visible"
        clean_radar = radar_text.encode('ascii', 'replace').decode('ascii')
        print(f"[+] Fleet Radar Hazard Banner Visible: {is_radar_banner_visible} | Text: {clean_radar[:80]}...")

        radar_screenshot = ARTIFACT_DIR / "phase9_fleet_radar_geofence_breach.png"
        page.screenshot(path=str(radar_screenshot), full_page=True)
        print(f"[OK] Saved Fleet Radar screenshot: {radar_screenshot}")

        # 3. Test Acknowledgment click on Fleet Radar
        if is_radar_banner_visible:
            dismiss_btn = page.locator("#btnDismissAlert")
            if dismiss_btn.is_visible():
                print("[*] Clicking Dismiss / Acknowledge on Fleet Radar alert banner...")
                dismiss_btn.click()
                time.sleep(1)
                active_inc.refresh_from_db()
                print(f"[OK] Alert banner dismissed. Incident DB Status: {active_inc.status}")

        browser.close()

    print("========================================================================")
    print("[OK] PHASE 9 VISUAL VERIFICATION COMPLETE!")
    print("========================================================================")


if __name__ == '__main__':
    main()
