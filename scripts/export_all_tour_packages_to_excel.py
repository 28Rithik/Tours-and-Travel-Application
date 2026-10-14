"""
Comprehensive Tour Packages Data Exporter to Excel (.xlsx) and CSV
Exports 100% of the tour packages database including:
1. Tour Packages Master Catalog (6,252 packages)
2. Day-by-Day Itineraries (30,508 itineraries)
3. Vehicle-Wise Tariffs (31,221 tariffs)
4. Temple Darshan Slots (1,589 slots)
5. Document & Visa Checklists (6,125 rules)
6. Departure Batches & Inventory (60 batches)
7. Boarding Pickup Points (224 stops)
8. Master Package Templates (6 templates)
9. Package Seasonal Surge Rates (4 records)
10. B2B Agent Margins (3 records)
11. College IV Expeditions (9 expeditions)
12. Tour Passenger Manifests (595 passengers)
13. Tour Feedback Logs (4 reviews)
"""

import os
import sys
import csv
import time
import django

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
django.setup()

import xlsxwriter
from packages.models import (
    Package,
    ItineraryDay,
    PackageVehicleTariff,
    TempleDarshanSlot,
    InternationalDocumentChecklist,
    PackageInventory,
    BoardingPoint,
    PackageTemplate,
    PackageSeasonalRate,
    PackageB2BMargin,
    CollegeIVExpedition,
    TourPassengerManifest,
    TourFeedbackLog,
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPORTS_DIR = os.path.join(BASE_DIR, 'exports')
os.makedirs(EXPORTS_DIR, exist_ok=True)

EXCEL_FILE = os.path.join(EXPORTS_DIR, 'Sivagayathiri_Tour_Packages_Master.xlsx')

print(f"Starting Export to {EXPORTS_DIR}...")
start_time = time.time()

# Helper to write CSV
def write_csv(filename, headers, rows):
    filepath = os.path.join(EXPORTS_DIR, filename)
    with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)
    print(f"  [CSV] Exported {len(rows):,} rows -> {filename}")
    return filepath

# Initialize Excel Workbook
workbook = xlsxwriter.Workbook(EXCEL_FILE, {'constant_memory': False})

# Cell formats
header_fmt = workbook.add_format({
    'bold': True,
    'bg_color': '#1E3A8A', # Deep Navy Blue
    'font_color': '#FFFFFF',
    'border': 1,
    'align': 'center',
    'valign': 'vcenter',
    'font_name': 'Segoe UI',
    'font_size': 10
})

data_fmt = workbook.add_format({
    'border': 1,
    'border_color': '#E2E8F0',
    'font_name': 'Segoe UI',
    'font_size': 9,
    'valign': 'top'
})

currency_fmt = workbook.add_format({
    'border': 1,
    'border_color': '#E2E8F0',
    'font_name': 'Segoe UI',
    'font_size': 9,
    'num_format': '₹#,##0.00',
    'align': 'right',
    'valign': 'top'
})

int_fmt = workbook.add_format({
    'border': 1,
    'border_color': '#E2E8F0',
    'font_name': 'Segoe UI',
    'font_size': 9,
    'num_format': '#,##0',
    'align': 'right',
    'valign': 'top'
})

pct_fmt = workbook.add_format({
    'border': 1,
    'border_color': '#E2E8F0',
    'font_name': 'Segoe UI',
    'font_size': 9,
    'num_format': '0.00%',
    'align': 'right',
    'valign': 'top'
})

# -------------------------------------------------------------
# 1. Packages Master Catalog
# -------------------------------------------------------------
print("Exporting 1. Packages Master Catalog...")
pkg_headers = [
    'Package ID', 'Package Code', 'Package Name', 'Destination', 'Category',
    'Transit Mode', 'Flight Est / Pax (INR)', 'Train Est / Pax (INR)',
    'Duration Days', 'Duration Nights', 'Pricing Type', 'Base Price (INR)',
    'Price With Food (INR)', 'Price Without Food (INR)',
    'Hotel Cost / Pax (INR)', 'Coach Cost / Pax (INR)', 'Meals Cost / Pax (INR)',
    'Activities Cost / Pax (INR)', 'Misc Cost / Pax (INR)', 'Min Pax',
    'Complementary Staff Count', 'Hotel Star Category', 'Room Sharing Type',
    'Meal Plan', 'Default Vehicle Type', 'Vehicle Seating Desc', 'Bus Amenities Desc',
    'Has Campfire DJ', 'Has Jeep Safari', 'Has Boating', 'Has Industrial Visit',
    'Is Devotional', 'Temple Darshan Info', 'Satvik Pure Veg Meals',
    'Senior Citizen Friendly', 'Temple Dress Code', 'Is International',
    'Destination Country', 'Visa Required', 'Visa Guidelines',
    'Passport Validity Months', 'Currency Code', 'Flight Inclusive',
    'Flight Details Note', 'Overseas DMC Partner', 'Inclusions', 'Exclusions',
    'Terms & Conditions', 'Contact Persons Footer', 'Description', 'Is Active', 'Created At'
]

