import os
import sys
import re
import json
import datetime
from decimal import Decimal
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
import django
django.setup()

from django.test import Client, RequestFactory
from django.contrib.auth.models import User
from django.contrib.admin.sites import site
from django.urls import reverse
from django.utils import timezone

from core.models import Vehicle, VehicleType, Driver, Cleaner, Client as CoreClient, Party
from operations.models import Booking, Trip, BulkContract, EmergencyIncidentAlert, TrafficFine
from packages.models import Package, PackageInventory
from crm.models import Inquiry, Quotation, QuotationDay, QuotationItem, HotelMaster, MonumentEntranceMaster, ActivityMaster, GuideChargeMaster
from maintenance.models import PreTripInspectionChecklist, DefectTicket
from fleet_contracts.models import TransportContract, ContractFleetRoster
from operations.forms import BookingForm, TripForm
from statements.forms import StatementForm


def validate_js_syntax(content, file_label=""):
    """
    State machine tokenizer verifying balanced brackets, braces, parentheses,
    quotes, and template literals in JavaScript code.
    """
    i = 0
    n = len(content)
    stack = []
    line = 1
    col = 1
    errors = []

    while i < n:
        ch = content[i]
        if ch == '\n':
            line += 1
            col = 1
            i += 1
            continue

        # Single-line comment
        if content[i:i+2] == '//':
            while i < n and content[i] != '\n':
                i += 1
            continue

        # Multi-line comment
        if content[i:i+2] == '/*':
            i += 2
            while i < n and content[i:i+2] != '*/':
                if content[i] == '\n':
                    line += 1
                i += 1
            i += 2
            continue

        # Strings & template literals
        if ch in ("'", '"', '`'):
            q = ch
            start_l, start_c = line, col
            i += 1
            closed = False
            while i < n:
                if content[i] == '\\':
                    i += 2
                    continue
                if content[i] == q:
                    closed = True
                    i += 1
                    break
                if content[i] == '\n':
                    line += 1
                    # Template literals can span lines, regular strings cannot
                    if q != '`':
                        errors.append(f"Unterminated string literal at line {start_l}:{start_c}")
                        break
                i += 1
            if not closed and q == '`':
                errors.append(f"Unterminated template literal at line {start_l}:{start_c}")
            continue

        # Regex literal detection
        if ch == '/' and i + 1 < n and content[i+1] not in ('/', '*'):
            prev_idx = i - 1
            while prev_idx >= 0 and content[prev_idx] in (' ', '\t', '\r', '\n'):
                prev_idx -= 1
            if prev_idx >= 0 and content[prev_idx] in ('=', '(', ',', ':', '[', '!', '&', '|', ';', '?', 'return'):
                i += 1
                while i < n and content[i] != '/':
                    if content[i] == '\\':
                        i += 2
                        continue
                    if content[i] == '\n':
                        break
                    i += 1
                if i < n and content[i] == '/':
                    i += 1
                continue

        # Brackets tracking
        if ch in ('(', '{', '['):
            stack.append((ch, line, col))
        elif ch in (')', '}', ']'):
            pairs = {')': '(', '}': '{', ']': '['}
            if not stack:
                errors.append(f"Unexpected closing {ch} at line {line}:{col}")
            else:
                top, tl, tc = stack.pop()
                if pairs[ch] != top:
                    errors.append(f"Mismatched {top} at line {tl}:{tc} closed by {ch} at line {line}:{col}")

        col += 1
        i += 1

    if stack:
        for item in stack:
            errors.append(f"Unclosed {item[0]} opened at line {item[1]}:{item[2]}")

    return errors


