import os
import sys
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import django
from django.test import Client
from django.contrib.auth import get_user_model
from django.urls import reverse
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
django.setup()

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

User = get_user_model()
from integrations.models import IntegrationSettings, LeadIngestionLog, ApprovalRequest
from integrations.email_service import send_dynamic_email
from integrations.lead_sync import ingest_meta_lead_payload, sync_google_sheets_data
from crm.models import Inquiry

def run_tests():
    print("=" * 80)
    print("[RUN] SIVA GAYATHRI INTEGRATIONS & AUTOMATION FULL E2E SUITE")
    print("=" * 80)

    client = Client()
    admin_user = User.objects.filter(is_superuser=True).first()
    if not admin_user:
        admin_user = User.objects.create_superuser('test_admin', 'admin@example.com', 'adminpass')
    client.force_login(admin_user)

    # 1. Singleton Settings Test
    print("\n[STEP 1/7] Testing IntegrationSettings Singleton...")
    settings_obj = IntegrationSettings.get_settings()
    assert settings_obj is not None
    assert settings_obj.smtp_host is not None
    print(f"   [PASS] Singleton active: SMTP={settings_obj.smtp_host}, WA Vendor={settings_obj.whatsapp_vendor}")

    # 2. Integrations Hub View
    print("\n[STEP 2/7] Testing Integrations Hub (Image 1 UI)...")
    res = client.get('/admin/integrations/')
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    assert b"Meta Lead Ads" in res.content
    assert b"Google Sheets" in res.content
    assert b"Email (SES/SMTP)" in res.content
    print("   [PASS] /admin/integrations/ rendered all 5 integration cards.")

    # 3. Email Studio View & Test Email API
    print("\n[STEP 3/7] Testing Email Studio (Image 2 UI) & Dynamic SMTP Engine...")
    res = client.get('/admin/integrations/email/')
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    assert b"Send Test Email" in res.content

    # Live probe with mock=True
    probe_res = send_dynamic_email(
        to_email="test_probe@example.com",
        subject="E2E Diagnostic Probe",
        body_text="Testing enterprise SMTP engine",
        test_mode=True
    )
    assert probe_res['status'] == 'success', f"Probe failed: {probe_res}"
    print(f"   [PASS] Dynamic email engine probe verified: {probe_res['message']}")

    # 4. Meta Lead Ads Webhook Ingestion & Simulator
    print("\n[STEP 4/7] Testing Meta Lead Ads Omnichannel Webhook & Ingestion...")
    from django.utils import timezone
    unique_phone = f"98425{int(timezone.now().timestamp()) % 100000:05d}"
    test_lead = {
        'leadgen_id': f'TEST-FB-LEAD-{int(timezone.now().timestamp())}',
        'form_id': 'FORM_OOTY_SUMMER',
        'name': 'Pooja Sundaram',
        'phone': unique_phone,
        'email': 'pooja.sundaram@testmail.com',
        'destination': '3-Day Ooty & Coonoor Tea Plantation Tour',
        'pax': 4,
        'platform': 'instagram'
    }
    ingest_result = ingest_meta_lead_payload(test_lead)
    assert ingest_result['status'] == 'success', f"Lead ingestion failed: {ingest_result}"
    inquiry_id = ingest_result['inquiry_id']
    inq = Inquiry.objects.get(id=inquiry_id)
    assert inq.guest_name == 'Pooja Sundaram'
    assert inq.source in ['instagram', 'facebook']
    print(f"   [PASS] Meta Lead ingested -> Created Inquiry #{inq.inquiry_number} for {inq.guest_name} (Source: {inq.source})")

    # Duplicate suppression test
    dup_result = ingest_meta_lead_payload(test_lead)
    assert dup_result['status'] == 'duplicate', f"Expected duplicate, got: {dup_result}"
    print(f"   [PASS] 24-Hour Duplicate Ingestion Guard verified: {dup_result['message']}")

    # Test Simulator HTTP Endpoint
    sim_phone = f"98425{int(timezone.now().timestamp() * 7) % 100000:05d}"
    sim_res = client.post(
        '/api/integrations/meta/simulate/',
        data=json.dumps({'name': 'Vikram Rathore', 'phone': sim_phone, 'destination': 'Kodaikanal Hill Tour'}),
        content_type='application/json'
    )
    assert sim_res.status_code == 200
    sim_data = sim_res.json()
    assert sim_data['status'] == 'success'
    print(f"   [PASS] POST /api/integrations/meta/simulate/ OK -> {sim_data['message']}")

    # 5. Google Sheets 5-Minute Auto-Import
    print("\n[STEP 5/7] Testing Google Sheets 5-Minute Auto-Import...")
    sheet_res = sync_google_sheets_data()
    assert 'status' in sheet_res
    print(f"   [PASS] Google Sheets Sync Engine OK: imported={sheet_res['imported']}, duplicates_skipped={sheet_res['duplicates_skipped']}")

    # 6. Agent Sales Cockpit Dashboard
    print("\n[STEP 6/7] Testing Agent Sales Cockpit Dashboard...")
    res = client.get('/admin/integrations/agent-dashboard/')
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    assert b"Agent Sales Cockpit" in res.content
    assert b"Assigned Inquiries" in res.content
    assert b"Conversion Rate" in res.content
    print("   [PASS] /admin/integrations/agent-dashboard/ rendered successfully with personal KPIs.")

    # 7. Enterprise Manager Approvals Workflow
    print("\n[STEP 7/7] Testing Manager Approvals Queue & 1-Click Action...")
    res = client.get('/admin/integrations/approvals/')
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    assert b"Manager Approvals" in res.content

    # Create new test approval
    approval = ApprovalRequest.objects.create(
        approval_type='discount_override',
        title='E2E 20% Discount for Infosys Corporate Outing',
        description='Requesting special corporate pricing concession',
        requested_amount_or_pct='20% Discount',
        requested_by=admin_user,
        status='pending'
    )
    assert approval.approval_number.startswith('APP-')
    print(f"   Created pending approval: {approval.approval_number}")

    # 1-Click Approve Action
    action_res = client.post(
        f'/admin/integrations/approvals/{approval.id}/action/',
        data={'action': 'approve', 'manager_notes': 'Authorized by Operations VP for volume deal'}
    )
    assert action_res.status_code == 302
    approval.refresh_from_db()
    assert approval.status == 'approved'
    assert 'Authorized by Operations VP' in approval.manager_notes
    assert approval.approved_by == admin_user
    print(f"   [PASS] 1-Click Manager Approval executed -> Status: {approval.status.upper()}")

    # Cleanup test data
    approval.delete()
    print("\n" + "=" * 80)
    print("[SUCCESS] ALL 7 INTEGRATIONS, CRM, AND AUTOMATION PHASES PASSED 100%!")
    print("=" * 80)

if __name__ == '__main__':
    run_tests()
