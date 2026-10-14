"""
Enterprise Role-Based Access Control (RBAC) View Decorators
Provides fine-grained role clearance, capability gates, and financial approval ceilings.
"""
from functools import wraps
from decimal import Decimal
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.shortcuts import redirect
from django.contrib import messages


# Comprehensive Capability-to-Role Authorization Matrix (15 Granular Capabilities)
CAPABILITY_ROLE_MAP = {
    # 1. Fleet Dispatch & Live Telematics
    'live_fleet_radar': {
        'roles': ['admin', 'manager', 'operations', 'night_dispatcher', 'workshop_manager', 'compliance_rto_officer', 'b2b_corporate_lead', 'customer_service'],
        'label': 'Real-Time Fleet Radar Map & GPS Telematics',
        'desc': 'Stream sub-second vehicle telemetry, geofence ingress/egress, and overspeed alerts.',
    },
    'trip_roster_dispatch': {
        'roles': ['admin', 'manager', 'operations', 'night_dispatcher', 'b2b_corporate_lead'],
        'label': 'Trip Roster Allocation & Standby Vehicle Dispatch',
        'desc': 'Reassign trips, allocate backup luxury coaches, and manage driver duty manifests.',
    },
    'damage_inspection': {
        'roles': ['admin', 'manager', 'operations', 'night_dispatcher', 'driver', 'workshop_manager', 'compliance_rto_officer'],
        'label': 'Digital Handover Inspection & 2D Damage Studio',
        'desc': 'Mark pre-trip cosmetic blemishes, odometer captures, and fuel tank levels.',
    },
    'fleet_relocation_transfer': {
        'roles': ['admin', 'manager', 'operations', 'night_dispatcher'],
        'label': 'Inter-Depot Vehicle Relocation & Fleet Rebalancing',
        'desc': 'Initiate, authorize, and receive inter-depot vehicle fleet transfers.',
    },

    # 2. Asset Maintenance & Workshop
    'maintenance_work_orders': {
        'roles': ['admin', 'manager', 'workshop_manager', 'compliance_rto_officer'],
        'label': 'Maintenance Work Orders & Mechanical Defect Job Cards',
        'desc': 'Create defect tickets, allocate garage mechanics, and authorize OEM spare parts.',
    },
    'tire_health_audit': {
        'roles': ['admin', 'manager', 'workshop_manager', 'operations'],
        'label': 'Preventative Service Schedules & Tire Tread Mileage Audit',
        'desc': 'Track 10,000 km oil intervals, tire tread depth thresholds, and scheduled overhauls.',
    },

    # 3. Safety, RTO Compliance & SOS
    'emergency_sos_command': {
        'roles': ['admin', 'manager', 'operations', 'night_dispatcher', 'driver', 'customer_service', 'compliance_rto_officer', 'b2b_corporate_lead'],
        'label': 'Emergency SOS Panic Trigger & Incident Escalation Desk',
        'desc': '24/7 emergency response console with AIS-140 panic feed and city police liaison.',
    },
    'rto_compliance_ledger': {
        'roles': ['admin', 'manager', 'compliance_rto_officer', 'workshop_manager', 'operations'],
        'label': 'RTO Fitness (FC), Border Permits & Insurance Ledger',
        'desc': 'Monitor All India Tourist Permit expiries, speed governor certs, and PUC renewals.',
    },

    # 4. Commercial, CRM & Itineraries
    'crm_itinerary_builder': {
        'roles': ['admin', 'manager', 'tour_designer_lead', 'sales_executive', 'sales', 'b2b_corporate_lead'],
        'label': 'Bespoke Itinerary Architect & Multi-Day Tariff Engine',
        'desc': 'Design day-by-day tour itineraries with hotel voucher costing and route calculations.',
    },
    'crm_pipeline_kanban': {
        'roles': ['admin', 'manager', 'sales_executive', 'tour_designer_lead', 'sales', 'b2b_corporate_lead'],
        'label': 'CRM Leads Pipeline, Kanban Board & Digital Proposals',
        'desc': 'Manage inquiry stages, follow-up reminders, and digital customer proposals.',
    },

    # 5. B2B Corporate Commute Contracts
    'b2b_contracts_rosters': {
        'roles': ['admin', 'manager', 'b2b_corporate_lead', 'operations', 'night_dispatcher'],
        'label': 'Corporate Master Contracts & Employee Roster Studio',
        'desc': 'Corporate client tariff matrices, multi-shift route rosters, and SEZ transport hubs.',
    },
    'b2b_sla_penalty_audit': {
        'roles': ['admin', 'manager', 'b2b_corporate_lead', 'compliance_rto_officer'],
        'label': 'SLA Delay Penalty Audits & Night Escort Safe-Drop Index',
        'desc': 'Reconcile on-time trip penalties, escort sign-offs, and automated client billing.',
    },

    # 6. Billing, GST Invoicing & Tax
    'gst_tax_invoice': {
        'roles': ['admin', 'manager', 'finance_controller', 'operation_account'],
        'label': 'Issue Tax Invoices (GST INV-1) & NIC E-Way Bill Exports',
        'desc': 'Generate statutory B2B GST tax invoices, calculate SGST/CGST/IGST, and push JSON to NIC.',
    },
    'tally_zoho_export': {
        'roles': ['admin', 'finance_controller'],
        'label': 'Tally Prime / Zoho Books Export & TDS Section 194C Filing',
        'desc': 'Export XML ledgers for Tally Prime and reconcile 1% / 2% transport contractor TDS.',
    },

    # 7. Driver Bata, Fuel & Cash Custody
    'trip_bata_settlement': {
        'roles': ['admin', 'manager', 'operation_account', 'finance_controller', 'treasury_petty_cashier', 'operations'],
        'label': 'Driver Bata, Diesel Fuel Slips Audit & Trip Settlements',
        'desc': 'Audit HPCL/IOCL fleet fuel receipts, toll slips, and calculate driver night batas.',
    },
    'petty_cash_disbursement': {
        'roles': ['admin', 'manager', 'treasury_petty_cashier', 'operation_account', 'finance_controller'],
        'label': 'Depot Petty Cash Disbursements & Fastag Wallet Top-Ups',
        'desc': 'Manage branch cash vaults, driver trip advances, and toll Fastag balance top-ups.',
    },

    # 8. Executive Governance & Approvals
    'discount_override': {
        'roles': ['admin', 'manager'],
        'label': 'Commercial Margin Waiver & High-Value Discount (>15%)',
        'desc': 'Sign off on non-standard client discounts, credit terms, and low-margin contracts.',
    },
    'master_governance_audit': {
        'roles': ['admin'],
        'label': 'Staff Provisioning, RBAC Clearance Matrix & Master Audit Log',
        'desc': 'Provision employee profiles, adjust approval ceilings, and review forensic system logs.',
    },
}