pkg_rows = []
for p in Package.objects.all().order_by('id'):
    created_str = p.created_at.strftime('%Y-%m-%d %H:%M') if p.created_at else ''
    row = [
        p.id,
        p.package_code or '',
        p.name or '',
        p.destination or '',
        p.category or '',
        p.transit_mode or '',
        float(p.flight_estimate_per_pax) if p.flight_estimate_per_pax is not None else 0.0,
        float(p.train_estimate_per_pax) if p.train_estimate_per_pax is not None else 0.0,
        p.duration_days or 0,
        p.duration_nights or 0,
        p.pricing_type or '',
        float(p.base_price) if p.base_price is not None else 0.0,
        float(p.price_with_food) if p.price_with_food is not None else 0.0,
        float(p.price_without_food) if p.price_without_food is not None else 0.0,
        float(p.cost_hotel_per_pax) if p.cost_hotel_per_pax is not None else 0.0,
        float(p.cost_coach_per_pax) if p.cost_coach_per_pax is not None else 0.0,
        float(p.cost_meals_per_pax) if p.cost_meals_per_pax is not None else 0.0,
        float(p.cost_activities_per_pax) if p.cost_activities_per_pax is not None else 0.0,
        float(p.cost_misc_per_pax) if p.cost_misc_per_pax is not None else 0.0,
        p.min_pax or 0,
        p.complementary_staff_count or 0,
        p.hotel_star_category or '',
        p.room_sharing_type or '',
        p.meal_plan or '',
        p.default_vehicle_type or '',
        p.vehicle_seating_desc or '',
        p.bus_amenities_desc or '',
        'Yes' if p.has_campfire_dj else 'No',
        'Yes' if p.has_jeep_safari else 'No',
        'Yes' if p.has_boating else 'No',
        'Yes' if p.has_industrial_visit else 'No',
        'Yes' if p.is_devotional else 'No',
        p.temple_darshan_info or '',
        'Yes' if p.satvik_pure_veg_meals else 'No',
        'Yes' if p.senior_citizen_friendly else 'No',
        p.temple_dress_code or '',
        'Yes' if p.is_international else 'No',
        p.destination_country or '',
        'Yes' if p.visa_required else 'No',
        p.visa_guidelines or '',
        p.passport_validity_months or 0,
        p.currency_code or 'INR',
        'Yes' if p.flight_inclusive else 'No',
        p.flight_details_note or '',
        p.overseas_dmc_partner or '',
        p.inclusions or '',
        p.exclusions or '',
        p.terms_and_conditions or '',
        p.contact_persons_footer or '',
        p.description or '',
        'Active' if p.is_active else 'Inactive',
        created_str
    ]
    pkg_rows.append(row)

write_csv('01_Tour_Packages_Catalog.csv', pkg_headers, pkg_rows)

ws1 = workbook.add_worksheet('Tour Packages')
ws1.set_row(0, 26)
for col_idx, col_name in enumerate(pkg_headers):
    ws1.write(0, col_idx, col_name, header_fmt)

for row_idx, row in enumerate(pkg_rows, start=1):
    for col_idx, val in enumerate(row):
        if col_idx in [6, 7, 11, 12, 13, 14, 15, 16, 17, 18]:
            ws1.write(row_idx, col_idx, val, currency_fmt)
        elif col_idx in [0, 8, 9, 19, 20, 40]:
            ws1.write(row_idx, col_idx, val, int_fmt)
        else:
            ws1.write(row_idx, col_idx, str(val) if val is not None else '', data_fmt)

ws1.set_column('A:A', 10)
ws1.set_column('B:B', 16)
ws1.set_column('C:C', 35)
ws1.set_column('D:E', 20)
ws1.set_column('F:F', 14)
ws1.set_column('G:J', 14)
ws1.set_column('K:N', 16)
ws1.set_column('O:T', 14)
ws1.freeze_panes(1, 3)

