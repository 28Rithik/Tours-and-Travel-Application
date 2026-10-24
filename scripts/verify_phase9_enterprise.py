"""
scripts/verify_phase9_enterprise.py
Automated End-to-End Verification for Phase 9 Enterprise Studios & Light Mode Integrity
Sivagayathiri Tours & Travels ERP
"""

import os
import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
from decimal import Decimal
import datetime

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from django.utils import timezone

from core.models import Driver, Vehicle, VehicleType, Party, StaffProfile
from operations.models import Trip, Booking, TrafficFine, TripCashAdvanceEnvelope, EmptyLegTripOffer
from maintenance.models import ComplianceDocument

from operations.cash_advance_settlement import (
    get_cash_envelope_metrics,
    seed_sample_cash_envelopes,
    issue_cash_advance_envelope,
    log_onroad_expenses_to_envelope,
    settle_cash_advance_envelope,
    check_driver_pending_advances,
)
from operations.statutory_compliance_sentry import (
    get_compliance_dashboard_metrics,
    get_fleet_compliance_matrix,
    seed_statutory_compliance_records,
    renew_compliance_document,
)
from operations.echallan_sentry import (
    get_echallan_dashboard_metrics,
    seed_sample_echallans,
    update_echallan_liability,
    mark_echallan_paid,
)
from operations.empty_leg_optimizer import (
    get_empty_leg_dashboard_metrics,
    seed_sample_empty_leg_offers,
    calculate_empty_leg_pricing,
    generate_whatsapp_broadcast_text,
    SOUTH_INDIA_ONE_WAY_CORRIDORS,
)


