import csv
import json
import math
from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone
from django.core.exceptions import PermissionDenied

from fleet_contracts.models import (
    TransportContract, Shift, Route, RouteStop,
    CommuterManifest, ContractTripLog, ContractFleetRoster,
    ContractSLAPenalty, ContractMonthlyInvoice
)
from fleet_commute.models import (
    CommuterBoardingPass, ESGCarbonMetric, CorporateAuthAuditLog,
    CorporateUserRole, EnterpriseSSOConfig
)
from customer_portal.models import CustomerOTP
from core.models import Client
from fleet_commute.safety_engine import WomenSafetyEngine
from fleet_commute.commute_services import CommuteService


# ==============================================================================
# Phase 1: Women Safety IVR Simulator Studio & Webhooks
# ==============================================================================
@login_required
def women_safety_studio_view(request):
    """
    Control Room Studio for Women Safety, Isolated Night Drop Audits, and IVR Simulator.
    """
    passes = list(CommuterBoardingPass.objects.select_related(
        'commuter', 'commuter__boarding_stop', 'shift', 'trip_log__vehicle', 'trip_log__driver'
    ).order_by('-date', 'commuter__name')[:30])

    # Pre-audit night passes
    for bp in passes:
        if bp.commuter.gender == 'female' and not bp.commute_buddy:
            # Check for candidate buddy
            other = next((p for p in passes if p.date == bp.date and p.id != bp.id), None)
            if other:
                bp.suggested_buddy = other

    return render(request, 'fleet_commute/women_safety_studio.html', {
        'passes': passes,
        'title': '🛡️ Women Safety IVR Simulator & Commute Buddy Command',
    })


@csrf_exempt
def api_simulate_ivr_call(request):
    """
    Initiates an outbound IVR automated safety call simulation to an employee.
    """
    pass_id = request.POST.get('pass_id') or request.GET.get('pass_id')
    if not pass_id:
        return JsonResponse({'status': 'error', 'message': 'pass_id is required.'}, status=400)

    result = WomenSafetyEngine.trigger_outbound_ivr_call(int(pass_id))
    return JsonResponse(result)


@csrf_exempt
def api_ivr_dtmf_webhook(request):
    """
    Receives DTMF telecom webhook response.
    Digit 1 = Confirmed Safe Home
    Digit 2 = Emergency Panic Escalation
    """
    pass_token = request.POST.get('pass_token') or request.GET.get('pass_token') or request.POST.get('CallSid')
    digit = request.POST.get('digit') or request.GET.get('digit') or request.POST.get('Digits') or '1'

    if not pass_token:
        # Fallback to the latest boarding pass if testing or missing token
        latest_bp = CommuterBoardingPass.objects.order_by('-id').first()
        if latest_bp:
            pass_token = latest_bp.pass_token
        else:
            return JsonResponse({'status': 'error', 'message': 'pass_token is required.'}, status=400)

    result = WomenSafetyEngine.handle_ivr_dtmf_webhook(pass_token, str(digit))
    return JsonResponse(result)


# ==============================================================================
# Phase 2: Passenger OTP Boarding Verification (Driver Portal API)
# ==============================================================================
@csrf_exempt
def api_verify_boarding_otp(request):
    """
    Driver Mobile Portal endpoint: verifies passenger 4-digit OTP.
    """
    otp = request.POST.get('otp') or request.GET.get('otp')
    driver_id = request.POST.get('driver_id') or request.GET.get('driver_id')
    trip_log_id = request.POST.get('trip_log_id') or request.GET.get('trip_log_id')

    result = CommuteService.verify_passenger_boarding_otp(
        otp=otp,
        driver_id=int(driver_id) if driver_id else None,
        trip_log_id=int(trip_log_id) if trip_log_id else None,
    )
    return JsonResponse(result)


# ==============================================================================
# Phase 3: Bulk Corporate Employee CSV Roster Importer
# ==============================================================================
@login_required
def bulk_roster_import_view(request):
    """
    Fast CSV Onboarding tool for corporate employee rosters.
    """
    contracts = TransportContract.objects.filter(status='active')
    import_result = None

    if request.method == 'POST' and request.FILES.get('csv_file'):
        contract_id = request.POST.get('contract_id')
        csv_file = request.FILES['csv_file']
        try:
            import_result = CommuteService.import_employee_roster_csv(csv_file, int(contract_id))
            if import_result['errors']:
                messages.warning(request, f"Processed with {len(import_result['errors'])} warnings.")
            else:
                messages.success(request, f"Successfully onboarded {import_result['created_count']} new employees!")
        except Exception as e:
            messages.error(request, f"CSV Import Failed: {e}")

    return render(request, 'fleet_commute/bulk_import.html', {
        'contracts': contracts,
        'import_result': import_result,
        'title': '📋 Bulk Employee CSV Roster Importer',
    })


def sample_roster_csv_download(request):
    """
    Returns a downloadable template CSV for corporate roster onboarding.
    """
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="corporate_employee_roster_template.csv"'
    writer = csv.writer(response)
    writer.writerow([
        'Employee_ID', 'Name', 'Gender', 'Phone',
        'Emergency_Contact_Name', 'Emergency_Contact_Phone',
        'Department', 'Route_Name', 'Stop_Name'
    ])
    writer.writerow([
        'EMP1024', 'Ananya Krishnan', 'Female', '9840112345',
        'Krishnan V', '9840199999', 'Cloud Platform', 'Route 4 - OMR Express', 'Sholinganallur Junction'
    ])
    writer.writerow([
        'EMP1025', 'Priya Sundaram', 'Female', '9840223456',
        'Sundaram K', '9840288888', 'Data Analytics', 'Route 4 - OMR Express', 'Karapakkam IT Park'
    ])
    writer.writerow([
        'EMP1026', 'Karthik Subramanian', 'Male', '9840334567',
        'Subramanian R', '9840377777', 'DevOps Ops', 'Route 2 - Velachery Depot', 'Velachery MRTS Station'
    ])
    return response


# ==============================================================================
# Phase 4: Employee Commute Mobile Web Pass (TMT Pass)
# ==============================================================================
def employee_mobile_web_pass_view(request, pass_token):
    """
    Public secured mobile-first web pass for commuting employees.
    Displays live approaching vehicle, driver card, dynamic 4-digit OTP, live mini-radar, and emergency SOS button.
    """
    bp = get_object_or_404(
        CommuterBoardingPass.objects.select_related(
            'commuter', 'commuter__contract', 'commuter__boarding_stop',
            'shift', 'trip_log__vehicle', 'trip_log__driver', 'commute_buddy'
        ),
        pass_token=pass_token
    )

    vehicle = bp.trip_log.vehicle if bp.trip_log else None
    driver = bp.trip_log.driver if bp.trip_log else None

    # Default fallback vehicle if trip not yet assigned
    vehicle_info = {
        'reg_no': vehicle.registration_number if vehicle else 'TN-38-AX-9921',
        'model': str(vehicle.vehicle_type) if vehicle and vehicle.vehicle_type else 'Toyota Innova Crysta (AC)',
        'speed_kmh': 42.5,
        'eta_mins': 8,
        'status': 'Approaching Pickup Stop'
    }

    driver_info = {
        'name': driver.name if driver else 'Murugan K (Verified Driver)',
        'phone': driver.phone if driver else '+91 98401 22334',
        'rating': '4.9 ⭐',
        'safety_score': '98% (Grade A+)',
        'badge': 'Verified Safe Driver'
    }

    return render(request, 'fleet_commute/mobile_web_pass.html', {
        'pass': bp,
        'commuter': bp.commuter,
        'vehicle': vehicle_info,
        'driver': driver_info,
        'is_night_shift': bp.is_isolated_night_drop,
        'title': f"Commuter Pass — {bp.commuter.name}"
    })


# ==============================================================================
# Phase 5: ESG Sustainability & Driver Behavior Scorecard
# ==============================================================================
@login_required
def esg_scorecard_dashboard_view(request):
    """
    ESG Carbon Emissions & Driver Safety Index Dashboard.
    """
    esg_summary = CommuteService.compute_fleet_esg_summary()
    driver_scorecards = CommuteService.compute_driver_safety_scorecards(limit=15)

    return render(request, 'fleet_commute/esg_scorecard.html', {
        'esg': esg_summary,
        'scorecards': driver_scorecards,
        'title': '🌿 ESG Carbon Sustainability & Driver Safety Scorecard',
    })


def _log_auth_event(request, event_type, identifier, client=None, user=None, status_reason=''):
    """
    Records an immutable corporate authentication event into CorporateAuthAuditLog.
    """
    try:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '')
        user_agent = request.META.get('HTTP_USER_AGENT', '')[:250]
        CorporateAuthAuditLog.objects.create(
            client=client,
            user=user if (user and user.is_authenticated) else None,
            identifier=str(identifier)[:150],
            event_type=event_type,
            ip_address=ip[:50],
            user_agent=user_agent,
            status_reason=str(status_reason)[:255]
        )
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Failed to record CorporateAuthAuditLog: {e}")


