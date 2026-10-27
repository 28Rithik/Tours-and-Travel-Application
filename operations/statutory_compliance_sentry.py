"""
operations/statutory_compliance_sentry.py
Commercial Fleet RTO Fitness (FC), AIS-140 GPS & Statutory Compliance Sentry
Sivagayathiri Tours & Travels ERP

Enforces Indian commercial yellow-board transport compliance:
- RTO Fitness Certificate (FC)
- AIS-140 Emergency Panic Button & GPS Telematics Certification
- Speed Governor Calibration Certificate (80 km/h / 60 km/h limiters)
- All India Tourist Permit (AITP) & State Permits
- Commercial Passenger Comprehensive & Third-Party Insurance
- Road Tax & Pollution Under Control (PUC)

Provides visual 30/15/7-day countdown radar, automated dispatch lock,
and 1-click renewal certification updates.
"""

from datetime import date, timedelta
from django.utils import timezone
from core.models import Vehicle
from maintenance.models import ComplianceDocument
from django.core.cache import cache


COMPLIANCE_CATEGORY_LABELS = {
    'fc': {'title': 'RTO Fitness Certificate (FC)', 'icon': '🔧', 'interval_months': 12},
    'speed_governor': {'title': 'Speed Governor (80 km/h) Cert', 'icon': '⚡', 'interval_months': 12},
    'ais140': {'title': 'AIS-140 GPS & Panic Button', 'icon': '📡', 'interval_months': 12},
    'insurance': {'title': 'Commercial Passenger Insurance', 'icon': '🛡️', 'interval_months': 12},
    'permit': {'title': 'AITP / State Tourist Permit', 'icon': '📋', 'interval_months': 60},
    'tax': {'title': 'State Commercial Road Tax', 'icon': '💰', 'interval_months': 3},
    'pollution': {'title': 'Pollution Under Control (PUC)', 'icon': '💨', 'interval_months': 6},
}


def get_compliance_dashboard_metrics():
    """
    Computes overall fleet compliance statistics using fast SQL aggregates,
    cached for 60 seconds to guarantee sub-millisecond response latency.
    """
    cache_key = 'compliance_dashboard_metrics_cache'
    cached_metrics = cache.get(cache_key)
    if cached_metrics is not None:
        return cached_metrics

    today = timezone.now().date()
    seven_days = today + timedelta(days=7)
    thirty_days = today + timedelta(days=30)

    from django.db.models import Count, Q
    counts = ComplianceDocument.objects.aggregate(
        total_docs=Count('id'),
        expired_docs=Count('id', filter=Q(expiry_date__lt=today)),
        critical_docs=Count('id', filter=Q(expiry_date__gte=today, expiry_date__lte=seven_days)),
        warning_docs=Count('id', filter=Q(expiry_date__gt=seven_days, expiry_date__lte=thirty_days)),
        compliant_docs=Count('id', filter=Q(expiry_date__gt=thirty_days)),
    )
    total_docs = counts['total_docs'] or 0
    expired_docs = counts['expired_docs'] or 0
    critical_docs = counts['critical_docs'] or 0
    warning_docs = counts['warning_docs'] or 0
    compliant_docs = counts['compliant_docs'] or 0

    total_vehicles = Vehicle.objects.count()
    locked_vehicles = Vehicle.objects.filter(compliance_documents__expiry_date__lt=today).distinct().count()
    vehicles_with_warnings = Vehicle.objects.filter(
        compliance_documents__expiry_date__gte=today,
        compliance_documents__expiry_date__lte=thirty_days
    ).exclude(
        compliance_documents__expiry_date__lt=today
    ).distinct().count()

    compliance_rate = 100
    if total_docs > 0:
        compliance_rate = round(((total_docs - expired_docs) / total_docs) * 100, 1)

    result = {
        'total_docs': total_docs,
        'expired_docs': expired_docs,
        'critical_docs': critical_docs,
        'warning_docs': warning_docs,
        'compliant_docs': compliant_docs,
        'total_vehicles': total_vehicles,
        'locked_vehicles': locked_vehicles,
        'vehicles_with_warnings': vehicles_with_warnings,
        'compliance_rate': compliance_rate,
    }
    cache.set(cache_key, result, timeout=60)
    return result