# -------------------------------------------------------------
# 2. Day-by-Day Itineraries
# -------------------------------------------------------------
print("Exporting 2. Day-by-Day Itineraries...")
itin_headers = [
    'Itinerary ID', 'Package ID', 'Package Code', 'Package Name',
    'Day Number', 'Day Title', 'Route Segment', 'Sightseeing Spots',
    'Morning Activity', 'Evening / Night Activity', 'Activities Description',
    'Night Stay Location', 'Meals Included', 'Hotel Info', 'Transport Info'
]

itin_rows = []
for itin in ItineraryDay.objects.select_related('package').all().order_by('package_id', 'day_number'):
    p = itin.package
    row = [
        itin.id,
        itin.package_id,
        p.package_code if p else '',
        p.name if p else '',
        itin.day_number,
        itin.title or '',
        itin.route_segment or '',
        itin.sightseeing_spots or '',
        itin.morning_activity or '',
        itin.evening_night_activity or '',
        itin.activities or '',
        itin.night_stay_location or '',
        itin.meals_included or '',
        itin.hotel_info or '',
        itin.transport_info or ''
    ]
    itin_rows.append(row)

write_csv('02_Day_by_Day_Itineraries.csv', itin_headers, itin_rows)

ws2 = workbook.add_worksheet('Day-by-Day Itineraries')
ws2.set_row(0, 26)
for col_idx, col_name in enumerate(itin_headers):
    ws2.write(0, col_idx, col_name, header_fmt)

for row_idx, row in enumerate(itin_rows, start=1):
    for col_idx, val in enumerate(row):
        if col_idx in [0, 1, 4]:
            ws2.write(row_idx, col_idx, val, int_fmt)
        else:
            ws2.write(row_idx, col_idx, str(val) if val is not None else '', data_fmt)

ws2.set_column('A:B', 12)
ws2.set_column('C:C', 16)
ws2.set_column('D:D', 32)
ws2.set_column('E:E', 10)
ws2.set_column('F:G', 25)
ws2.set_column('H:K', 30)
ws2.set_column('L:O', 20)
ws2.freeze_panes(1, 4)

# -------------------------------------------------------------
# 3. Vehicle-Wise Tariffs
# -------------------------------------------------------------
print("Exporting 3. Vehicle-Wise Tariffs...")
tariff_headers = [
    'Tariff ID', 'Package ID', 'Package Code', 'Package Name',
    'Vehicle Type', 'Rate Type', 'Seating Tier',
    'Package Rate (INR)', 'Per Day Rate (INR)', 'Included KM',
    'Extra KM Rate (INR)', 'Local Package Hours', 'Extra Hour Rate (INR)',
    'Driver Bata Included', 'Driver Bata Per Day (INR)', 'Night Halt Charge (INR)',
    'Double Driver Included', 'Toll & Parking Included', 'Interstate Permit Included'
]

tariff_rows = []
for t in PackageVehicleTariff.objects.select_related('package').all().order_by('package_id', 'id'):
    p = t.package
    row = [
        t.id,
        t.package_id,
        p.package_code if p else '',
        p.name if p else '',
        t.vehicle_type or '',
        t.rate_type or '',
        t.seating_tier or '',
        float(t.package_rate) if t.package_rate is not None else 0.0,
        float(t.per_day_rate) if t.per_day_rate is not None else 0.0,
        t.included_km or 0,
        float(t.extra_km_rate) if t.extra_km_rate is not None else 0.0,
        t.local_package_hours or 0,
        float(t.extra_hour_rate) if t.extra_hour_rate is not None else 0.0,
        'Yes' if t.driver_bata_included else 'No',
        float(t.driver_bata_per_day) if t.driver_bata_per_day is not None else 0.0,
        float(t.night_halt_charge) if t.night_halt_charge is not None else 0.0,
        'Yes' if t.double_driver_included else 'No',
        'Yes' if t.toll_parking_included else 'No',
        'Yes' if t.interstate_permit_included else 'No'
    ]
    tariff_rows.append(row)

write_csv('03_Vehicle_Wise_Tariffs.csv', tariff_headers, tariff_rows)

ws3 = workbook.add_worksheet('Vehicle-Wise Tariffs')
ws3.set_row(0, 26)
for col_idx, col_name in enumerate(tariff_headers):
    ws3.write(0, col_idx, col_name, header_fmt)

for row_idx, row in enumerate(tariff_rows, start=1):
    for col_idx, val in enumerate(row):
        if col_idx in [7, 8, 10, 12, 14, 15]:
            ws3.write(row_idx, col_idx, val, currency_fmt)
        elif col_idx in [0, 1, 9, 11]:
            ws3.write(row_idx, col_idx, val, int_fmt)
        else:
            ws3.write(row_idx, col_idx, str(val) if val is not None else '', data_fmt)

