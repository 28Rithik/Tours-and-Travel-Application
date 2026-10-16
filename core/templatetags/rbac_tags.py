from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def can_access(context, *roles):
    """
    Returns True if the logged-in user in context has any of the listed roles.
    Example: {% can_access 'fleet_manager' 'workshop' 'superuser' %}
    """
    for role in roles:
        role = role.strip().lower()
        if role in ('superuser', 'admin') and (context.get('is_superuser') or context.get('is_admin')):
            return True
        if role in ('manager', 'branch_manager') and context.get('is_manager'):
            return True
        if role in ('fleet_manager', 'fleet') and context.get('is_fleet_manager'):
            return True
        if role in ('booking_manager', 'booking', 'dispatch') and context.get('is_booking_manager'):
            return True
        if role in ('finance_user', 'finance', 'accountant') and context.get('is_finance_user'):
            return True
        if role in ('tour_designer', 'tour_designer_lead') and context.get('is_tour_designer'):
            return True
        if role in ('workshop', 'workshop_manager') and context.get('is_workshop'):
            return True
        if role in ('compliance', 'rto', 'safety') and context.get('is_compliance'):
            return True
        if role in ('night_dispatcher', 'sos') and context.get('is_night_dispatcher'):
            return True
        if role in ('b2b', 'corporate') and context.get('is_b2b_corporate'):
            return True
        if role in ('sales', 'sales_executive') and (context.get('is_sales') or context.get('is_sales_executive')):
            return True
        if role == 'driver' and context.get('is_driver'):
            return True
        if role in ('customer_service', 'support') and context.get('is_customer_service'):
            return True
    return False


@register.filter
def has_role(user, role_name):
    """Filter syntax: {% if user|has_role:'fleet_manager' %}"""
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    profile = getattr(user, 'staff_profile', None)
    if profile and profile.role == role_name:
        return True
    return user.groups.filter(name__iexact=role_name).exists()
