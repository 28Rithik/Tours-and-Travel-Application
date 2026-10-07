from functools import wraps
from django.conf import settings
from django.shortcuts import redirect, render


def role_required(*allowed_roles):
    """
    Decorator requiring user to be a superuser or member of at least one of the allowed roles.
    Allowed roles can be 'Fleet_Managers', 'Booking_Managers', 'Finance_Team'.
    If unauthorized, renders templates/403.html with HTTP status 403.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect(f"{settings.LOGIN_URL}?next={request.path}")

            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            user_groups = set(request.user.groups.values_list('name', flat=True))
            if any(role in user_groups for role in allowed_roles):
                return view_func(request, *args, **kwargs)

            return render(
                request,
                '403.html',
                {
                    'required_roles': [r.replace('_', ' ') for r in allowed_roles],
                    'user_role_label': list(user_groups)[0].replace('_', ' ') if user_groups else 'Operations Staff',
                },
                status=403,
            )
        return _wrapped_view
    return decorator