ws3.set_column('A:B', 12)
ws3.set_column('C:C', 16)
ws3.set_column('D:D', 32)
ws3.set_column('E:G', 16)
ws3.set_column('H:I', 16)
ws3.set_column('J:M', 14)
ws3.set_column('N:S', 15)
ws3.freeze_panes(1, 4)

# -------------------------------------------------------------
# 4. Temple Darshan Slots
# -------------------------------------------------------------
print("Exporting 4. Temple Darshan Slots...")
temple_headers = [
    'Slot ID', 'Package ID', 'Package Code', 'Package Name',
    'Day Number', 'Temple Name', 'Deity / Circuit', 'Darshan Type',
    'Booked Slot Time', 'Token / Ticket Number', 'Reporting Location',
    'Dress Code Notes', 'Prasad Details', 'Senior Citizen Support'
]

temple_rows = []
for s in TempleDarshanSlot.objects.select_related('package', 'itinerary_day').all().order_by('package_id', 'id'):
    p = s.package
    itin = s.itinerary_day
    row = [
        s.id,
        s.package_id,
        p.package_code if p else '',
        p.name if p else '',
        itin.day_number if itin else '',
        s.temple_name or '',
        s.deity_or_circuit or '',
        s.darshan_type or '',
        str(s.booked_slot_time) if s.booked_slot_time else '',
        s.token_ticket_number or '',
        s.reporting_location or '',
        s.dress_code_notes or '',
        s.prasad_details or '',
        'Yes' if s.senior_citizen_support else 'No'
    ]
    temple_rows.append(row)

write_csv('04_Temple_Darshan_Slots.csv', temple_headers, temple_rows)

ws4 = workbook.add_worksheet('Temple Darshan Slots')
ws4.set_row(0, 26)
for col_idx, col_name in enumerate(temple_headers):
    ws4.write(0, col_idx, col_name, header_fmt)

for row_idx, row in enumerate(temple_rows, start=1):
    for col_idx, val in enumerate(row):
        if col_idx in [0, 1, 4] and str(val).isdigit():
            ws4.write(row_idx, col_idx, int(val), int_fmt)
        else:
            ws4.write(row_idx, col_idx, str(val) if val is not None else '', data_fmt)

ws4.set_column('A:B', 12)
ws4.set_column('C:C', 16)
ws4.set_column('D:D', 32)
ws4.set_column('E:E', 12)
ws4.set_column('F:H', 22)
ws4.set_column('I:N', 20)
ws4.freeze_panes(1, 4)

# -------------------------------------------------------------
# 5. International Document & Visa Checklists
# -------------------------------------------------------------
print("Exporting 5. Document & Visa Checklists...")
doc_headers = [
    'Checklist ID', 'Package ID', 'Package Code', 'Package Name',
    'Document Name', 'Is Mandatory', 'Submission Deadline (Days Before Tour)', 'Notes'
]

doc_rows = []
for c in InternationalDocumentChecklist.objects.select_related('package').all().order_by('package_id', 'id'):
    p = c.package
    row = [
        c.id,
        c.package_id,
        p.package_code if p else '',
        p.name if p else '',
        c.document_name or '',
        'Mandatory' if c.is_mandatory else 'Optional',
        c.submission_deadline_days or 0,
        c.notes or ''
    ]
    doc_rows.append(row)

write_csv('05_Document_Visa_Checklists.csv', doc_headers, doc_rows)

ws5 = workbook.add_worksheet('Visa & Document Checklists')
ws5.set_row(0, 26)
for col_idx, col_name in enumerate(doc_headers):
    ws5.write(0, col_idx, col_name, header_fmt)

for row_idx, row in enumerate(doc_rows, start=1):
    for col_idx, val in enumerate(row):
        if col_idx in [0, 1, 6]:
            ws5.write(row_idx, col_idx, val, int_fmt)
        else:
            ws5.write(row_idx, col_idx, str(val) if val is not None else '', data_fmt)

ws5.set_column('A:B', 12)
ws5.set_column('C:C', 16)
ws5.set_column('D:D', 32)
ws5.set_column('E:E', 25)
ws5.set_column('F:G', 16)
ws5.set_column('H:H', 35)
ws5.freeze_panes(1, 4)

# -------------------------------------------------------------
# 6. Departure Batches & Inventory
# -------------------------------------------------------------
print("Exporting 6. Departure Batches & Inventory...")
batch_headers = [
    'Batch ID', 'Package ID', 'Package Code', 'Package Name',
    'Departure Date', 'Return Date', 'Assigned Vehicle', 'Assigned Driver',
    'Total Seats', 'Available Seats', 'Booked Seats', 'Price Override (INR)', 'Status'
]