# Group to Role aliases for backwards-compatibility
GROUP_ROLE_MAP = {
    'Super_Admins': 'admin',
    'General_Managers': 'manager',
    'Fleet_Managers': 'operations',
    'Booking_Managers': 'sales_executive',
    'Finance_Team': 'operation_account',
    'Corporate_Sales': 'sales',
    'Chauffeur_Drivers': 'driver',
    'Guest_Support': 'customer_service',
    'Workshop_Maintenance': 'workshop_manager',
    'Compliance_RTO': 'compliance_rto_officer',
    'Treasury_Cashiers': 'treasury_petty_cashier',
}


def get_user_effective_roles(user):
    """
    Returns the set of active role identifiers for a given User object.
    Includes explicit StaffProfile role, superuser escalation, and mapped Django Groups.
    """
    if not user or not user.is_authenticated:
        return set()

    if user.is_superuser:
        # Superuser possesses all roles
        from core.models import StaffProfile
        return set(dict(StaffProfile.ROLE_CHOICES).keys()) | {'admin'}

    roles = set()

    # Explicit StaffProfile role
    profile = getattr(user, 'staff_profile', None)
    if profile is None:
        try:
            from core.models import StaffProfile
            profile = StaffProfile.objects.select_related('linked_driver').get(user=user)
        except Exception:
            profile = None

    if profile and profile.role:
        roles.add(profile.role)

    # Mapped Django Groups
    for g_name in user.groups.values_list('name', flat=True):
        if g_name in GROUP_ROLE_MAP:
            roles.add(GROUP_ROLE_MAP[g_name])

    return roles


def has_staff_role(user, *allowed_roles):
    """
    Returns True if user has ANY of the specified allowed roles, or is a superuser.
    """
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    user_roles = get_user_effective_roles(user)
    return bool(user_roles.intersection(set(allowed_roles)))