def get_fleet_compliance_matrix(search_query=None, limit=120):
    """
    Builds a vehicle-by-vehicle statutory readiness matrix for dispatchers.
    Prefetches compliance documents to prevent N+1 queries.
    """
    today = timezone.now().date()
    qs = Vehicle.objects.prefetch_related('compliance_documents').order_by('registration_number')
    if search_query:
        qs = qs.filter(registration_number__icontains=search_query)
    vehicles = qs[:limit]
    matrix = []

    for v in vehicles:
        docs = {d.document_type: d for d in v.compliance_documents.all()}
        doc_summaries = {}
        has_expired = False
        has_critical = False

        for dtype, meta in COMPLIANCE_CATEGORY_LABELS.items():
            doc = docs.get(dtype)
            if not doc:
                doc_summaries[dtype] = {
                    'status': 'missing',
                    'badge': '⚠️ Missing Record',
                    'days_left': None,
                    'expiry': None,
                    'doc_number': None,
                }
                has_critical = True
            else:
                days_left = (doc.expiry_date - today).days
                if days_left < 0:
                    status = 'expired'
                    badge = f"🔴 Expired {abs(days_left)}d ago"
                    has_expired = True
                elif days_left <= 7:
                    status = 'critical'
                    badge = f"⏰ {days_left}d Left"
                    has_critical = True
                elif days_left <= 30:
                    status = 'warning'
                    badge = f"🟡 {days_left}d Left"
                else:
                    status = 'compliant'
                    badge = f"🟢 {days_left}d Valid"

                doc_summaries[dtype] = {
                    'status': status,
                    'badge': badge,
                    'days_left': days_left,
                    'expiry': doc.expiry_date.strftime('%d-%b-%Y'),
                    'doc_number': doc.document_number or '—',
                    'doc_id': doc.id,
                }

        # Overall dispatch readiness
        if has_expired:
            dispatch_status = 'LOCKED'
            status_color = 'red'
        elif has_critical:
            dispatch_status = 'ACTION_REQUIRED'
            status_color = 'amber'
        else:
            dispatch_status = 'CLEARED'
            status_color = 'emerald'

        matrix.append({
            'vehicle_id': v.id,
            'reg_no': v.registration_number,
            'model': f"{v.brand} {v.model}".strip() if v.brand or v.model else v.registration_number,
            'seating': getattr(v, 'seating_capacity', 7),
            'dispatch_status': dispatch_status,
            'status_color': status_color,
            'docs': doc_summaries,
        })

    return matrix


def is_vehicle_legally_clear_for_dispatch(vehicle_id):
    """
    Guard rule for dispatch engine:
    Checks if vehicle has any expired statutory papers.
    """
    today = timezone.now().date()
    vehicle = Vehicle.objects.get(pk=vehicle_id)
    expired_docs = vehicle.compliance_documents.filter(expiry_date__lt=today)
    
    if expired_docs.exists():
        issues = [f"{d.get_document_type_display()} expired on {d.expiry_date}" for d in expired_docs]
        return False, issues
    return True, []


def renew_compliance_document(doc_id, new_expiry_date, new_doc_number="", notes=""):
    """
    Updates a compliance certificate with new renewal dates.
    """
    doc = ComplianceDocument.objects.get(pk=doc_id)
    doc.expiry_date = new_expiry_date
    if new_doc_number:
        doc.document_number = new_doc_number
    if notes:
        doc.notes = f"{doc.notes}\n[Renewed on {timezone.now().strftime('%Y-%m-%d')}]: {notes}".strip()
    doc.save()
    cache.delete('compliance_dashboard_metrics_cache')
    return doc