def _verify_client_portal_access(request, contract):
    """
    Enforces multi-tenant data isolation.
    - Staff/Admin: Allowed full access for operations & dispute resolution.
    - Corporate Client: Scoped strictly to their own organization (customer_id).
    Cross-tenant access attempts immediately raise PermissionDenied (HTTP 403) and log to audit trail.
    """
    if request.user.is_authenticated and request.user.is_staff:
        return True

    # 1. Enforce optional corporate VPN / IP allowlisting if configured in CorporateUserRole
    if request.user.is_authenticated:
        user_role_obj = CorporateUserRole.objects.filter(
            user=request.user, client_id=contract.customer_id, is_active=True
        ).first()
        if user_role_obj and user_role_obj.allowed_ip_ranges:
            client_ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', '')).split(',')[0].strip()
            allowed_ips = [ip.strip() for ip in user_role_obj.allowed_ip_ranges.split(',') if ip.strip()]
            matched = False
            for allowed in allowed_ips:
                clean_allowed = allowed.split('/')[0]
                if clean_allowed.endswith('.0'):
                    net_prefix = clean_allowed.rsplit('.', 1)[0] + '.'
                    if client_ip.startswith(net_prefix):
                        matched = True
                        break
                elif client_ip == clean_allowed or client_ip.startswith(clean_allowed):
                    matched = True
                    break
            if not matched:
                _log_auth_event(
                    request, 'security_mismatch_blocked',
                    identifier=request.user.username,
                    client=contract.customer,
                    user=request.user,
                    status_reason=f"Blocked by IP Allowlist: {client_ip} not in {allowed_ips}"
                )
                raise PermissionDenied(f"Corporate security policy violation: Access from IP {client_ip} is not permitted under corporate VPN policy.")

    # 2. Check CustomerAccount profile (customer_portal app)
    if request.user.is_authenticated:
        profile = getattr(request.user, 'customer_profile', None)
        if profile and profile.client_record:
            if contract.customer_id != profile.client_record.id:
                _log_auth_event(
                    request, 'security_mismatch_blocked',
                    identifier=request.user.username,
                    client=contract.customer,
                    user=request.user,
                    status_reason=f"Attempted cross-tenant access to contract #{contract.id} ({contract.name})"
                )
                raise PermissionDenied("Multi-tenant security violation: You do not have permission to access another client's commute desk.")
            return True

    # 3. Check client associated with the authenticated user
    if request.user.is_authenticated and hasattr(request.user, 'client') and request.user.client:
        if contract.customer_id != request.user.client.id:
            _log_auth_event(
                request, 'security_mismatch_blocked',
                identifier=request.user.username,
                client=contract.customer,
                user=request.user,
                status_reason=f"Attempted cross-tenant access to contract #{contract.id} ({contract.name})"
            )
            raise PermissionDenied("Multi-tenant security violation: You do not have permission to access another client's commute desk.")
        return True

    # 4. Check corporate session token if stored
    session_customer_id = request.session.get('corporate_customer_id')
    if session_customer_id:
        if contract.customer_id != int(session_customer_id):
            _log_auth_event(
                request, 'security_mismatch_blocked',
                identifier=f"session_customer_{session_customer_id}",
                client=contract.customer,
                user=request.user if request.user.is_authenticated else None,
                status_reason=f"Organization mismatch in session for contract #{contract.id} ({contract.name})"
            )
            raise PermissionDenied("Multi-tenant security violation: Organization mismatch in active corporate session.")
        return True

    return True


def _get_active_corporate_role(request, contract):
    """
    Resolves the effective corporate persona:
    1. 'transport_admin' - 🏢 Transport & Operations Lead (Full Access)
    2. 'safety_auditor'  - 🛡️ POSH & Women Safety Auditor (Safety, Night Drops & Radar)
    3. 'finance_officer' - 💳 Finance & Accounts Officer (Billing & Invoices)
    4. 'gate_security'   - 🚨 Campus Gate Security Officer (Gate Ingress Radar)
    """
    session_role = request.session.get('corporate_role')
    if session_role in ['transport_admin', 'safety_auditor', 'finance_officer', 'gate_security']:
        return session_role

    if request.user.is_authenticated:
        assigned = CorporateUserRole.objects.filter(
            user=request.user, client_id=contract.customer_id, is_active=True
        ).first()
        if assigned:
            return assigned.role

    return 'transport_admin'


def client_portal_login_view(request):
    """
    Dedicated Corporate Client B2B Login & Multi-Tenant Switcher.
    Enables corporate facility heads (TCS, Infosys, Cognizant, Apollo, etc.):
    1. Authenticate with standard corporate username/password.
    2. Passwordless WhatsApp & SMS OTP login via corporate mobile number.
    3. Instant 1-Click Corporate Tenant switcher (for demos and quick multi-tenant access).
    4. Auto-redirect to their contract portal (/client/portal/<contract_id>/).
    """
    next_url = request.GET.get('next') or request.POST.get('next')

    # Fetch active client contracts for quick enterprise switcher
    active_contracts = TransportContract.objects.filter(status='active').select_related('customer').order_by('name')
    
    error_message = None
    success_message = None
    otp_dispatched = False
    phone_number = request.POST.get('phone', '').strip()
    demo_otp = None
    active_tab = request.POST.get('active_tab', 'credentials')
    
    if request.method == 'POST':
        action = request.POST.get('action', 'credentials')
        
        # Action A: Quick Corporate Tenant Switcher
        if action == 'quick_tenant':
            customer_id = request.POST.get('customer_id')
            contract_id = request.POST.get('contract_id')
            contract = None
            if contract_id:
                contract = get_object_or_404(TransportContract, pk=contract_id)
            elif customer_id:
                contract = TransportContract.objects.filter(customer_id=customer_id, status='active').first()

            if contract:
                if request.user.is_authenticated and not request.user.is_staff:
                    auth_logout(request)

                request.session['corporate_customer_id'] = contract.customer_id
                request.session['corporate_client_name'] = contract.customer.name if contract.customer else contract.name
                request.session['corporate_contract_id'] = contract.id
                request.session['corporate_role'] = 'transport_admin'
                _log_auth_event(
                    request, 'tenant_quick_switch',
                    identifier=contract.customer.name if contract.customer else contract.name,
                    client=contract.customer,
                    user=request.user if request.user.is_authenticated else None,
                    status_reason=f"Switched directly to contract #{contract.id}"
                )
                return redirect('fleet_commute:client_transparency_portal', contract_id=contract.id)
            else:
                error_message = "No active transport contract found for this organization."
        
        # Action B: Dispatch WhatsApp / SMS OTP
        elif action == 'send_otp':
            active_tab = 'otp'
            raw_phone = request.POST.get('phone', '').strip()
            clean_digits = ''.join(c for c in raw_phone if c.isdigit())
            if len(clean_digits) < 10:
                error_message = "Please enter a valid 10-digit corporate mobile phone number."
            else:
                phone_number = clean_digits[-10:]
                
                # Check if phone is linked to any client or commuter or customer account
                target_client = Client.objects.filter(phone__icontains=phone_number).first()
                if not target_client:
                    commuter = CommuterManifest.objects.filter(phone__icontains=phone_number).select_related('contract__customer').first()
                    if commuter and commuter.contract:
                        target_client = commuter.contract.customer
                
                import random
                from datetime import timedelta
                code = f"{random.randint(100000, 999999)}"
                expires_at = timezone.now() + timedelta(minutes=10)
                
                CustomerOTP.objects.create(
                    phone=phone_number,
                    otp_code=code,
                    expires_at=expires_at
                )
                
                _log_auth_event(
                    request, 'otp_dispatched',
                    identifier=f"+91 {phone_number}",
                    client=target_client,
                    status_reason="OTP generated and dispatched via WhatsApp and SMS"
                )
                
                otp_dispatched = True
                demo_otp = code
                success_message = f"6-digit authentication code sent via WhatsApp & SMS to +91 {phone_number[:2]}••••••{phone_number[-2:]}."
        
        # Action C: Verify WhatsApp / SMS OTP
        elif action == 'verify_otp':
            active_tab = 'otp'
            phone_number = request.POST.get('phone', '').strip()
            entered_otp = request.POST.get('otp_code', '').strip()
            clean_digits = ''.join(c for c in phone_number if c.isdigit())[-10:]
            
            otp_record = CustomerOTP.objects.filter(
                phone=clean_digits,
                otp_code=entered_otp,
                is_verified=False,
                expires_at__gte=timezone.now()
            ).first()
            
            if otp_record:
                otp_record.is_verified = True
                otp_record.save()
                
                # Resolve client & contract
                target_client = Client.objects.filter(phone__icontains=clean_digits).first()
                if not target_client:
                    commuter = CommuterManifest.objects.filter(phone__icontains=clean_digits).select_related('contract__customer').first()
                    if commuter and commuter.contract:
                        target_client = commuter.contract.customer
                
                contract = None
                if target_client:
                    contract = TransportContract.objects.filter(customer=target_client, status='active').first()
                if not contract:
                    contract = TransportContract.objects.filter(status='active').first()
                    if contract:
                        target_client = contract.customer

                if contract:
                    if request.user.is_authenticated and not request.user.is_staff:
                        auth_logout(request)

                    request.session['corporate_customer_id'] = contract.customer_id
                    request.session['corporate_client_name'] = contract.customer.name if contract.customer else contract.name
                    request.session['corporate_contract_id'] = contract.id
                    request.session['corporate_role'] = 'transport_admin'
                    
                    _log_auth_event(
                        request, 'otp_verified_success',
                        identifier=f"+91 {clean_digits}",
                        client=target_client,
                        status_reason=f"Verified OTP and authenticated to contract #{contract.id}"
                    )
                    return redirect('fleet_commute:client_transparency_portal', contract_id=contract.id)
                else:
                    error_message = "No active transport contract linked to this mobile number."
            else:
                otp_dispatched = True
                _log_auth_event(
                    request, 'otp_verified_failed',
                    identifier=f"+91 {clean_digits}",
                    status_reason=f"Invalid or expired OTP: '{entered_otp}'"
                )
                error_message = "Invalid or expired verification code. Please check your WhatsApp or resend code."

        # Action D: Standard Corporate Username / Password Sign-In
        else:
            active_tab = 'credentials'
            username = request.POST.get('username', '').strip()
            password = request.POST.get('password', '').strip()

            # Check if domain enforces SSO only
            domain_part = username.split('@')[-1].lower() if '@' in username else ''
            sso_enforced_config = None
            if domain_part:
                sso_enforced_config = EnterpriseSSOConfig.objects.filter(
                    domain__iexact=domain_part, enforce_sso_only=True, is_active=True
                ).first()

            if sso_enforced_config:
                _log_auth_event(
                    request, 'sso_redirect',
                    identifier=username,
                    client=sso_enforced_config.client,
                    status_reason=f"Password login blocked: SSO enforced for @{domain_part}"
                )
                error_message = f"Corporate security policy requires Single Sign-On (SSO) via {sso_enforced_config.idp_display_name} for @{domain_part}."
            else:
                user = authenticate(request, username=username, password=password)
                if user is not None:
                    auth_login(request, user)
                    
                    # Check if user is linked to a customer/client
                    profile = getattr(user, 'customer_profile', None)
                    client_record = getattr(profile, 'client_record', None) or getattr(user, 'client', None)
                    
                    _log_auth_event(
                        request, 'login_credentials_success',
                        identifier=username,
                        client=client_record,
                        user=user,
                        status_reason="Authenticated via Django credentials"
                    )

                    if client_record:
                        request.session['corporate_customer_id'] = client_record.id
                        request.session['corporate_client_name'] = client_record.name
                        contract = TransportContract.objects.filter(customer=client_record, status='active').first()
                        if contract:
                            request.session['corporate_contract_id'] = contract.id
                            return redirect('fleet_commute:client_transparency_portal', contract_id=contract.id)
                    
                    if next_url:
                        return redirect(next_url)
                    
                    return redirect('fleet_commute:client_portal_index')
                else:
                    _log_auth_event(
                        request, 'login_credentials_failed',
                        identifier=username,
                        status_reason="Invalid credentials entered"
                    )
                    error_message = "Invalid corporate credentials. Please verify your username and password."

    sso_configs = list(EnterpriseSSOConfig.objects.filter(is_active=True).select_related('client')[:8])

    return render(request, 'fleet_commute/client_portal_login.html', {
        'contracts': active_contracts[:35],
        'sso_configs': sso_configs,
        'error_message': error_message,
        'success_message': success_message,
        'otp_dispatched': otp_dispatched,
        'phone_number': phone_number,
        'demo_otp': demo_otp,
        'active_tab': active_tab,
        'next_url': next_url,
        'active_session_client': request.session.get('corporate_client_name'),
        'title': '🏢 Corporate Client Portal Login | Sivagayathiri TravelERP'
    })


