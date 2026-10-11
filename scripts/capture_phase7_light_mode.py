import os
import sys
from pathlib import Path

BASE_DIR = Path(r"c:\Users\rithi\Documents\Documents Project Intership and Course\Projects\Rag chatbot\Tours and Travel Application")
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
import django
django.setup()

from django.contrib.auth.models import User
import django.contrib.auth
from django.conf import settings
from importlib import import_module
from playwright.sync_api import sync_playwright

ARTIFACT_DIR = Path(r"C:\Users\rithi\.gemini\antigravity-ide\brain\38a90fa8-4427-4e87-a010-66c145b9a064")

user = User.objects.filter(is_superuser=True).first()
if not user:
    user = User.objects.create_superuser('admin_audit', 'admin@example.com', 'auditpass123')

engine = import_module(settings.SESSION_ENGINE)
session = engine.SessionStore()
session[django.contrib.auth.SESSION_KEY] = str(user.pk)
session[django.contrib.auth.BACKEND_SESSION_KEY] = 'django.contrib.auth.backends.ModelBackend'
session[django.contrib.auth.HASH_SESSION_KEY] = user.get_session_auth_hash()
session.save()
session_key = session.session_key

from fleet_commute.models import CommuterBoardingPass
bp = CommuterBoardingPass.objects.first()
pass_token = bp.pass_token if bp else "BP-DEMO-SAMPLE"

pages_to_capture = [
    ("roster_dispatcher_light_mode.png", "http://127.0.0.1:8000/commute/roster-dispatcher/"),
    ("sla_penalties_light_mode.png", "http://127.0.0.1:8000/commute/sla-penalties/"),
    ("women_safety_light_mode.png", "http://127.0.0.1:8000/commute/women-safety/"),
]

if bp:
    pages_to_capture.append(("live_bus_tracking_light_mode.png", f"http://127.0.0.1:8000/commute/track/{pass_token}/"))

print(f"Starting Phase 7 captures with {len(pages_to_capture)} pages...")

with sync_playwright() as p:
    try:
        browser = p.chromium.launch(channel="msedge", headless=True)
    except Exception:
        browser = p.chromium.launch(channel="chrome", headless=True)

    context = browser.new_context(viewport={"width": 1920, "height": 1080})
    context.add_cookies([{
        "name": settings.SESSION_COOKIE_NAME,
        "value": session_key,
        "domain": "127.0.0.1",
        "path": "/",
        "httpOnly": True,
        "sameSite": "Lax",
    }])

    for fname, url in pages_to_capture:
        page = context.new_page()
        page.add_init_script("localStorage.setItem('theme', 'light'); localStorage.setItem('_x_adminTheme', 'light');")
        try:
            resp = page.goto(url, wait_until="networkidle", timeout=25000)
            print(f"Loaded {url} with status {resp.status if resp else 'N/A'}")
            page.wait_for_timeout(1000)
            out_path = ARTIFACT_DIR / fname
            page.screenshot(path=str(out_path), full_page=False)
            print(f"Saved: {out_path} ({out_path.stat().st_size} bytes)")
        except Exception as e:
            print(f"Error capturing {url}: {e}")
        finally:
            page.close()

    browser.close()
print("Phase 7 screenshot captures completed!")
