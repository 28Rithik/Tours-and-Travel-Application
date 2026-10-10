from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from packages.models import Package
from finance.models import Payment
from operations.models import Booking
from core.models import Client
from django.db.models import Sum, Count
from django.db.models.functions import TruncMonth
import datetime
from django.utils import timezone

@staff_member_required
def package_profitability_dashboard(request):
    """
    Reporting dashboard for package profitability, customer profitability, and forecasting.
    Accessible only by staff (Admin).
    """
    # 1. Package Profitability
    packages = list(Package.objects.all())
    package_rev_map = dict(
        Payment.objects.filter(
            booking__package__isnull=False,
            payment_type='customer_receipt'
        ).values('booking__package_id').annotate(
            total=Sum('amount')
        ).values_list('booking__package_id', 'total')
    )
    package_bookings_map = dict(
        Booking.objects.filter(
            package__isnull=False
        ).values('package_id').annotate(
            count=Count('id')
        ).values_list('package_id', 'count')
    )
    package_data = []
    for package in packages:
        package_data.append({
            'package_name': package.name,
            'total_bookings': package_bookings_map.get(package.pk, 0),
            'revenue': package_rev_map.get(package.pk, 0)
        })
        
    # 2. Customer Profitability
    customers = list(Client.objects.all())
    customer_rev_map = dict(
        Payment.objects.filter(
            booking__party__isnull=False,
            payment_type='customer_receipt'
        ).values('booking__party_id').annotate(
            total=Sum('amount')
        ).values_list('booking__party_id', 'total')
    )
    customer_bookings_map = dict(
        Booking.objects.filter(
            party__isnull=False
        ).values('party_id').annotate(
            count=Count('id')
        ).values_list('party_id', 'count')
    )
    customer_data = []
    for customer in customers:
        total_revenue = customer_rev_map.get(customer.pk, 0)
        if total_revenue > 0:
            customer_data.append({
                'name': customer.name,
                'total_bookings': customer_bookings_map.get(customer.pk, 0),
                'revenue': total_revenue
            })
            
    # Sort customers by revenue
    customer_data = sorted(customer_data, key=lambda x: x['revenue'], reverse=True)[:20] # Top 20

    # 3. Seasonal Demand Forecasting (Past 12 months trend)
    one_year_ago = timezone.now().date() - datetime.timedelta(days=365)
    monthly_trend = Booking.objects.filter(
        booking_date__gte=one_year_ago
    ).annotate(
        month=TruncMonth('booking_date')
    ).values('month').annotate(
        count=Count('id')
    ).order_by('month')
    
    forecast_data = []
    for item in monthly_trend:
        forecast_data.append({
            'month': item['month'].strftime('%B %Y') if item['month'] else 'Unknown',
            'bookings': item['count']
        })
        
    return render(request, 'analytics/dashboard.html', {
        'package_data': package_data,
        'customer_data': customer_data,
        'forecast_data': forecast_data
    })


from decimal import Decimal
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from core.models import Vehicle, Driver
from .models import DriverScorecard
from .services import (
    calculate_driver_scorecard,
    calculate_vehicle_cpk,
    calculate_fleet_cpk_bulk,
    get_fleet_utilization_breakdown,
    get_driver_scorecards_leaderboard,
)


import time
from django.core.cache import cache

FLEET_ANALYTICS_CACHE_KEY = 'fleet_analytics_payload_v3'
FLEET_ANALYTICS_CACHE_TTL = 600  # 10 minutes


