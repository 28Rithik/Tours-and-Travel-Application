import os
import sys
import time

# Configure UTF-8 for console output on Windows
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
django.setup()

from packages.models import Package, PackageTemplate

def verify_file_syntax():
    print("=== 1. Checking CSS and JS Syntax & Braces ===")
    css_path = os.path.join(BASE_DIR, 'packages', 'static', 'packages', 'css', 'package_admin_custom.css')
    js_path = os.path.join(BASE_DIR, 'packages', 'static', 'packages', 'js', 'package_dynamic_form.js')

    with open(css_path, 'r', encoding='utf-8') as f:
        css = f.read()
    with open(js_path, 'r', encoding='utf-8') as f:
        js = f.read()

    css_open, css_close = css.count('{'), css.count('}')
    print(f"CSS braces: {css_open} open, {css_close} close.")
    assert css_open == css_close, f"CSS brace mismatch: {css_open} != {css_close}"

    # Use tokenizer to check braces and parens outside strings/comments
    i = 0
    n = len(js)
    paren_stack = []
    brace_stack = []
    line = 1
    while i < n:
        ch = js[i]
        if ch == '\n':
            line += 1
            i += 1
            continue
        if ch == '/' and i + 1 < n and js[i+1] == '/':
            while i < n and js[i] != '\n':
                i += 1
            continue
        if ch == '/' and i + 1 < n and js[i+1] == '*':
            i += 2
            while i + 1 < n and not (js[i] == '*' and js[i+1] == '/'):
                if js[i] == '\n':
                    line += 1
                i += 1
            i += 2
            continue
        if ch in ('"', "'"):
            quote = ch
            i += 1
            while i < n and js[i] != quote:
                if js[i] == '\\':
                    i += 2
                else:
                    if js[i] == '\n':
                        line += 1
                    i += 1
            i += 1
            continue
        if ch == '`':
            i += 1
            while i < n and js[i] != '`':
                if js[i] == '\\':
                    i += 2
                else:
                    if js[i] == '\n':
                        line += 1
                    i += 1
            i += 1
            continue
        if ch == '(':
            paren_stack.append(line)
        elif ch == ')':
            assert paren_stack, f"Extra ) at line {line}"
            paren_stack.pop()
        elif ch == '{':
            brace_stack.append(line)
        elif ch == '}':
            assert brace_stack, f"Extra }} at line {line}"
            brace_stack.pop()
        i += 1

    assert not paren_stack, f"Unclosed parens at lines: {paren_stack}"
    assert not brace_stack, f"Unclosed braces at lines: {brace_stack}"
    assert 'applyCategoryDefaults' in js, "applyCategoryDefaults function missing from JS"
    print("✅ CSS & JS static syntax passed tokenizer integrity check!")

def verify_models_deduplication():
    print("\n=== 2. Checking Category Deduplication in Models ===")
    categories_dict = dict(Package.CATEGORIES)
    print(f"Total categories in Package: {len(categories_dict)}")
    for k, v in Package.CATEGORIES:
        print(f"  - {k}: {v}")

    assert 'pilgrimage' not in categories_dict, "Duplicate 'pilgrimage' category should be removed!"
    assert 'hill_station' in categories_dict, "'hill_station' category must exist!"
    assert 'holiday' in categories_dict, "'holiday' category must exist!"
    assert 'Hill Station' in categories_dict['hill_station'], "'hill_station' label must reference Hill Station"
    assert 'Hill Station' not in categories_dict['holiday'], "'holiday' label must NOT contain duplicate 'Hill Station'!"
    assert 'Leisure' in categories_dict['holiday'], "'holiday' label should specify Leisure & Beach"
    print("✅ Model category deduplication verified!")

