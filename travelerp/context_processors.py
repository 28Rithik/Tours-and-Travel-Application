"""
Enterprise Role-Based Access Control (RBAC) Context Processor
Provides comprehensive role flags, staff profiles, and active persona info across all templates.
"""
from django.contrib.auth.models import User
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
    is_sales_exec = is_admin or is_manager or (role == 'sales_executive') or ('Sales_Executives' in group_names) or ('Booking_Managers' in group_names)
    is_sales = is_sales_exec or (role == 'sales') or ('Corporate_Sales' in group_names)
    is_ops = is_admin or is_manager or (role == 'operations') or ('Operations_Dispatch' in group_names) or ('Fleet_Managers' in group_names)
    is_acct = is_admin or is_manager or (role == 'operation_account') or ('Accounts_Finance' in group_names) or ('Finance_Team' in group_names)
    is_driver = (role == 'driver') or ('Chauffeur_Drivers' in group_names)
    is_cust_service = is_admin or is_manager or (role == 'customer_service') or ('Guest_Support' in group_names)

    # Legacy flags for template and test backwards-compatibility
    is_fleet = ('Fleet_Managers' in group_names) or (role in ('operations', 'admin', 'manager')) or is_super
    is_booking = ('Booking_Managers' in group_names) or (role in ('sales_executive', 'sales', 'customer_service', 'admin', 'manager')) or is_super
    is_finance = ('Finance_Team' in group_names) or (role in ('operation_account', 'admin', 'manager')) or is_super

    # Role meta dictionary
    role_meta = {
        'admin': ('System Director / Admin', '👑', '#e11d48'),
        'manager': ('General Manager', '🏢', '#8b5cf6'),
        'sales_executive': ('Senior Sales Executive', '📑', '#10b981'),
        'sales': ('Corporate Sales', '💼', '#059669'),
        'operations': ('Fleet & Dispatch Operations', '🚛', '#0284c7'),
        'operation_account': ('Operations Accounts & Billing', '💰', '#d97706'),
        'driver': ('Senior Chauffeur', '👨‍✈️', '#f97316'),
        'customer_service': ('Guest Experience & Concierge', '🎧', '#06b6d4'),
    }

    if is_admin and not profile:
        role_label, role_icon, role_color = ('Superuser Admin', '👑', '#e11d48')
    elif profile and profile.role in role_meta:
        role_label, role_icon, role_color = role_meta[profile.role]
    elif 'Fleet_Managers' in group_names and len(group_names) == 1:
        role_label, role_icon, role_color = ('Fleet Manager', '🚛', '#0284c7')
    elif 'Booking_Managers' in group_names and len(group_names) == 1:
        role_label, role_icon, role_color = ('Booking & Dispatch', '📋', '#10b981')
    elif 'Finance_Team' in group_names and len(group_names) == 1:
        role_label, role_icon, role_color = ('Finance & Accounts', '💰', '#d97706')
    else:
        role_label, role_icon, role_color = ('Enterprise Staff', '👤', '#64748b')

    # Demo personas for instant 1-click evaluation switching
    demo_personas = [
        {
            'username': 'admin_rajesh',
            'name': 'Rajesh Kannan',
            'role_label': 'System Director / Admin',
            'role_code': 'admin',
            'empid': 'SGT-EXEC-001',
            'badge_color': '#e11d48',
            'icon': '👑',
            'branch': 'Chennai HQ',
            'focus': 'Full Root Governance & Master Audit',
        },
        {
            'username': 'mgr_vikram',
            'name': 'Vikram Sundaram',
            'role_label': 'General Manager',
            'role_code': 'manager',
            'empid': 'SGT-MGR-002',
            'badge_color': '#8b5cf6',
            'icon': '🏢',
            'branch': 'Coimbatore Hub',
            'focus': 'Discount Approvals & P&L Margins',
        },
        {
            'username': 'sales_priya',
            'name': 'Priya Natarajan',
            'role_label': 'Senior Sales Executive',
            'role_code': 'sales_executive',
            'empid': 'SGT-SLS-003',
            'badge_color': '#10b981',
            'icon': '📑',
            'branch': 'Chennai HQ',
            'focus': 'Tour Quotations & Itinerary Proposals',
        },
        {
            'username': 'sales_arun',
            'name': 'Arun Kumar',
            'role_label': 'Corporate Sales',
            'role_code': 'sales',
            'empid': 'SGT-SLS-004',
            'badge_color': '#059669',
            'icon': '💼',
            'branch': 'Bengaluru Station',
            'focus': 'Corporate B2B Contracts & College IV',
        },
        {
            'username': 'ops_suresh',
            'name': 'Suresh Balaji',
            'role_label': 'Fleet & Dispatch Operations',
            'role_code': 'operations',
            'empid': 'SGT-OPS-005',
            'badge_color': '#0284c7',
            'icon': '🚛',
            'branch': 'Coimbatore Hub',
            'focus': 'Live Radar, Driver Rosters & Standby',
        },
        {
            'username': 'acct_meena',
            'name': 'Meenakshi Raman',
            'role_label': 'Accounts & Billing Officer',
            'role_code': 'operation_account',
            'empid': 'SGT-FIN-006',
            'badge_color': '#d97706',
            'icon': '💰',
            'branch': 'Chennai HQ',
            'focus': 'GST Tax Invoices, TDS & Driver Settlements',
        },
        {
            'username': 'driver_muthu',
            'name': 'Muthukumar S',
            'role_label': 'Senior Chauffeur',
            'role_code': 'driver',
            'empid': 'SGT-DRV-007',
            'badge_color': '#f97316',
            'icon': '👨‍✈️',
            'branch': 'Madurai Depo',
            'focus': 'Mobile Digital Handover & Fuel Slips',
        },
        {
            'username': 'support_divya',
            'name': 'Divya Selvam',
            'role_label': 'Guest Support Specialist',
            'role_code': 'customer_service',
            'empid': 'SGT-SUP-008',
            'badge_color': '#06b6d4',
            'icon': '🎧',
            'branch': 'Chennai HQ',
            'focus': 'Passenger Care, SOS & Concierge',
        },
    ]

    return {
        'is_superuser': is_super,
        'is_admin': is_admin,
        'is_manager': is_manager,
        'is_sales_executive': is_sales_exec,
        'is_sales': is_sales,
        'is_operations': is_ops,
        'is_operation_account': is_acct,
        'is_driver': is_driver,
        'is_customer_service': is_cust_service,
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
    }