@staff_member_required
def fleet_analytics_dashboard(request):
    """
    Fleet Intelligence Command:
    - True Cost-Per-KM (CPK) Analysis by Vehicle & Model (bulk single-query set aggregates)
    - Fleet Utilization breakdown (Active vs Standby vs Workshop vs Idle)
    - Captain Driver Performance Scorecards Leaderboard
    - High-Performance In-Memory Caching (Sub-5ms on cache hits)
    """
    t_start = time.perf_counter()
    refresh_scores = request.GET.get('refresh', '').lower() in ['1', 'true', 'yes']

    cached_data = None if refresh_scores else cache.get(FLEET_ANALYTICS_CACHE_KEY)

    if cached_data is not None:
        utilization = cached_data['utilization']
        cpk_list = cached_data['cpk_list']
        benchmarks_summary = cached_data['benchmarks_summary']
        scorecards = cached_data['scorecards']
        cached_at = cached_data.get('cached_at', 'Just now')
        from_cache = True
    else:
        # 1. Utilization Breakdown (4 bulk queries)
        utilization = get_fleet_utilization_breakdown()

        # 2. Vehicle CPK Performance (bulk prefetch & single aggregates)
        vehicles = list(Vehicle.objects.all().select_related('vehicle_type'))
        cpk_list = calculate_fleet_cpk_bulk(vehicles)

        # Benchmark CPK by Vehicle Type
        model_benchmarks = {}
        for item in cpk_list:
            vtype = item['vehicle_type']
            if vtype not in model_benchmarks:
                model_benchmarks[vtype] = {
                    'count': 0,
                    'total_cost': Decimal('0.0'),
                    'total_km': 0,
                    'total_revenue': Decimal('0.0'),
                }
            model_benchmarks[vtype]['count'] += 1
            model_benchmarks[vtype]['total_cost'] += item['total_cost']
            model_benchmarks[vtype]['total_km'] += item['total_km']
            model_benchmarks[vtype]['total_revenue'] += item['revenue']

        benchmarks_summary = []
        for vtype, data in model_benchmarks.items():
            km = Decimal(str(max(1, data['total_km'])))
            avg_cpk = round(data['total_cost'] / km, 2)
            avg_rpk = round(data['total_revenue'] / km, 2)
            margin = round(avg_rpk - avg_cpk, 2)
            benchmarks_summary.append({
                'vehicle_type': vtype,
                'count': data['count'],
                'avg_cpk': avg_cpk,
                'avg_rpk': avg_rpk,
                'margin': margin,
            })

        # 3. Driver Scorecard Leaderboard (persisted monthly snapshots or bulk computed)
        scorecards = get_driver_scorecards_leaderboard(refresh=refresh_scores)

        cached_at = timezone.now().strftime('%d %b, %H:%M:%S')
        from_cache = False

        cache.set(FLEET_ANALYTICS_CACHE_KEY, {
            'utilization': utilization,
            'cpk_list': cpk_list,
            'benchmarks_summary': benchmarks_summary,
            'scorecards': scorecards,
            'cached_at': cached_at,
        }, timeout=FLEET_ANALYTICS_CACHE_TTL)

    t_elapsed_ms = round((time.perf_counter() - t_start) * 1000, 1)

    return render(request, 'analytics/fleet_dashboard.html', {
        'utilization': utilization,
        'cpk_list': cpk_list,
        'benchmarks_summary': benchmarks_summary,
        'scorecards': scorecards,
        'from_cache': from_cache,
        'cached_at': cached_at,
        't_elapsed_ms': t_elapsed_ms,
    })


@staff_member_required
def api_driver_scorecard_detail(request, driver_id):
    driver = get_object_or_404(Driver, pk=driver_id)
    card = calculate_driver_scorecard(driver)
    return JsonResponse({
        "status": "success",
        "driver": {
            "id": driver.pk,
            "name": driver.name,
            "phone": driver.phone,
        },
        "scorecard": {
            "month": card.month.strftime('%B %Y'),
            "grade": card.grade,
            "overall_score": float(card.overall_composite_score),
            "punctuality_score": float(card.punctuality_score),
            "safety_score": float(card.safety_score),
            "customer_rating_score": float(card.customer_rating_score),
            "fuel_efficiency_score": float(card.fuel_efficiency_score),
            "total_trips": card.total_trips,
            "total_kms": card.total_kms_driven,
            "overspeeding_count": card.overspeeding_count,
            "harsh_braking_count": card.harsh_braking_count,
            "traffic_fines_count": card.traffic_fines_count,
            "average_rating": float(card.average_rating),
        }
    })