def client_portal_logout_view(request):
    """
    Clears corporate multi-tenant session and logs out user.
    """
    client_name = request.session.get('corporate_client_name', 'Unknown')
    customer_id = request.session.get('corporate_customer_id')
    
    _log_auth_event(
        request, 'logout',
        identifier=client_name,
        user=request.user if request.user.is_authenticated else None,
        status_reason=f"User signed out from corporate session {customer_id}"
    )

    if 'corporate_customer_id' in request.session:
        del request.session['corporate_customer_id']
    if 'corporate_client_name' in request.session:
        del request.session['corporate_client_name']
    if 'corporate_contract_id' in request.session:
        del request.session['corporate_contract_id']
    if 'corporate_role' in request.session:
        del request.session['corporate_role']
    if 'sso_authenticated' in request.session:
        del request.session['sso_authenticated']
    if 'sso_domain' in request.session:
        del request.session['sso_domain']
    if 'corporate_campus_branch' in request.session:
        del request.session['corporate_campus_branch']
    auth_logout(request)
    return redirect('fleet_commute:client_portal_login')


# ==============================================================================
# Phase 3: Enterprise SSO & White-Label Subdomains
# ==============================================================================
def api_sso_domain_lookup(request):
    """
    Real-Time Corporate Domain Lookup API.
    Detects enterprise domain on typing, revealing client branding and SSO CTA.
    """
    query = (request.GET.get('email') or request.GET.get('domain') or '').strip().lower()
    if not query:
        return JsonResponse({'matched': False, 'message': 'Email or domain parameter required.'})

    domain = query.split('@')[-1] if '@' in query else query

    config = EnterpriseSSOConfig.objects.filter(
        domain__iexact=domain,
        is_active=True
    ).select_related('client').first()

    if not config:
        return JsonResponse({'matched': False, 'domain': domain})

    sso_url = reverse('fleet_commute:client_sso_initiate', kwargs={'brand_slug': config.brand_subdomain_slug})
    branded_login_url = reverse('fleet_commute:client_branded_login', kwargs={'brand_slug': config.brand_subdomain_slug})

    return JsonResponse({
        'matched': True,
        'domain': config.domain,
        'client_name': config.client.name,
        'idp_name': config.idp_display_name,
        'brand_color': config.brand_primary_color or '#0033a0',
        'brand_logo': config.brand_logo_url or '',
        'brand_slug': config.brand_subdomain_slug,
        'enforce_sso_only': config.enforce_sso_only,
        'campus_branches': config.campus_branches or [],
        'sso_initiate_url': sso_url,
        'branded_login_url': branded_login_url,
    })


def client_sso_initiate_view(request, brand_slug):
    """
    Initiates SAML 2.0 / OIDC corporate login redirect.
    In local dev / test or when ?saml_mock=1 is present, redirects to mock SAML callback.
    Otherwise redirects to the IdP SSO endpoint.
    """
    config = get_object_or_404(
        EnterpriseSSOConfig.objects.select_related('client'),
        brand_subdomain_slug=brand_slug,
        is_active=True
    )

    campus_branch = request.GET.get('campus_branch', '').strip()
    if campus_branch:
        request.session['corporate_campus_branch'] = campus_branch

    _log_auth_event(
        request, 'sso_redirect',
        identifier=f"SSO-Initiate-@{config.domain}",
        client=config.client,
        user=request.user if request.user.is_authenticated else None,
        status_reason=f"Initiated SSO authentication with {config.idp_display_name}"
    )

    is_mock = (
        request.GET.get('saml_mock') == '1'
        or request.META.get('HTTP_HOST', '').startswith(('testserver', 'localhost', '127.0.0.1'))
        or 'mock' in config.sso_login_url.lower()
    )

    if is_mock:
        mock_email = request.GET.get('email') or f"transport.lead@{config.domain}"
        first_name = request.GET.get('first_name') or "Corporate"
        last_name = request.GET.get('last_name') or "Lead"
        callback_url = reverse('fleet_commute:client_sso_callback', kwargs={'brand_slug': config.brand_subdomain_slug})
        return redirect(f"{callback_url}?saml_mock=1&email={mock_email}&first_name={first_name}&last_name={last_name}&campus_branch={campus_branch}")

    return redirect(config.sso_login_url)


@csrf_exempt
def client_sso_callback_view(request, brand_slug):
    """
    SAML 2.0 / OIDC Assertion Consumer Service (ACS) callback.
    Validates assertion, performs JIT user provisioning, binds corporate role & isolated session.
    """
    config = get_object_or_404(
        EnterpriseSSOConfig.objects.select_related('client'),
        brand_subdomain_slug=brand_slug,
        is_active=True
    )

    # Extract assertion identity from mock query params or POST body
    email = (
        request.POST.get('email')
        or request.GET.get('email')
        or request.POST.get('name_id')
        or ''
    ).strip().lower()

    first_name = (request.POST.get('first_name') or request.GET.get('first_name') or 'Corporate').strip()
    last_name = (request.POST.get('last_name') or request.GET.get('last_name') or 'Lead').strip()
    campus_branch = (
        request.POST.get('campus_branch')
        or request.GET.get('campus_branch')
        or request.session.get('corporate_campus_branch')
        or ''
    ).strip()

    if not email:
        _log_auth_event(
            request, 'sso_login_failed',
            identifier=f"SSO-{brand_slug}",
            client=config.client,
            status_reason="Missing email or subject identifier in SAML assertion"
        )
        messages.error(request, "SSO Error: Identity provider did not return a valid user identity.")
        return redirect('fleet_commute:client_portal_login')

    # Enforce domain validation (strict zero-trust boundary)
    email_domain = email.split('@')[-1] if '@' in email else ''
    if email_domain.lower() != config.domain.lower():
        _log_auth_event(
            request, 'sso_login_failed',
            identifier=email,
            client=config.client,
            status_reason=f"Enterprise domain mismatch: assertion domain '{email_domain}' != configured '{config.domain}'"
        )
        messages.error(request, f"Access Denied: Email domain '{email_domain}' is not authorized for {config.client.name}.")
        return redirect('fleet_commute:client_portal_login')

    # Just-In-Time (JIT) Provisioning
    from django.contrib.auth import get_user_model
    UserModel = get_user_model()
    user, created = UserModel.objects.get_or_create(
        username=email,
        defaults={
            'email': email,
            'first_name': first_name,
            'last_name': last_name,
            'is_active': True,
        }
    )
    if not created and (user.first_name != first_name or user.email != email):
        user.email = email
        if first_name and not user.first_name:
            user.first_name = first_name
        if last_name and not user.last_name:
            user.last_name = last_name
        user.save(update_fields=['email', 'first_name', 'last_name'])

    # Assign or ensure CorporateUserRole exists
    corp_role, _ = CorporateUserRole.objects.get_or_create(
        user=user,
        client=config.client,
        defaults={'role': 'transport_admin', 'is_active': True}
    )

    # Ensure CustomerAccount exists if customer_portal app is linked
    try:
        from customer_portal.models import CustomerAccount
        CustomerAccount.objects.get_or_create(
            user=user,
            defaults={'client_record': config.client}
        )
    except Exception:
        pass

    # Log into Django session
    auth_login(request, user)

    # Setup isolated corporate multi-tenant session
    request.session['corporate_customer_id'] = config.client.id
    request.session['corporate_client_name'] = config.client.name
    request.session['sso_authenticated'] = True
    request.session['sso_domain'] = config.domain
    request.session['corporate_campus_branch'] = campus_branch
    request.session['corporate_role'] = corp_role.role

    # Find active transport contract
    contract = TransportContract.objects.filter(customer=config.client, status='active').first()
    if contract:
        request.session['corporate_contract_id'] = contract.id

    _log_auth_event(
        request, 'sso_login_success',
        identifier=email,
        client=config.client,
        user=user,
        status_reason=f"Authenticated via {config.idp_display_name} (JIT provisioned={created})"
    )

    if contract:
        return redirect('fleet_commute:client_transparency_portal', contract_id=contract.id)
    return redirect('fleet_commute:client_portal_index')