def run_playwright_e2e():
    print("\n=== 3. Running Headless Playwright Browser Test ===")
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Playwright not available, skipping browser test.")
        return

    with sync_playwright() as p:
        browser = p.chromium.launch(channel='msedge', headless=True)
        context = browser.new_context(viewport={'width': 1400, 'height': 900})
        page = context.new_page()

        page.on('console', lambda msg: print(f"Browser Console [{msg.type}]: {msg.text}"))
        page.on('pageerror', lambda err: print(f"Browser Page Error: {err}"))

        # 1. Inject Django session cookie to authenticate directly
        from django.test import Client
        c = Client()
        c.login(username='rithik', password='rithik123')
        session_cookie = c.cookies['sessionid'].value
        context.add_cookies([{'name': 'sessionid', 'value': session_cookie, 'domain': '127.0.0.1', 'path': '/'}])

        print("Navigating directly to add package page...", flush=True)
        page.goto('http://127.0.0.1:8000/admin/packages/package/add/', wait_until='domcontentloaded')
        page.wait_for_timeout(1000)

        print(f"Current page URL: {page.url}", flush=True)

        # Check template field removal
        print("Checking that template field has been cleanly removed from Step 1...")
        template_input = page.locator('#id_template')
        assert template_input.count() == 0, "Template field was NOT removed from PackageAdmin fieldsets!"
        print("✅ Template field successfully removed from Step 1.")

        # Test Preset 1: Devotional
        print("\nTesting Preset 1: Devotional...")
        page.click('#btn-preset-devotional')
        page.wait_for_timeout(400)
        cat_val = page.locator('#id_category').input_value()
        nights = page.locator('#id_duration_nights').input_value()
        days = page.locator('#id_duration_days').input_value()
        ap = page.locator('#id_price_with_food').input_value()
        min_pax = page.locator('#id_min_pax').input_value()
        is_dev = page.locator('#id_is_devotional').is_checked()
        print(f"Devotional: cat={cat_val}, nights={nights}, days={days}, AP={ap}, min_pax={min_pax}, is_devotional={is_dev}")
        assert cat_val == 'devotional', f"Expected devotional, got {cat_val}"
        assert nights == '3' and days == '4', f"Expected 3N/4D, got {nights}N/{days}D"
        assert is_dev is True, "Expected is_devotional to be checked"
        assert float(ap) > 0, f"Expected non-zero AP price, got {ap}"
        print("✅ Preset 1 (Devotional) passed.")

        # Test Preset 2: College IV
        print("\nTesting Preset 2: College IV...")
        page.click('#btn-preset-iv')
        page.wait_for_timeout(400)
        cat_val = page.locator('#id_category').input_value()
        nights = page.locator('#id_duration_nights').input_value()
        days = page.locator('#id_duration_days').input_value()
        min_pax = page.locator('#id_min_pax').input_value()
        staff = page.locator('#id_complementary_staff_count').input_value()
        has_dj = page.locator('#id_has_campfire_dj').is_checked()
        print(f"College IV: cat={cat_val}, nights={nights}, days={days}, min_pax={min_pax}, staff={staff}, has_dj={has_dj}")
        assert cat_val == 'college_iv', f"Expected college_iv, got {cat_val}"
        assert nights == '4' and days == '5', f"Expected 4N/5D, got {nights}N/{days}D"
        assert min_pax == '50', f"Expected 50 pax, got {min_pax}"
        assert staff == '2', f"Expected 2 staff, got {staff}"
        assert has_dj is True, "Expected DJ campfire checked"
        print("✅ Preset 2 (College IV) passed.")

        # Test Preset 3: Intl Tour
        print("\nTesting Preset 3: Intl Tour...")
        page.click('#btn-preset-intl')
        page.wait_for_timeout(400)
        cat_val = page.locator('#id_category').input_value()
        nights = page.locator('#id_duration_nights').input_value()
        days = page.locator('#id_duration_days').input_value()
        is_intl = page.locator('#id_is_international').is_checked()
        visa = page.locator('#id_visa_required').is_checked()
        curr = page.locator('#id_currency_code').input_value()
        print(f"Intl Tour: cat={cat_val}, nights={nights}, days={days}, is_intl={is_intl}, visa={visa}, currency={curr}")
        assert cat_val == 'international', f"Expected international, got {cat_val}"
        assert is_intl is True, "Expected is_international checked"
        assert visa is True, "Expected visa_required checked"
        assert curr == 'AED', f"Expected AED, got {curr}"
        print("✅ Preset 3 (Intl Tour) passed.")

        # Test Preset 4: Hill Station
        print("\nTesting Preset 4: Hill Station...")
        page.click('#btn-preset-holiday')
        page.wait_for_timeout(400)
        cat_val = page.locator('#id_category').input_value()
        nights = page.locator('#id_duration_nights').input_value()
        days = page.locator('#id_duration_days').input_value()
        min_pax = page.locator('#id_min_pax').input_value()
        meal = page.locator('#id_meal_plan').input_value()
        print(f"Hill Station: cat={cat_val}, nights={nights}, days={days}, min_pax={min_pax}, meal={meal}")
        assert cat_val == 'hill_station', f"Expected hill_station, got {cat_val}"
        assert nights == '2' and days == '3', f"Expected 2N/3D, got {nights}N/{days}D"
        assert min_pax == '6', f"Expected 6 pax, got {min_pax}"
        assert meal == 'MAP', f"Expected MAP meal plan, got {meal}"
        print("✅ Preset 4 (Hill Station) passed.")

        # Test Preset 5: 1-Day Local
        print("\nTesting Preset 5: 1-Day Local...")
        page.click('#btn-preset-local')
        page.wait_for_timeout(400)
        cat_val = page.locator('#id_category').input_value()
        nights = page.locator('#id_duration_nights').input_value()
        days = page.locator('#id_duration_days').input_value()
        pricing_type = page.locator('#id_pricing_type').input_value()
        base_p = page.locator('#id_base_price').input_value()
        print(f"1-Day Local: cat={cat_val}, nights={nights}, days={days}, pricing_type={pricing_type}, base={base_p}")
        assert cat_val == 'local_tour', f"Expected local_tour, got {cat_val}"
        assert nights == '0' and days == '1', f"Expected 0N/1D, got {nights}N/{days}D"
        assert pricing_type == 'vehicle_rate', f"Expected vehicle_rate, got {pricing_type}"
        assert float(base_p) > 0, f"Expected non-zero base price, got {base_p}"
        print("✅ Preset 5 (1-Day Local) passed.")

        # Test dropdown selection directly
        print("\nTesting Dropdown Selection: devotional...")
        page.select_option('#id_category', 'devotional')
        page.dispatch_event('#id_category', 'change')
        page.wait_for_timeout(400)
        assert page.locator('#id_duration_nights').input_value() == '3'
        assert page.locator('#id_duration_days').input_value() == '4'
        assert page.locator('#id_is_devotional').is_checked() is True
        print("✅ Dropdown selection adaptively updated form across all steps.")

        # Capture step screenshots
        artifact_dir = os.path.join(os.environ.get('USERPROFILE', ''), '.gemini', 'antigravity-ide', 'brain', '12e9440a-ec76-4489-aa28-9f0807948a00')
        os.makedirs(artifact_dir, exist_ok=True)
        shot_path = os.path.join(artifact_dir, 'step1_preset_verified.png')
        page.screenshot(path=shot_path, full_page=False)
        print(f"Saved verified screenshot to {shot_path}")

        browser.close()
        print("\n🎉 ALL E2E PLAYWRIGHT TESTS PASSED SUCCESSFULLY!")

if __name__ == '__main__':
    verify_file_syntax()
    verify_models_deduplication()
    run_playwright_e2e()