def has_staff_capability(user, capability_key):
    """
    Returns True if user has authorization for the specified capability key.
    """
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True

    cap_config = CAPABILITY_ROLE_MAP.get(capability_key)
    if not cap_config:
        # Unknown capability defaults to superuser/admin only
        return has_staff_role(user, 'admin')

    allowed_roles = cap_config.get('roles', [])
    return has_staff_role(user, *allowed_roles)


def is_ajax_request(request):
    """
    Detects whether the incoming request expects a JSON or HTMX response.
    """
    return (
        request.headers.get('x-requested-with') == 'XMLHttpRequest' or
        request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest' or
        request.headers.get('hx-request') == 'true' or
        '/api/' in request.path or
        'application/json' in request.headers.get('accept', '') or
        'application/json' in getattr(request, 'content_type', '')
    )


def require_staff_role(*allowed_roles):
    """
    Decorator for views requiring one of the specified StaffProfile roles.
    Raises PermissionDenied (HTTP 403) or returns JSON error if unauthorized.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect(f"/staff/login/?next={request.path}")

            if not has_staff_role(request.user, *allowed_roles):
                profile = getattr(request.user, 'staff_profile', None)
                role_label = profile.get_role_display() if profile else 'Unassigned Staff'
                required_names = ', '.join(allowed_roles)
                denial_msg = (
                    f"Security Clearance Restricted: Action requires authorization for [{required_names}]. "
                    f"Your current clearance is [{role_label}]."
                )

                if is_ajax_request(request):
                    return JsonResponse({
                        'status': 'forbidden',
                        'error': 'Restricted Clearance',
                        'detail': denial_msg,
                        'required_roles': list(allowed_roles),
                        'current_role': profile.role if profile else None,
                    }, status=403)

                raise PermissionDenied(denial_msg)

            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


def require_staff_capability(capability_key):
    """
    Decorator for views requiring clearance for a specific operational capability.
    Validates against CAPABILITY_ROLE_MAP and raises PermissionDenied (HTTP 403) if denied.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect(f"/staff/login/?next={request.path}")

            if not has_staff_capability(request.user, capability_key):
                cap_config = CAPABILITY_ROLE_MAP.get(capability_key, {})
                cap_label = cap_config.get('label', capability_key)
                cap_roles = cap_config.get('roles', ['admin'])

                profile = getattr(request.user, 'staff_profile', None)
                role_label = profile.get_role_display() if profile else 'Unassigned Staff'
                roles_str = ', '.join(cap_roles)

                denial_msg = (
                    f"Clearance Restricted for Capability [{cap_label}]. "
                    f"Requires one of [{roles_str}]. Your active clearance is [{role_label}]."
                )

                if is_ajax_request(request):
                    return JsonResponse({
                        'status': 'forbidden',
                        'error': 'Capability Clearance Required',
                        'capability': capability_key,
                        'capability_label': cap_label,
                        'detail': denial_msg,
                        'authorized_roles': cap_roles,
                        'current_role': profile.role if profile else None,
                    }, status=403)

                raise PermissionDenied(denial_msg)

            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


def require_approval_ceiling(amount_extractor=None, max_ceiling=None):
    """
    Decorator enforcing financial governance thresholds.
    Checks whether the requested transaction amount is within the user's approval_limit.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect(f"/staff/login/?next={request.path}")

            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            # Determine the requested amount
            amount = None
            if callable(amount_extractor):
                amount = amount_extractor(request, *args, **kwargs)
            elif isinstance(amount_extractor, str):
                val = request.POST.get(amount_extractor) or request.GET.get(amount_extractor)
                if val:
                    try:
                        amount = Decimal(str(val))
                    except Exception:
                        amount = None

            if amount is not None:
                profile = getattr(request.user, 'staff_profile', None)
                limit = profile.approval_limit if profile else Decimal('0.00')

                # Check against role limit or hard ceiling
                effective_max = min(limit, max_ceiling) if max_ceiling else limit

                if amount > effective_max:
                    denial_msg = (
                        f"Financial Approval Ceiling Exceeded: Transaction amount ₹{amount:,.2f} "
                        f"exceeds your authorized clearance ceiling of ₹{effective_max:,.2f}. "
                        f"Executive counter-signature required."
                    )
                    if is_ajax_request(request):
                        return JsonResponse({
                            'status': 'forbidden',
                            'error': 'Approval Ceiling Exceeded',
                            'detail': denial_msg,
                            'amount': float(amount),
                            'ceiling': float(effective_max),
                        }, status=403)

                    raise PermissionDenied(denial_msg)

            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator
