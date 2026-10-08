from functools import wraps
from django.conf import settings
from django.shortcuts import redirect, render
from core.models import StaffProfile


def role_required(*allowed_roles):
    """
    Decorator requiring user to be a superuser or member of at least one of the allowed roles or groups.
    Allowed roles can be:
      - 'admin', 'manager', 'sales_executive', 'sales', 'operations', 'operation_account', 'driver', 'customer_service'
      - Or group names: 'Fleet_Managers', 'Booking_Managers', 'Finance_Team', 'General_Managers', etc.
    If unauthorized, renders templates/403.html with HTTP status 403.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect(f"{settings.LOGIN_URL}?next={request.path}")

            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            # Check user groups
            user_groups = set(request.user.groups.values_list('name', flat=True))
            if any(role in user_groups for role in allowed_roles):
                return view_func(request, *args, **kwargs)

            # Check user staff_profile role
            profile = getattr(request.user, 'staff_profile', None)
            if profile is None:
                try:
                    profile = StaffProfile.objects.get(user=request.user)
                except StaffProfile.DoesNotExist:
                    profile = None

            if profile:
                # Direct role match
                if profile.role in allowed_roles:
                    return view_func(request, *args, **kwargs)

                # Hierarchy & alias matching
                if 'admin' in allowed_roles and profile.role == 'admin':
                    return view_func(request, *args, **kwargs)
                if 'manager' in allowed_roles and profile.role in ('admin', 'manager'):
                    return view_func(request, *args, **kwargs)
                if ('operations' in allowed_roles or 'Fleet_Managers' in allowed_roles) and profile.role in ('admin', 'manager', 'operations'):
                    return view_func(request, *args, **kwargs)
                if ('sales_executive' in allowed_roles or 'sales' in allowed_roles or 'Booking_Managers' in allowed_roles) and profile.role in ('admin', 'manager', 'sales_executive', 'sales', 'customer_service'):
                    return view_func(request, *args, **kwargs)
                if ('operation_account' in allowed_roles or 'Finance_Team' in allowed_roles) and profile.role in ('admin', 'manager', 'operation_account'):
                    return view_func(request, *args, **kwargs)

            return render(
                request,
                '403.html',
                {
                    'required_roles': [r.replace('_', ' ') for r in allowed_roles],
                    'user_role_label': profile.get_role_display() if profile else (list(user_groups)[0].replace('_', ' ') if user_groups else 'Operations Staff'),
                },
                status=403,
            )
        return _wrapped_view
    return decorator