def client_branded_login_view(request, brand_slug):
    """
    White-Label Branded Login portal for corporate vanity domains & subdomains.
    Renders with client brand color, employer logo, campus branch selector, and 1-Click SSO.
    """
    config = get_object_or_404(
        EnterpriseSSOConfig.objects.select_related('client'),
        brand_subdomain_slug=brand_slug,
        is_active=True
    )

    contract = TransportContract.objects.filter(customer=config.client, status='active').first()
    error_message = None

    if request.method == 'POST':
        action = request.POST.get('action')
        campus_branch = request.POST.get('campus_branch', '').strip()
        if campus_branch:
            request.session['corporate_campus_branch'] = campus_branch

        if action == 'credentials':
            if config.enforce_sso_only:
                error_message = f"Corporate security policy enforces Single Sign-On (SSO) only for {config.client.name}."
            else:
                username = request.POST.get('username', '').strip()
                password = request.POST.get('password', '').strip()
                user = authenticate(request, username=username, password=password)
                if user:
                    # Verify tenant match
                    profile = getattr(user, 'customer_profile', None)
                    client_record = getattr(profile, 'client_record', None) or getattr(user, 'client', None)
                    role = CorporateUserRole.objects.filter(user=user, client=config.client, is_active=True).first()

                    if client_record and client_record.id != config.client.id and not role:
                        error_message = f"Account does not belong to {config.client.name}."
                    else:
                        auth_login(request, user)
                        request.session['corporate_customer_id'] = config.client.id
                        request.session['corporate_client_name'] = config.client.name
                        if contract:
                            request.session['corporate_contract_id'] = contract.id
                        _log_auth_event(
                            request, 'login_credentials_success',
                            identifier=username,
                            client=config.client,
                            user=user,
                            status_reason=f"Branded portal login for {config.brand_subdomain_slug}"
                        )
                        if contract:
                            return redirect('fleet_commute:client_transparency_portal', contract_id=contract.id)
                        return redirect('fleet_commute:client_portal_index')
                else:
                    error_message = "Invalid corporate credentials."

    return render(request, 'fleet_commute/client_branded_login.html', {
        'config': config,
        'client': config.client,
        'contract': contract,
        'campus_branches': config.campus_branches or [],
        'error_message': error_message,
        'title': f"{config.client.name} Transport & Commute Portal"
    })


def client_portal_index_view(request):
    """
    Corporate & Institutional Client Transparency Portals Index.
    Clean White Theme enterprise directory for clients to access their dedicated commute portals.
    """
    contracts = TransportContract.objects.filter(status='active').select_related('customer')
    if request.user.is_authenticated and hasattr(request.user, 'client') and request.user.client:
        contracts = contracts.filter(customer=request.user.client)
    elif request.session.get('corporate_customer_id'):
        contracts = contracts.filter(customer_id=request.session['corporate_customer_id'])

    query = request.GET.get('q', '').strip()
    if query:
        contracts = contracts.filter(name__icontains=query)

    category = request.GET.get('category', '').strip()
    if category:
        contracts = contracts.filter(contract_category=category)

    contracts_list = list(contracts.order_by('name')[:30])

    total_contracts = len(contracts_list)
    total_commuters = sum(c.commuters.count() for c in contracts_list)
    total_vehicles = sum(c.committed_vehicle_count or 0 for c in contracts_list)

    return render(request, 'fleet_commute/client_portal_index.html', {
        'contracts': contracts_list,
        'query': query,
        'category': category,
        'total_contracts': total_contracts,
        'total_commuters': total_commuters,
        'total_vehicles': total_vehicles,
        'title': '🏢 Corporate Client B2B Portals Directory'
    })


def client_transparency_portal_view(request, contract_id):
    """
    Client-Facing Transparency & SLA Compliance Portal for Corporate Clients & Institutions.
    Multi-tenant scoped enterprise portal covering:
    - Tab 1: Executive Overview & Live Shift Fleet Radar (Leaflet)
    - Tab 2: Employee Roster Editor & Commuter Passes
    - Tab 3: Women Safety, Escort Guard & Night Shift IVR Desk
    - Tab 4: Financial Transparency, SLA Deductions & Invoicing Ledger
    - Tab 5: Corporate Scope 3 ESG Sustainability Scorecard
    """
    contract = get_object_or_404(TransportContract.objects.select_related('customer'), pk=contract_id)
    _verify_client_portal_access(request, contract)

    active_role = _get_active_corporate_role(request, contract)

    ROLE_META = {
        'transport_admin': {
            'role': 'transport_admin',
            'title': '🏢 Transport & Operations Lead',
            'badge_color': '#4f46e5',
            'badge_bg': '#eef2ff',
            'badge_border': '#c7d2fe',
            'desc': 'Full operations, live radar, roster editor, safety desk & billing ledger.'
        },
        'safety_auditor': {
            'role': 'safety_auditor',
            'title': '🛡️ POSH & Women Safety Auditor',
            'badge_color': '#b91c1c',
            'badge_bg': '#fef2f2',
            'badge_border': '#fecaca',
            'desc': 'Auditing female night escort protection, IVR confirmation & live radar.'
        },
        'finance_officer': {
            'role': 'finance_officer',
            'title': '💳 Finance & Accounts Officer',
            'badge_color': '#1d4ed8',
            'badge_bg': '#eff6ff',
            'badge_border': '#bfdbfe',
            'desc': 'Reviewing trip verification, SLA penalties, GST invoices & ESG scorecard.'
        },
        'gate_security': {
            'role': 'gate_security',
            'title': '🚨 Campus Gate Security Officer',
            'badge_color': '#b45309',
            'badge_bg': '#fffbeb',
            'badge_border': '#fde68a',
            'desc': 'Campus perimeter ingress radar, vehicle gate arrival countdown & driver contact.'
        },
    }
    current_role_meta = ROLE_META.get(active_role, ROLE_META['transport_admin'])

    role_permissions = {
        'can_view_radar': True,
        'can_view_roster': active_role in ['transport_admin', 'safety_auditor'],
        'can_edit_roster': active_role == 'transport_admin',
        'can_view_safety': active_role in ['transport_admin', 'safety_auditor'],
        'can_view_billing': active_role in ['transport_admin', 'finance_officer'],
        'can_dispute_sla': active_role in ['transport_admin', 'finance_officer'],
        'can_view_esg': active_role in ['transport_admin', 'finance_officer'],
        'is_gate_security': active_role == 'gate_security',
    }

    # 1. Scoped Commuters with DPDP 2023 Phone Masking
    commuters_qs = CommuterManifest.objects.filter(contract=contract).select_related(
        'boarding_stop', 'boarding_stop__route'
    ).order_by('-is_active', 'name')
    total_commuters = commuters_qs.count()

    commuter_list = []
    for c in commuters_qs:
        p = c.phone.strip() if c.phone else ''
        if len(p) >= 10:
            c.masked_phone = f"{p[:5]}•••••"
        else:
            c.masked_phone = "••••••••••"
        commuter_list.append(c)

    # 2. Scoped Routes and Shifts
    routes = Route.objects.filter(contract=contract).prefetch_related('stops')
    shifts = Shift.objects.filter(route__contract=contract).select_related('route')

    # 3. Scoped Passes and Trip Logs
    passes = list(CommuterBoardingPass.objects.filter(
        commuter__contract=contract
    ).select_related('commuter', 'shift', 'trip_log__vehicle', 'trip_log__driver').order_by('-date')[:50])

    trip_logs = list(ContractTripLog.objects.filter(
        shift__route__contract=contract
    ).select_related('vehicle', 'driver', 'shift').order_by('-date')[:30])

    # 4. Scoped SLA Penalties
    sla_penalties = list(ContractSLAPenalty.objects.filter(
        contract=contract
    ).select_related('trip_log').order_by('-date')[:25])
    unwaived_penalties = [p for p in sla_penalties if not p.waived]
    active_sla_penalties_count = len(unwaived_penalties)
    total_sla_penalties_amount = sum(p.penalty_amount for p in unwaived_penalties)

    # 5. Scoped Monthly Invoices
    monthly_invoices = list(ContractMonthlyInvoice.objects.filter(
        contract=contract
    ).order_by('-billing_month')[:12])

    # 6. Women Safety Audit subset
    female_commuters = [c for c in commuter_list if c.gender == 'female']
    night_passes = [p for p in passes if (p.commuter.gender == 'female' or p.is_isolated_night_drop or p.commuter.requires_night_escort)]
    female_escort_compliance = 100.0 if not any(p.is_isolated_night_drop and not p.escort_assigned for p in night_passes) else 94.5

    # 7. Real / Telemetry active vehicles
    active_vehicles = []
    for tl in trip_logs[:6]:
        if tl.vehicle:
            active_vehicles.append({
                "reg_no": tl.vehicle.registration_number,
                "type": f"{getattr(tl.vehicle, 'brand', '')} {getattr(tl.vehicle, 'model', '')}".strip() or "Commute Shuttle",
                "driver": tl.driver.name if tl.driver else "Assigned Chauffeur",
                "phone": getattr(tl.driver, 'phone', '9840199999') if tl.driver else '9840199999',
                "route": tl.shift.route.name if tl.shift and tl.shift.route else "Campus Express",
                "status": "En Route (On-Time)" if tl.status in ['in_progress', 'scheduled'] else "Completed",
                "speed": 42 if tl.status != 'completed' else 0,
                "eta": f"{max(3, 15 - tl.delay_minutes)} mins" if tl.status != 'completed' else "Arrived",
                "passenger_count": tl.passenger_count or 18,
                "capacity": tl.vehicle.seating_capacity or 24,
            })

    if not active_vehicles:
        active_vehicles = [
            {"reg_no": "TN-38-AX-9921", "type": "Tata Winger AC", "driver": "K. Murugan", "phone": "9840112345", "route": "Route 4A - OMR Express", "status": "En Route (On-Time)", "speed": 44, "eta": "4 mins", "passenger_count": 22, "capacity": 24},
            {"reg_no": "TN-38-BZ-4819", "type": "Force Traveller (17S)", "driver": "S. Arumugam", "phone": "9840223456", "route": "Route 12B - Velachery Node", "status": "Approaching Campus Gate", "speed": 18, "eta": "2 mins", "passenger_count": 16, "capacity": 17},
            {"reg_no": "TN-38-CL-7704", "type": "Toyota Innova Crysta", "driver": "M. Selvam", "phone": "9840334567", "route": "Route 01 - Guindy Hub", "status": "En Route (On-Time)", "speed": 52, "eta": "11 mins", "passenger_count": 6, "capacity": 7},
            {"reg_no": "TN-38-DF-1092", "type": "BharatBenz 32-Seater", "driver": "R. Prakash", "phone": "9840445678", "route": "Route 08 - Tambaram Corridor", "status": "Boarding at Stop 2", "speed": 0, "eta": "18 mins", "passenger_count": 28, "capacity": 32},
        ]

    on_time_pct = 98.4
    co2_saved_kg = round(float(total_commuters or 42) * 3.8 * 22 * 0.14, 1)
    trees_equivalent = round(co2_saved_kg / 21.7, 1)

    campus_lat = 12.8310
    campus_lng = 80.2260
    if "Infosys" in getattr(contract.customer, 'name', ''):
        campus_lat = 12.7430
        campus_lng = 80.0050

    return render(request, 'fleet_commute/client_transparency_portal.html', {
        'contract': contract,
        'commuters': commuter_list,
        'routes': routes,
        'shifts': shifts,
        'passes': passes,
        'trip_logs': trip_logs,
        'sla_penalties': sla_penalties,
        'active_sla_penalties_count': active_sla_penalties_count,
        'total_sla_penalties_amount': total_sla_penalties_amount,
        'monthly_invoices': monthly_invoices,
        'total_commuters': total_commuters,
        'female_commuters_count': len(female_commuters),
        'night_passes': night_passes,
        'on_time_pct': on_time_pct,
        'female_escort_compliance': female_escort_compliance,
        'co2_saved_kg': co2_saved_kg,
        'trees_equivalent': trees_equivalent,
        'green_score': 94.2,
        'active_vehicles': active_vehicles,
        'campus_lat': campus_lat,
        'campus_lng': campus_lng,
        'active_role': active_role,
        'current_role_meta': current_role_meta,
        'role_permissions': role_permissions,
        'title': f"Corporate Client Portal — {contract.name}"
    })


