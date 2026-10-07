import json
from decimal import Decimal
from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods

from core.models import Vehicle, VehicleType
from .cpk_engine import (
    DEFAULT_DIESEL_PRICE,
    get_fleet_cpk_radar_metrics,
    calculate_vehicle_cpk,
    get_route_profitability_benchmarks,
    simulate_what_if_tariff,
    get_fuel_anomaly_radar,
)


@login_required
def admin_cpk_radar_studio_view(request):
    """
    Enterprise Django Unfold Real-Time Fleet Profitability & Cost-Per-KM (CPK) Optimization Radar Studio.
    Factors live diesel prices, FASTag tolls, driver batta, and vehicle maintenance vs revenue.
    """
    diesel_price_raw = request.GET.get('diesel_price')
    diesel_price = Decimal(diesel_price_raw) if diesel_price_raw and diesel_price_raw.replace('.', '', 1).isdigit() else DEFAULT_DIESEL_PRICE

    tier_filter = request.GET.get('tier')
    search_query = request.GET.get('q', '').strip().lower()

    metrics = get_fleet_cpk_radar_metrics(diesel_price_override=diesel_price)
    benchmarks = get_route_profitability_benchmarks(diesel_price=diesel_price)
    anomalies = get_fuel_anomaly_radar()
    vehicle_types = VehicleType.objects.all().order_by('name')

    # Apply filtering to leaderboard if specified
    filtered_leaderboard = metrics['leaderboard']
    if tier_filter:
        filtered_leaderboard = [v for v in filtered_leaderboard if v['tier'] == tier_filter]
    if search_query:
        filtered_leaderboard = [
            v for v in filtered_leaderboard
            if search_query in v['registration_number'].lower() or search_query in v['model_name'].lower()
        ]

    # Pre-calculated simulation for initial load
    initial_sim = simulate_what_if_tariff(
        diesel_price=diesel_price,
        distance_km=350,
        vehicle_category='innova',
        target_margin_pct=Decimal('25.0')
    )

    context = {
        'title': 'Fleet Profitability & Cost-Per-KM (CPK) Optimization Radar',
        'diesel_price': diesel_price,
        'metrics': metrics,
        'leaderboard': filtered_leaderboard,
        'tier_filter': tier_filter,
        'search_query': search_query,
        'benchmarks': benchmarks,
        'anomalies': anomalies,
        'vehicle_types': vehicle_types,
        'initial_sim': initial_sim,
        'current_tab': request.GET.get('tab', 'leaderboard'),
    }
    return render(request, 'admin/finance/cpk_radar_studio.html', context)


@login_required
def api_cpk_radar_metrics(request):
    """
    JSON API: Real-time fleet CPK metrics, leaderboard, and tier counts with dynamic diesel price override.
    """
    diesel_price_raw = request.GET.get('diesel_price')
    diesel_price = Decimal(diesel_price_raw) if diesel_price_raw and diesel_price_raw.replace('.', '', 1).isdigit() else DEFAULT_DIESEL_PRICE

    metrics = get_fleet_cpk_radar_metrics(diesel_price_override=diesel_price)

    # Convert Decimals for JSON serialization
    serialized_leaderboard = []
    for item in metrics['leaderboard'][:30]:
        serialized_leaderboard.append({
            'vehicle_id': item['vehicle_id'],
            'registration_number': item['registration_number'],
            'model_name': item['model_name'],
            'vehicle_type': item['vehicle_type'],
            'total_km': item['total_km'],
            'billed_revenue': float(item['billed_revenue']),
            'total_cost': float(item['total_operating_cost']),
            'fuel_cpk': float(item['fuel_cpk']),
            'toll_cpk': float(item['toll_cpk']),
            'driver_cpk': float(item['driver_cpk']),
            'maintenance_cpk': float(item['maintenance_cpk']),
            'fixed_cpk': float(item['fixed_cpk']),
            'total_cpk': float(item['total_cpk']),
            'rpk': float(item['rpk']),
            'net_profit': float(item['net_profit']),
            'margin_pct': float(item['margin_pct']),
            'tier': item['tier'],
            'tier_label': item['tier_label'],
            'is_theft_suspected': item['is_theft_suspected'],
        })

    return JsonResponse({
        'success': True,
        'diesel_price': float(diesel_price),
        'vehicles_analyzed': metrics['vehicles_analyzed'],
        'total_fleet_km': metrics['total_fleet_km'],
        'total_fleet_revenue': float(metrics['total_fleet_revenue']),
        'total_fleet_cost': float(metrics['total_fleet_cost']),
        'fleet_net_profit': float(metrics['fleet_net_profit']),
        'fleet_margin_pct': float(metrics['fleet_margin_pct']),
        'fleet_avg_cpk': float(metrics['fleet_avg_cpk']),
        'fleet_avg_rpk': float(metrics['fleet_avg_rpk']),
        'fleet_fuel_cpk': float(metrics['fleet_fuel_cpk']),
        'fleet_toll_cpk': float(metrics['fleet_toll_cpk']),
        'fleet_driver_cpk': float(metrics['fleet_driver_cpk']),
        'fleet_maint_cpk': float(metrics['fleet_maint_cpk']),
        'fleet_fixed_cpk': float(metrics['fleet_fixed_cpk']),
        'theft_alert_count': metrics['theft_alert_count'],
        'total_theft_loss': float(metrics['total_theft_loss']),
        'tier_counts': metrics['tier_counts'],
        'leaderboard': serialized_leaderboard,
    })


@login_required
@require_http_methods(['GET', 'POST'])
def api_optimize_tariff(request):
    """
    JSON API: Real-time What-If Tariff Simulation & Break-Even Quote Optimizer.
    """
    if request.method == 'POST':
        try:
            if request.content_type == 'application/json':
                data = json.loads(request.body.decode('utf-8'))
            else:
                data = request.POST.dict()
        except Exception:
            data = request.POST.dict()
    else:
        data = request.GET.dict()

    diesel_price = Decimal(str(data.get('diesel_price') or DEFAULT_DIESEL_PRICE))
    distance_km = int(data.get('distance_km') or 300)
    vehicle_cat = str(data.get('vehicle_category') or 'innova').lower()
    target_margin = Decimal(str(data.get('target_margin_pct') or '25.0'))
    days_count = int(data.get('days_count') or 1)
    toll_override = Decimal(str(data['toll_override'])) if data.get('toll_override') else None

    sim = simulate_what_if_tariff(
        diesel_price=diesel_price,
        distance_km=distance_km,
        vehicle_category=vehicle_cat,
        target_margin_pct=target_margin,
        toll_override=toll_override,
        days_count=days_count
    )

    return JsonResponse({
        'success': True,
        'diesel_price': float(sim['diesel_price']),
        'distance_km': sim['distance_km'],
        'vehicle_category': sim['vehicle_category'],
        'days_count': sim['days_count'],
        'mileage_kmpl': float(sim['mileage_kmpl']),
        'fuel_liters': float(sim['fuel_liters']),
        'fuel_cost': float(sim['fuel_cost']),
        'toll_cost': float(sim['toll_cost']),
        'driver_cost': float(sim['driver_cost']),
        'maintenance_cost': float(sim['maintenance_cost']),
        'fixed_overhead': float(sim['fixed_overhead']),
        'total_trip_cost': float(sim['total_trip_cost']),
        'cpk': float(sim['cpk']),
        'break_even_quote': float(sim['break_even_quote']),
        'target_margin_pct': float(sim['target_margin_pct']),
        'recommended_quote': float(sim['recommended_quote']),
        'recommended_rpk': float(sim['recommended_rpk']),
        'projected_profit': float(sim['projected_profit']),
    })
