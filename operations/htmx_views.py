import datetime
from decimal import Decimal
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from core.models import Party, Vehicle, Driver
from operations.models import Booking, Trip, BulkContract
from packages.models import Package, PackageInventory
from maintenance.models import DefectTicket


@login_required
@require_http_methods(["GET", "POST"])
def htmx_booking_package_context(request):
    """
    HTMX partial returning rich package overview and interactive departure batch
    selectors with real-time seat counts.
    """
    package_id = request.GET.get('package') or request.GET.get('package_id') or request.POST.get('package')
    if not package_id:
        return HttpResponse("")

    try:
        package = Package.objects.filter(pk=package_id).first()
    except (ValueError, TypeError):
        return HttpResponse("")

    if not package:
        return HttpResponse("")

    today = timezone.now().date()
    batches = PackageInventory.objects.filter(
        package=package,
        departure_date__gte=today
    ).exclude(status='cancelled').order_by('departure_date')[:8]

    batch_data = []
    for b in batches:
        free = b.available_seats
        batch_data.append({
            'obj': b,
            'departure_str': b.departure_date.strftime('%d %b %Y'),
            'return_str': b.return_date.strftime('%d %b %Y') if b.return_date else '',
            'free_seats': free,
            'total_seats': b.total_seats,
            'is_sold_out': free <= 0 or b.status == 'sold_out',
        })

    return render(request, 'htmx/booking_package_card.html', {
        'package': package,
        'batches': batch_data,
        'batch_count': len(batch_data),
    })


@login_required
@require_http_methods(["GET", "POST"])
def htmx_booking_quote_calc(request):
    """
    HTMX partial calculating live quotation estimates with GST and balance.
    """
    params = request.POST if request.method == 'POST' else request.GET

    try:
        pax = int(params.get('pax_count') or 1)
        if pax <= 0:
            pax = 1
    except (ValueError, TypeError):
        pax = 1

    try:
        price_str = params.get('quoted_price', '0').replace(',', '').strip()
        quoted_price = Decimal(price_str) if price_str else Decimal('0.00')
    except Exception:
        quoted_price = Decimal('0.00')

    try:
        gst_str = params.get('gst_rate', '5').replace('%', '').strip()
        gst_rate = Decimal(gst_str) if gst_str else Decimal('5.00')
    except Exception:
        gst_rate = Decimal('5.00')

    try:
        adv_str = params.get('advance_received', '0').replace(',', '').strip()
        advance = Decimal(adv_str) if adv_str else Decimal('0.00')
    except Exception:
        advance = Decimal('0.00')

    gst_amount = (quoted_price * (gst_rate / Decimal('100'))).quantize(Decimal('0.01'))
    grand_total = (quoted_price + gst_amount).quantize(Decimal('0.01'))
    balance_due = max(Decimal('0.00'), grand_total - advance)
    per_pax = (grand_total / pax).quantize(Decimal('0.01')) if pax > 0 else grand_total

    return render(request, 'htmx/booking_quote_calc.html', {
        'pax': pax,
        'quoted_price': quoted_price,
        'gst_rate': gst_rate,
        'gst_amount': gst_amount,
        'grand_total': grand_total,
        'advance': advance,
        'balance_due': balance_due,
        'per_pax': per_pax,
    })


@login_required
@require_http_methods(["GET", "POST"])
def htmx_party_ledger_summary(request):
    """
    HTMX partial returning client / vendor ledger snapshot.
    """
    party_id = request.GET.get('party') or request.GET.get('party_id') or request.POST.get('party')
    if not party_id:
        return HttpResponse("")

    try:
        party = Party.objects.filter(pk=party_id).first()
    except (ValueError, TypeError):
        return HttpResponse("")

    if not party:
        return HttpResponse("")

    try:
        from finance.services import calculate_party_ledger
        ledger = calculate_party_ledger(party)
        closing_balance = ledger.get('closing_balance', party.opening_balance)
    except Exception:
        closing_balance = party.opening_balance

    active_bookings = party.bookings.exclude(status__in=['completed', 'cancelled']).count()
    active_trips = party.trips.filter(status__in=['assigned', 'started']).count()

    return render(request, 'htmx/party_ledger_card.html', {
        'party': party,
        'closing_balance': closing_balance,
        'is_due': closing_balance > 0,
        'is_credit': closing_balance < 0,
        'active_bookings': active_bookings,
        'active_trips': active_trips,
    })


@login_required
@require_http_methods(["GET", "POST"])
def htmx_vehicle_compliance_gate(request):
    """
    HTMX partial verifying RTO compliance, FC, insurance, and open defect tickets.
    """
    params = request.POST if request.method == 'POST' else request.GET
    vehicle_id = params.get('vehicle') or params.get('vehicle_id')
    if not vehicle_id:
        return HttpResponse("")

    try:
        vehicle = Vehicle.objects.select_related('vehicle_type').filter(pk=vehicle_id).first()
    except (ValueError, TypeError):
        return HttpResponse("")

    if not vehicle:
        return HttpResponse("")

    start_date_str = params.get('start_date')
    trip_date = timezone.now().date()
    if start_date_str:
        try:
            trip_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
        except ValueError:
            pass

    violations = []
    if vehicle.status == 'maintenance':
        violations.append("Vehicle is under active workshop maintenance.")
    elif vehicle.status == 'out_of_service':
        violations.append("Vehicle is marked out of service.")

    if vehicle.fc_expiry and vehicle.fc_expiry < trip_date:
        violations.append(f"Fitness Certificate (FC) expired on {vehicle.fc_expiry.strftime('%d-%b-%Y')}")
    if vehicle.insurance_expiry and vehicle.insurance_expiry < trip_date:
        violations.append(f"Insurance expired on {vehicle.insurance_expiry.strftime('%d-%b-%Y')}")
    if vehicle.permit_expiry and vehicle.permit_expiry < trip_date:
        violations.append(f"State/All-India Permit expired on {vehicle.permit_expiry.strftime('%d-%b-%Y')}")
    if vehicle.tax_expiry and vehicle.tax_expiry < trip_date:
        violations.append(f"Road Tax expired on {vehicle.tax_expiry.strftime('%d-%b-%Y')}")
    if vehicle.pollution_expiry and vehicle.pollution_expiry < trip_date:
        violations.append(f"Pollution (PUC) certificate expired on {vehicle.pollution_expiry.strftime('%d-%b-%Y')}")

    open_defects = DefectTicket.objects.filter(vehicle=vehicle, status='open')
    defect_count = open_defects.count()
    if defect_count > 0:
        violations.append(f"{defect_count} open safety defect ticket(s) pending in workshop.")

    return render(request, 'htmx/vehicle_compliance_badge.html', {
        'vehicle': vehicle,
        'trip_date': trip_date,
        'violations': violations,
        'is_compliant': len(violations) == 0,
        'defect_count': defect_count,
    })


@login_required
@require_http_methods(["GET", "POST"])
def htmx_driver_status_card(request):
    """
    HTMX partial displaying driver qualification, license validity, and assignment safety.
    """
    params = request.POST if request.method == 'POST' else request.GET
    driver_id = params.get('driver') or params.get('driver_id')
    if not driver_id:
        return HttpResponse("")

    try:
        driver = Driver.objects.filter(pk=driver_id).first()
    except (ValueError, TypeError):
        return HttpResponse("")

    if not driver:
        return HttpResponse("")

    start_date_str = params.get('start_date')
    trip_date = timezone.now().date()
    if start_date_str:
        try:
            trip_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
        except ValueError:
            pass

    issues = []
    if driver.status != 'active':
        issues.append(f"Driver is {driver.get_status_display()}, not active.")

    license_exp = driver.license_validity_tr or driver.license_validity_nt
    if license_exp and license_exp < trip_date:
        issues.append(f"Driving License expired on {license_exp.strftime('%d-%b-%Y')}")

    # Check active trip conflicts
    conflicts = Trip.objects.filter(
        driver=driver,
        status__in=['started', 'assigned', 'driver_confirmed'],
        start_date__lte=trip_date,
        end_date__gte=trip_date
    )
    conflict_trip = conflicts.first()
    if conflict_trip:
        issues.append(f"Conflict: Already assigned to Trip #{conflict_trip.trip_id} on {trip_date.strftime('%d-%b-%Y')}")

    return render(request, 'htmx/driver_status_card.html', {
        'driver': driver,
        'issues': issues,
        'is_cleared': len(issues) == 0,
        'trip_date': trip_date,
    })


@login_required
@require_http_methods(["GET", "POST"])
def htmx_trip_calculate_totals(request):
    """
    HTMX partial calculating live trip billing, distance, extra KMs, driver bata,
    and total customer billing amount.
    """
    params = request.POST if request.method == 'POST' else request.GET
    billing_model = params.get('billing_model', 'fixed')

    def to_dec(val, default='0.00'):
        try:
            return Decimal(str(val).replace(',', '').strip()) if val else Decimal(default)
        except Exception:
            return Decimal(default)

    day_rate = to_dec(params.get('day_rate'))
    km_rate = to_dec(params.get('km_rate'))
    fixed_amount = to_dec(params.get('fixed_amount'))
    days_count = to_dec(params.get('days_count'), '1.00')
    driver_bata = to_dec(params.get('driver_bata'))
    fines = to_dec(params.get('customer_billable_fines'))
    
    opening_km = to_dec(params.get('opening_km'))
    closing_km = to_dec(params.get('closing_km'))
    total_km = max(Decimal('0'), closing_km - opening_km) if closing_km > opening_km else Decimal('0')

    base_amount = Decimal('0.00')
    if billing_model == 'km':
        base_amount = total_km * km_rate
    elif billing_model == 'day':
        base_amount = days_count * day_rate
    elif billing_model in ['fixed', 'package']:
        base_amount = fixed_amount

    grand_total = (base_amount + driver_bata + fines).quantize(Decimal('0.01'))

    return render(request, 'htmx/trip_pricing_summary.html', {
        'billing_model': billing_model,
        'day_rate': day_rate,
        'km_rate': km_rate,
        'fixed_amount': fixed_amount,
        'days_count': days_count,
        'driver_bata': driver_bata,
        'fines': fines,
        'total_km': total_km,
        'base_amount': base_amount,
        'grand_total': grand_total,
    })


@login_required
@require_http_methods(["GET", "POST"])
def htmx_fine_vehicle_driver(request):
    """
    HTMX partial looking up driver, vehicle, and date from an associated Trip
    for Traffic Fine registration.
    """
    params = request.POST if request.method == 'POST' else request.GET
    trip_id = params.get('trip') or params.get('trip_id')
    if not trip_id:
        return HttpResponse("")

    try:
        trip = Trip.objects.select_related('vehicle', 'driver', 'party').filter(pk=trip_id).first()
    except (ValueError, TypeError):
        return HttpResponse("")

    if not trip:
        return HttpResponse("")

    return render(request, 'htmx/traffic_fine_trip_context.html', {
        'trip': trip,
        'vehicle': trip.vehicle,
        'driver': trip.driver,
        'start_date': trip.start_date,
    })


@login_required
@require_http_methods(["GET", "POST"])
def htmx_contract_rate_lookup(request):
    """
    HTMX partial looking up agreed vehicle rates and day specs for a BulkContract.
    """
    params = request.POST if request.method == 'POST' else request.GET
    contract_id = params.get('contract') or params.get('contract_id')
    if not contract_id:
        return HttpResponse("")

    try:
        contract = BulkContract.objects.prefetch_related('vehicle_rates__vehicle_type').filter(pk=contract_id).first()
    except (ValueError, TypeError):
        return HttpResponse("")

    if not contract:
        return HttpResponse("")

    rates = contract.vehicle_rates.all()
    days_count = contract.days.count()

    return render(request, 'htmx/contract_rate_card.html', {
        'contract': contract,
        'rates': rates,
        'days_count': days_count,
    })


