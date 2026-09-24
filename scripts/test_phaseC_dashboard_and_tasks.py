import os
import sys
import datetime
from decimal import Decimal
import django

# Setup environment
sys.stdout.reconfigure(encoding='utf-8')
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
django.setup()

from django.utils import timezone
from django.contrib.auth.models import User
from django.test import Client as HttpClient
from core.models import Party, Client, VehicleType
from operations.models import Booking
from crm.models import (
    Inquiry, Quotation, SupplierProfile, SupplierServiceVoucher,
    PartnerProfile, DmcTask
)
from crm.analytics import get_dmc_executive_metrics

def run_tests():
    print("=" * 80)
    print("🚀 PHASE C VALIDATION: EXECUTIVE DMC BUSINESS DASHBOARD & TO-DO ENGINE")
    print("=" * 80)

    # Setup Staff User & Agency
    user, _ = User.objects.get_or_create(username='dmc_exec_user', defaults={'email': 'exec@travelerp.com', 'is_staff': True})
    user.set_password('AdminPass123!')
    user.save()

    partner_party, _ = Party.objects.get_or_create(
        name="Cox & Kings Bharat Inbound",
        defaults={
            'party_type': 'travel_agency',
            'phone': "022 6666 7777",
            'email': "inbound@coxandkings.com"
        }
    )
    PartnerProfile.objects.get_or_create(
        party=partner_party,
        defaults={'category': 'diamond', 'credit_limit': Decimal('750000.00')}
    )

    vtype, _ = VehicleType.objects.get_or_create(
        name="Toyota Fortuner 4x4 AC",
        defaults={'seating_capacity': 7}
    )

    today = timezone.now().date()

    # --------------------------------------------------------------------------
    # TEST 1: Query Velocity & Conversion Rate Metrics
    # --------------------------------------------------------------------------
    print("\n[TEST 1] Query Velocity & Conversion Analytics...")
    inq_today = Inquiry.objects.create(
        party=partner_party,
        guest_name="Kishore Kumar Group",
        pickup_location="Coimbatore Airport",
        destination="Munnar & Tea Hills",
        pickup_date=today + datetime.timedelta(days=7),
        pickup_time=datetime.time(10, 0),
        adult_count=6,
        priority='high',
        source='agent_referral',
        status='won',
        assigned_to=user
    )

    metrics = get_dmc_executive_metrics()
    assert metrics['today_queries'] >= 1, "Today's queries count must be >= 1"
    assert metrics['month_queries'] >= 1, "Monthly queries count must be >= 1"
    assert metrics['conversion_rate'] > 0, "Conversion rate must be > 0"
    print(f"  ✓ Today's Inbound Queries: {metrics['today_queries']}")
    print(f"  ✓ Monthly Query Demand: {metrics['month_queries']}")
    print(f"  ✓ Lead Win Conversion Rate: {metrics['conversion_rate']}%")

    # --------------------------------------------------------------------------
    # TEST 2: Status-Wise Query Pipeline Funnel
    # --------------------------------------------------------------------------
    print("\n[TEST 2] Status-Wise Query Distribution Funnel...")
    assert 'won' in metrics['status_counts']
    assert 'new' in metrics['status_counts']
    assert 'quoted' in metrics['status_counts']
    won_cnt = metrics['status_counts']['won']['count']
    assert won_cnt >= 1
    print(f"  ✓ Status Pipeline Funnel captured {len(metrics['status_counts'])} stages.")
    print(f"  ✓ Converted/Won Leads: {won_cnt}")

    # --------------------------------------------------------------------------
    # TEST 3: Monthly Sales & Gross Margin Engine
    # --------------------------------------------------------------------------
    print("\n[TEST 3] Monthly Gross Sales & Gross Margin Engine...")
    
    # Create confirmed Booking with known quoted revenue
    booking = Booking.objects.create(
        party=partner_party,
        guest_name="Kishore Kumar Group",
        guest_phone="9876543210",
        pickup_location="Coimbatore Airport",
        destination="Munnar & Tea Hills",
        pickup_date=today + datetime.timedelta(days=2),
        drop_date=today + datetime.timedelta(days=5),
        pickup_time=datetime.time(10, 0),
        journey_type='outstation',
        vehicle_type=vtype,
        pax_count=6,
        billing_type='package',
        quoted_price=Decimal('60000.00'),
        status='confirmed'
    )

    # Create supplier voucher for supplier cost
    supplier_party, _ = Party.objects.get_or_create(
        name="Tea County Hill Resort",
        defaults={'party_type': 'supplier', 'phone': '04865 230460'}
    )
    supplier_profile, _ = SupplierProfile.objects.get_or_create(
        party=supplier_party,
        defaults={'supplier_type': 'hotelier', 'destination_city': 'Munnar'}
    )

    voucher = SupplierServiceVoucher.objects.create(
        supplier=supplier_profile,
        booking=booking,
        voucher_type='hotel_reservation',
        guest_name="Kishore Kumar Group",
        pax_count=6,
        service_date_start=booking.pickup_date,
        service_date_end=booking.drop_date,
        duration_nights=3,
        hotel_room_type="Premium Tea Valley Room",
        room_count=3,
        total_payable_to_supplier=Decimal('42000.00'), # 3 rooms x 3 nights
        status='confirmed'
    )

    metrics_fin = get_dmc_executive_metrics()
    assert metrics_fin['monthly_sales_revenue'] >= Decimal('60000.00')
    assert metrics_fin['monthly_supplier_cost'] >= Decimal('42000.00')
    expected_margin = metrics_fin['monthly_sales_revenue'] - metrics_fin['monthly_supplier_cost']
    assert metrics_fin['monthly_gross_margin_amount'] == expected_margin
    assert metrics_fin['monthly_gross_margin_pct'] > 0
    print(f"  ✓ Monthly Gross Sales Revenue: ₹{metrics_fin['monthly_sales_revenue']:,.2f}")
    print(f"  ✓ Committed Supplier Costs: ₹{metrics_fin['monthly_supplier_cost']:,.2f}")
    print(f"  ✓ Net Gross Margin: ₹{metrics_fin['monthly_gross_margin_amount']:,.2f} ({metrics_fin['monthly_gross_margin_pct']}%)")

    # --------------------------------------------------------------------------
    # TEST 4: Destination Popularity & 6-Month Trajectory
    # --------------------------------------------------------------------------
    print("\n[TEST 4] Destination Information & 6-Month Demand Trajectory...")
    top_dest = metrics_fin['top_destinations']
    assert len(top_dest) >= 1
    assert any(d['destination'] == "Munnar & Tea Hills" or d['share_pct'] > 0 for d in top_dest)
    print(f"  ✓ Top Destination identified: {top_dest[0]['destination']} ({top_dest[0]['share_pct']}% share)")

    trends = metrics_fin['monthly_trends']
    assert len(trends) == 6, f"Expected 6 months historical trend, got {len(trends)}"
    print(f"  ✓ 6-Month trajectory generated from {trends[0]['month_label']} to {trends[-1]['month_label']}")

    # --------------------------------------------------------------------------
    # TEST 5: Top 5 FTOs Leaderboard
    # --------------------------------------------------------------------------
    print("\n[TEST 5] List of Top 5 FTOs & Corporates...")
    top_ftos = metrics_fin['top_ftos']
    assert len(top_ftos) >= 1
    assert any(f['name'] == partner_party.name for f in top_ftos)
    leader = [f for f in top_ftos if f['name'] == partner_party.name][0]
    assert leader['revenue'] >= Decimal('60000.00')
    print(f"  ✓ Leaderboard Account: {leader['name']} ({leader['category']}) - ₹{leader['revenue']:,.2f}")

    # --------------------------------------------------------------------------
    # TEST 6: Team To-Do List & Task Lifecycle Management
    # --------------------------------------------------------------------------
    print("\n[TEST 6] Team To-Do List & Task Allocation Engine...")
    
    # Task 1: Future task (not overdue)
    task_future = DmcTask.objects.create(
        title="Confirm special dinner arrangement for Kishore Kumar group",
        priority='high',
        assigned_to=user,
        due_date=today + datetime.timedelta(days=2),
        status='pending'
    )
    assert not task_future.is_overdue, "Future task must not be overdue"

    # Task 2: Overdue task
    task_overdue = DmcTask.objects.create(
        title="Send revised CP tariff to Kuoni Inbound",
        priority='urgent',
        assigned_to=user,
        due_date=today - datetime.timedelta(days=1),
        status='pending'
    )
    assert task_overdue.is_overdue, "Past due date must flag is_overdue=True"

    # Test Status Toggle
    task_overdue.status = 'completed'
    task_overdue.completed_at = timezone.now()
    task_overdue.save()
    assert not task_overdue.is_overdue, "Completed task must not be flagged overdue"
    print(f"  ✓ Task priority classification verified: {task_future.get_priority_display()}")
    print(f"  ✓ SLA Overdue Task Watchdog verified (Auto-cleared on completion)")

    # --------------------------------------------------------------------------
    # TEST 7: HTTP Views Validation & Task APIs
    # --------------------------------------------------------------------------
    print("\n[TEST 7] HTTP Endpoints & Dashboard Rendering...")
    http = HttpClient()
    http.force_login(user)

    # 1. Executive Dashboard View
    resp = http.get('/crm/dashboard/')
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    assert b"Executive Travel Operations" in resp.content or b"DMC Executive Business Dashboard" in resp.content
    assert b"Monthly Gross Sales" in resp.content
    print("  ✓ GET /crm/dashboard/ -> 200 OK (Executive Business Dashboard loaded)")

    # 2. Task Creation API
    resp_task = http.post('/crm/api/tasks/create/', {
        'title': 'Call transport contractor for Innova Crysta booking',
        'priority': 'urgent',
        'due_date': str(today),
        'assigned_to': user.id
    })
    assert resp_task.status_code == 200, f"Expected 200, got {resp_task.status_code}"
    task_data = resp_task.json()
    assert task_data['status'] == 'success'
    new_task_id = task_data['task_id']
    print(f"  ✓ POST /crm/api/tasks/create/ -> 200 OK (Task #{new_task_id} created)")

    # 3. Task Toggle API
    resp_toggle = http.post(f'/crm/api/tasks/{new_task_id}/toggle/')
    assert resp_toggle.status_code == 200, f"Expected 200, got {resp_toggle.status_code}"
    toggle_data = resp_toggle.json()
    assert toggle_data['new_status'] == 'completed'
    assert toggle_data['is_completed'] is True
    print(f"  ✓ POST /crm/api/tasks/{new_task_id}/toggle/ -> 200 OK (Task marked Completed)")

    print("\n" + "=" * 80)
    print("🎉 ALL PHASE C VERIFICATION TESTS PASSED SUCCESSFULLY!")
    print("=" * 80)

if __name__ == '__main__':
    run_tests()
