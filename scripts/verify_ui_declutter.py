import os
import sys

# Configure UTF-8 for console output on Windows
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from packages.models import Package, PackageTemplate

def verify_css_and_js_integrity():
    print("--- 1. Testing CSS & JS File Integrity ---")
    css_path = os.path.join('packages', 'static', 'packages', 'css', 'package_admin_custom.css')
    js_path = os.path.join('packages', 'static', 'packages', 'js', 'package_dynamic_form.js')
    
    assert os.path.exists(css_path), f"CSS file missing: {css_path}"
    assert os.path.exists(js_path), f"JS file missing: {js_path}"
    
    with open(css_path, 'r', encoding='utf-8') as f:
        css_content = f.read()
    
    with open(js_path, 'r', encoding='utf-8') as f:
        js_content = f.read()
        
    # Check CSS brackets
    open_c = css_content.count('{')
    close_c = css_content.count('}')
    print(f"CSS braces: {open_c} open, {close_c} close.")
    assert open_c == close_c, f"Mismatched CSS braces: {open_c} != {close_c}"
    
    # Check essential CSS classes
    assert '.sg-unified-toolbar' in css_content, "Missing .sg-unified-toolbar in CSS"
    assert '.sg-help-hidden' in css_content, "Missing .sg-help-hidden in CSS"
    assert '.sg-tooltip-badge' in css_content, "Missing .sg-tooltip-badge in CSS"
    assert '#sg-margin-caret' in css_content, "Missing #sg-margin-caret in CSS"
    print("✅ CSS file passed integrity checks.")
    
    # Check JS brackets and parentheses
    open_b = js_content.count('{')
    close_b = js_content.count('}')
    open_p = js_content.count('(')
    close_p = js_content.count(')')
    print(f"JS braces: {open_b} open, {close_b} close. Parentheses: {open_p} open, {close_p} close.")
    assert open_b == close_b, f"Mismatched JS braces: {open_b} != {close_b}"
    assert open_p == close_p, f"Mismatched JS parentheses: {open_p} != {close_p}"
    
    # Check essential JS automation
    assert 'sg-unified-toolbar' in js_content, "Missing sg-unified-toolbar in JS"
    assert 'sg-intel-collapsible-content' in js_content, "Missing sg-intel-collapsible-content in JS"
    assert 'streamlineFieldHelpTexts' in js_content, "Missing streamlineFieldHelpTexts in JS"
    assert 'autoGenSmartPackageCode' in js_content, "Missing autoGenSmartPackageCode in JS"
    assert 'autoDetectDurationFromName' in js_content, "Missing autoDetectDurationFromName in JS"
    assert '/packages/api/template/' in js_content, "Missing template api call in JS"
    print("✅ JS file passed integrity checks.")

def verify_api_template():
    print("\n--- 2. Testing API Template Info Endpoint ---")
    user, _ = User.objects.get_or_create(username='admin_test', defaults={'is_staff': True, 'is_superuser': True})
    client = Client()
    client.force_login(user)
    
    # Get or create a template
    tmpl, _ = PackageTemplate.objects.get_or_create(
        name="Kerala Backwaters & Munnar Circuit",
        defaults={
            'destination': 'Kerala',
            'category': 'holiday',
            'duration_days': 4,
            'duration_nights': 3,
            'base_price': 5500.0,
            'description': 'Scenic hill station and backwater cruise tour.'
        }
    )
    
    resp = client.get(f'/packages/api/template/{tmpl.id}/info/')
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    data = resp.json()
    assert data['success'] is True, "API did not return success: True"
    assert data['name'] == tmpl.name, "Template name mismatch"
    assert data['duration_days'] == 4, "Duration days mismatch"
    print(f"✅ Template API endpoint works perfectly: {data['name']} (ID {data['id']})")

def verify_admin_change_form():
    print("\n--- 3. Testing Package Admin Change Form Rendering ---")
    user, _ = User.objects.get_or_create(username='admin_test', defaults={'is_staff': True, 'is_superuser': True})
    client = Client()
    client.force_login(user)
    
    pkg = Package.objects.first()
    if not pkg:
        print("No package found, skipping form change test.")
        return
        
    resp = client.get(f'/admin/packages/package/{pkg.id}/change/')
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    html = resp.content.decode('utf-8')
    assert 'package_dynamic_form.js' in html, "package_dynamic_form.js not loaded in change form"
    assert 'package_admin_custom.css' in html, "package_admin_custom.css not loaded in change form"
    print(f"✅ Package change form rendered 200 OK with custom CSS & JS assets loaded.")

if __name__ == '__main__':
    verify_css_and_js_integrity()
    verify_api_template()
    verify_admin_change_form()
    print("\n🎉 ALL UI DECLUTTER & SMART FORM ENTRY CHECKS PASSED!")
