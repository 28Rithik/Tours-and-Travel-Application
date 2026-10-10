import json
import logging
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone

from .models import IntegrationSettings, LeadIngestionLog, ApprovalRequest
from .email_service import send_dynamic_email
from .lead_sync import ingest_meta_lead_payload, sync_google_sheets_data
from crm.models import Inquiry, InquiryFollowUp, Quotation
from operations.models import Booking

logger = logging.getLogger(__name__)


# ==============================================================================
# 1. INTEGRATIONS HUB (MATCHING IMAGE 1)
# ==============================================================================

@login_required
def integrations_hub_view(request):
    """
    Centralized integrations management hub displaying all 5 connected platforms:
    Meta Lead Ads, WhatsApp Business, Google Sheets, WhatsApp Gateway, and Email SES/SMTP.
    """
    cfg = IntegrationSettings.get_settings()
    
    # Recent lead logs
    recent_logs = LeadIngestionLog.objects.select_related('created_inquiry')[:8]
    
    context = {
        'cfg': cfg,
        'recent_logs': recent_logs,
        'title': 'Integrations & External Channels',
    }
    return render(request, 'integrations/hub.html', context)


# ==============================================================================
# 2. EMAIL (SES / SMTP) STUDIO (MATCHING IMAGE 2 EXACTLY)
# ==============================================================================

@login_required
def email_service_studio_view(request):
    """
    Dedicated visual SMTP and Amazon SES configuration studio matching Image 2,
    supporting interactive live credential verification and test email dispatch.
    """
    cfg = IntegrationSettings.get_settings()

    if request.method == 'POST':
        # Update SMTP Server Connection
        cfg.smtp_host = request.POST.get('smtp_host', cfg.smtp_host).strip()
        try:
            cfg.smtp_port = int(request.POST.get('smtp_port', 587))
        except (ValueError, TypeError):
            cfg.smtp_port = 587
        cfg.smtp_encryption = request.POST.get('smtp_encryption', 'tls')
        cfg.smtp_username = request.POST.get('smtp_username', '').strip()
        
        # Only update password if a new one was provided
        pwd = request.POST.get('smtp_password', '').strip()
        if pwd and pwd != '••••••••':
            cfg.smtp_password = pwd

        # Update Sender Identity Profile
        cfg.sender_email = request.POST.get('sender_email', cfg.sender_email).strip()
        cfg.sender_name = request.POST.get('sender_name', cfg.sender_name).strip()
        cfg.email_active = 'email_active' in request.POST or request.POST.get('email_active') == 'true'

        cfg.save()
        messages.success(request, f"Email (SES/SMTP) server parameters saved successfully! Host: {cfg.smtp_host}:{cfg.smtp_port}")
        return redirect('integrations:email_studio')

    context = {
        'cfg': cfg,
        'smtp_hosts': IntegrationSettings.SMTP_HOST_CHOICES,
        'encryptions': IntegrationSettings.ENCRYPTION_CHOICES,
    }
    return render(request, 'integrations/email_studio.html', context)


@csrf_exempt
@login_required
def api_test_email(request):
    """
    Live test and verification AJAX endpoint for Image 2 ('Test & Verification' box).
    Dispatches a real-time verification probe using the configured or temporary credentials.
    """
    if request.method != 'POST':
        return HttpResponseBadRequest("Only POST allowed")

    try:
        data = json.loads(request.body.decode('utf-8')) if request.body else request.POST
    except Exception:
        data = request.POST

    test_email = data.get('test_email', '').strip()
    if not test_email:
        return JsonResponse({'status': 'error', 'message': 'Please enter a test email address.'}, status=400)

    cfg = IntegrationSettings.get_settings()
    
    # Subject & body for verification test
    subject = f"✅ Sivagayathiri TravelERP — Email Verification Test [{timezone.now().strftime('%H:%M:%S')}]"
    body_text = (
        f"Namaste!\n\n"
        f"This is an automated test message from Sivagayathiri Travels & Expeditions.\n"
        f"Your Email (SES/SMTP) integration is operating with 100% success.\n\n"
        f"• SMTP Server: {cfg.smtp_host}:{cfg.smtp_port}\n"
        f"• Encryption: {cfg.smtp_encryption.upper()}\n"
        f"• Sender Profile: {cfg.sender_name} <{cfg.sender_email}>\n"
        f"• Verified At: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        f"Sivagayathiri TravelERP Operations Mission Control"
    )
    body_html = f"""
    <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto; padding: 24px; border: 1px solid #e2e8f0; border-radius: 12px; background: #ffffff;">
        <div style="background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%); color: white; padding: 18px 24px; border-radius: 8px; margin-bottom: 20px;">
            <h2 style="margin: 0; font-size: 1.3rem;">🚌 Sivagayathiri TravelERP</h2>
            <p style="margin: 4px 0 0; font-size: 0.85rem; opacity: 0.9;">SMTP & Amazon SES Live Verification</p>
        </div>
        <p style="font-size: 1rem; color: #1e293b;">Namaste!</p>
        <p style="font-size: 0.95rem; color: #334155;">Your transactional email server connection has been successfully verified.</p>
        <div style="background: #f8fafc; border-left: 4px solid #10b981; padding: 12px 16px; border-radius: 4px; margin: 16px 0;">
            <div style="font-size: 0.85rem; color: #475569;"><strong>SMTP Host:</strong> {cfg.smtp_host}:{cfg.smtp_port} ({cfg.smtp_encryption.upper()})</div>
            <div style="font-size: 0.85rem; color: #475569;"><strong>Sender:</strong> {cfg.sender_name} &lt;{cfg.sender_email}&gt;</div>
            <div style="font-size: 0.85rem; color: #475569;"><strong>Status:</strong> Live & Connected ✅</div>
        </div>
        <p style="font-size: 0.8rem; color: #94a3b8; margin-top: 24px;">Sent from Sivagayathiri Travels & Expeditions · Headquarters: Gandhipuram, Coimbatore</p>
    </div>
    """

    res = send_dynamic_email(test_email, subject, body_text, body_html=body_html, test_mode=True)
    return JsonResponse(res)


# ==============================================================================
# 3. META LEAD ADS WEBHOOK & SIMULATOR
# ==============================================================================

@csrf_exempt
def api_meta_lead_webhook(request):
    """
    Official Webhook endpoint for Meta Lead Ads (Facebook & Instagram).
    Handles GET for challenge handshake and POST for live lead ingestion.
    Endpoint: /api/integrations/meta/webhook/
    """
    cfg = IntegrationSettings.get_settings()

    # Handshake verification for Meta
    if request.method == 'GET':
        mode = request.GET.get('hub.mode')
        token = request.GET.get('hub.verify_token')
        challenge = request.GET.get('hub.challenge')

        if mode == 'subscribe' and token == cfg.meta_verify_token:
            return HttpResponse(challenge, content_type='text/plain')
        return HttpResponse("Verification token mismatch", status=403)

    # Inbound lead payload
    if request.method == 'POST':
        try:
            payload = json.loads(request.body.decode('utf-8'))
        except Exception:
            payload = request.POST.dict()

        # Check if wrapped in Meta change entry structure
        lead_data = payload
        if 'entry' in payload and payload['entry']:
            for entry in payload['entry']:
                for change in entry.get('changes', []):
                    val = change.get('value', {})
                    lead_data = {
                        'leadgen_id': val.get('leadgen_id', ''),
                        'form_id': val.get('form_id', ''),
                        'name': val.get('full_name', 'Meta Lead Traveler'),
                        'phone': val.get('phone_number', '9842500000'),
                        'email': val.get('email', 'meta@sivagayathiritravels.com'),
                        'destination': val.get('destination', 'Ooty / Kodaikanal'),
                        'platform': 'instagram'
                    }

        result = ingest_meta_lead_payload(lead_data)
        return JsonResponse(result)

    return HttpResponseBadRequest("Invalid request method")


@csrf_exempt
@login_required
def api_meta_lead_simulate(request):
    """
    Simulates a live lead ad form submission from Instagram or Facebook
    to test the ingestion pipeline with 1 click.
    """
    if request.method != 'POST':
        return HttpResponseBadRequest("Only POST allowed")

    try:
        data = json.loads(request.body.decode('utf-8')) if request.body else request.POST
    except Exception:
        data = request.POST

    mock_lead = {
        'leadgen_id': f"FB-AD-{int(timezone.now().timestamp())}",
        'form_id': 'FORM_OOTY_SUMMER_2026',
        'full_name': data.get('name', 'Ananya Sharma'),
        'phone_number': data.get('phone', '9842599111'),
        'email': data.get('email', 'ananya.sharma@example.com'),
        'destination': data.get('destination', '3-Day Ooty & Coonoor Hill Escape'),
        'pax': int(data.get('pax', 4) or 4),
        'platform': data.get('platform', 'instagram'),
        'city': data.get('city', 'Bangalore')
    }

    res = ingest_meta_lead_payload(mock_lead)
    return JsonResponse(res)


# ==============================================================================
# 4. GOOGLE SHEETS 5-MINUTE AUTO-IMPORT
# ==============================================================================

@csrf_exempt
@login_required
def api_google_sheet_sync(request):
    """
    Syncs the connected Google Sheet into CRM Inquiries with 1 click.
    Endpoint: POST /api/integrations/google-sheets/sync/
    """
    if request.method != 'POST':
        return HttpResponseBadRequest("Only POST allowed")

    res = sync_google_sheets_data()
    return JsonResponse(res)


# ==============================================================================
# 5. PERSONAL AGENT DASHBOARD (MATCHING LEFT SIDEBAR 'AGENT DASHBOARD')
# ==============================================================================

@login_required
def agent_dashboard_view(request):
    """
    Personalized workspace for Sales Executives & Tour Planners:
      - My Assigned Inquiries
      - Follow-ups Scheduled for Today
      - Pending Quotation Revisions
      - Personal Won / Conversion Rate
    """
    user = request.user
    today = timezone.now().date()

    # Filtered by current user if not superuser
    my_inquiries = Inquiry.objects.filter(assigned_to=user) if not user.is_superuser else Inquiry.objects.all()
    
    # Overdue or Today's follow-ups
    pending_followups = InquiryFollowUp.objects.filter(
        inquiry__in=my_inquiries,
        is_done=False
    ).select_related('inquiry').order_by('scheduled_at')[:10]

    # Quick KPIs
    total_assigned = my_inquiries.count()
    won_count = my_inquiries.filter(status='won').count()
    in_pipeline = my_inquiries.filter(status__in=['new', 'in_progress', 'quoted', 'negotiating']).count()
    conversion_rate = round((won_count / total_assigned * 100), 1) if total_assigned > 0 else 0.0

    my_quotations = Quotation.objects.filter(created_by=user).order_by('-created_at')[:6] if not user.is_superuser else Quotation.objects.all().order_by('-created_at')[:6]

    context = {
        'title': 'Agent Sales Cockpit',
        'total_assigned': total_assigned,
        'won_count': won_count,
        'in_pipeline': in_pipeline,
        'conversion_rate': conversion_rate,
        'pending_followups': pending_followups,
        'my_inquiries': my_inquiries.order_by('-created_at')[:8],
        'my_quotations': my_quotations,
    }
    return render(request, 'integrations/agent_dashboard.html', context)


# ==============================================================================
# 6. MANAGER APPROVALS INBOX (MATCHING LEFT SIDEBAR 'APPROVALS')
# ==============================================================================

@login_required
def manager_approvals_view(request):
    """
    Enterprise Manager Approvals queue for Quotation discounts (>15%),
    corporate credit terms, and driver emergency advances.
    """
    # Auto-seed sample approval if empty
    if not ApprovalRequest.objects.exists():
        ApprovalRequest.objects.create(
            approval_type='discount_override',
            title='18.5% Special Discount for PSG College Tech IV (120 Pax)',
            description='Requesting special volume group discount of 18.5% on 3-Day Ooty package to win contract against competitor.',
            requested_amount_or_pct='18.5% Discount',
            requested_by=request.user,
            status='pending'
        )
        ApprovalRequest.objects.create(
            approval_type='driver_advance',
            title='Driver Emergency Cash Advance - Ooty Convoy (Trip #TR-1238)',
            description='Driver Murugan requested ₹5,000 diesel top-up and permit emergency float for Valparai hill segment.',
            requested_amount_or_pct='₹5,000 Advance',
            requested_by=request.user,
            status='pending'
        )

    pending_approvals = ApprovalRequest.objects.filter(status='pending').order_by('-created_at')
    actioned_approvals = ApprovalRequest.objects.exclude(status='pending').order_by('-actioned_at')[:15]

    context = {
        'title': 'Manager Approvals Queue',
        'pending_approvals': pending_approvals,
        'actioned_approvals': actioned_approvals,
    }
    return render(request, 'integrations/approvals.html', context)


@csrf_exempt
@login_required
def api_action_approval(request, approval_id):
    """
    1-Click manager approval or rejection action.
    """
    if request.method != 'POST':
        return HttpResponseBadRequest("Only POST allowed")

    approval = get_object_or_404(ApprovalRequest, id=approval_id)
    action = request.POST.get('action', 'approve')
    notes = request.POST.get('manager_notes', '').strip()

    if action == 'approve':
        approval.status = 'approved'
        approval.manager_notes = notes or "Approved by Manager"
        approval.approved_by = request.user
        approval.actioned_at = timezone.now()
        approval.save()
        messages.success(request, f"Approval Request #{approval.approval_number} was officially APPROVED!")
    else:
        approval.status = 'rejected'
        approval.manager_notes = notes or "Rejected by Manager"
        approval.approved_by = request.user
        approval.actioned_at = timezone.now()
        approval.save()
        messages.warning(request, f"Approval Request #{approval.approval_number} was REJECTED.")

    return redirect('integrations:manager_approvals')


@csrf_exempt
def arattai_inbound_webhook_view(request):
    """
    Inbound webhook receiver for Zoho Arattai business platform.
    Automatically processes incoming guest messages, status lookups,
    and questions answered through Rathasārathi AI grounded RAG!
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'ok', 'gateway': 'Zoho Arattai Business Webhook Active'})

    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        data = request.POST.dict()

    from .arattai_service import ArattaiBusinessService
    result = ArattaiBusinessService.handle_inbound_webhook(data)
    return JsonResponse(result)

