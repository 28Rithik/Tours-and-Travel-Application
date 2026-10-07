import os
import sys
import json
from decimal import Decimal
from pathlib import Path

# Configure utf-8 encoding for Windows stdout
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

# Setup Django Environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
import django
django.setup()

from django.test import RequestFactory
from django.conf import settings
from django.contrib.auth.models import User
from django.utils import timezone
from core.models import Client, Party
from crm.models import Inquiry, InquiryFollowUp, StaffNotification
from crm import views as crm_views
from django.contrib.admin.models import LogEntry, ADDITION, CHANGE


def print_step(title):
    print("\n" + "=" * 70)
    print(f"🚀  {title}")
    print("=" * 70)


def run_verification():
    factory = RequestFactory()

    # Create / Get Admin User
    admin_user, _ = User.objects.get_or_create(
        username='powerup_admin',
        defaults={
            'email': 'admin.powerup@travelerp.in',
            'is_staff': True,
            'is_superuser': True,
            'first_name': 'Super',
            'last_name': 'Admin'
        }
    )

    # -------------------------------------------------------------
    # 1. VERIFY ENTERPRISE PASSWORD POLICY
    # -------------------------------------------------------------
    print_step("1. Verifying Enterprise Password Policy Enforcement")
    validators = settings.AUTH_PASSWORD_VALIDATORS
    assert len(validators) >= 4, f"Expected at least 4 password validators, found {len(validators)}"
    validator_names = [v['NAME'] for v in validators]
    assert any('MinimumLengthValidator' in v for v in validator_names), "MinimumLengthValidator missing!"
    assert any('CommonPasswordValidator' in v for v in validator_names), "CommonPasswordValidator missing!"
    print(f"✅ Password Policy Enforced: {len(validators)} validators configured:")
    for v in validators:
        print(f"   - {v['NAME'].split('.')[-1]}")

    # -------------------------------------------------------------
    # 2. VERIFY DESTINATION DROPDOWN & SOCIAL SOURCES ON INQUIRY
    # -------------------------------------------------------------
    print_step("2. Verifying Destination Dropdown & Social Source Ingestion")
    client, _ = Client.objects.get_or_create(
        phone='+91 9888877771',
        defaults={'name': 'Devaki Ammal', 'party_type': 'individual', 'address': 'Coimbatore'}
    )
    inq = Inquiry.objects.create(
        party=client,
        guest_name='Devaki Ammal',
        guest_phone='+91 9888877771',
        pickup_location='Coimbatore',
        destination_dropdown='munnar',
        pickup_date=timezone.now().date(),
        pickup_time=timezone.now().time(),
        source='facebook',
        priority='urgent',
        target_tat_hours=4,
    )
    assert inq.source == 'facebook', f"Unexpected source {inq.source}"
    assert 'munnar' in inq.destination_dropdown, f"Unexpected dropdown {inq.destination_dropdown}"
    assert 'Munnar' in inq.destination, f"Destination auto-sync failed! Got {inq.destination}"
    assert inq.tat_deadline is not None, "TAT deadline not populated!"
    print(f"✅ Lead Created: {inq.inquiry_number} | Source: {inq.get_source_display()} | Dest: {inq.destination}")

    # -------------------------------------------------------------
    # 3. VERIFY OBJECTION MANAGEMENT ON LOST LEADS
    # -------------------------------------------------------------
    print_step("3. Verifying Objection Management & Win/Loss Rating")
    inq.status = 'lost'
    inq.lost_reason = 'competitor_won'
    inq.competitor_name = 'South India Holidays Pvt Ltd'
    inq.objection_notes = 'Competitor provided all-inclusive driver bata and toll fees waived.'
    inq.win_loss_rating = 4
    inq.save()

    refetched = Inquiry.objects.get(pk=inq.pk)
    assert refetched.status == 'lost'
    assert refetched.lost_reason == 'competitor_won'
    assert refetched.win_loss_rating == 4
    print(f"✅ Objection Logged: {refetched.get_lost_reason_display()} | Competitor: {refetched.competitor_name} | Rating: {refetched.win_loss_rating}/5")

    # -------------------------------------------------------------
    # 4. VERIFY RECORD CLONING API
    # -------------------------------------------------------------
    print_step("4. Verifying Ability to Clone a Record (Lead Clone)")
    req_clone = factory.post(f'/crm/api/inquiries/{inq.pk}/clone/')
    req_clone.user = admin_user
    res_clone = crm_views.api_inquiry_clone(req_clone, inq.pk)
    assert res_clone.status_code == 200, f"Clone failed: {res_clone.content}"
    data_clone = json.loads(res_clone.content)
    cloned_id = data_clone['cloned_id']
    cloned_inq = Inquiry.objects.get(pk=cloned_id)
    assert cloned_inq.status == 'new', f"Clone should be 'new', got {cloned_inq.status}"
    assert cloned_inq.pk != inq.pk, "Clone must have new primary key!"
    assert cloned_inq.inquiry_number != inq.inquiry_number, "Clone must have distinct inquiry number!"
    print(f"✅ Cloned Record: Original={inq.inquiry_number} ➔ Cloned={cloned_inq.inquiry_number} (ID: {cloned_id})")

    # -------------------------------------------------------------
    # 5. VERIFY REAL-TIME STAFF NOTIFICATIONS & POLLING API
    # -------------------------------------------------------------
    print_step("5. Verifying Staff Notification Center & Polling API")
    StaffNotification.push(
        notification_type='new_booking',
        title='VIP Lead Arrived',
        body='Devaki Ammal Munnar Circuit',
        recipient=admin_user,
    )
    req_poll = factory.get('/crm/api/notifications/poll/')
    req_poll.user = admin_user
    res_poll = crm_views.api_notifications_poll(req_poll)
    assert res_poll.status_code == 200
    data_poll = json.loads(res_poll.content)
    assert data_poll['count'] > 0, "No notifications found!"
    print(f"✅ Bell Polling API: {data_poll['count']} unread notification(s) retrieved.")

    # Mark read
    req_read = factory.post(
        '/crm/api/notifications/mark-read/',
        data=json.dumps({'all': True}),
        content_type='application/json'
    )
    req_read.user = admin_user
    res_read = crm_views.api_notifications_mark_read(req_read)
    assert res_read.status_code == 200
    print("✅ Mark All Read API executed successfully.")

    # -------------------------------------------------------------
    # 6. VERIFY SOCIAL LEAD WEBHOOK (FACEBOOK & INSTAGRAM)
    # -------------------------------------------------------------
    print_step("6. Verifying Facebook & Instagram Lead Ads Webhook")
    # Challenge GET verification
    req_challenge = factory.get('/crm/webhooks/social-lead/?hub.mode=subscribe&hub.challenge=778899&hub.verify_token=tutterfly_crm_token')
    res_challenge = crm_views.api_social_lead_webhook(req_challenge)
    assert res_challenge.status_code == 200
    assert res_challenge.content.decode() == '778899', "Challenge verification failed!"
    print("✅ Webhook Handshake (GET Challenge): Passed (778899)")

    # Lead Ingestion POST
    social_payload = {
        'source': 'instagram',
        'full_name': 'Meenakshi Sundaram',
        'phone': '+91 9776655443',
        'email': 'meenakshi@example.com',
        'destination_dropdown': 'kodaikanal',
        'ad_name': 'Summer Hill Stations IG Campaign 2026',
        'notes': 'Interested in honeymoon cottage with valley view cab',
        'adult_count': 2
    }
    req_ingest = factory.post(
        '/crm/webhooks/social-lead/',
        data=json.dumps(social_payload),
        content_type='application/json'
    )
    res_ingest = crm_views.api_social_lead_webhook(req_ingest)
    assert res_ingest.status_code == 200
    data_ingest = json.loads(res_ingest.content)
    assert data_ingest['status'] == 'success'
    ig_inq = Inquiry.objects.get(pk=data_ingest['inquiry_id'])
    assert ig_inq.source == 'instagram'
    assert 'Kodaikanal' in ig_inq.destination
    print(f"✅ Ingested Social Lead: {ig_inq.inquiry_number} | Guest: {ig_inq.guest_name} | Source: {ig_inq.source}")

    # -------------------------------------------------------------
    # 7. VERIFY 360° PROFILE ENHANCER API
    # -------------------------------------------------------------
    print_step("7. Verifying 360° Profile Enhancer Intelligence API")
    req_pe = factory.get(f'/crm/api/profile-enhancer/{client.pk}/')
    req_pe.user = admin_user
    res_pe = crm_views.api_profile_enhancer(req_pe, client.pk)
    assert res_pe.status_code == 200
    data_pe = json.loads(res_pe.content)['client']
    assert data_pe['name'] == client.name
    assert 'tier' in data_pe
    assert 'win_rate' in data_pe
    print(f"✅ Profile 360: Client={data_pe['name']} | Tier={data_pe['tier']} | Inquiries={data_pe['total_inquiries']}")

    # -------------------------------------------------------------
    # 8. VERIFY TENANT ADMIN USER UPDATE & AUDIT LOGS
    # -------------------------------------------------------------
    print_step("8. Verifying Tenant Admin Area: Activity Log & User Management")
    test_user, _ = User.objects.get_or_create(username='temp_agent', defaults={'email': 'temp@travelerp.in'})
    req_usr = factory.post(
        '/crm/api/tenant-admin/user/update/',
        data=json.dumps({
            'user_id': test_user.pk,
            'first_name': 'Kavitha',
            'last_name': 'Ramasamy',
            'email': 'kavitha.r@travelerp.in',
        }),
        content_type='application/json'
    )
    req_usr.user = admin_user
    res_usr = crm_views.api_tenant_admin_user_update(req_usr)
    assert res_usr.status_code == 200
    test_user.refresh_from_db()
    assert test_user.first_name == 'Kavitha'
    assert test_user.email == 'kavitha.r@travelerp.in'
    print(f"✅ Tenant User Updated: {test_user.get_full_name()} | Email: {test_user.email}")

    # Verify Activity Logs API
    req_logs = factory.get('/crm/api/tenant-admin/logs/')
    req_logs.user = admin_user
    res_logs = crm_views.api_tenant_admin_logs(req_logs)
    assert res_logs.status_code == 200
    data_logs = json.loads(res_logs.content)
    print(f"✅ Tenant Audit Log API: Retrieved {data_logs['count']} log items.")

    # -------------------------------------------------------------
    # 9. VERIFY SAMPLE DATA GENERATOR & CLEANER
    # -------------------------------------------------------------
    print_step("9. Verifying Sample Records Generator & Safe Cleanup")
    req_gen = factory.post('/crm/api/sample-records/generate/')
    req_gen.user = admin_user
    res_gen = crm_views.api_sample_records_generate(req_gen)
    assert res_gen.status_code == 200
    sample_cnt = Inquiry.objects.filter(guest_name__startswith='[SAMPLE]').count()
    assert sample_cnt >= 5, f"Expected at least 5 sample leads, found {sample_cnt}"
    print(f"✅ Generated {sample_cnt} sample leads in the pipeline.")

    # Now clean
    req_clean = factory.post('/crm/api/sample-records/clean/')
    req_clean.user = admin_user
    res_clean = crm_views.api_sample_records_clean(req_clean)
    assert res_clean.status_code == 200
    cleaned_cnt = Inquiry.objects.filter(guest_name__startswith='[SAMPLE]').count()
    assert cleaned_cnt == 0, f"Sample leads still remaining: {cleaned_cnt}"
    print("✅ Sample Records Cleaned: Zero test records remaining.")

    # -------------------------------------------------------------
    # 10. VERIFY TAT DASHBOARD & OBJECTION ANALYTICS
    # -------------------------------------------------------------
    print_step("10. Verifying TAT Dashboard & Objection Analytics API")
    req_tat = factory.get('/crm/api/tat-dashboard/')
    req_tat.user = admin_user
    res_tat = crm_views.api_tat_dashboard(req_tat)
    assert res_tat.status_code == 200
    data_tat = json.loads(res_tat.content)
    assert 'pipeline' in data_tat
    assert 'objection_analysis' in data_tat
    print(f"✅ TAT Dashboard: {len(data_tat['pipeline'])} pipeline stages tracked with average SLA durations.")

    print("\n" + "🎉" * 35)
    print("ALL 10 CRM & POWER-UP FEATURES VERIFIED SUCCESSFULLY!")
    print("🎉" * 35)


if __name__ == '__main__':
    run_verification()