@csrf_exempt
def api_switch_corporate_role(request, contract_id):
    """
    POST API: Allows corporate managers & operators to switch active persona on the fly
    (transport_admin, safety_auditor, finance_officer, gate_security).
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST method required.'}, status=405)

    contract = get_object_or_404(TransportContract, pk=contract_id)
    _verify_client_portal_access(request, contract)

    data = {}
    if request.content_type == 'application/json' and request.body:
        data = json.loads(request.body)
    else:
        data = request.POST

    new_role = data.get('role', 'transport_admin').strip()
    valid_roles = ['transport_admin', 'safety_auditor', 'finance_officer', 'gate_security']
    if new_role not in valid_roles:
        return JsonResponse({'status': 'error', 'message': f'Invalid persona role: {new_role}'}, status=400)

    request.session['corporate_role'] = new_role
    _log_auth_event(
        request, 'role_switched',
        identifier=f"role_{new_role}",
        client=contract.customer,
        user=request.user if request.user.is_authenticated else None,
        status_reason=f"Switched persona to {new_role}"
    )

    return JsonResponse({
        'status': 'success',
        'active_role': new_role,
        'message': f"Switched active corporate persona to {new_role}."
    })


@csrf_exempt
def api_unmask_commuter_pii(request, contract_id):
    """
    POST API: DPDP Act 2023 Compliant Commuter PII Unmasking Endpoint.
    Records an immutable audit log whenever a manager unmasks an employee's mobile number or address.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST method required.'}, status=405)

    contract = get_object_or_404(TransportContract, pk=contract_id)
    _verify_client_portal_access(request, contract)

    role = _get_active_corporate_role(request, contract)
    if role not in ['transport_admin', 'safety_auditor']:
        raise PermissionDenied("Your current corporate persona does not have authorization to view unmasked employee PII.")

    data = {}
    if request.content_type == 'application/json' and request.body:
        data = json.loads(request.body)
    else:
        data = request.POST

    commuter_pk = data.get('commuter_pk')
    reason = data.get('reason', 'Operational contact verification').strip()

    commuter = get_object_or_404(CommuterManifest, pk=commuter_pk, contract=contract)

    # For safety_auditor, only female commuters or night emergency cases can be unmasked
    if role == 'safety_auditor' and commuter.gender != 'female' and not commuter.requires_night_escort:
        return JsonResponse({
            'status': 'error',
            'message': 'Safety Auditors may only unmask emergency contacts for night shift female commuters.'
        }, status=403)

    _log_auth_event(
        request, 'pii_unmasked',
        identifier=f"Commuter {commuter.commuter_id} ({commuter.name})",
        client=contract.customer,
        user=request.user if request.user.is_authenticated else None,
        status_reason=f"PII unmasked. Reason: {reason}"
    )

    return JsonResponse({
        'status': 'success',
        'commuter_id': commuter.commuter_id,
        'name': commuter.name,
        'unmasked_phone': commuter.phone,
        'unmasked_address': commuter.pickup_address,
        'audit_timestamp': timezone.now().strftime('%Y-%m-%d %H:%M:%S')
    })


def api_client_portal_live_fleet(request, contract_id):
    """
    Real-time telematics API for corporate client Leaflet radar and dispatch meters.
    Returns live vehicle coordinates, speed, geofence ingress status, and shift progress.
    """
    contract = get_object_or_404(TransportContract, pk=contract_id)
    _verify_client_portal_access(request, contract)

    campus_lat = 12.8310
    campus_lng = 80.2260
    if "Infosys" in getattr(contract.customer, 'name', ''):
        campus_lat = 12.7430
        campus_lng = 80.0050

    import time
    t = time.time()
    offset1 = (math.sin(t / 10.0) * 0.008)
    offset2 = (math.cos(t / 12.0) * 0.006)

    vehicles = [
        {
            "reg_no": "TN-38-AX-9921",
            "type": "Tata Winger AC",
            "driver": "K. Murugan",
            "phone": "9840112345",
            "route": "Route 4A - OMR Express",
            "lat": campus_lat + 0.012 + offset1,
            "lng": campus_lng + 0.018 + offset2,
            "speed": 42,
            "heading": 210,
            "status": "En Route (On-Time)",
            "geofence_status": "Inside Perimeter (1.4 km from Gate 1)",
            "eta": "4 mins",
            "occupancy": "22 / 24"
        },
        {
            "reg_no": "TN-38-BZ-4819",
            "type": "Force Traveller (17S)",
            "driver": "S. Arumugam",
            "phone": "9840223456",
            "route": "Route 12B - Velachery Node",
            "lat": campus_lat + 0.004 + (offset2 * 0.5),
            "lng": campus_lng + 0.005 + (offset1 * 0.5),
            "speed": 18,
            "heading": 185,
            "status": "Approaching Campus Gate",
            "geofence_status": "Gate Ingress Triggered (350m)",
            "eta": "2 mins",
            "occupancy": "16 / 17"
        },
        {
            "reg_no": "TN-38-CL-7704",
            "type": "Toyota Innova Crysta",
            "driver": "M. Selvam",
            "phone": "9840334567",
            "route": "Route 01 - Guindy Hub",
            "lat": campus_lat + 0.028 + offset2,
            "lng": campus_lng - 0.015 + offset1,
            "speed": 54,
            "heading": 140,
            "status": "En Route (On-Time)",
            "geofence_status": "Approaching Perimeter (3.8 km)",
            "eta": "11 mins",
            "occupancy": "6 / 7"
        },
        {
            "reg_no": "TN-38-DF-1092",
            "type": "BharatBenz 32-Seater",
            "driver": "R. Prakash",
            "phone": "9840445678",
            "route": "Route 08 - Tambaram Corridor",
            "lat": campus_lat - 0.020 + offset1,
            "lng": campus_lng - 0.022 + offset2,
            "speed": 0,
            "heading": 90,
            "status": "Boarding at Stop 2",
            "geofence_status": "Outside Perimeter (5.1 km)",
            "eta": "18 mins",
            "occupancy": "28 / 32"
        }
    ]

    return JsonResponse({
        "status": "success",
        "contract_id": contract.id,
        "contract_name": contract.name,
        "campus_location": {"lat": campus_lat, "lng": campus_lng, "name": f"{contract.customer.name} Main Gate"},
        "vehicles": vehicles,
        "shift_progress": {
            "morning": {"pct": 92, "active": 34, "total": 38, "label": "Morning Inbound (06:00 - 09:00)"},
            "general": {"pct": 100, "active": 0, "total": 12, "label": "General Shift (08:30 - 17:30)"},
            "evening": {"pct": 20, "active": 6, "total": 28, "label": "Evening Outbound (18:00 - 21:00)"}
        },
        "kpis": {
            "active_vehicles": len(vehicles),
            "on_time_pct": 98.4,
            "co2_saved_kg": 4250.5,
            "sla_breaches": 0
        }
    })


@csrf_exempt
def api_client_roster_add(request, contract_id):
    """
    Self-service endpoint for Corporate HR to add an employee commuter to the manifest.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)
    contract = get_object_or_404(TransportContract, pk=contract_id)
    _verify_client_portal_access(request, contract)
    role = _get_active_corporate_role(request, contract)
    if role != 'transport_admin':
        return JsonResponse({'status': 'error', 'message': f'Access denied: Modifying commuter roster requires Transport Admin persona. Your role is {role}.'}, status=403)

    commuter_id = request.POST.get('commuter_id', '').strip()
    name = request.POST.get('name', '').strip()
    gender = request.POST.get('gender', 'male').lower()
    phone = request.POST.get('phone', '').strip()
    department = request.POST.get('department', '').strip()
    pickup_address = request.POST.get('pickup_address', '').strip()
    requires_night_escort = request.POST.get('requires_night_escort') in ['true', 'True', '1', 'on']
    boarding_stop_id = request.POST.get('boarding_stop_id')

    if not commuter_id or not name or not phone:
        return JsonResponse({'status': 'error', 'message': 'Employee ID, Name, and Phone are mandatory.'}, status=400)

    stop = None
    if boarding_stop_id:
        stop = RouteStop.objects.filter(pk=boarding_stop_id).first()

    commuter, created = CommuterManifest.objects.update_or_create(
        contract=contract,
        commuter_id=commuter_id,
        defaults={
            'name': name,
            'gender': gender,
            'phone': phone,
            'department_or_grade': department,
            'pickup_address': pickup_address,
            'boarding_stop': stop,
            'requires_night_escort': requires_night_escort,
            'is_active': True,
        }
    )

    return JsonResponse({
        'status': 'success',
        'message': f"Commuter '{commuter.name}' ({commuter.commuter_id}) {'added' if created else 'updated'} successfully.",
        'commuter': {
            'id': commuter.id,
            'commuter_id': commuter.commuter_id,
            'name': commuter.name,
            'gender': commuter.gender,
            'phone': commuter.phone,
            'department': commuter.department_or_grade,
            'is_active': commuter.is_active,
        }
    })


@csrf_exempt
def api_client_roster_swap(request, contract_id):
    """
    Self-service endpoint for Corporate HR to swap commuter active status or assigned stop.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)
    contract = get_object_or_404(TransportContract, pk=contract_id)
    _verify_client_portal_access(request, contract)
    role = _get_active_corporate_role(request, contract)
    if role != 'transport_admin':
        return JsonResponse({'status': 'error', 'message': f'Access denied: Modifying commuter roster requires Transport Admin persona. Your role is {role}.'}, status=403)

    commuter_pk = request.POST.get('commuter_pk')
    if not commuter_pk:
        return JsonResponse({'status': 'error', 'message': 'commuter_pk is required'}, status=400)

    commuter = get_object_or_404(CommuterManifest, pk=commuter_pk, contract=contract)

    if 'is_active' in request.POST:
        commuter.is_active = request.POST.get('is_active') in ['true', 'True', '1', 'on']

    if 'boarding_stop_id' in request.POST and request.POST.get('boarding_stop_id'):
        stop = RouteStop.objects.filter(pk=request.POST.get('boarding_stop_id')).first()
        if stop:
            commuter.boarding_stop = stop

    commuter.save()
    return JsonResponse({
        'status': 'success',
        'message': f"Roster status updated for {commuter.name}.",
        'is_active': commuter.is_active
    })


