from django.core.cache import cache
from core.models import VehicleType
from fleet_contracts.models import TransportContract

CACHE_KEY_VEHICLE_TYPES = 'master:vehicle_types'
CACHE_KEY_ACTIVE_CONTRACTS = 'master:active_transport_contracts'
CACHE_KEY_TELEMATICS_PREFIX = 'telematics:vehicle'


def get_cached_vehicle_types():
    """
    Returns list of all VehicleType objects cached in-memory for 1 hour.
    """
    vtypes = cache.get(CACHE_KEY_VEHICLE_TYPES)
    if vtypes is None:
        vtypes = list(VehicleType.objects.all().order_by('name'))
        cache.set(CACHE_KEY_VEHICLE_TYPES, vtypes, timeout=3600)
    return vtypes


def invalidate_vehicle_types_cache():
    """Invalidates cached vehicle types."""
    cache.delete(CACHE_KEY_VEHICLE_TYPES)


def get_cached_active_contracts():
    """
    Returns list of active TransportContract objects cached in-memory for 15 minutes.
    """
    contracts = cache.get(CACHE_KEY_ACTIVE_CONTRACTS)
    if contracts is None:
        contracts = list(TransportContract.objects.filter(status='active').order_by('name'))
        cache.set(CACHE_KEY_ACTIVE_CONTRACTS, contracts, timeout=900)
    return contracts


def invalidate_active_contracts_cache():
    """Invalidates cached active contracts."""
    cache.delete(CACHE_KEY_ACTIVE_CONTRACTS)


def get_cached_latest_telematics(vehicle_id):
    """
    Retrieves the latest GPS telematics dictionary for a vehicle from memory cache.
    Returns None if cache miss.
    """
    if not vehicle_id:
        return None
    key = f"{CACHE_KEY_TELEMATICS_PREFIX}:{vehicle_id}:latest"
    return cache.get(key)


def set_cached_latest_telematics(vehicle_id, ping_data):
    """
    Caches latest GPS telematics dictionary in memory with a 120-second TTL.
    """
    if not vehicle_id or not ping_data:
        return
    key = f"{CACHE_KEY_TELEMATICS_PREFIX}:{vehicle_id}:latest"
    cache.set(key, ping_data, timeout=120)


# ==============================================================================
# Phase 4: High-Performance Binary PDF In-Memory Caching Tier
# ==============================================================================

def get_or_render_cached_pdf(cache_key: str, render_fn, timeout: int = 3600) -> bytes:
    """
    Retrieves rendered PDF bytes from in-memory cache if present.
    On cache miss, executes the generator function (e.g. ReportLab),
    caches the generated binary bytes in RAM, and returns them.
    Subsequent downloads return in < 2ms without CPU rendering penalty.
    """
    cached_pdf = cache.get(cache_key)
    if cached_pdf is not None:
        return cached_pdf

    pdf_bytes = render_fn()
    if pdf_bytes:
        cache.set(cache_key, pdf_bytes, timeout=timeout)
    return pdf_bytes


def invalidate_cached_pdf(cache_key: str):
    """Purges a specific cached PDF document from memory."""
    cache.delete(cache_key)