batch_rows = []
for b in PackageInventory.objects.select_related('package', 'assigned_vehicle', 'assigned_driver').all().order_by('id'):
    p = b.package
    row = [
        b.id,
        b.package_id,
        p.package_code if p else '',
        p.name if p else '',
        b.departure_date.strftime('%Y-%m-%d') if b.departure_date else '',
        b.return_date.strftime('%Y-%m-%d') if b.return_date else '',
        str(b.assigned_vehicle) if b.assigned_vehicle else 'Unassigned',
        str(b.assigned_driver) if b.assigned_driver else 'Unassigned',
        b.total_seats or 0,
        b.available_seats or 0,
        b.booked_seats or 0,
        float(b.price_override) if b.price_override is not None else 0.0,
        b.status or ''
    ]
    batch_rows.append(row)

write_csv('06_Departure_Batches_Inventory.csv', batch_headers, batch_rows)

ws6 = workbook.add_worksheet('Departure Batches')
ws6.set_row(0, 26)
for col_idx, col_name in enumerate(batch_headers):
    ws6.write(0, col_idx, col_name, header_fmt)

for row_idx, row in enumerate(batch_rows, start=1):
    for col_idx, val in enumerate(row):
        if col_idx == 11:
            ws6.write(row_idx, col_idx, val, currency_fmt)
        elif col_idx in [0, 1, 8, 9, 10]:
            ws6.write(row_idx, col_idx, val, int_fmt)
        else:
            ws6.write(row_idx, col_idx, str(val) if val is not None else '', data_fmt)

ws6.set_column('A:B', 12)
ws6.set_column('C:C', 16)
ws6.set_column('D:D', 30)
ws6.set_column('E:F', 14)
ws6.set_column('G:H', 22)
ws6.set_column('I:M', 14)
ws6.freeze_panes(1, 4)

# -------------------------------------------------------------
# 7. Boarding Pickup Points
# -------------------------------------------------------------
print("Exporting 7. Boarding Pickup Points...")
bp_headers = [
    'Boarding Point ID', 'Batch ID', 'Stop Order', 'Stop Name',
    'Pickup Time', 'Landmark', 'Coordinator Phone'
]

bp_rows = []
for bp in BoardingPoint.objects.all().order_by('departure_id', 'stop_order'):
    row = [
        bp.id,
        bp.departure_id or '',
        bp.stop_order or 0,
        bp.stop_name or '',
        str(bp.pickup_time) if bp.pickup_time else '',
        bp.landmark or '',
        bp.coordinator_phone or ''
    ]
    bp_rows.append(row)

write_csv('07_Boarding_Points.csv', bp_headers, bp_rows)

ws7 = workbook.add_worksheet('Boarding Points')
ws7.set_row(0, 26)
for col_idx, col_name in enumerate(bp_headers):
    ws7.write(0, col_idx, col_name, header_fmt)

for row_idx, row in enumerate(bp_rows, start=1):
    for col_idx, val in enumerate(row):
        if col_idx in [0, 1, 2]:
            ws7.write(row_idx, col_idx, val, int_fmt)
        else:
            ws7.write(row_idx, col_idx, str(val) if val is not None else '', data_fmt)

ws7.set_column('A:C', 14)
ws7.set_column('D:D', 26)
ws7.set_column('E:E', 14)
ws7.set_column('F:G', 22)
ws7.freeze_panes(1, 2)

# -------------------------------------------------------------
# 8. Master Package Templates
# -------------------------------------------------------------
print("Exporting 8. Master Package Templates...")
tpl_headers = [
    'Template ID', 'Template Name', 'Destination', 'Category',
    'Duration Days', 'Duration Nights', 'Base Price (INR)', 'Is Active', 'Description'
]

tpl_rows = []
for t in PackageTemplate.objects.all().order_by('id'):
    row = [
        t.id,
        t.name or '',
        t.destination or '',
        t.category or '',
        t.duration_days or 0,
        t.duration_nights or 0,
        float(t.base_price) if t.base_price is not None else 0.0,
        'Active' if t.is_active else 'Inactive',
        t.description or ''
    ]
    tpl_rows.append(row)

write_csv('08_Package_Templates.csv', tpl_headers, tpl_rows)

ws8 = workbook.add_worksheet('Package Templates')
ws8.set_row(0, 26)
for col_idx, col_name in enumerate(tpl_headers):
    ws8.write(0, col_idx, col_name, header_fmt)

