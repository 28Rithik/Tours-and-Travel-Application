"""
Enterprise Rate Limiting Engine for TravelERP
Provides high-performance, cache-backed request rate limiting via decorators and middleware.
Compatible with both Redis (production) and LocMemCache (development).
"""
import time
import functools
from django.core.cache import caches
from django.http import JsonResponse, HttpResponse
from django.conf import settings


def get_client_ip(request):
    """
    Extract the real client IP address from request headers,
    handling reverse proxies (Nginx, Cloudflare, AWS ALB).
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        # Take the leftmost IP (the original client)
        ip = x_forwarded_for.split(',')[0].strip()
        if ip:
            return ip
    x_real_ip = request.META.get('HTTP_X_REAL_IP')
    if x_real_ip:
        return x_real_ip.strip()
    return request.META.get('REMOTE_ADDR', '127.0.0.1')


def parse_rate(rate_str):
    """
    Parses a rate string like '60/m', '5/s', '1000/h', '10000/d'.
    Returns (limit, period_seconds).
    """
    parts = rate_str.strip().lower().split('/')
    if len(parts) != 2:
        raise ValueError(f"Invalid rate format: '{rate_str}'. Expected format like '60/m'.")

    limit = int(parts[0])
    unit = parts[1]

    multipliers = {
        's': 1,
        'sec': 1,
        'second': 1,
        'm': 60,
        'min': 60,
        'minute': 60,
        'h': 3600,
        'hr': 3600,
        'hour': 3600,
        'd': 86400,
        'day': 86400,
    }

    if unit not in multipliers:
        raise ValueError(f"Unknown time unit '{unit}' in rate '{rate_str}'.")

    return limit, multipliers[unit]


def check_rate_limit(key, rate_str, cache_alias='default', increment=True):
    """
    Checks and optionally increments the request count for a given key.
    Uses a fixed-window cache counter with automatic expiration.
    Returns: (is_limited, current_count, limit, retry_after)
    """
    limit, period = parse_rate(rate_str)
    cache = caches[cache_alias]

    now = int(time.time())
    window_bucket = now // period
    cache_key = f"ratelimit:{key}:{window_bucket}"
    retry_after = (window_bucket + 1) * period - now

    try:
        # Add key with initial value 0 if not present, TTL = period + 2s buffer
        cache.add(cache_key, 0, timeout=period + 2)
        if increment:
            try:
                count = cache.incr(cache_key)
            except Exception:
                # Fallback if cache doesn't support atomic incr (e.g. dummy cache or error)
                count = (cache.get(cache_key) or 0) + 1
                cache.set(cache_key, count, timeout=period + 2)
        else:
            count = cache.get(cache_key) or 0

        is_limited = count > limit
        return is_limited, count, limit, max(1, retry_after)
    except Exception:
        # Graceful degradation: If cache fails, do not block legitimate user traffic
        return False, 0, limit, 0


def ratelimit(rate='60/m', key='ip', block=True, method='ALL', cache='default'):
    """
    View decorator for rate limiting.

    Usage:
        @ratelimit(rate='30/m', key='ip', block=True)
        def my_view(request):
            ...

        @ratelimit(rate='10/m', key='user', block=True)
        def user_specific_view(request):
            ...
    """
    def decorator(view_func):
        @functools.wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            # Check HTTP method filter
            if method != 'ALL':
                allowed_methods = [method] if isinstance(method, str) else method
                if request.method not in allowed_methods:
                    return view_func(request, *args, **kwargs)

            # Determine rate limit key
            if key == 'ip':
                key_val = get_client_ip(request)
            elif key == 'user':
                key_val = str(request.user.pk) if request.user.is_authenticated else get_client_ip(request)
            elif callable(key):
                key_val = key(request)
            else:
                key_val = get_client_ip(request)

            rate_key = f"{view_func.__module__}.{view_func.__name__}:{key_val}"
            is_limited, count, limit, retry_after = check_rate_limit(rate_key, rate, cache_alias=cache)

            # Attach metadata to request
            request.ratelimit = {
                'limited': is_limited,
                'count': count,
                'limit': limit,
                'retry_after': retry_after,
            }

            if is_limited and block:
                # Return 429 response
                response_data = {
                    'error': 'Too Many Requests',
                    'detail': f'Rate limit of {rate} exceeded. Please retry after {retry_after} seconds.',
                    'retry_after': retry_after,
                }
                resp = JsonResponse(response_data, status=429)
                resp['Retry-After'] = str(retry_after)
                return resp

            return view_func(request, *args, **kwargs)

        return _wrapped
    return decorator


class APIRateLimitMiddleware:
    """
    Middleware that applies global rate limiting to all unauthenticated API requests,
    preventing DDoS attacks and resource exhaustion.
    """
    EXEMPT_PREFIXES = (
        '/health/',
        '/static/',
        '/media/',
        '/favicon.ico',
        '/robots.txt',
        '/sitemap.xml',
    )

    def __init__(self, get_response):
        self.get_response = get_response
        self.rate = getattr(settings, 'GLOBAL_API_RATE_LIMIT', '120/m')
        self.enabled = getattr(settings, 'ENABLE_RATE_LIMITING', True)

    def __call__(self, request):
        if not self.enabled:
            return self.get_response(request)

        path = request.path

        # Only protect API paths
        is_api_path = (
            path.startswith('/api/') or
            '/api/' in path or
            path.startswith('/operations/api/') or
            path.startswith('/crm/api/')
        )

        if not is_api_path or any(path.startswith(prefix) for prefix in self.EXEMPT_PREFIXES):
            return self.get_response(request)

        # Authenticated superusers are exempt from global rate limiting
        if getattr(request, 'user', None) and request.user.is_superuser:
            return self.get_response(request)

        ip = get_client_ip(request)
        rate_key = f"global_api:{ip}"

        is_limited, count, limit, retry_after = check_rate_limit(rate_key, self.rate)

        if is_limited:
            response = JsonResponse({
                'error': 'Too Many Requests',
                'detail': f'Global API request threshold ({self.rate}) exceeded. Please retry later.',
                'retry_after': retry_after,
            }, status=429)
            response['Retry-After'] = str(retry_after)
            return response

        return self.get_response(request)