@login_required
@require_http_methods(["GET", "POST"])
def htmx_ai_quotation_calc(request):
    """
    🤖 Dynamic AI Quotation & Tariff Calculator.
    Computes route distance, applies hill station surcharges,
    interstate permits, driver bata, toll/parking, and GST.
    """
    from operations.quotation_engine import compute_single_vehicle_quote
    from core.models import VehicleType

    params = request.POST if request.method == 'POST' else request.GET
    origin = params.get('origin', '').strip()
    destination = params.get('destination', '').strip()

    if not origin or not destination:
        vehicle_types = VehicleType.objects.all().order_by('name')
        return render(request, 'htmx/ai_quotation_form.html', {
            'vehicle_types': vehicle_types,
            'show_form': True,
        })

    vehicle_type_id = params.get('vehicle_type_id') or None
    trip_type = params.get('trip_type', 'round_trip')
    duration_days = int(params.get('duration_days') or 1)
    custom_km = params.get('custom_km') or None
    pax_count = int(params.get('pax_count') or 1)
    gst_rate_str = params.get('gst_rate', '5').replace('%', '')

    try:
        gst_rate = Decimal(gst_rate_str)
    except Exception:
        gst_rate = Decimal('5.00')

    include_hill = params.get('include_hill_surcharge')
    include_permit = params.get('include_interstate_permit')

    quote = compute_single_vehicle_quote(
        origin=origin,
        destination=destination,
        vehicle_type_id=int(vehicle_type_id) if vehicle_type_id else None,
        trip_type=trip_type,
        duration_days=duration_days,
        custom_km=int(custom_km) if custom_km else None,
        pax_count=pax_count,
        gst_rate=gst_rate,
        include_hill_surcharge=True if include_hill == 'on' else (False if include_hill == 'off' else None),
        include_interstate_permit=True if include_permit == 'on' else (False if include_permit == 'off' else None),
    )

    vehicle_types = VehicleType.objects.all().order_by('name')
    return render(request, 'htmx/ai_quotation_result.html', {
        'q': quote,
        'vehicle_types': vehicle_types,
    })


@login_required
@require_http_methods(["GET", "POST"])
def htmx_convoy_quotation(request):
    """
    Multi-vehicle convoy quotation generator.
    Accepts JSON-style form data for multiple vehicle types.
    """
    import json
    from operations.quotation_engine import compute_convoy_quotation
    from core.models import VehicleType

    params = request.POST if request.method == 'POST' else request.GET
    origin = params.get('origin', '').strip()
    destination = params.get('destination', '').strip()

    if not origin or not destination:
        return HttpResponse("")

    trip_type = params.get('trip_type', 'round_trip')
    duration_days = int(params.get('duration_days') or 1)
    custom_km = params.get('custom_km') or None
    gst_rate = Decimal(params.get('gst_rate', '5').replace('%', '') or '5')

    # Parse vehicle specs from form
    vehicles = []
    # Support up to 5 vehicle slots
    for i in range(1, 6):
        vt_id = params.get(f'vehicle_{i}_type')
        count = params.get(f'vehicle_{i}_count')
        pax = params.get(f'vehicle_{i}_pax')
        if vt_id and count:
            vehicles.append({
                'vehicle_type_id': int(vt_id),
                'count': int(count),
                'pax': int(pax or 0),
            })

    if not vehicles:
        return HttpResponse("<p class='text-amber-400'>Please add at least one vehicle to the convoy.</p>")

    result = compute_convoy_quotation(
        origin=origin,
        destination=destination,
        vehicles=vehicles,
        trip_type=trip_type,
        duration_days=duration_days,
        custom_km=int(custom_km) if custom_km else None,
        gst_rate=gst_rate,
    )

    vehicle_types = VehicleType.objects.all().order_by('name')
    return render(request, 'htmx/convoy_quotation_result.html', {
        'convoy': result,
        'vehicle_types': vehicle_types,
    })