for row_idx, row in enumerate(tpl_rows, start=1):
    for col_idx, val in enumerate(row):
        if col_idx == 6:
            ws8.write(row_idx, col_idx, val, currency_fmt)
        elif col_idx in [0, 4, 5]:
            ws8.write(row_idx, col_idx, val, int_fmt)
        else:
            ws8.write(row_idx, col_idx, str(val) if val is not None else '', data_fmt)

ws8.set_column('A:A', 12)
ws8.set_column('B:C', 26)
ws8.set_column('D:D', 18)
ws8.set_column('E:G', 15)
ws8.set_column('H:H', 12)
ws8.set_column('I:I', 40)
ws8.freeze_panes(1, 2)

# -------------------------------------------------------------
# 9. Seasonal Surge Rates
# -------------------------------------------------------------
print("Exporting 9. Seasonal Surge Rates...")
seasonal_headers = [
    'Seasonal Rate ID', 'Package ID', 'Package Code', 'Package Name',
    'Season Name', 'Season Type', 'Start Date', 'End Date',
    'Surge Percentage (%)', 'Price With Food Override (INR)',
    'Price Without Food Override (INR)', 'Vehicle Tariff Surge (%)', 'Notes', 'Is Active'
]

seasonal_rows = []
for sr in PackageSeasonalRate.objects.select_related('package').all().order_by('id'):
    p = sr.package
    seasonal_rows.append([
        sr.id,
        sr.package_id,
        p.package_code if p else '',
        p.name if p else '',
        sr.season_name or '',
        sr.season_type or '',
        sr.start_date.strftime('%Y-%m-%d') if sr.start_date else '',
        sr.end_date.strftime('%Y-%m-%d') if sr.end_date else '',
        float(sr.surge_percentage) if sr.surge_percentage is not None else 0.0,
        float(sr.price_with_food_override) if sr.price_with_food_override is not None else 0.0,
        float(sr.price_without_food_override) if sr.price_without_food_override is not None else 0.0,
        float(sr.vehicle_tariff_surge_percent) if sr.vehicle_tariff_surge_percent is not None else 0.0,
        sr.notes or '',
        'Active' if sr.is_active else 'Inactive'
    ])

write_csv('09_Package_Seasonal_Rates.csv', seasonal_headers, seasonal_rows)

ws9 = workbook.add_worksheet('Seasonal Rates')
ws9.set_row(0, 26)
for col_idx, col_name in enumerate(seasonal_headers):
    ws9.write(0, col_idx, col_name, header_fmt)

for row_idx, row in enumerate(seasonal_rows, start=1):
    for col_idx, val in enumerate(row):
        if col_idx in [9, 10]:
            ws9.write(row_idx, col_idx, val, currency_fmt)
        elif col_idx in [0, 1]:
            ws9.write(row_idx, col_idx, val, int_fmt)
        elif col_idx in [8, 11]:
            ws9.write(row_idx, col_idx, val, int_fmt)
        else:
            ws9.write(row_idx, col_idx, str(val) if val is not None else '', data_fmt)

ws9.set_column('A:B', 14)
ws9.set_column('C:D', 20)
ws9.set_column('E:H', 16)
ws9.set_column('I:L', 16)
ws9.set_column('M:N', 20)
ws9.freeze_panes(1, 4)

# -------------------------------------------------------------
# 10. B2B Agent Margins
# -------------------------------------------------------------
print("Exporting 10. B2B Agent Margins...")
b2b_headers = [
    'B2B Margin ID', 'Package ID', 'Package Code', 'Package Name',
    'Tier Name', 'Commission Percent (%)', 'Fixed Discount / Pax (INR)', 'Is Active'
]

b2b_rows = []
for bm in PackageB2BMargin.objects.select_related('package').all().order_by('id'):
    p = bm.package
    b2b_rows.append([
        bm.id,
        bm.package_id if bm.package else '',
        p.package_code if p else 'All Packages (Global)',
        p.name if p else 'Global Enterprise Baseline',
        bm.tier_name or '',
        float(bm.commission_percent) if bm.commission_percent is not None else 0.0,
        float(bm.fixed_discount_per_pax) if bm.fixed_discount_per_pax is not None else 0.0,
        'Active' if bm.is_active else 'Inactive'
    ])

write_csv('10_B2B_Agent_Margins.csv', b2b_headers, b2b_rows)

ws10 = workbook.add_worksheet('B2B Margins')
ws10.set_row(0, 26)
for col_idx, col_name in enumerate(b2b_headers):
    ws10.write(0, col_idx, col_name, header_fmt)