def seed_statutory_compliance_records():
    """
    Populates sample compliance documents for vehicles ensuring all 7 categories exist.
    """
    today = timezone.now().date()
    vehicles = Vehicle.objects.all()[:8]

    if not vehicles:
        return

    sample_configs = [
        # Vehicle 1: Fully Compliant
        {
            'fc': (today + timedelta(days=210), 'FC/TN38/2026/8812'),
            'speed_governor': (today + timedelta(days=190), 'SG-ROS-44021'),
            'ais140': (today + timedelta(days=240), 'AIS-140-TN-9921'),
            'insurance': (today + timedelta(days=150), 'UIIC-COMM-8821094'),
            'permit': (today + timedelta(days=730), 'AITP-TN-2025-091'),
            'tax': (today + timedelta(days=60), 'RTO-TAX-TN38-2026-Q4'),
            'pollution': (today + timedelta(days=110), 'PUC-TN-994102'),
        },
        # Vehicle 2: FC Expiring in 5 days (Critical)
        {
            'fc': (today + timedelta(days=5), 'FC/TN38/2025/1102'),
            'speed_governor': (today + timedelta(days=180), 'SG-AUT-11024'),
            'ais140': (today + timedelta(days=210), 'AIS-140-TN-1102'),
            'insurance': (today + timedelta(days=120), 'NIC-COMM-449102'),
            'permit': (today + timedelta(days=400), 'AITP-TN-2024-551'),
            'tax': (today + timedelta(days=45), 'RTO-TAX-TN38-2026-Q4'),
            'pollution': (today + timedelta(days=90), 'PUC-TN-882103'),
        },
        # Vehicle 3: Insurance Expired (Locked!)
        {
            'fc': (today + timedelta(days=120), 'FC/TN43/2026/0091'),
            'speed_governor': (today + timedelta(days=140), 'SG-PRM-99120'),
            'ais140': (today + timedelta(days=160), 'AIS-140-TN-0091'),
            'insurance': (today - timedelta(days=3), 'BAJAJ-COMM-99410'),
            'permit': (today + timedelta(days=500), 'AITP-TN-2024-883'),
            'tax': (today + timedelta(days=70), 'RTO-TAX-TN43-2026-Q4'),
            'pollution': (today + timedelta(days=40), 'PUC-TN-771204'),
        },
        # Vehicle 4: AIS-140 & Speed Governor Warning (< 25 days)
        {
            'fc': (today + timedelta(days=80), 'FC/TN37/2026/4412'),
            'speed_governor': (today + timedelta(days=18), 'SG-ROS-88319'),
            'ais140': (today + timedelta(days=22), 'AIS-140-TN-4412'),
            'insurance': (today + timedelta(days=95), 'HDFC-ERGO-44129'),
            'permit': (today + timedelta(days=600), 'AITP-TN-2025-441'),
            'tax': (today + timedelta(days=35), 'RTO-TAX-TN37-2026-Q4'),
            'pollution': (today + timedelta(days=55), 'PUC-TN-441290'),
        },
    ]

    for idx, v in enumerate(vehicles):
        cfg = sample_configs[idx % len(sample_configs)]
        for dtype, (exp_date, doc_num) in cfg.items():
            doc = ComplianceDocument.objects.filter(vehicle=v, document_type=dtype).first()
            if not doc:
                doc = ComplianceDocument(
                    vehicle=v,
                    document_type=dtype,
                    document_number=doc_num,
                    issue_date=exp_date - timedelta(days=365),
                    expiry_date=exp_date,
                    notes=f"Statutory {COMPLIANCE_CATEGORY_LABELS[dtype]['title']} recorded in ERP."
                )
            else:
                doc.expiry_date = exp_date
                doc.document_number = doc_num
            doc.save()