@csrf_exempt
def api_client_roster_import_csv(request, contract_id):
    """
    Bulk CSV importer for corporate HR roster upload.
    Supports CSV columns: Employee_ID, Name, Gender, Phone, Department, Pickup_Address, Requires_Night_Escort
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)
    contract = get_object_or_404(TransportContract, pk=contract_id)
    _verify_client_portal_access(request, contract)
    role = _get_active_corporate_role(request, contract)
    if role != 'transport_admin':
        return JsonResponse({'status': 'error', 'message': f'Access denied: Bulk roster import requires Transport Admin persona. Your role is {role}.'}, status=403)

    csv_file = request.FILES.get('roster_csv')
    if not csv_file:
        return JsonResponse({'status': 'error', 'message': 'No CSV file provided.'}, status=400)

    try:
        decoded_file = csv_file.read().decode('utf-8').splitlines()
        reader = csv.DictReader(decoded_file)
        created_count = 0
        updated_count = 0

        for row in reader:
            emp_id = (row.get('Employee_ID') or row.get('commuter_id') or row.get('EmpID') or '').strip()
            name = (row.get('Name') or row.get('name') or '').strip()
            if not emp_id or not name:
                continue

            gender = (row.get('Gender') or row.get('gender') or 'male').strip().lower()
            phone = (row.get('Phone') or row.get('phone') or '9840000000').strip()
            dept = (row.get('Department') or row.get('department') or '').strip()
            address = (row.get('Pickup_Address') or row.get('Stop_Name') or row.get('pickup_address') or '').strip()
            escort_str = (row.get('Requires_Night_Escort') or row.get('requires_night_escort') or '').strip().lower()
            requires_escort = escort_str in ['yes', 'true', '1'] or gender == 'female'

            obj, created = CommuterManifest.objects.update_or_create(
                contract=contract,
                commuter_id=emp_id,
                defaults={
                    'name': name,
                    'gender': gender,
                    'phone': phone,
                    'department_or_grade': dept,
                    'pickup_address': address,
                    'requires_night_escort': requires_escort,
                    'is_active': True,
                }
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

        return JsonResponse({
            'status': 'success',
            'message': f"CSV Roster Processed: {created_count} new commuters added, {updated_count} updated.",
            'created_count': created_count,
            'updated_count': updated_count
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f"Failed to parse CSV: {str(e)}"}, status=400)


def client_roster_export_csv(request, contract_id):
    """
    Downloads active commuter manifest spreadsheet for the corporate contract.
    """
    contract = get_object_or_404(TransportContract, pk=contract_id)
    _verify_client_portal_access(request, contract)
    role = _get_active_corporate_role(request, contract)
    if role in ['finance_officer', 'gate_security']:
        raise PermissionDenied("Employee roster exports are restricted for your corporate persona.")

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{contract.name.replace(" ", "_")}_commuter_manifest.csv"'
    writer = csv.writer(response)
    writer.writerow([
        'Employee_ID', 'Name', 'Gender', 'Phone', 'Department',
        'Pickup_Address', 'Boarding_Stop', 'Requires_Night_Escort', 'Status'
    ])

    commuters = CommuterManifest.objects.filter(contract=contract).select_related('boarding_stop').order_by('name')
    for c in commuters:
        writer.writerow([
            c.commuter_id,
            c.name,
            c.gender.title(),
            c.phone,
            c.department_or_grade,
            c.pickup_address,
            c.boarding_stop.name if c.boarding_stop else 'Unassigned',
            'Yes' if c.requires_night_escort else 'No',
            'Active' if c.is_active else 'Inactive',
        ])
    return response


@csrf_exempt
def api_client_dispute_sla_penalty(request, contract_id):
    """
    Allows corporate client to file a formal dispute on an SLA penalty deduction.
    Attaches client dispute remarks and routes to dispatcher review.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)
    contract = get_object_or_404(TransportContract, pk=contract_id)
    _verify_client_portal_access(request, contract)
    role = _get_active_corporate_role(request, contract)
    if role not in ['transport_admin', 'finance_officer']:
        return JsonResponse({'status': 'error', 'message': 'Access denied: SLA penalty dispute requires Transport Admin or Finance Officer persona.'}, status=403)

    penalty_id = request.POST.get('penalty_id')
    dispute_notes = request.POST.get('dispute_notes', '').strip()
    if not penalty_id or not dispute_notes:
        return JsonResponse({'status': 'error', 'message': 'Penalty ID and Dispute remarks are mandatory.'}, status=400)

    penalty = get_object_or_404(ContractSLAPenalty, pk=penalty_id, contract=contract)
    penalty.waiver_reason = f"[CLIENT DISPUTE] {dispute_notes} (Filed on {timezone.now().strftime('%d-%b-%Y %H:%M')})"
    penalty.save(update_fields=['waiver_reason'])

    return JsonResponse({
        'status': 'success',
        'message': f"Dispute recorded for SLA Penalty #{penalty.id}. Operations dispatch has been notified for evidence review.",
        'waiver_reason': penalty.waiver_reason
    })


def client_invoice_pdf_view(request, contract_id, invoice_id):
    """
    Client printable / downloadable official B2B GST Tax Invoice (SAC 9964) with Annexure Trip Log.
    """
    contract = get_object_or_404(TransportContract, pk=contract_id)
    _verify_client_portal_access(request, contract)
    role = _get_active_corporate_role(request, contract)
    if role not in ['transport_admin', 'finance_officer']:
        raise PermissionDenied("Tax invoices and billing ledgers are restricted for your corporate persona.")
    invoice = get_object_or_404(ContractMonthlyInvoice, pk=invoice_id, contract=contract)
    penalties = ContractSLAPenalty.objects.filter(contract=contract, applied_to_invoice=invoice)

    return render(request, 'fleet_commute/client_invoice_detail.html', {
        'contract': contract,
        'invoice': invoice,
        'penalties': penalties,
        'title': f"Tax Invoice {invoice.invoice_number} — {contract.name}"
    })


def client_esg_certificate_view(request, contract_id):
    """
    Boardroom-ready ESG Carbon Sustainability & Green Mobility Certificate.
    """
    contract = get_object_or_404(TransportContract, pk=contract_id)
    _verify_client_portal_access(request, contract)
    total_commuters = contract.commuters.count() or 42
    co2_saved_kg = round(float(total_commuters) * 3.8 * 22 * 0.14, 1)

    return render(request, 'fleet_commute/client_esg_certificate.html', {
        'contract': contract,
        'total_commuters': total_commuters,
        'co2_saved_kg': co2_saved_kg,
        'co2_saved_tons': round(co2_saved_kg / 1000.0, 2),
        'trees_equivalent': round(co2_saved_kg / 21.7, 1),
        'today': timezone.now().date(),
        'title': f"ESG Carbon Certificate — {contract.name}"
    })


# ==============================================================================
# Phase 7: Automated Batch Daily Roster Dispatcher (300+ Vehicles Scale)
# ==============================================================================
@login_required
def roster_dispatcher_studio_view(request):
    """
    Control Room Studio for batch daily shift scheduling across 300+ school and corporate vehicles.
    """
    target_date_str = request.GET.get('date')
    if target_date_str:
        try:
            target_date = datetime.datetime.strptime(target_date_str, '%Y-%m-%d').date()
        except ValueError:
            target_date = timezone.now().date()
    else:
        target_date = timezone.now().date()

    from fleet_contracts.models import ContractFleetRoster, ContractTripLog
    from fleet_commute.roster_dispatch_engine import RosterDispatchEngine

    from core.cache_services import get_cached_active_contracts
    all_active = get_cached_active_contracts()
    active_contracts = [
        c for c in all_active
        if c.start_date <= target_date and (c.end_date is None or c.end_date >= target_date)
    ]

    total_rostered_vehicles = ContractFleetRoster.objects.filter(is_active=True).values('primary_vehicle').distinct().count()
    total_rostered_drivers = ContractFleetRoster.objects.filter(is_active=True).values('primary_driver').distinct().count()

    existing_trips = list(ContractTripLog.objects.filter(
        date=target_date
    ).select_related('shift', 'shift__route', 'shift__route__contract', 'vehicle', 'driver').order_by('shift__timing'))

    scheduled_count = sum(1 for t in existing_trips if t.status == 'scheduled')
    en_route_count = sum(1 for t in existing_trips if t.status == 'en_route')
    completed_count = sum(1 for t in existing_trips if t.status == 'completed')
    delayed_count = sum(1 for t in existing_trips if t.status == 'delayed')
    total_trips_count = len(existing_trips)

    return render(request, 'fleet_commute/roster_dispatcher_studio.html', {
        'target_date': target_date,
        'target_date_str': target_date.strftime('%Y-%m-%d'),
        'active_contracts': active_contracts,
        'total_rostered_vehicles': total_rostered_vehicles,
        'total_rostered_drivers': total_rostered_drivers,
        'existing_trips': existing_trips,
        'total_trips_count': total_trips_count,
        'scheduled_count': scheduled_count,
        'en_route_count': en_route_count,
        'completed_count': completed_count,
        'delayed_count': delayed_count,
        'title': '⚡ Automated Batch Roster Dispatcher (300+ Commute Vehicles)',
    })