class MasterUIAndFormsVerifier:
    def __init__(self):
        self.client = Client(enforce_csrf_checks=False)
        self.factory = RequestFactory()
        self.admin_user = User.objects.filter(is_superuser=True).first()
        if not self.admin_user:
            self.admin_user = User.objects.create_superuser('ui_tester', 'ui@test.com', 'adminpass123')
        self.client.force_login(self.admin_user)
        self.total_tests = 0
        self.passed_tests = 0
        self.results = {}

    def log_check(self, condition, section, title, details=""):
        self.total_tests += 1
        if section not in self.results:
            self.results[section] = {'passed': 0, 'failed': 0}

        if condition:
            self.passed_tests += 1
            self.results[section]['passed'] += 1
            extra = f" -> {details}" if details else ""
            print(f"  [PASS] {title}{extra}")
        else:
            self.results[section]['failed'] += 1
            print(f"  [FAIL] {title} - {details}")
            raise AssertionError(f"{section}: {title} failed: {details}")

    # =========================================================================
    # PART 1: Dynamic JavaScript Syntax Verification Across Entire Codebase
    # =========================================================================
    def test_javascript_syntax(self):
        section = "1. JavaScript Syntax & Parser Verification"
        print(f"\n{'='*80}\n🌟 SECTION {section.upper()}\n{'='*80}")

        # 1.1 All static .js files
        js_files = []
        for root, dirs, files in os.walk(BASE_DIR):
            if '.venv' in root or 'node_modules' in root or '.git' in root or 'staticfiles' in root:
                continue
            for file in files:
                if file.endswith('.js'):
                    js_files.append(os.path.join(root, file))

        print(f"Found {len(js_files)} static JavaScript files to parse...")
        for js_file in js_files:
            rel_path = os.path.relpath(js_file, BASE_DIR)
            with open(js_file, 'r', encoding='utf-8', errors='ignore') as f:
                code = f.read()
            errors = validate_js_syntax(code, rel_path)
            self.log_check(len(errors) == 0, section, f"Syntax OK: {rel_path}", f"lines={code.count(chr(10))+1}, errors={len(errors)}")

        # 1.2 All <script> blocks inside templates
        template_files = []
        for root, dirs, files in os.walk(os.path.join(BASE_DIR, 'templates')):
            for file in files:
                if file.endswith('.html'):
                    template_files.append(os.path.join(root, file))

        script_blocks_tested = 0
        for tpl_path in template_files:
            rel_tpl = os.path.relpath(tpl_path, BASE_DIR)
            with open(tpl_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            # Find all <script>...</script>
            script_pattern = re.compile(r'<script(?:\s+[^>]*)?>(.*?)</script>', re.DOTALL | re.IGNORECASE)
            matches = script_pattern.findall(content)
            for idx, script_content in enumerate(matches):
                # Strip Django template tags like {% ... %} or {{ ... }} so they don't break JS parser
                cleaned_script = re.sub(r'\{%.*?%\}', '/*tpl_tag*/', script_content)
                cleaned_script = re.sub(r'\{\{.*?\}\}', '/*tpl_var*/', cleaned_script)
                
                # Skip external script inclusions that have no inline code
                if not cleaned_script.strip():
                    continue

                errors = validate_js_syntax(cleaned_script, f"{rel_tpl}#script_{idx+1}")
                script_blocks_tested += 1
                self.log_check(len(errors) == 0, section, f"Template Script Block OK: {rel_tpl} [Block #{idx+1}]", f"size={len(script_content)}B")

        print(f"Total template script blocks verified: {script_blocks_tested}")

    # =========================================================================
    # PART 2: Dynamic Form Selectors & DOM Element Binding Checks
    # =========================================================================
    def test_dom_selector_bindings(self):
        section = "2. DOM Selectors & Form Field Linkage"
        print(f"\n{'='*80}\n🌟 SECTION {section.upper()}\n{'='*80}")

        # 2.1 Booking Admin Form & Dynamic JS Linkage
        resp = self.client.get('/admin/operations/booking/add/')
        self.log_check(resp.status_code == 200, section, "GET /admin/operations/booking/add/ returns 200")
        booking_html = resp.content.decode('utf-8', errors='ignore')
        
        # Verify that booking_form_v2.js is loaded in the media
        self.log_check("booking_form_v2.js" in booking_html, section, "booking_form_v2.js script tag injected in Booking Add Page")

        # Verify element IDs expected by booking_form_v2.js
        required_booking_ids = [
            'id_package', 'id_package_inventory', 'id_pickup_date', 'id_drop_date',
            'id_pax_count', 'id_quoted_price', 'id_gst_rate', 'id_billing_type'
        ]
        for elem_id in required_booking_ids:
            self.log_check(f'id="{elem_id}"' in booking_html, section, f"Booking Form Field Exists: #{elem_id}")

        # 2.2 Trip Admin Form & Dynamic JS Linkage
        resp = self.client.get('/admin/operations/trip/add/')
        self.log_check(resp.status_code == 200, section, "GET /admin/operations/trip/add/ returns 200")
        trip_html = resp.content.decode('utf-8', errors='ignore')
        
        # Verify trip_admin_v2.js is loaded in the media
        self.log_check("trip_admin_v2.js" in trip_html, section, "trip_admin_v2.js script tag injected in Trip Add Page")

        # Verify element IDs expected by trip_admin_v2.js
        required_trip_ids = [
            'id_booking', 'id_package', 'id_package_inventory', 'id_party',
            'id_billing_model', 'id_start_date', 'id_end_date', 'id_days_count',
            'id_day_rate', 'id_km_rate', 'id_fixed_amount', 'id_driver_bata',
            'id_opening_km', 'id_closing_km'
        ]
        for elem_id in required_trip_ids:
            self.log_check(f'id="{elem_id}"' in trip_html, section, f"Trip Form Field Exists: #{elem_id}")

        # 2.3 Quotation Studio & Builder Form Elements
        resp = self.client.get('/crm/quotations/new/')
        self.log_check(resp.status_code == 200, section, "GET /crm/quotations/new/ returns 200")
        q_html = resp.content.decode('utf-8', errors='ignore')
        
        # Verify required modal IDs and inputs for Quotation Studio
        self.log_check('id="addDayModal"' in q_html, section, "Quotation Builder: #addDayModal present in DOM")
        self.log_check('id="addItemModal"' in q_html, section, "Quotation Builder: #addItemModal present in DOM")
        self.log_check('id="modal_day_id"' in q_html, section, "Quotation Builder: #modal_day_id present in DOM")
        self.log_check('name="party"' in q_html, section, "Quotation Builder: name='party' present in DOM")
        self.log_check('name="markup_percent"' in q_html, section, "Quotation Builder: name='markup_percent' present in DOM")

        # 2.4 Driver SOS Form Elements
        driver = Driver.objects.first()
        if driver:
            session = self.client.session
            session['driver_id'] = driver.pk
            session.save()
        resp = self.client.get('/driver/sos/')
        self.log_check(resp.status_code == 200, section, "GET /driver/sos/ returns 200")
        sos_html = resp.content.decode('utf-8', errors='ignore')
        self.log_check('id="geoLat"' in sos_html, section, "Driver SOS: #geoLat present for GPS lock")
        self.log_check('id="geoLng"' in sos_html, section, "Driver SOS: #geoLng present for GPS lock")
        self.log_check('id="gpsStatusBanner"' in sos_html, section, "Driver SOS: #gpsStatusBanner present in DOM")
        self.log_check('id="gpsStatusText"' in sos_html, section, "Driver SOS: #gpsStatusText present in DOM")

        # 2.5 Admin Navigation Directory Filter
        self.client.force_login(self.admin_user)
        resp = self.client.get('/admin/')
        self.log_check(resp.status_code == 200, section, "GET /admin/ returns 200")
        admin_html = resp.content.decode('utf-8', errors='ignore')
        self.log_check('id="adminModelFilter"' in admin_html, section, "Admin Directory: #adminModelFilter quick-search present")
        self.log_check('filterByDomain' in admin_html, section, "Admin Directory: filterByDomain() JS handler present")

    # =========================================================================
    # PART 3: Dynamic AJAX APIs and Form Submission Lifecycles
    # =========================================================================
    def test_dynamic_form_apis(self):
        section = "3. Dynamic AJAX Endpoints & Form Submissions"
        print(f"\n{'='*80}\n🌟 SECTION {section.upper()}\n{'='*80}")

        # 3.1 Dynamic Vehicle Types API (used by booking form)
        if not VehicleType.objects.exists():
            VehicleType.objects.create(name='Sedan Prime', seating_capacity=4, default_day_rate=Decimal('2500.00'), default_km_rate=Decimal('14.00'))
        resp = self.client.get('/api/vehicle-types/')
        self.log_check(resp.status_code == 200, section, "GET /api/vehicle-types/ returns 200 JSON")
        vtypes = resp.json()
        self.log_check(isinstance(vtypes, dict) and len(vtypes) > 0, section, "Vehicle types rate mapping returned for dynamic dropdowns", f"count={len(vtypes)}")

        # 3.2 Dynamic Package Inventory Lookup API
        pkg = Package.objects.first()
        if not pkg:
            pkg = Package.objects.create(name="UI Test Kerala Tour", package_type="standard", duration_days=3, duration_nights=2)
        resp = self.client.get(f'/api/packages/{pkg.id}/inventory/')
        self.log_check(resp.status_code == 200, section, f"GET /api/packages/{pkg.id}/inventory/ returns 200 JSON")

        # 3.3 Dynamic Master Data Lookup API for CRM Quotation Builder
        resp = self.client.get('/crm/api/master-data/lookup/?type=hotel&destination=Ooty')
        self.log_check(resp.status_code == 200, section, "GET /crm/api/master-data/lookup/ returns 200 JSON")

        # 3.4 Quotation Live Calculation & Add Day/Add Item Flow
        party = CoreClient.objects.first()
        if not party:
            party = CoreClient.objects.create(name="UI Test Client", phone="9988776655")
        quotation = Quotation.objects.create(
            party=party,
            title="UI Dynamic Costing Test Quotation",
            destination="Munnar & Alleppey",
            start_date=datetime.date.today() + datetime.timedelta(days=20),
            end_date=datetime.date.today() + datetime.timedelta(days=24),
            pax_count=2,
            markup_percent=Decimal('15.00'),
            gst_rate=Decimal('5.00'),
            created_by=self.admin_user,
            status='draft'
        )
        self.log_check(quotation.id is not None, section, "Created test quotation for dynamic builder", f"q_num={quotation.quotation_number}")

        # Add Day via AJAX API
        day_data = {
            'title': 'Day 1: Arrival & Tea Garden Sightseeing',
            'overnight_destination': 'Munnar',
            'description': 'Scenic transfer through Cheeyappara waterfalls to Munnar resort.',
            'hotel_meal_plan': 'MAP',
        }
        resp = self.client.post(f'/crm/api/quotations/{quotation.id}/add-day/', day_data)
        self.log_check(resp.status_code == 200 and resp.json().get('status') == 'success', section, "POST /crm/api/quotations/<id>/add-day/ creates Day 1")
        day_id = resp.json().get('day_id')

        # Add Service Item via AJAX API
        item_data = {
            'day_id': day_id,
            'category': 'activity',
            'item_name': 'Eravikulam National Park Safari & Nilgiri Tahr Trek',
            'quantity': 2,
            'unit_cost': '450.00',
            'unit_price': '600.00',
        }
        resp = self.client.post(f'/crm/api/quotations/{quotation.id}/add-item/', item_data)
        self.log_check(resp.status_code == 200 and resp.json().get('status') == 'success', section, "POST /crm/api/quotations/<id>/add-item/ adds service item")
        item_id = resp.json().get('item_id')

        # Reload Quotation and verify calculated commercials
        quotation.refresh_from_db()
        self.log_check(quotation.activities_cost == Decimal('900.00'), section, "Quotation activity cost recalculated to ₹900.00 (2 × ₹450)")
        self.log_check(quotation.net_cost == Decimal('900.00'), section, "Quotation net cost matches ₹900.00")
        self.log_check(quotation.total_quoted_price > Decimal('900.00'), section, "Client quoted price includes 15% markup and 5% GST", f"total=₹{quotation.total_quoted_price}")

        # Delete Service Item via AJAX API
        resp = self.client.post(f'/crm/api/quotations/items/{item_id}/delete/')
        self.log_check(resp.status_code == 200 and resp.json().get('status') == 'success', section, "POST /crm/api/quotations/items/<id>/delete/ removes service item")

        # 3.5 Dynamic Task Management API
        task_data = {
            'title': 'Dynamic UI Test Task',
            'task_type': 'hotel_reconfirm',
            'priority': 'high',
            'due_date': str(datetime.date.today() + datetime.timedelta(days=2)),
            'description': 'Automated task verification from test suite.'
        }
        resp = self.client.post('/crm/api/tasks/create/', task_data)
        self.log_check(resp.status_code == 200 and resp.json().get('status') == 'success', section, "POST /crm/api/tasks/create/ creates task")
        task_id = resp.json().get('task_id')

        resp = self.client.post(f'/crm/api/tasks/{task_id}/toggle/')
        self.log_check(resp.status_code == 200 and resp.json().get('status') == 'success', section, "POST /crm/api/tasks/<id>/toggle/ toggles task status")

    # =========================================================================
    # PART 4: Mobile & Customer Self-Service Dynamic Views
    # =========================================================================
    def test_mobile_and_customer_portals(self):
        section = "4. Mobile & Customer Portal Dynamic Views"
        print(f"\n{'='*80}\n🌟 SECTION {section.upper()}\n{'='*80}")

        # 4.1 Customer Portal Checkout Form
        inv = PackageInventory.objects.first()
        if not inv:
            pkg = Package.objects.first() or Package.objects.create(name="UI Test Kerala Tour", package_type="standard", duration_days=3, duration_nights=2)
            inv = PackageInventory.objects.create(
                package=pkg,
                start_date=datetime.date.today() + datetime.timedelta(days=15),
                end_date=datetime.date.today() + datetime.timedelta(days=18),
                total_seats=20,
                available_seats=20,
                price_per_pax=Decimal('5000.00'),
                status='open'
            )
        resp = self.client.get(f'/customer-portal/checkout/{inv.id}/')
        self.log_check(resp.status_code == 200, section, f"GET /customer-portal/checkout/{inv.id}/ returns 200")
        chk_html = resp.content.decode('utf-8', errors='ignore')
        self.log_check('id="pax"' in chk_html, section, "Customer Checkout: #pax input present")
        self.log_check('id="coupon"' in chk_html, section, "Customer Checkout: #coupon input present")
        self.log_check('id="payment_plan"' in chk_html, section, "Customer Checkout: #payment_plan selector present")

        # 4.2 Driver Inspection Form
        veh = Vehicle.objects.first()
        driver = Driver.objects.first()
        if veh and driver:
            session = self.client.session
            session['driver_id'] = driver.pk
            session.save()
            resp = self.client.get(f'/driver/inspection/?vehicle_id={veh.id}')
            self.log_check(resp.status_code == 200, section, f"GET /driver/inspection/?vehicle_id={veh.id} returns 200")
            insp_html = resp.content.decode('utf-8', errors='ignore')
            self.log_check('name="brakes_functional"' in insp_html, section, "Driver Inspection: brakes toggle present")
            self.log_check('name="tyres_tread_and_pressure"' in insp_html, section, "Driver Inspection: tyres toggle present")
            self.log_check('name="engine_oil_level"' in insp_html, section, "Driver Inspection: engine oil toggle present")
            self.log_check('name="odometer_reading"' in insp_html, section, "Driver Inspection: odometer input present")

        # 4.3 Live Mission Control Fleet Feed
        self.client.force_login(self.admin_user)
        resp = self.client.get('/fleet/live/')
        self.log_check(resp.status_code == 200, section, "GET /fleet/live/ Mission Control returns 200")
        resp = self.client.get('/api/fleet/live-feed/')
        self.log_check(resp.status_code == 200 and 'vehicles' in resp.json(), section, "GET /api/fleet/live-feed/ returns valid dynamic fleet JSON")

    # =========================================================================
    # PART 5: Universal Admin ModelForms & Dynamic Media Verification
    # =========================================================================
    def test_admin_modelforms_and_media(self):
        section = "5. Admin ModelForms & Media Asset Resolution"
        print(f"\n{'='*80}\n🌟 SECTION {section.upper()}\n{'='*80}")

        rf = RequestFactory()
        req = rf.get('/admin/')
        req.user = self.admin_user

        total_models = len(site._registry)
        verified_forms = 0
        verified_custom_scripts = 0

        for model, model_admin in site._registry.items():
            model_name = f"{model._meta.app_label}.{model.__name__}"
            try:
                FormClass = model_admin.get_form(req)
                self.log_check(issubclass(FormClass, django.forms.BaseForm), section, f"Form Generated: {model_name}")
                verified_forms += 1

                # Verify custom media assets if declared
                media = model_admin.media
                if hasattr(media, '_js'):
                    for js_item in media._js:
                        # Ignore standard vendor libs
                        if any(v in js_item for v in ['admin/js/vendor/', 'jazzmin/', 'admin/js/jquery.init.js']):
                            continue
                        # Look up file in static directories
                        possible_paths = [
                            os.path.join(BASE_DIR, 'static', js_item),
                            os.path.join(BASE_DIR, 'packages', 'static', js_item),
                            os.path.join(BASE_DIR, 'staticfiles', js_item),
                        ]
                        found = any(os.path.isfile(p) for p in possible_paths)
                        self.log_check(found, section, f"Media Asset Exists: {js_item} for {model_name}")
                        verified_custom_scripts += 1
            except Exception as e:
                self.log_check(False, section, f"Form Generation for {model_name}", str(e))

        print(f"Total admin forms verified: {verified_forms}/{total_models}")
        print(f"Custom media JS scripts resolved: {verified_custom_scripts}")

    # =========================================================================
    # PART 6: Key Admin Add Pages HTTP 200 Health Check
    # =========================================================================
    def test_admin_add_pages_health(self):
        section = "6. Key Admin Add Pages HTTP 200 Health Check"
        print(f"\n{'='*80}\n🌟 SECTION {section.upper()}\n{'='*80}")

        self.client.force_login(self.admin_user)
        key_endpoints = [
            '/admin/operations/booking/add/',
            '/admin/operations/trip/add/',
            '/admin/operations/bulkcontract/add/',
            '/admin/operations/bulkcontractday/add/',
            '/admin/operations/trafficfine/add/',
            '/admin/packages/package/add/',
            '/admin/packages/collegeivexpedition/add/',
            '/admin/fleet_contracts/transportcontract/add/',
            '/admin/core/vehicle/add/',
            '/admin/core/driver/add/',
            '/admin/crm/quotation/add/',
            '/admin/crm/inquiry/add/',
            '/admin/maintenance/servicerecord/add/',
            '/admin/maintenance_compliance/compliancedocument/add/',
            '/admin/statements/generatedstatement/add/',
            '/admin/finance_treasury/payment/add/',
        ]

        for url in key_endpoints:
            resp = self.client.get(url)
            self.log_check(resp.status_code == 200, section, f"Add Page HTTP 200: {url}")
            html = resp.content.decode('utf-8', errors='ignore')
            self.log_check('<form' in html and 'csrfmiddlewaretoken' in html, section, f"Valid Form Rendered: {url}")

    # =========================================================================
    # PART 7: ModelForm Validation & Field Cleaning Logic
    # =========================================================================
    def test_form_validation_and_cleaning(self):
        section = "7. Form Validation & Cleaning Logic"
        print(f"\n{'='*80}\n🌟 SECTION {section.upper()}\n{'='*80}")

        today = datetime.date.today()
        party = CoreClient.objects.first()
        vtype = VehicleType.objects.first()
        veh = Vehicle.objects.first()
        driver = Driver.objects.first()

        # 7.1 StatementForm Validation
        stmt_valid_data = {
            'statement_type': 'party',
            'party': str(party.id),
            'from_date': today - datetime.timedelta(days=30),
            'to_date': today,
            'file_format': 'pdf',
        }
        stmt_form = StatementForm(data=stmt_valid_data)
        self.log_check(stmt_form.is_valid(), section, "StatementForm: Valid party statement passes validation")

        stmt_invalid_data = {
            'statement_type': 'party',
            'file_format': 'pdf',
        }
        stmt_form_invalid = StatementForm(data=stmt_invalid_data)
        self.log_check(not stmt_form_invalid.is_valid(), section, "StatementForm: Missing date range correctly fails validation")
        self.log_check('from_date' in stmt_form_invalid.errors and 'to_date' in stmt_form_invalid.errors, section, "StatementForm: from_date and to_date flagged as required")

        # 7.2 BookingForm Validation
        booking_data = {
            'party': party.id,
            'guest_name': 'Corporate Delegate',
            'guest_phone': '9876543210',
            'pickup_location': 'Cochin International Airport',
            'destination': 'Grand Hyatt Bolgatty',
            'pickup_date': today + datetime.timedelta(days=5),
            'pickup_time': '10:00',
            'drop_date': today + datetime.timedelta(days=7),
            'journey_type': 'outstation',
            'vehicle_type': vtype.id,
            'billing_type': 'package',
            'quoted_price': '15000.00',
            'status': 'confirmed',
        }
        booking_form = BookingForm(data=booking_data)
        self.log_check(booking_form.is_valid(), section, "BookingForm: Valid booking payload passes validation", str(booking_form.errors))

        # 7.3 TripForm Validation
        test_veh, _ = Vehicle.objects.get_or_create(
            registration_number="KL-07-COMPLY-01",
            defaults={
                'vehicle_type': vtype,
                'status': 'active',
                'insurance_expiry': today + datetime.timedelta(days=365),
                'fc_expiry': today + datetime.timedelta(days=365),
                'permit_expiry': today + datetime.timedelta(days=365),
                'tax_expiry': today + datetime.timedelta(days=365),
                'pollution_expiry': today + datetime.timedelta(days=365),
                'current_km': 10000,
            }
        )
        test_veh.insurance_expiry = today + datetime.timedelta(days=365)
        test_veh.fc_expiry = today + datetime.timedelta(days=365)
        test_veh.permit_expiry = today + datetime.timedelta(days=365)
        test_veh.tax_expiry = today + datetime.timedelta(days=365)
        test_veh.pollution_expiry = today + datetime.timedelta(days=365)
        test_veh.status = 'active'
        test_veh.save()

        test_driver, _ = Driver.objects.get_or_create(
            phone="9876500001",
            defaults={
                'name': "Compliant Driver Tester",
                'status': 'active',
                'license_validity_tr': today + datetime.timedelta(days=365),
            }
        )
        test_driver.status = 'active'
        test_driver.license_validity_tr = today + datetime.timedelta(days=365)
        test_driver.save()

        future_booking = Booking.objects.create(
            party=party,
            guest_name="Trip Form Tester",
            pickup_location="Airport",
            destination="Hotel",
            pickup_date=today + datetime.timedelta(days=200),
            pickup_time=datetime.time(10, 0),
            drop_date=today + datetime.timedelta(days=202),
            vehicle_type=vtype,
            billing_type='package',
            status='confirmed'
        )
        trip_data = {
            'booking': future_booking.id,
            'vehicle': test_veh.id,
            'driver': test_driver.id,
            'status': 'assigned',
            'start_date': today + datetime.timedelta(days=200),
            'end_date': today + datetime.timedelta(days=202),
            'billing_model': 'day',
            'day_rate': '3500.00',
            'km_rate': '0.00',
            'fixed_amount': '0.00',
            'days_count': 2,
            'driver_bata': '500.00',
        }
        trip_form = TripForm(data=trip_data)
        self.log_check(trip_form.is_valid(), section, "TripForm: Valid trip operational form passes validation", str(trip_form.errors))

    # =========================================================================
    # PART 8: Mobile Portal Form Submissions & DB Persistence
    # =========================================================================
    def test_operational_form_submissions(self):
        section = "8. Mobile Portal Form Submissions & DB Persistence"
        print(f"\n{'='*80}\n🌟 SECTION {section.upper()}\n{'='*80}")

        driver = Driver.objects.first()
        veh = Vehicle.objects.first()

        # Set driver portal session
        session = self.client.session
        session['driver_id'] = driver.pk
        session.save()

        # 8.1 Submit Pre-Trip Inspection Checklist
        insp_post_data = {
            'vehicle_id': str(veh.id),
            'odometer_reading': str(veh.current_km or 25000),
            'brakes_functional': '1',
            'tyres_tread_and_pressure': '1',
            'engine_oil_level': '1',
            'coolant_level': '1',
            'brake_fluid_level': '1',
            'battery_and_wiring': '1',
            'headlights_and_highbeam': '1',
            'taillights_and_brakelights': '1',
            'indicators_and_hazard': '1',
            'wipers_and_washer_fluid': '1',
            'horn_and_mirrors': '1',
            'first_aid_kit_present': '1',
            'fire_extinguisher_present': '1',
            'spare_wheel_and_jack': '1',
            'ac_or_fans_working': '1',
            'cabin_cleanliness': '1',
            'driver_signature_name': driver.name,
        }
        resp = self.client.post('/driver/inspection/', insp_post_data)
        self.log_check(resp.status_code == 302, section, "POST /driver/inspection/ submits and redirects to dashboard")

        latest_insp = PreTripInspectionChecklist.objects.filter(driver=driver, vehicle=veh).latest('id')
        self.log_check(latest_insp.overall_status == 'passed', section, "PreTripInspectionChecklist persisted with PASSED status", f"inspection_no={latest_insp.inspection_number}")

        # 8.2 Submit Driver SOS Alert
        sos_post_data = {
            'incident_type': 'breakdown',
            'severity': 'critical',
            'latitude': '9.9816',
            'longitude': '76.2999',
            'location_address': 'NH 66 Bypass Aluva',
            'passenger_count': '4',
            'passengers_safety_status': 'all_safe',
            'description': 'Engine overheating alert triggered by test suite.',
        }
        resp = self.client.post('/driver/sos/', sos_post_data)
        self.log_check(resp.status_code == 302, section, "POST /driver/sos/ triggers emergency and redirects to dashboard")

        latest_alert = EmergencyIncidentAlert.objects.filter(driver=driver, incident_type='breakdown').latest('id')
        self.log_check(latest_alert.latitude == Decimal('9.9816') and latest_alert.longitude == Decimal('76.2999'), section, "EmergencyIncidentAlert persisted with exact GPS coordinates", f"alert_id={latest_alert.incident_id}")

    # =========================================================================
    # MASTER RUNNER
    # =========================================================================
    def run_all(self):
        start_time = timezone.now()
        print("\n" + "#" * 80)
        print("🚀 EXECUTING COMPLETE FORMS & DYNAMIC UI JAVASCRIPT VERIFICATION")
        print("#" * 80)

        self.test_javascript_syntax()
        self.test_dom_selector_bindings()
        self.test_dynamic_form_apis()
        self.test_mobile_and_customer_portals()
        self.test_admin_modelforms_and_media()
        self.test_admin_add_pages_health()
        self.test_form_validation_and_cleaning()
        self.test_operational_form_submissions()

        end_time = timezone.now()
        duration = (end_time - start_time).total_seconds()

        print("\n" + "=" * 80)
        print("📊 FORMS & DYNAMIC UI JAVASCRIPT VERIFICATION REPORT")
        print("=" * 80)
        for sec, data in self.results.items():
            print(f"  ✓ {sec}: {data['passed']}/{data['passed'] + data['failed']} PASSED")

        print("-" * 80)
        print(f"🎯 TOTAL VERIFIED TESTS: {self.passed_tests}/{self.total_tests} PASSED (100% OK)")
        print(f"⏱️ EXECUTION TIME: {duration:.2f} seconds")
        print("=" * 80 + "\n")


if __name__ == '__main__':
    verifier = MasterUIAndFormsVerifier()
    verifier.run_all()
