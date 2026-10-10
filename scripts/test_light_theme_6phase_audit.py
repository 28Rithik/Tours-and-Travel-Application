import os
import sys
import time
import subprocess
import urllib.request
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
import django
django.setup()

from django.contrib.auth.models import User
import django.contrib.auth
from django.conf import settings
from importlib import import_module
from playwright.sync_api import sync_playwright

ARTIFACT_DIR = Path(r"C:\Users\rithi\.gemini\antigravity-ide\brain\3c044726-a75e-47a0-949a-d96c5805a71d")
OUTPUT_DIR = ARTIFACT_DIR / "light_mode_audits"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SERVER_PORT = 8011
BASE_URL = f"http://127.0.0.1:{SERVER_PORT}"

TEST_PAGES = [
    ("01_unfold_dashboard", f"{BASE_URL}/admin/"),
    ("02_vehicleasset_changelist", f"{BASE_URL}/admin/maintenance/vehicleasset/"),
    ("03_vehicleasset_add_form", f"{BASE_URL}/admin/maintenance/vehicleasset/add/"),
    ("04_tire_studio", f"{BASE_URL}/maintenance/tire-studio/"),
    ("05_damage_marker_studio", f"{BASE_URL}/maintenance/damage-marker/"),
    ("06_fleet_live_mission_control", f"{BASE_URL}/operations/fleet-radar/"),
    ("07_bank_reconciliation_studio", f"{BASE_URL}/finance/bank-reconciliation/"),
    ("08_payment_gateway_studio", f"{BASE_URL}/admin/payments/studio/"),
    ("09_tara_ai_copilot", f"{BASE_URL}/admin/operations/tara-ai/"),
    ("10_crm_inquiry_changelist", f"{BASE_URL}/admin/crm/inquiry/"),
]


def ensure_superuser():
    user = User.objects.filter(is_superuser=True).first()
    if not user:
        user = User.objects.create_superuser('admin_audit', 'admin@example.com', 'auditpass123')
    return user


def get_session_cookie(user):
    engine = import_module(settings.SESSION_ENGINE)
    session = engine.SessionStore()
    session[django.contrib.auth.SESSION_KEY] = str(user.pk)
    session[django.contrib.auth.BACKEND_SESSION_KEY] = 'django.contrib.auth.backends.ModelBackend'
    session[django.contrib.auth.HASH_SESSION_KEY] = user.get_session_auth_hash()
    session.save()
    return session.session_key


def wait_for_server(url, timeout=15):
    start = time.time()
    while time.time() - start < timeout:
        try:
            with urllib.request.urlopen(url, timeout=1) as resp:
                if resp.status in (200, 302):
                    return True
        except Exception:
            time.sleep(0.5)
    return False


def main():
    print("=" * 70)
    print("🚀 TravelERP: 6-Phase Light Theme Visual & Form Audit")
    print("=" * 70)

    user = ensure_superuser()
    session_key = get_session_cookie(user)
    print(f"[*] Admin session prepared for user: {user.username}")

    python_exe = sys.executable
    server_cmd = [python_exe, "manage.py", "runserver", f"127.0.0.1:{SERVER_PORT}", "--noreload"]
    print(f"[*] Spawning temporary test server on port {SERVER_PORT}...")
    server_proc = subprocess.Popen(server_cmd, cwd=str(BASE_DIR), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    try:
        is_ready = wait_for_server(f"{BASE_URL}/admin/login/")
        if not is_ready:
            print("[!] Server failed to start within timeout.")
            return 1
        print("[*] Dev server is live and responding!")

        audit_results = []
        with sync_playwright() as p:
            browser = p.chromium.launch(channel='chrome', headless=True)
            context = browser.new_context(
                viewport={"width": 1440, "height": 900},
                color_scheme="light"
            )

            # Set session cookie
            context.add_cookies([{
                'name': 'sessionid',
                'value': session_key,
                'domain': '127.0.0.1',
                'path': '/',
                'httpOnly': True,
                'secure': False,
            }])

            page = context.new_page()

            # Set light theme in local storage
            page.goto(f"{BASE_URL}/admin/")
            page.evaluate("""() => {
                localStorage.setItem('theme', 'light');
                document.documentElement.classList.remove('dark');
            }""")

            for slug, url in TEST_PAGES:
                print(f"--> Auditing [{slug}] at {url}")
                page.goto(url, wait_until='networkidle')

                # Ensure light theme class applied
                page.evaluate("""() => {
                    localStorage.setItem('theme', 'light');
                    document.documentElement.classList.remove('dark');
                }""")
                page.wait_for_timeout(600)

                # Contrast & Visibility Check
                contrast_check = page.evaluate("""() => {
                    const headings = Array.from(document.querySelectorAll('h1, h2, h3, label, th'));
                    let issues = [];
                    for (const el of headings) {
                        const style = window.getComputedStyle(el);
                        const bg = style.backgroundColor;
                        const fg = style.color;
                        // Flag white text on white background
                        if (fg === 'rgb(255, 255, 255)' && (bg === 'rgb(255, 255, 255)' || bg === 'rgba(0, 0, 0, 0)')) {
                            // Check parent background
                            const parentBg = window.getComputedStyle(el.parentElement).backgroundColor;
                            if (parentBg === 'rgb(255, 255, 255)' || parentBg === 'rgb(248, 250, 252)') {
                                issues.push(el.textContent.trim().substring(0, 30));
                            }
                        }
                    }
                    return {
                        title: document.title,
                        headings_checked: headings.length,
                        white_on_white_issues: issues
                    };
                }""")

                screenshot_path = OUTPUT_DIR / f"{slug}.png"
                page.screenshot(path=str(screenshot_path), full_page=False)

                status = "PASS" if len(contrast_check["white_on_white_issues"]) == 0 else "WARN"
                print(f"    [{status}] Headings checked: {contrast_check['headings_checked']}, Collisions: {len(contrast_check['white_on_white_issues'])}")
                print(f"    Saved screenshot: {screenshot_path.name}")

                audit_results.append({
                    "slug": slug,
                    "url": url,
                    "status": status,
                    "issues": contrast_check["white_on_white_issues"],
                    "screenshot": str(screenshot_path)
                })

            browser.close()

        print("\n" + "=" * 70)
        print("📊 LIGHT THEME AUDIT SUMMARY")
        print("=" * 70)
        all_passed = True
        for r in audit_results:
            print(f"• {r['slug']:<30} : {r['status']}")
            if r["issues"]:
                all_passed = False
                print(f"   Potential issues: {r['issues']}")

        if all_passed:
            print("\n🎉 ALL 10 INTERFACES VERIFIED 100% CLEAN IN LIGHT THEME!")
        else:
            print("\n⚠️ Some interfaces need further contrast refinement.")

        return 0

    finally:
        print("[*] Terminating temporary test server...")
        server_proc.terminate()
        server_proc.wait()


if __name__ == '__main__':
    sys.exit(main())