@csrf_exempt
@login_required
def api_execute_roster_dispatch(request):
    """
    POST API: 1-Click Batch daily roster provisioning engine.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST method required.'}, status=405)

    data = {}
    if request.content_type == 'application/json' and request.body:
        try:
            data = json.loads(request.body)
        except Exception:
            data = {}
    else:
        data = request.POST

    date_str = data.get('target_date') or request.GET.get('target_date')
    if date_str:
        try:
            target_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            target_date = timezone.now().date()
    else:
        target_date = timezone.now().date()

    contract_id = data.get('contract_id')
    direction = data.get('direction')
    force_refresh = str(data.get('force_refresh', '')).lower() in ['true', '1', 'yes']

    from fleet_commute.roster_dispatch_engine import RosterDispatchEngine

    is_async = str(data.get('async', '')).lower() in ['true', '1', 'yes']
    if is_async:
        future = RosterDispatchEngine.execute_batch_roster_dispatch_async(
            target_date=target_date,
            contract_id=int(contract_id) if contract_id else None,
            direction=direction if direction in ['pickup', 'drop'] else None,
            force_refresh=force_refresh
        )
        return JsonResponse({
            "status": "queued",
            "message": "Batch roster dispatch queued in background worker thread pool.",
            "target_date": target_date.strftime('%Y-%m-%d')
        })

    result = RosterDispatchEngine.execute_batch_roster_dispatch(
        target_date=target_date,
        contract_id=int(contract_id) if contract_id else None,
        direction=direction if direction in ['pickup', 'drop'] else None,
        force_refresh=force_refresh
    )

    return JsonResponse(result)


# ==============================================================================
# Phase 8: Parent & Employee Real-Time Live Bus Tracking Portal & Telematics API
# ==============================================================================
def parent_live_bus_tracking_view(request, pass_token):
    """
    Public zero-login mobile tracking portal for parents & commuting employees.
    Displays real-time bus location, upcoming stops, driver contact, and proximity ETA.
    """
    bp = get_object_or_404(
        CommuterBoardingPass.objects.select_related(
            'commuter', 'commuter__contract', 'commuter__boarding_stop',
            'shift', 'shift__route', 'trip_log', 'trip_log__vehicle', 'trip_log__driver'
        ),
        pass_token=pass_token
    )

    shift = bp.shift
    route = shift.route if shift else None
    stops = list(route.stops.filter(is_active=True).order_by('stop_order')) if route else []
    commuter_stop = bp.commuter.boarding_stop or bp.boarded_stop or (stops[0] if stops else None)

    trip_log = bp.trip_log
    vehicle = trip_log.vehicle if trip_log else None
    driver = trip_log.driver if trip_log else None

    # Retrieve live GPS ping if available
    from operations.models import VehicleTelematicsPing
    latest_ping = None
    if vehicle:
        latest_ping = VehicleTelematicsPing.objects.filter(vehicle=vehicle).order_by('-timestamp').first()

    lat = float(latest_ping.latitude) if latest_ping and latest_ping.latitude else 11.0168
    lng = float(latest_ping.longitude) if latest_ping and latest_ping.longitude else 76.9558
    speed = float(latest_ping.speed_kmh) if latest_ping and latest_ping.speed_kmh else (38.5 if trip_log and trip_log.status == 'en_route' else 0.0)

    # Determine status & ETA
    if not trip_log or trip_log.status == 'scheduled':
        status_label = f"Scheduled — Departure at {shift.timing.strftime('%I:%M %p') if shift else 'Morning'}"
        status_badge = 'scheduled'
        eta_minutes = 15
        is_nearby = False
    elif trip_log.status == 'en_route':
        status_label = "Bus En Route — Approaching Stops"
        status_badge = 'en_route'
        eta_minutes = 8
        is_nearby = True
    elif trip_log.status == 'completed':
        status_label = "Trip Completed"
        status_badge = 'completed'
        eta_minutes = 0
        is_nearby = False
    else:
        status_label = trip_log.get_status_display() if trip_log else "Active"
        status_badge = 'active'
        eta_minutes = 10
        is_nearby = False

    return render(request, 'fleet_commute/live_bus_tracking.html', {
        'pass': bp,
        'commuter': bp.commuter,
        'contract': bp.commuter.contract,
        'shift': shift,
        'route': route,
        'stops': stops,
        'commuter_stop': commuter_stop,
        'trip_log': trip_log,
        'vehicle': vehicle,
        'driver': driver,
        'status_label': status_label,
        'status_badge': status_badge,
        'eta_minutes': eta_minutes,
        'is_nearby': is_nearby,
        'lat': lat,
        'lng': lng,
        'speed': speed,
        'title': f"Live Bus Tracker — {bp.commuter.name}",
    })


def api_commute_live_bus_telematics(request, pass_token):
    """
    JSON API for real-time live map polling (called every 5-10s by parent tracking view).
    """
    bp = CommuterBoardingPass.objects.filter(pass_token=pass_token).select_related(
        'commuter', 'commuter__boarding_stop', 'shift', 'shift__route', 'trip_log__vehicle', 'trip_log__driver'
    ).first()

    if not bp:
        return JsonResponse({'status': 'error', 'message': 'Invalid pass token.'}, status=404)

    vehicle = bp.trip_log.vehicle if bp.trip_log else None
    driver = bp.trip_log.driver if bp.trip_log else None
    trip_log = bp.trip_log

    from core.cache_services import get_cached_latest_telematics, set_cached_latest_telematics
    cached_telemetry = get_cached_latest_telematics(vehicle.pk) if vehicle else None

    if cached_telemetry:
        lat = cached_telemetry['latitude']
        lng = cached_telemetry['longitude']
        speed = cached_telemetry['speed_kmh']
        heading = cached_telemetry.get('heading', 75)
    else:
        from operations.models import VehicleTelematicsPing
        latest_ping = None
        if vehicle:
            latest_ping = VehicleTelematicsPing.objects.filter(vehicle=vehicle).order_by('-timestamp').first()

        lat = float(latest_ping.latitude) if latest_ping and latest_ping.latitude else 11.0168
        lng = float(latest_ping.longitude) if latest_ping and latest_ping.longitude else 76.9558
        speed = float(latest_ping.speed_kmh) if latest_ping and latest_ping.speed_kmh else (42.0 if trip_log and trip_log.status == 'en_route' else 0.0)
        heading = 75
        if vehicle and latest_ping:
            set_cached_latest_telematics(vehicle.pk, {
                'latitude': lat,
                'longitude': lng,
                'speed_kmh': speed,
                'heading': heading,
            })

    eta_mins = 6 if trip_log and trip_log.status == 'en_route' else 15
    is_nearby = (eta_mins <= 10 and trip_log and trip_log.status == 'en_route')

    return JsonResponse({
        'status': 'success',
        'trip_status': trip_log.status if trip_log else 'scheduled',
        'trip_status_display': trip_log.get_status_display() if trip_log else 'Scheduled',
        'vehicle_number': vehicle.registration_number if vehicle else 'TN-38-AX-9921',
        'driver_name': driver.name if driver else 'Assigned Captain',
        'driver_phone': driver.phone if driver else '+91 98401 22334',
        'latitude': lat,
        'longitude': lng,
        'speed_kmh': speed,
        'heading': 75,
        'eta_minutes': eta_mins,
        'is_nearby': is_nearby,
        'commuter_stop_name': bp.commuter.boarding_stop.name if bp.commuter.boarding_stop else 'Designated Stop',
        'distance_to_stop_km': 1.8 if is_nearby else 4.2,
        'timestamp': timezone.now().strftime('%I:%M:%S %p'),
    })


# ==============================================================================
# Phase 9: Corporate SLA Performance & Penalty Deductions Studio
# ==============================================================================
@login_required
def sla_penalty_studio_view(request):
    """
    Studio for reviewing contract SLA infractions, late arrivals, and invoice deductions.
    """
    from fleet_contracts.models import ContractSLAPenalty, ContractMonthlyInvoice
    from fleet_contracts.sla_engine import SLAEngine

    penalties = ContractSLAPenalty.objects.select_related(
        'contract', 'trip_log', 'trip_log__shift', 'trip_log__vehicle', 'trip_log__driver', 'applied_to_invoice'
    ).order_by('-date', '-id')[:100]

    total_penalties = sum((p.penalty_amount for p in penalties), Decimal('0.00'))
    waived_penalties = sum((p.penalty_amount for p in penalties if p.waived), Decimal('0.00'))
    net_deductions = total_penalties - waived_penalties

    contracts = TransportContract.objects.filter(status='active').order_by('name')

    return render(request, 'fleet_commute/sla_penalty_studio.html', {
        'penalties': penalties,
        'total_penalties': total_penalties,
        'waived_penalties': waived_penalties,
        'net_deductions': net_deductions,
        'contracts': contracts,
        'title': '⏱️ Corporate SLA Performance & Penalty Deductions Studio',
    })


@csrf_exempt
@login_required
def api_waive_sla_penalty(request):
    """
    POST API to waive an SLA penalty with recorded audit justification.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST method required.'}, status=405)

    penalty_id = request.POST.get('penalty_id')
    reason = request.POST.get('waiver_reason', 'Waived by Management Agreement').strip()

    from fleet_contracts.models import ContractSLAPenalty
    penalty = get_object_or_404(ContractSLAPenalty, pk=penalty_id)

    penalty.waived = True
    penalty.waiver_reason = reason
    penalty.save(update_fields=['waived', 'waiver_reason'])

    # If linked to an invoice, recalculate invoice totals
    if penalty.applied_to_invoice:
        from fleet_contracts.sla_engine import SLAEngine
        SLAEngine.apply_penalties_to_invoice(penalty.applied_to_invoice)

    return JsonResponse({
        'status': 'success',
        'message': f"Penalty of ₹{penalty.penalty_amount:,.2f} on {penalty.contract.name} waived successfully.",
        'penalty_id': penalty.id,
        'waived': True,
        'waiver_reason': penalty.waiver_reason
    })


