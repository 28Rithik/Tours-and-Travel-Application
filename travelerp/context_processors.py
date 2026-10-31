"""
Enterprise Role-Based Access Control (RBAC) Context Processor
Provides comprehensive role flags, staff profiles, and active persona info across all templates.

✅ PERFORMANCE FIX: RBAC data is now cached per-user (keyed by user.pk + session simulating_persona).
   Previously 2 DB queries fired on EVERY page request. Now cached for 300 seconds (5 minutes).
   Cache is invalidated when user switches persona or when TTL expires.
"""
from django.contrib.auth.models import User
from django.core.cache import cache
from core.models import StaffProfile


def rbac_context(request):
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return {
            'is_superuser': False,
            'is_admin': False,
            'is_manager': False,
            'is_sales_executive': False,
            'is_sales': False,
            'is_operations': False,
            'is_operation_account': False,
            'is_driver': False,
            'is_customer_service': False,
            'is_fleet_manager': False,
            'is_booking_manager': False,
            'is_finance_user': False,
            'user_role_label': 'Guest / Portal User',
            'user_role_icon': '👤',
            'user_role_color': '#64748b',
            'user_role_code': 'guest',
            'user_employee_id': '',
            'user_branch': '',
            'user_designation': '',
            'staff_profile': None,
            'demo_personas': [],
        }

    # ── CACHE KEY: includes persona simulation state so switching roles invalidates cache ──
    simulating_persona = request.session.get('simulating_persona', '')
    cache_key = f'rbac_ctx_v2_{user.pk}_{simulating_persona}'

    cached_ctx = cache.get(cache_key)
    if cached_ctx is not None:
        return cached_ctx

    # ── CACHE MISS: Build RBAC context (2 DB queries, then cached for 5 min) ──

    # Fetch groups
    group_names = set(user.groups.values_list('name', flat=True))

    # Fetch staff profile
    profile = getattr(user, 'staff_profile', None)
    if profile is None:
        try:
            profile = StaffProfile.objects.select_related('linked_driver').get(user=user)
        except StaffProfile.DoesNotExist:
            profile = None

    role = profile.role if profile else None

    is_super = user.is_superuser
    is_admin = is_super or (role == 'admin') or ('Super_Admins' in group_names)
    is_manager = is_admin or (role == 'manager') or ('General_Managers' in group_names)
    is_sales_exec = is_admin or is_manager or (role in ('sales_executive', 'tour_designer_lead', 'booking_manager')) or ('Sales_Executives' in group_names) or ('Booking_Managers' in group_names)
    is_sales = is_sales_exec or (role in ('sales', 'b2b_corporate_lead')) or ('Corporate_Sales' in group_names)
    is_ops = is_admin or is_manager or (role in ('operations', 'night_dispatcher', 'workshop_manager', 'fleet_manager')) or ('Operations_Dispatch' in group_names) or ('Fleet_Managers' in group_names)
    is_acct = is_admin or is_manager or (role in ('operation_account', 'finance_controller', 'treasury_petty_cashier')) or ('Accounts_Finance' in group_names) or ('Finance_Team' in group_names)
    is_driver = (role == 'driver') or ('Chauffeur_Drivers' in group_names)
    is_cust_service = is_admin or is_manager or (role == 'customer_service') or ('Guest_Support' in group_names)

    # Specialized Role Flags
    is_tour_designer = is_admin or is_manager or (role == 'tour_designer_lead')
    is_b2b_corporate = is_admin or is_manager or (role in ('b2b_corporate_lead', 'sales'))
    is_workshop = is_admin or is_manager or (role == 'workshop_manager') or ('Workshop_Maintenance' in group_names)
    is_compliance = is_admin or is_manager or (role == 'compliance_rto_officer') or ('Compliance_RTO' in group_names)
    is_night_dispatcher = is_admin or (role == 'night_dispatcher')
    is_finance_controller = is_admin or (role == 'finance_controller')
    is_petty_cash = is_admin or is_manager or (role == 'treasury_petty_cashier') or ('Treasury_Cashiers' in group_names)

    # Legacy flags for template and test backwards-compatibility
    is_fleet = ('Fleet_Managers' in group_names) or (role in ('operations', 'admin', 'manager', 'workshop_manager', 'night_dispatcher', 'fleet_manager')) or is_super
    is_booking = ('Booking_Managers' in group_names) or (role in ('sales_executive', 'tour_designer_lead', 'sales', 'b2b_corporate_lead', 'customer_service', 'admin', 'manager', 'booking_manager')) or is_super
    is_finance = ('Finance_Team' in group_names) or (role in ('operation_account', 'finance_controller', 'treasury_petty_cashier', 'admin', 'manager')) or is_super

    # Simulation HUD Detection
    is_simulating_persona = bool(simulating_persona)

    # Role meta dictionary
    role_meta = {
        'admin': ('System Director / Admin', 'fa-solid fa-crown', '#e11d48'),
        'manager': ('General / Branch Manager', 'fa-solid fa-building-user', '#8b5cf6'),
        'tour_designer_lead': ('Senior Tour Designer & Package Architect', 'fa-solid fa-compass-drafting', '#0ea5e9'),
        'b2b_corporate_lead': ('Corporate Mobility & Key Accounts Lead', 'fa-solid fa-briefcase', '#4f46e5'),
        'sales_executive': ('Senior Sales Executive & Proposal Designer', 'fa-solid fa-file-signature', '#10b981'),
        'sales': ('Corporate Sales Representative', 'fa-solid fa-handshake', '#059669'),
        'operations': ('Fleet & Dispatch Operations Lead', 'fa-solid fa-truck-ramp-box', '#0284c7'),
        'fleet_manager': ('Fleet Manager', 'fa-solid fa-truck-ramp-box', '#0284c7'),
        'booking_manager': ('Booking Manager', 'fa-solid fa-calendar-check', '#10b981'),
        'night_dispatcher': ('Night Shift & SOS Emergency Dispatcher', 'fa-solid fa-moon', '#312e81'),
        'workshop_manager': ('Fleet Maintenance & Workshop Supervisor', 'fa-solid fa-wrench', '#ea580c'),
        'compliance_rto_officer': ('Safety, Compliance & RTO Liaison Officer', 'fa-solid fa-shield-halved', '#0369a1'),
        'finance_controller': ('Chief Financial Controller & Tax Lead', 'fa-solid fa-vault', '#7c3aed'),
        'operation_account': ('Operations Accounts & Billing Officer', 'fa-solid fa-file-invoice-dollar', '#d97706'),
        'treasury_petty_cashier': ('Depot Petty Cash & Fastag Custodian', 'fa-solid fa-money-bill-transfer', '#ca8a04'),
        'driver': ('Senior Fleet Chauffeur', 'fa-solid fa-id-badge', '#f97316'),
        'customer_service': ('Guest Experience & WhatsApp Concierge', 'fa-solid fa-headset', '#06b6d4'),
    }

    if is_super:
        role_label, role_icon, role_color = ('Superuser Admin', 'fa-solid fa-crown', '#e11d48')
    elif profile and profile.role in role_meta:
        role_label, role_icon, role_color = role_meta[profile.role]
    elif 'Fleet_Managers' in group_names and len(group_names) == 1:
        role_label, role_icon, role_color = ('Fleet Manager', 'fa-solid fa-truck-ramp-box', '#0284c7')
    elif 'Booking_Managers' in group_names and len(group_names) == 1:
        role_label, role_icon, role_color = ('Booking & Dispatch', 'fa-solid fa-calendar-check', '#10b981')
    elif 'Finance_Team' in group_names and len(group_names) == 1:
        role_label, role_icon, role_color = ('Finance & Accounts', 'fa-solid fa-file-invoice-dollar', '#d97706')
    else:
        role_label, role_icon, role_color = ('Enterprise Staff', 'fa-solid fa-user', '#64748b')

    # Demo personas for instant 1-click evaluation switching (All 14 Enterprise Roles)
    demo_personas = [
        {
            'username': 'admin_rajesh',
            'name': 'Rajesh Kannan',
            'role_label': 'System Director / Super Admin',
            'role_code': 'admin',
            'empid': 'SGT-EXEC-001',
            'badge_color': '#e11d48',
            'icon_class': 'fa-solid fa-crown',
            'branch': 'Coimbatore Central HQ',
            'focus': 'Full Root Governance & Master Audit',
        },
        {
            'username': 'mgr_vikram',
            'name': 'Vikram Sundaram',
            'role_label': 'General / Branch Manager',
            'role_code': 'manager',
            'empid': 'SGT-MGR-002',
            'badge_color': '#8b5cf6',
            'icon_class': 'fa-solid fa-building-user',
            'branch': 'Coimbatore Central HQ',
            'focus': 'Discount Approvals & P&L Margins',
        },
        {
            'username': 'tour_ananya',
            'name': 'Ananya Deshmukh',
            'role_label': 'Tour Designer & Package Architect',
            'role_code': 'tour_designer_lead',
            'empid': 'SGT-TRN-003',
            'badge_color': '#0ea5e9',
            'icon_class': 'fa-solid fa-compass-drafting',
            'branch': 'Coimbatore Central HQ',
            'focus': 'Bespoke Itineraries & Tour Tariffs',
        },
        {
            'username': 'sales_arun',
            'name': 'Arun Kumar',
            'role_label': 'Corporate Mobility & Key Accounts',
            'role_code': 'b2b_corporate_lead',
            'empid': 'SGT-B2B-004',
            'badge_color': '#4f46e5',
            'icon_class': 'fa-solid fa-briefcase',
            'branch': 'Hosur Branch',
            'focus': 'Corporate B2B Commute & SEZ Shuttles',
        },
        {
            'username': 'sales_priya',
            'name': 'Priya Natarajan',
            'role_label': 'Senior Sales Executive & Proposals',
            'role_code': 'sales_executive',
            'empid': 'SGT-SLS-005',
            'badge_color': '#10b981',
            'icon_class': 'fa-solid fa-file-signature',
            'branch': 'Chennai Branch',
            'focus': 'CRM Kanban & Digital Proposals',
        },
        {
            'username': 'ops_suresh',
            'name': 'Suresh Balaji',
            'role_label': 'Fleet & Dispatch Operations Lead',
            'role_code': 'operations',
            'empid': 'SGT-OPS-006',
            'badge_color': '#0284c7',
            'icon_class': 'fa-solid fa-truck-ramp-box',
            'branch': 'Coimbatore Central HQ',
            'focus': 'Live Radar, Driver Rosters & Standby',
        },
        {
            'username': 'night_arvind',
            'name': 'Arvind Swaminathan',
            'role_label': 'Night Shift & SOS Dispatcher',
            'role_code': 'night_dispatcher',
            'empid': 'SGT-NIT-007',
            'badge_color': '#312e81',
            'icon_class': 'fa-solid fa-moon',
            'branch': 'Coimbatore Central HQ',
            'focus': 'Graveyard Supervision & Panic Triggers',
        },
        {
            'username': 'workshop_karthik',
            'name': 'Karthik Raghavan',
            'role_label': 'Maintenance & Workshop Supervisor',
            'role_code': 'workshop_manager',
            'empid': 'SGT-MNT-008',
            'badge_color': '#ea580c',
            'icon_class': 'fa-solid fa-wrench',
            'branch': 'Erode Branch',
            'focus': 'Preventive Service & Tire Audits',
        },
        {
            'username': 'compliance_bala',
            'name': 'Balasubramanian S',
            'role_label': 'Safety, RTO & Compliance Officer',
            'role_code': 'compliance_rto_officer',
            'empid': 'SGT-RTO-009',
            'badge_color': '#0369a1',
            'icon_class': 'fa-solid fa-shield-halved',
            'branch': 'Coimbatore Central HQ',
            'focus': 'RTO Fitness (FC), Permits & Insurance',
        },
        {
            'username': 'tax_srinivas',
            'name': 'Srinivas V',
            'role_label': 'Chief Financial Controller & Tax',
            'role_code': 'finance_controller',
            'empid': 'SGT-TAX-010',
            'badge_color': '#7c3aed',
            'icon_class': 'fa-solid fa-vault',
            'branch': 'Coimbatore Central HQ',
            'focus': 'GST INV-1, E-Way Bills & Tally Export',
        },
        {
            'username': 'acct_meena',
            'name': 'Meenakshi Raman',
            'role_label': 'Trip Settlement & Billing Officer',
            'role_code': 'operation_account',
            'empid': 'SGT-FIN-011',
            'badge_color': '#d97706',
            'icon_class': 'fa-solid fa-file-invoice-dollar',
            'branch': 'Tirupur Branch',
            'focus': 'Driver Bata, Fuel Slips & Toll Claims',
        },
        {
            'username': 'cash_ramesh',
            'name': 'Ramesh Chandran',
            'role_label': 'Depot Petty Cash & Fastag Custodian',
            'role_code': 'treasury_petty_cashier',
            'empid': 'SGT-CSH-012',
            'badge_color': '#ca8a04',
            'icon_class': 'fa-solid fa-money-bill-transfer',
            'branch': 'Coimbatore Central HQ',
            'focus': 'Driver Cash Advances & Fastag Vault',
        },
        {
            'username': 'driver_muthu',
            'name': 'Muthukumar S',
            'role_label': 'Senior Fleet Chauffeur',
            'role_code': 'driver',
            'empid': 'SGT-DRV-013',
            'badge_color': '#f97316',
            'icon_class': 'fa-solid fa-id-badge',
            'branch': 'Trichy Branch',
            'focus': 'Mobile PWA Handover & Duty Roster',
        },
        {
            'username': 'support_divya',
            'name': 'Divya Selvam',
            'role_label': 'Guest Experience & Concierge',
            'role_code': 'customer_service',
            'empid': 'SGT-SUP-014',
            'badge_color': '#06b6d4',
            'icon_class': 'fa-solid fa-headset',
            'branch': 'Chennai Branch',
            'focus': 'Passenger Care, SOS & Concierge',
        },
    ]

    context = {
        'is_superuser': is_super,
        'is_admin': is_admin,
        'is_manager': is_manager,
        'is_sales_executive': is_sales_exec,
        'is_sales': is_sales,
        'is_operations': is_ops,
        'is_operation_account': is_acct,
        'is_driver': is_driver,
        'is_customer_service': is_cust_service,
        # Specialized flags
        'is_tour_designer': is_tour_designer,
        'is_b2b_corporate': is_b2b_corporate,
        'is_workshop': is_workshop,
        'is_compliance': is_compliance,
        'is_night_dispatcher': is_night_dispatcher,
        'is_finance_controller': is_finance_controller,
        'is_petty_cash': is_petty_cash,
        # Legacy backward-compatible keys
        'is_fleet_manager': is_fleet,
        'is_booking_manager': is_booking,
        'is_finance_user': is_finance,
        # UI Badging
        'user_role_label': role_label,
        'user_role_icon': role_icon,
        'user_role_color': role_color,
        'user_role_code': role,
        'user_employee_id': profile.employee_id if profile else '',
        'user_branch': profile.branch if profile else 'Main Office',
        'user_designation': profile.designation if profile else (role_label),
        'user_groups': group_names,
        'staff_profile': profile,
        'demo_personas': demo_personas,
        'is_simulating_persona': is_simulating_persona,
    }

    # ── STORE IN CACHE: 300s TTL (5 minutes). Staff profile object is excluded from
    # cache since Django model instances can't be pickled reliably across sessions.
    # We cache everything except staff_profile (fetched fresh only on cache miss).
    cacheable_ctx = {k: v for k, v in context.items() if k != 'staff_profile'}
    cacheable_ctx['staff_profile'] = None  # Will be None from cache; re-attach below if needed
    cache.set(cache_key, cacheable_ctx, timeout=300)

    # Return the full context (with profile object attached) for this request
    return context