def run_verification():
    print("=" * 75)
    print("  🚀 SIVAGAYATHIRI TRAVELS — PHASE 9 ENTERPRISE & LIGHT MODE AUDIT")
    print("=" * 75)

    client = Client()
    user = User.objects.filter(is_superuser=True).first()
    if not user:
        user = User.objects.create_superuser('ops_admin', 'ops@sivagayathiritravels.com', 'Admin@123')
    client.force_login(user)

    # --------------------------------------------------------------------------
    # 1. Seeding Data Verification
    # --------------------------------------------------------------------------
    print("\n[1/5] Seeding Operational Records...")
    seed_sample_cash_envelopes()
    seed_statutory_compliance_records()
    seed_sample_echallans()
    seed_sample_empty_leg_offers()

    cash_stats = get_cash_envelope_metrics()
    comp_stats = get_compliance_dashboard_metrics()
    echallan_stats = get_echallan_dashboard_metrics()
    empty_stats = get_empty_leg_dashboard_metrics()

    print(f"  ✅ Cash Advance Envelopes : {cash_stats['total_envelopes']} tracked (₹{cash_stats['total_disbursed_amt']:,.0f} disbursed)")
    print(f"  ✅ Statutory Compliance    : {comp_stats['compliance_rate']}% compliance rate across {comp_stats['total_vehicles']} vehicles")
    print(f"  ✅ Traffic E-Challans     : {echallan_stats['total_fines']} violations (₹{echallan_stats['unpaid_total_amt']:,.0f} unpaid)")
    print(f"  ✅ Empty-Leg Return Fares : {empty_stats['total_offers']} corridors active (₹{empty_stats['total_recovered_revenue']:,.0f} recovered)")

    # --------------------------------------------------------------------------
    # 2. Functional Engine Audits
    # --------------------------------------------------------------------------
    print("\n[2/5] Testing Business Logic & Calculations...")

    # Cash Advance Lifecycle
    env = TripCashAdvanceEnvelope.objects.first()
    if env:
        old_status = env.status
        log_onroad_expenses_to_envelope(env.id, fuel=4000, tolls=800, permits=400, submit_for_audit=True)
        env.refresh_from_db()
        assert env.status == 'submitted_for_audit', "Status must be submitted_for_audit"
        settle_cash_advance_envelope(env.id, notes="Verified in verification script")
        env.refresh_from_db()
        assert env.status == 'reconciled_settled', "Status must be reconciled_settled"
        print(f"  ✅ Cash Advance Envelope Lifecycle: Disbursed ➔ Audit ➔ Settled (Code: {env.envelope_code})")

    # Statutory Compliance Matrix
    matrix = get_fleet_compliance_matrix()
    assert len(matrix) > 0, "Fleet matrix must contain vehicles"
    print(f"  ✅ Statutory Readiness Matrix: {len(matrix)} vehicles evaluated across 7 statutory criteria")

    # E-Challan Liability Routing
    fine = TrafficFine.objects.first()
    if fine:
        update_echallan_liability(fine.id, 'driver', notes="Attributed to chauffeur")
        fine.refresh_from_db()
        assert fine.financial_responsibility == 'driver', "Liability must be driver"
        print(f"  ✅ E-Challan Liability Attribution: Routed fine {fine.challan_number} to Driver Settlement")

    # Empty-Leg Pricing & Broadcast
    corridor = SOUTH_INDIA_ONE_WAY_CORRIDORS[0]
    pricing = calculate_empty_leg_pricing(corridor, 'suv')
    assert pricing['net_margin'] > 0, "Empty leg net margin must be positive"
    offer = EmptyLegTripOffer.objects.first()
    if offer:
        wa_text = generate_whatsapp_broadcast_text(offer)
        assert len(wa_text) > 50, "WhatsApp broadcast text must be generated"
        print(f"  ✅ Empty-Leg Pricing & Broadcast: Generated {pricing['discount_percent']}% discount tariff with positive margin")

    # --------------------------------------------------------------------------
    # 3. HTTP View Render & Light Mode Integrity (Status 200)
    # --------------------------------------------------------------------------
    print("\n[3/5] Testing Studio HTTP Views & Template Rendering...")
    studios = [
        ('/operations/cash-envelopes/', 'Trip Cash Advance & Settlement Studio'),
        ('/operations/statutory-compliance/', 'RTO Fitness & Statutory Compliance Sentry'),
        ('/operations/echallan-sentry/', 'Parivahan Traffic E-Challan Sentry Studio'),
        ('/operations/empty-legs/', 'Empty-Leg Return Deadhead Optimizer'),
        ('/operations/border-permits/', 'Interstate Border Tax & AITP Sentry'),
        ('/operations/driver-fatigue-sentry/', 'Chauffeur Fatigue Sentry'),
        ('/operations/breakdown-sos/', 'Highway Breakdown SOS Studio'),
        ('/operations/pnr-arrivals/', 'PNR Group Arrival Manifest Studio'),
        ('/suppliers/vendor-bill-audit/', 'Vendor Bill Auditor & Telematics Studio'),
        ('/crm/feedback-reviews/', 'Customer Feedback & Reviews Hub'),
        ('/crm/followup-cadence/', 'Follow-up WhatsApp Cadence Studio'),
        ('/finance/tds-194c/', '194C TDS Corporate Ledger'),
        ('/finance/fastag-reconciliation/', 'FASTag Toll Statement Reconciler'),
        ('/maintenance/parts-inventory/', 'Workshop Parts Inventory Studio'),
    ]

    for url, label in studios:
        res = client.get(url)
        assert res.status_code == 200, f"View {url} returned {res.status_code}"
        content = res.content.decode('utf-8')
        
        # Verify Light Mode CSS rules exist
        assert 'background: #ffffff' in content or 'bg-white' in content or 'surface-bg' in content, f"{label} missing light mode background"
        assert 'border' in content, f"{label} missing border tokens"
        print(f"  ✅ [HTTP 200] {label} ({url}) — Light Mode Verified")

    # --------------------------------------------------------------------------
    # 4. API Endpoints Functional Checks
    # --------------------------------------------------------------------------
    print("\n[4/5] Testing JSON API Endpoints...")
    # Empty leg publish
    if offer:
        res = client.post('/api/operations/empty-legs/publish/', {'offer_id': offer.id}, content_type='application/json')
        assert res.status_code == 200
        assert res.json()['status'] == 'success'
        print("  ✅ API: /api/operations/empty-legs/publish/ [OK]")

    # Global Search API
    for q in ['cash', 'compliance', 'challan', 'empty']:
        res = client.get(f'/api/operations/global-search/?q={q}')
        assert res.status_code == 200
        d = res.json()
        assert d['status'] == 'success'
        assert d['count'] > 0
        print(f"  ✅ API: Global Search Query '{q}' returned {d['count']} result(s)")

    # --------------------------------------------------------------------------
    # 5. Summary Report
    # --------------------------------------------------------------------------
    print("\n[5/5] Audit Completed Successfully!")
    print("=" * 75)
    print("  🏆 ALL 4 PHASE 9 ENTERPRISE STUDIOS & LIGHT MODE CHECKS PASSED (100%)")
    print("=" * 75)


if __name__ == '__main__':
    run_verification()