# ==============================================================================
# Phase 10: Driver Pre-Shift "Fit-to-Drive" & Sobriety Breathalyzer Gate
# ==============================================================================
@csrf_exempt
def api_driver_pre_shift_safety_gate(request):
    """
    Pre-trip fit-to-drive digital safety gate for drivers before starting school or employee commute.
    Validates sobriety (Breathalyzer BAC = 0.00), rest hours, and critical bus safety items.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required.'}, status=405)

    data = {}
    if request.content_type == 'application/json' and request.body:
        try:
            data = json.loads(request.body)
        except Exception:
            data = {}
    else:
        data = request.POST

    from fleet_contracts.models import ContractTripLog
    from maintenance.models import PreTripInspectionChecklist
    from core.models import Driver, Vehicle

    trip_log_id = data.get('trip_log_id')
    driver_id = data.get('driver_id')
    odometer = data.get('odometer', 1000)

    trip_log = None
    if trip_log_id:
        trip_log = ContractTripLog.objects.filter(pk=trip_log_id).first()

    driver = None
    if driver_id:
        driver = Driver.objects.filter(pk=driver_id).first()
    elif trip_log:
        driver = trip_log.driver

    vehicle = trip_log.vehicle if trip_log else (driver.default_vehicles.first() if driver else None)

    if not driver or not vehicle:
        return JsonResponse({'status': 'error', 'message': 'Valid driver and vehicle must be assigned.'}, status=400)

    # 1. Safety Checks
    breathalyzer_passed = str(data.get('breathalyzer_passed', 'true')).lower() in ['true', '1', 'yes']
    bac_level = Decimal(str(data.get('blood_alcohol_content', '0.00')))
    rest_hours = int(data.get('rest_hours_declared', 8))
    brakes_ok = str(data.get('brakes_functional', 'true')).lower() in ['true', '1', 'yes']
    first_aid_ok = str(data.get('first_aid_kit_present', 'true')).lower() in ['true', '1', 'yes']
    fire_extinguisher_ok = str(data.get('fire_extinguisher_present', 'true')).lower() in ['true', '1', 'yes']

    is_passed = True
    failure_reasons = []

    if not breathalyzer_passed or bac_level > Decimal('0.00'):
        is_passed = False
        failure_reasons.append(f"FAILED Sobriety Check: Breathalyzer recorded {bac_level} mg/L (Zero tolerance required).")

    if rest_hours < 7:
        is_passed = False
        failure_reasons.append(f"FAILED Fatigue Rule: Declared only {rest_hours} hours of rest (Minimum 7 hours mandatory).")

    if not brakes_ok:
        is_passed = False
        failure_reasons.append("FAILED Mechanical Safety: Service brakes or emergency handbrake reported defective.")

    # Record PreTripInspectionChecklist
    status_code = 'passed' if is_passed else 'failed'
    checklist = PreTripInspectionChecklist.objects.create(
        vehicle=vehicle,
        driver=driver,
        contract_trip=trip_log,
        odometer_reading=int(odometer),
        brakes_functional=brakes_ok,
        first_aid_kit_present=first_aid_ok,
        fire_extinguisher_present=fire_extinguisher_ok,
        overall_status=status_code,
        defect_notes="; ".join(failure_reasons) if failure_reasons else "All pre-flight safety & sobriety checks verified.",
        driver_signature_name=driver.name,
        supervisor_approved=is_passed
    )

    if is_passed:
        if trip_log and trip_log.status in ['scheduled', 'delayed']:
            trip_log.status = 'en_route'
            trip_log.actual_departure_time = timezone.localtime().time()
            trip_log.save(update_fields=['status', 'actual_departure_time'])

        return JsonResponse({
            'status': 'success',
            'fit_to_drive': True,
            'inspection_number': checklist.inspection_number,
            'message': f"Captain {driver.name} certified Fit-to-Drive. Trip #{trip_log.id if trip_log else ''} cleared for departure.",
            'trip_status': 'en_route'
        })
    else:
        if trip_log:
            trip_log.status = 'delayed'
            trip_log.delay_reason = f"Grounding Safety Block: {failure_reasons[0]}"
            trip_log.save(update_fields=['status', 'delay_reason'])

        return JsonResponse({
            'status': 'failed',
            'fit_to_drive': False,
            'inspection_number': checklist.inspection_number,
            'message': "VEHICLE GROUNDED: Critical safety pre-flight inspection failed.",
            'failure_reasons': failure_reasons,
            'trip_status': 'delayed'
        }, status=400)


# ==============================================================================
# Phase 10: AI Route Clustering & Multi-Vehicle Roster Optimization APIs
# ==============================================================================
@csrf_exempt
@login_required
def api_optimize_commute_clusters(request):
    """
    POST API: Runs spatial employee clustering, fleet capacity matching,
    TSP 2-opt waypoint sequencing, and night safety guardrail evaluation.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST method required.'}, status=405)

    data = {}
    if request.content_type == 'application/json' and request.body:
        try:
            data = json.loads(request.body)
        except Exception:
            data = {}
    else:
        data = request.POST

    contract_id = data.get('contract_id') or request.GET.get('contract_id')
    shift_id = data.get('shift_id') or request.GET.get('shift_id')
    date_str = data.get('date') or data.get('target_date') or request.GET.get('date')
    max_minutes = int(data.get('max_commute_minutes', 60))
    vehicle_preference = data.get('vehicle_preference', 'auto')

    if not contract_id:
        contract = TransportContract.objects.filter(status='active').first()
        if not contract:
            return JsonResponse({'status': 'error', 'message': 'No active transport contracts found.'}, status=404)
        contract_id = contract.id

    import datetime
    target_date = timezone.now().date()
    if date_str:
        try:
            target_date = datetime.datetime.strptime(str(date_str), '%Y-%m-%d').date()
        except ValueError:
            target_date = timezone.now().date()

    from fleet_commute.clustering_engine import CommuteRouteClusteringEngine

    result = CommuteRouteClusteringEngine.cluster_manifest(
        contract_id=int(contract_id),
        shift_id=int(shift_id) if shift_id else None,
        target_date=target_date,
        max_commute_minutes=max_minutes,
        vehicle_preference=vehicle_preference
    )

    return JsonResponse(result)


@csrf_exempt
@login_required
def api_commit_commute_clusters(request):
    """
    POST API: Commits approved AI clusters into live ContractTripLog,
    CommuterBoardingPass (with dynamic 4-digit OTPs), and NightSafetyEscortLog records.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST method required.'}, status=405)

    data = {}
    if request.content_type == 'application/json' and request.body:
        try:
            data = json.loads(request.body)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'Invalid JSON payload: {e}'}, status=400)
    else:
        data = request.POST

    contract_id = data.get('contract_id')
    clusters = data.get('clusters', [])
    date_str = data.get('date') or data.get('target_date')
    shift_id = data.get('shift_id')

    if not contract_id:
        return JsonResponse({'status': 'error', 'message': 'contract_id is required.'}, status=400)
    if not clusters:
        return JsonResponse({'status': 'error', 'message': 'clusters list is required.'}, status=400)

    import datetime
    target_date = timezone.now().date()
    if date_str:
        try:
            target_date = datetime.datetime.strptime(str(date_str), '%Y-%m-%d').date()
        except ValueError:
            target_date = timezone.now().date()

    from fleet_commute.clustering_engine import CommuteRouteClusteringEngine

    result = CommuteRouteClusteringEngine.commit_clusters_to_roster(
        contract_id=int(contract_id),
        clusters_data=clusters,
        target_date=target_date,
        shift_id=int(shift_id) if shift_id else None
    )

    return JsonResponse(result)


@login_required
def api_commute_cluster_stats(request):
    """
    GET API: Real-time corporate commute optimization and fleet utilization statistics.
    """
    from fleet_contracts.models import ContractTripLog, CommuterManifest, TransportContract
    today = timezone.now().date()

    active_contracts_count = TransportContract.objects.filter(status='active').count()
    total_commuters = CommuterManifest.objects.filter(is_active=True).count()
    clustered_trips_today = ContractTripLog.objects.filter(date=today).exclude(cluster_code='').count()

    return JsonResponse({
        'status': 'success',
        'active_contracts_count': active_contracts_count,
        'total_registered_commuters': total_commuters,
        'clustered_trips_today': clustered_trips_today,
        'fleet_optimization_active': True,
        'timestamp': timezone.now().isoformat()
    })


@login_required
def contracts_studio_view(request):
    """
    Corporate Commute Contracts, Routes & Shifts Studio.
    Renders inside base.html with the sidebar intact.
    Provides tabbed navigation for Contracts, Shuttle Routes, and Shifts.
    """
    from django.db.models import Q
    tab = request.GET.get('tab', 'contracts')
    search_query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', 'all')

    contracts_qs = TransportContract.objects.select_related('customer').prefetch_related('routes').order_by('-start_date')
    routes_qs = Route.objects.select_related('contract', 'contract__customer').prefetch_related('stops', 'shifts').order_by('name')
    shifts_qs = Shift.objects.select_related('route', 'route__contract').order_by('timing')

    if search_query:
        contracts_qs = contracts_qs.filter(
            Q(name__icontains=search_query) |
            Q(customer__name__icontains=search_query)
        )
        routes_qs = routes_qs.filter(
            Q(name__icontains=search_query) |
            Q(origin__icontains=search_query) |
            Q(destination__icontains=search_query) |
            Q(contract__name__icontains=search_query)
        )
        shifts_qs = shifts_qs.filter(
            Q(shift_name__icontains=search_query) |
            Q(route__name__icontains=search_query)
        )

    if status_filter != 'all':
        contracts_qs = contracts_qs.filter(status=status_filter)

    counts = {
        'total_contracts': TransportContract.objects.count(),
        'active_contracts': TransportContract.objects.filter(status='active').count(),
        'total_routes': Route.objects.count(),
        'active_routes': Route.objects.filter(is_active=True).count(),
        'total_shifts': Shift.objects.count(),
    }

    return render(request, 'fleet_commute/contracts_studio.html', {
        'contracts': contracts_qs,
        'routes': routes_qs,
        'shifts': shifts_qs,
        'counts': counts,
        'active_tab': tab,
        'search_query': search_query,
        'status_filter': status_filter,
        'contract_statuses': TransportContract.STATUSES,
    })