for row_idx, row in enumerate(b2b_rows, start=1):
    for col_idx, val in enumerate(row):
        if col_idx == 6:
            ws10.write(row_idx, col_idx, val, currency_fmt)
        elif col_idx in [0, 1] and str(val).isdigit():
            ws10.write(row_idx, col_idx, int(val), int_fmt)
        elif col_idx == 5:
            ws10.write(row_idx, col_idx, val, int_fmt)
        else:
            ws10.write(row_idx, col_idx, str(val) if val is not None else '', data_fmt)

ws10.set_column('A:B', 14)
ws10.set_column('C:D', 25)
ws10.set_column('E:H', 18)
ws10.freeze_panes(1, 4)

# -------------------------------------------------------------
# 11. College IV Expeditions
# -------------------------------------------------------------
print("Exporting 11. College IV Expeditions...")
iv_headers = [
    'Expedition ID', 'Package ID', 'Package Code', 'Package Name',
    'College Name', 'Department & Batch', 'Faculty Incharge', 'Faculty Phone',
    'Male Students', 'Female Students', 'Faculty Count', 'Total Pax',
    'Bus Count', 'Transit Mode', 'Destination City', 'Destination Coach Partner',
    'Permission Status', 'Has DJ & Campfire', 'Start Date', 'End Date', 'Status', 'Notes'
]

iv_rows = []
for iv in CollegeIVExpedition.objects.select_related('package').all().order_by('id'):
    p = iv.package
    iv_rows.append([
        iv.id,
        iv.package_id,
        p.package_code if p else '',
        p.name if p else '',
        iv.college_name or '',
        iv.department_and_batch or '',
        iv.faculty_incharge_name or '',
        iv.faculty_incharge_phone or '',
        iv.student_count_male or 0,
        iv.student_count_female or 0,
        iv.faculty_count or 0,
        iv.total_pax or 0,
        iv.bus_count or 0,
        iv.transit_mode or '',
        iv.destination_city or '',
        iv.destination_coach_partner or '',
        iv.permission_status or '',
        'Yes' if iv.has_dj_campfire else 'No',
        iv.start_date.strftime('%Y-%m-%d') if iv.start_date else '',
        iv.end_date.strftime('%Y-%m-%d') if iv.end_date else '',
        iv.status or '',
        iv.notes or ''
    ])

write_csv('11_College_IV_Expeditions.csv', iv_headers, iv_rows)

ws11 = workbook.add_worksheet('College IV Expeditions')
ws11.set_row(0, 26)
for col_idx, col_name in enumerate(iv_headers):
    ws11.write(0, col_idx, col_name, header_fmt)

for row_idx, row in enumerate(iv_rows, start=1):
    for col_idx, val in enumerate(row):
        if col_idx in [0, 1, 8, 9, 10, 11, 12]:
            ws11.write(row_idx, col_idx, val, int_fmt)
        else:
            ws11.write(row_idx, col_idx, str(val) if val is not None else '', data_fmt)

ws11.set_column('A:B', 14)
ws11.set_column('C:D', 24)
ws11.set_column('E:G', 22)
ws11.set_column('H:M', 14)
ws11.set_column('N:V', 18)
ws11.freeze_panes(1, 4)

# -------------------------------------------------------------
# 12. Tour Passenger Manifests
# -------------------------------------------------------------
print("Exporting 12. Tour Passenger Manifests...")
manifest_headers = [
    'Manifest ID', 'Departure Batch ID', 'IV Expedition ID', 'Passenger Name',
    'Roll Number', 'Gender', 'Age', 'Category', 'Bus Assignment', 'Seat Number',
    'Room Sharing Number', 'Boarding Point', 'Phone', 'Emergency Contact',
    'Aadhaar Number', 'Ticket / PNR Status', 'Senior Assistance Needed',
    'Passport Number', 'Passport Expiry Date', 'Visa Number'
]

manifest_rows = []
for m in TourPassengerManifest.objects.all().order_by('id'):
    manifest_rows.append([
        m.id,
        m.departure_id or '',
        m.iv_expedition_id or '',
        m.passenger_name or '',
        m.roll_number or '',
        m.gender or '',
        m.age or 0,
        m.category or '',
        m.bus_assignment or '',
        m.seat_number or '',
        m.room_sharing_number or '',
        str(m.boarding_point) if m.boarding_point else '',
        m.phone or '',
        m.emergency_contact or '',
        m.aadhaar_number or '',
        m.ticket_or_pnr_status or '',
        'Yes' if m.senior_assistance_needed else 'No',
        m.passport_number or '',
        m.passport_expiry_date.strftime('%Y-%m-%d') if m.passport_expiry_date else '',
        m.visa_number or ''
    ])

write_csv('12_Tour_Passenger_Manifests.csv', manifest_headers, manifest_rows)

