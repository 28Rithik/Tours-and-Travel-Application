import os, sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
import django
django.setup()



from django.test import Client, RequestFactory
from django.contrib.auth import get_user_model
from django.contrib import admin
from unfold.admin import ModelAdmin as UnfoldModelAdmin, TabularInline as UnfoldTabularInline, StackedInline as UnfoldStackedInline

User = get_user_model()
admin_user = User.objects.filter(is_superuser=True).first()

client = Client()
client.force_login(admin_user)
rf = RequestFactory()

print("=" * 80)
print("🚀 RUNNING PHASE 4 COMPLETE END-TO-END VERIFICATION SUITE")
print("=" * 80)

phase4_apps = ['core', 'finance', 'finance_fleet', 'finance_treasury', 'fleet_commute', 'maintenance', 'maintenance_compliance']

# 1. Verify Unfold Inheritance
print("\n--- 1. VERIFYING UNFOLD INHERITANCE ACROSS ALL ADMINS & INLINES ---")
unfold_admins_count = 0
unfold_inlines_count = 0
inheritance_errors = []

for model, admin_obj in admin.site._registry.items():
    if model._meta.app_label in phase4_apps:
        if isinstance(admin_obj, UnfoldModelAdmin):
            unfold_admins_count += 1
        else:
            inheritance_errors.append(f"ModelAdmin {admin_obj.__class__.__name__} does not inherit from Unfold ModelAdmin!")
        
        # Check inlines
        for inline in getattr(admin_obj, 'inlines', []):
            if issubclass(inline, (UnfoldTabularInline, UnfoldStackedInline)):
                unfold_inlines_count += 1
            else:
                inheritance_errors.append(f"Inline {inline.__name__} in {admin_obj.__class__.__name__} does not inherit from Unfold Tabular/Stacked Inline!")

print(f"  [PASS] Verified {unfold_admins_count} Phase 4 ModelAdmins inherit from Unfold ModelAdmin.")
print(f"  [PASS] Verified {unfold_inlines_count} Phase 4 Inlines inherit from Unfold Tabular/Stacked Inline.")
assert not inheritance_errors, f"Inheritance errors: {inheritance_errors}"

# 2. Verify Changelists, Add Views, and Change Views
print("\n--- 2. VERIFYING ADMIN URLS (CHANGELISTS, ADD VIEWS & CHANGE VIEWS) ---")
passed_cl = 0
passed_add = 0
passed_ch = 0
url_errors = []

for model, admin_obj in admin.site._registry.items():
    app = model._meta.app_label
    if app not in phase4_apps:
        continue
    m_name = model._meta.model_name
    
    # Changelist
    cl_url = f'/admin/{app}/{m_name}/'
    r_cl = client.get(cl_url)
    if r_cl.status_code == 200:
        passed_cl += 1
    else:
        url_errors.append(f"Changelist {cl_url} returned {r_cl.status_code}")
        
    # Add view
    add_url = f'/admin/{app}/{m_name}/add/'
    req = rf.get(add_url)
    req.user = admin_user
    r_add = client.get(add_url)
    if r_add.status_code == 200:
        passed_add += 1
    elif r_add.status_code == 403 and not admin_obj.has_add_permission(req):
        passed_add += 1  # Read-only admin
    else:
        url_errors.append(f"Add view {add_url} returned {r_add.status_code}")
        
    # Change view (use object in admin's queryset)
    inst = admin_obj.get_queryset(req).first()
    if inst:
        ch_url = f'/admin/{app}/{m_name}/{inst.pk}/change/'
        r_ch = client.get(ch_url)
        if r_ch.status_code == 200:
            passed_ch += 1
        else:
            url_errors.append(f"Change view {ch_url} returned {r_ch.status_code}")

print(f"  [PASS] All {passed_cl} Changelist views returned HTTP 200 OK.")
print(f"  [PASS] All {passed_add} Add views verified (HTTP 200 or authorized 403).")
print(f"  [PASS] All {passed_ch} Change views verified with live DB records.")
assert not url_errors, f"URL errors: {url_errors}"

# 3. Verify Vehicle Status Toggle Endpoint
print("\n--- 3. VERIFYING VEHICLE STATUS TOGGLE ENDPOINT ---")
from core.models import Vehicle
test_v = Vehicle.objects.filter(status='available').first()
if not test_v:
    test_v = Vehicle.objects.first()
    test_v.status = 'available'
    test_v.save()

resp_toggle = client.post(f'/admin/core/vehicle/{test_v.id}/toggle-status/')
assert resp_toggle.status_code == 200, f"Toggle failed: {resp_toggle.status_code}"
toggle_data = resp_toggle.json()
assert toggle_data.get('success') is True, f"Toggle not successful: {toggle_data}"
assert toggle_data.get('status') == 'inactive'

# Toggle back
resp_toggle_back = client.post(f'/admin/core/vehicle/{test_v.id}/toggle-status/')
assert resp_toggle_back.status_code == 200
assert resp_toggle_back.json().get('status') == 'available'
print("  [PASS] Vehicle status toggle verified: available <-> inactive transitions return clean JSON.")

# 4. Verify Autocomplete Filtering View
print("\n--- 4. VERIFYING PARTY-FILTERED AUTOCOMPLETE VIEW ---")
from core.models import Party
p = Party.objects.filter(party_type='customer').first() or Party.objects.first()
auto_url = f'/admin/autocomplete/?app_label=finance_treasury&model_name=payment&field_name=booking&party_id={p.id}'
resp_auto = client.get(auto_url)
assert resp_auto.status_code == 200, f"Autocomplete returned {resp_auto.status_code}"
auto_data = resp_auto.json()
assert 'results' in auto_data, "Autocomplete JSON missing results key"
print(f"  [PASS] PartyFilteredAutocompleteView returned {len(auto_data['results'])} party-filtered records.")

# 5. Verify HTMX Live Partials for Phase 4
print("\n--- 5. VERIFYING HTMX LIVE PARTIAL ENDPOINTS ---")
from django.urls import reverse
# 5.1 Party ledger summary partial
ledger_url = reverse('htmx_operations:party-ledger-summary') + f'?party={p.id}'
resp_ledger = client.get(ledger_url)
assert resp_ledger.status_code == 200, f"Party ledger partial returned {resp_ledger.status_code}"
assert 'Closing Ledger Balance' in resp_ledger.content.decode('utf-8')
print("  [PASS] HTMX Party Ledger Summary partial rendered successfully.")

# 5.2 Vehicle compliance gate partial
gate_url = reverse('htmx_operations:trip-vehicle-gate') + f'?vehicle={test_v.id}'
resp_gate = client.get(gate_url)
assert resp_gate.status_code == 200, f"Vehicle compliance gate returned {resp_gate.status_code}"
assert 'vehicle-compliance-htmx-container' in resp_gate.content.decode('utf-8')
print("  [PASS] HTMX Vehicle Compliance Gate partial rendered successfully.")



print("\n" + "=" * 80)
print("🎉 PHASE 4 FULL SUITE: 100% COMPLETE, INTEGRATED, AND VERIFIED!")
print("=" * 80)
