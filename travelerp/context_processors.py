"""
Role-Based Access Control (RBAC) Context Processor
Provides role flags and badges for staff members across all templates.
"""

def rbac_context(request):
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return {
            'is_superuser': False,
            'is_fleet_manager': False,
            'is_booking_manager': False,
            'is_finance_user': False,
            'user_role_label': 'Guest / Portal User',
            'user_role_icon': '👤',
            'user_role_color': '#64748b',
            'user_role_code': 'guest',
        }

    if user.is_superuser:
        return {
            'is_superuser': True,
            'is_fleet_manager': True,
            'is_booking_manager': True,
            'is_finance_user': True,
            'user_role_label': 'Superuser Admin',
            'user_role_icon': '👑',
            'user_role_color': '#f43f5e',
            'user_role_code': 'superuser',
        }

    # Fetch user group names
    group_names = set(user.groups.values_list('name', flat=True))

    is_fleet = 'Fleet_Managers' in group_names
    is_booking = 'Booking_Managers' in group_names
    is_finance = 'Finance_Team' in group_names

    # Determine primary role label & icon
    if is_fleet and not is_booking and not is_finance:
        role_label = 'Fleet Manager'
        role_icon = '🚛'
        role_color = '#0284c7'
        role_code = 'fleet_manager'
    elif is_booking and not is_fleet and not is_finance:
        role_label = 'Booking & Dispatch'
        role_icon = '📋'
        role_color = '#10b981'
        role_code = 'booking_manager'
    elif is_finance and not is_fleet and not is_booking:
        role_label = 'Finance & Accounts'
        role_icon = '💰'
        role_color = '#d97706'
        role_code = 'finance_team'
    elif group_names:
        role_label = ', '.join(g.replace('_', ' ') for g in group_names)
        role_icon = '💼'
        role_color = '#6366f1'
        role_code = 'custom_roles'
    else:
        role_label = 'Operations Staff'
        role_icon = '👤'
        role_color = '#64748b'
        role_code = 'staff'

    return {
        'is_superuser': False,
        'is_fleet_manager': is_fleet,
        'is_booking_manager': is_booking,
        'is_finance_user': is_finance,
        'user_role_label': role_label,
        'user_role_icon': role_icon,
        'user_role_color': role_color,
        'user_role_code': role_code,
        'user_groups': group_names,
    }