ws12 = workbook.add_worksheet('Passenger Manifests')
ws12.set_row(0, 26)
for col_idx, col_name in enumerate(manifest_headers):
    ws12.write(0, col_idx, col_name, header_fmt)

for row_idx, row in enumerate(manifest_rows, start=1):
    for col_idx, val in enumerate(row):
        if col_idx in [0, 6]:
            ws12.write(row_idx, col_idx, val, int_fmt)
        else:
            ws12.write(row_idx, col_idx, str(val) if val is not None else '', data_fmt)

ws12.set_column('A:C', 14)
ws12.set_column('D:D', 24)
ws12.set_column('E:H', 14)
ws12.set_column('I:L', 16)
ws12.set_column('M:T', 16)
ws12.freeze_panes(1, 4)

# -------------------------------------------------------------
# 13. Tour Feedback Logs
# -------------------------------------------------------------
print("Exporting 13. Tour Feedback Logs...")
fb_headers = [
    'Feedback ID', 'Package ID', 'Package Code', 'Package Name',
    'Guest Name', 'Guest Phone', 'Trip Date', 'Overall Rating (1-5)',
    'Driver Rating', 'Hotel Rating', 'Food Rating', 'Schedule Rating',
    'NPS Score (0-10)', 'Review Text', 'Flag Status', 'Resolution Notes',
    'Is Verified', 'Created At'
]

fb_rows = []
for fb in TourFeedbackLog.objects.select_related('package').all().order_by('id'):
    p = fb.package
    created_str = fb.created_at.strftime('%Y-%m-%d %H:%M') if fb.created_at else ''
    fb_rows.append([
        fb.id,
        fb.package_id,
        p.package_code if p else '',
        p.name if p else '',
        fb.guest_name or '',
        fb.guest_phone or '',
        fb.trip_date.strftime('%Y-%m-%d') if fb.trip_date else '',
        fb.overall_rating or 0,
        fb.coach_driver_rating or 0,
        fb.hotel_rating or 0,
        fb.food_rating or 0,
        fb.schedule_rating or 0,
        fb.nps_score or 0,
        fb.customer_review_text or '',
        fb.flag_status or '',
        fb.manager_resolution_notes or '',
        'Yes' if fb.is_verified else 'No',
        created_str
    ])

write_csv('13_Tour_Feedback_Logs.csv', fb_headers, fb_rows)

ws13 = workbook.add_worksheet('Feedback & Reviews')
ws13.set_row(0, 26)
for col_idx, col_name in enumerate(fb_headers):
    ws13.write(0, col_idx, col_name, header_fmt)

for row_idx, row in enumerate(fb_rows, start=1):
    for col_idx, val in enumerate(row):
        if col_idx in [0, 1, 7, 8, 9, 10, 11, 12]:
            ws13.write(row_idx, col_idx, val, int_fmt)
        else:
            ws13.write(row_idx, col_idx, str(val) if val is not None else '', data_fmt)

ws13.set_column('A:B', 14)
ws13.set_column('C:E', 22)
ws13.set_column('F:G', 16)
ws13.set_column('H:M', 12)
ws13.set_column('N:P', 25)
ws13.freeze_panes(1, 4)

# -------------------------------------------------------------
# Finalizing Excel Workbook
# -------------------------------------------------------------
print("Finalizing and saving multi-sheet Excel Workbook...")
workbook.close()

elapsed = time.time() - start_time
print(f"\n=======================================================")
print(f"ALL EXPORTS COMPLETED IN {elapsed:.2f} SECONDS!")
print(f"Master Excel Workbook: {EXCEL_FILE}")
print(f"Worksheets created: 13 sheets")
print(f"Total Packages: {len(pkg_rows):,}")
print(f"Total Day Itineraries: {len(itin_rows):,}")
print(f"Total Vehicle Tariffs: {len(tariff_rows):,}")
print(f"Total Darshan Slots: {len(temple_rows):,}")
print(f"Total Document Checklists: {len(doc_rows):,}")
print(f"Total Departure Batches: {len(batch_rows):,}")
print(f"Total Boarding Points: {len(bp_rows):,}")
print(f"Total Templates: {len(tpl_rows):,}")
print(f"Total Seasonal Rates: {len(seasonal_rows):,}")
print(f"Total B2B Margins: {len(b2b_rows):,}")
print(f"Total IV Expeditions: {len(iv_rows):,}")
print(f"Total Passenger Manifests: {len(manifest_rows):,}")
print(f"Total Feedback Logs: {len(fb_rows):,}")
print(f"=======================================================\n")
