from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.db import models
import datetime

from .models import VehicleCategory, VehicleType, Vehicle


def api_get_vehicle_types(request):
    from .cache_services import get_cached_vehicle_types
    rates = {
        str(vt.id): {
            'default_day_rate': str(vt.default_day_rate),
            'default_km_rate': str(vt.default_km_rate)
        }
        for vt in get_cached_vehicle_types()
    }
    return JsonResponse(rates)


def api_vehicle_check_availability(request, reg_no):
    """
    Fleet Tour Conflict Check API for Intercity Bus CRS.
    Endpoint: GET /api/vehicles/<reg_no>/check-availability/?date=YYYY-MM-DD
    Returns:
      Available:  {"available": True, "conflict": False, "status": "clear"}
      Conflicted: {"available": False, "conflict": True, "reason": "Booked for 3-Day Ooty Tour"}
    """
    clean_reg = reg_no.replace(' ', '').replace('-', '').upper()
    date_str = request.GET.get('date', '').strip()

    check_date = None
    if date_str:
        try:
            check_date = datetime.date.fromisoformat(date_str)
        except (ValueError, TypeError):
            check_date = None

    # Fast indexed lookup for vehicle (exact or clean registration)
    target_vehicle = (
        Vehicle.objects.filter(models.Q(registration_number__iexact=reg_no) | models.Q(registration_number__iexact=clean_reg))
        .first()
    )
    if not target_vehicle:
        for v in Vehicle.objects.only('id', 'registration_number', 'status'):
            if v.registration_number.replace(' ', '').replace('-', '').upper() == clean_reg:
                target_vehicle = v
                break

    if not target_vehicle:
        return JsonResponse({
            'available': True,
            'conflict': False,
            'registration_number': clean_reg,
            'date': date_str,
            'status': 'not_found',
            'message': f'Vehicle {reg_no} not registered in TravelERP master fleet. Free for intercity scheduled dispatch.'
        })

    # 1. Maintenance Check
    if target_vehicle.status in ['maintenance', 'inactive']:
        return JsonResponse({
            'available': False,
            'conflict': True,
            'registration_number': target_vehicle.registration_number,
            'date': date_str,
            'status': 'maintenance',
            'reason': f'Vehicle {target_vehicle.registration_number} is currently in TravelERP workshop ({target_vehicle.get_status_display()}).'
        })

    # 2. Tour & Trip Conflict Check
    from operations.models import Trip
    trips_qs = Trip.objects.filter(
        vehicle=target_vehicle,
        status__in=['assigned', 'driver_confirmed', 'started', 'completed']
    )

    if check_date:
        trips_qs = trips_qs.filter(
            models.Q(start_date__lte=check_date, end_date__gte=check_date) |
            models.Q(start_date=check_date)
        )

    if trips_qs.exists():
        trip = trips_qs.order_by('-start_date').first()
        dest = trip.booking.destination if (trip.booking and trip.booking.destination) else "Outstation Tour"
        pkg_title = f" ({trip.package.name})" if trip.package else ""
        return JsonResponse({
            'available': False,
            'conflict': True,
            'registration_number': target_vehicle.registration_number,
            'date': date_str,
            'trip_id': trip.trip_id or trip.id,
            'destination': dest,
            'status': 'booked_for_tour',
            'reason': f'Vehicle is reserved for TravelERP Tour #{trip.trip_id or trip.id}: {dest}{pkg_title}'
        })

    return JsonResponse({
        'available': True,
        'conflict': False,
        'registration_number': target_vehicle.registration_number,
        'date': date_str,
        'status': 'clear',
        'vehicle_type': str(target_vehicle.vehicle_type) if target_vehicle.vehicle_type else 'Coach',
        'message': 'Vehicle is free for intercity scheduled dispatch.'
    })


from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import redirect
from django.db.models import Q, Count
from core.models import Driver, Party
from core.depot_scoping import (
    get_user_depot_scope, get_scoped_vehicles, get_scoped_drivers, DEPOT_CHOICES
)


@login_required
def fleet_vehicles_roster_view(request):
    """
    Staff Portal: Dedicated Fleet Assets & Vehicles Management Studio.
    Enables Fleet Operations Leads and Workshop Managers to monitor, filter,
    toggle live availability, and add new fleet vehicles directly in the staff portal.
    """
    depot_param = request.GET.get('depot')
    depot_scope = get_user_depot_scope(request.user, depot_param)
    status_filter = request.GET.get('status', 'all')
    search_query = request.GET.get('q', '').strip()

    # Handle Add or Edit Vehicle Form Submission
    if request.method == 'POST' and request.POST.get('action') in ('add_vehicle', 'edit_vehicle'):
        is_edit = request.POST.get('action') == 'edit_vehicle'
        vehicle_id = request.POST.get('vehicle_id')
        reg_no = request.POST.get('registration_number', '').strip().upper()
        brand = request.POST.get('brand', '').strip()
        model = request.POST.get('model', '').strip()
        v_type_id = request.POST.get('vehicle_type')
        capacity = int(request.POST.get('seating_capacity') or 7)
        depot = request.POST.get('base_depot') or (depot_scope['effective_depot'] or 'Coimbatore Hub')
        ownership = request.POST.get('ownership_type', 'owned')
        fuel = request.POST.get('fuel_type', 'diesel')
        current_km = int(request.POST.get('current_km') or 0)
        driver_id = request.POST.get('default_driver')

        # Additional RTO Compliance & Mechanical Specs
        rc_exp = request.POST.get('rc_expiry') or None
        fc_exp = request.POST.get('fc_expiry') or None
        ins_exp = request.POST.get('insurance_expiry') or None
        permit_exp = request.POST.get('permit_expiry') or None
        puc_exp = request.POST.get('pollution_expiry') or None
        fastag = request.POST.get('fastag_id', '').strip()
        gps = request.POST.get('gps_imei', '').strip()
        ins_prov = request.POST.get('insurance_provider', '').strip()
        ins_pol = request.POST.get('insurance_policy_number', '').strip()
        eng_no = request.POST.get('engine_number', '').strip()
        chas_no = request.POST.get('chassis_number', '').strip()
        has_ac = 'has_ac' in request.POST
        has_susp = 'has_air_suspension' in request.POST
        is_sleeper = 'is_sleeper' in request.POST
        fuel_tank = int(request.POST.get('fuel_tank_capacity')) if request.POST.get('fuel_tank_capacity') else None
        def_cap = int(request.POST.get('def_capacity')) if request.POST.get('def_capacity') else None
        next_srv = int(request.POST.get('next_service_due_km')) if request.POST.get('next_service_due_km') else None

        if not reg_no or not brand:
            messages.error(request, "Registration number and brand are required.")
        elif not is_edit and Vehicle.objects.filter(registration_number__iexact=reg_no).exists():
            messages.error(request, f"Vehicle with registration {reg_no} already exists.")
        else:
            try:
                vt = VehicleType.objects.get(pk=v_type_id) if v_type_id else None
                drv = Driver.objects.get(pk=driver_id) if driver_id else None

                if is_edit:
                    v = get_object_or_404(Vehicle, pk=vehicle_id)
                    v.registration_number = reg_no
                    v.brand = brand
                    v.model = model
                    v.vehicle_type = vt
                    v.seating_capacity = capacity
                    v.base_depot = depot
                    v.ownership_type = ownership
                    v.fuel_type = fuel
                    v.current_km = current_km
                    v.default_driver = drv
                    v.rc_expiry = rc_exp
                    v.fc_expiry = fc_exp
                    v.insurance_expiry = ins_exp
                    v.permit_expiry = permit_exp
                    v.pollution_expiry = puc_exp
                    v.fastag_id = fastag
                    v.gps_imei = gps
                    v.insurance_provider = ins_prov
                    v.insurance_policy_number = ins_pol
                    v.engine_number = eng_no
                    v.chassis_number = chas_no
                    v.has_ac = has_ac
                    v.has_air_suspension = has_susp
                    v.is_sleeper = is_sleeper
                    v.fuel_tank_capacity = fuel_tank
                    v.def_capacity = def_cap
                    v.next_service_due_km = next_srv
                    v.save()
                    messages.success(request, f"✅ Vehicle {v.registration_number} specifications updated successfully!")
                else:
                    new_v = Vehicle.objects.create(
                        registration_number=reg_no,
                        brand=brand,
                        model=model,
                        vehicle_type=vt,
                        seating_capacity=capacity,
                        base_depot=depot,
                        ownership_type=ownership,
                        fuel_type=fuel,
                        current_km=current_km,
                        default_driver=drv,
                        status='available',
                        current_location=f"{depot} Operational Yard",
                        rc_expiry=rc_exp,
                        fc_expiry=fc_exp,
                        insurance_expiry=ins_exp,
                        permit_expiry=permit_exp,
                        pollution_expiry=puc_exp,
                        fastag_id=fastag,
                        gps_imei=gps,
                        insurance_provider=ins_prov,
                        insurance_policy_number=ins_pol,
                        engine_number=eng_no,
                        chassis_number=chas_no,
                        has_ac=has_ac,
                        has_air_suspension=has_susp,
                        is_sleeper=is_sleeper,
                        fuel_tank_capacity=fuel_tank,
                        def_capacity=def_cap,
                        next_service_due_km=next_srv,
                    )
                    messages.success(request, f"✅ Vehicle {new_v.registration_number} ({new_v.brand} {new_v.model}) successfully registered into {depot} fleet!")
                return redirect('fleet-vehicles-roster')
            except Exception as e:
                messages.error(request, f"Error saving vehicle: {str(e)}")

    vehicles_qs = get_scoped_vehicles(request.user, depot_param).select_related('vehicle_type', 'default_driver', 'owner_party').order_by('registration_number')

    if search_query:
        vehicles_qs = vehicles_qs.filter(
            Q(registration_number__icontains=search_query) |
            Q(brand__icontains=search_query) |
            Q(model__icontains=search_query) |
            Q(default_driver__name__icontains=search_query) |
            Q(current_location__icontains=search_query)
        )

    # Status counts
    counts = {
        'total': vehicles_qs.count(),
        'available': vehicles_qs.filter(status='available').count(),
        'on_trip': vehicles_qs.filter(status='on_trip').count(),
        'maintenance': vehicles_qs.filter(status__in=['maintenance', 'in_shop', 'breakdown']).count(),
        'inactive': vehicles_qs.filter(status='inactive').count(),
    }

    if status_filter == 'available':
        vehicles_qs = vehicles_qs.filter(status='available')
    elif status_filter == 'on_trip':
        vehicles_qs = vehicles_qs.filter(status='on_trip')
    elif status_filter == 'maintenance':
        vehicles_qs = vehicles_qs.filter(status__in=['maintenance', 'in_shop', 'breakdown'])
    elif status_filter == 'inactive':
        vehicles_qs = vehicles_qs.filter(status='inactive')

    all_vehicle_types = VehicleType.objects.all()
    all_drivers = Driver.objects.filter(status='active').order_by('name')

    from .pagination import paginate_queryset
    vehicles_page = paginate_queryset(vehicles_qs, request, default_page_size=25, max_page_size=100)

    return render(request, 'core/vehicle_roster.html', {
        'vehicles': vehicles_page.records,
        'vehicles_page': vehicles_page,
        'counts': counts,
        'current_status': status_filter,
        'search_query': search_query,
        'depot_scope': depot_scope,
        'current_depot': depot_scope['effective_depot'],
        'can_change_depot': depot_scope['can_change_depot'],
        'depot_choices': DEPOT_CHOICES,
        'vehicle_types': all_vehicle_types,
        'drivers': all_drivers,
    })


@login_required
def fleet_drivers_roster_view(request):
    """
    Staff Portal: Dedicated Chauffeurs & Drivers Directory.
    Enables fleet dispatchers and workshop managers to inspect drivers, check license expiries,
    view assigned vehicles, and register new chauffeurs directly in the staff portal.
    """
    depot_param = request.GET.get('depot')
    depot_scope = get_user_depot_scope(request.user, depot_param)
    search_query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', 'all')

    # Handle Register Driver Form Submission
    if request.method == 'POST' and request.POST.get('action') == 'add_driver':
        name = request.POST.get('name', '').strip()
        phone = request.POST.get('phone', '').strip()
        license_no = request.POST.get('license_number', '').strip().upper()
        license_expiry = request.POST.get('license_expiry') or None
        depot = request.POST.get('base_depot') or (depot_scope['effective_depot'] or 'Coimbatore Hub')

        if not name or not phone:
            messages.error(request, "Driver name and phone number are required.")
        else:
            try:
                new_d = Driver.objects.create(
                    name=name,
                    phone=phone,
                    license_number=license_no or f"DL-{depot[:3].upper()}-{phone[-4:]}",
                    license_validity_tr=license_expiry,
                    base_depot=depot,
                    status='active',
                )
                messages.success(request, f"✅ Chauffeur {new_d.name} successfully registered at {depot}!")
                return redirect('fleet-drivers-roster')
            except Exception as e:
                messages.error(request, f"Error registering chauffeur: {str(e)}")

    drivers_qs = get_scoped_drivers(request.user, depot_param).prefetch_related('default_vehicles').order_by('name')

    if search_query:
        drivers_qs = drivers_qs.filter(
            Q(name__icontains=search_query) |
            Q(phone__icontains=search_query) |
            Q(license_number__icontains=search_query) |
            Q(base_depot__icontains=search_query)
        )

    counts = {
        'total': drivers_qs.count(),
        'active': drivers_qs.filter(status='active').count(),
        'inactive': drivers_qs.filter(status='inactive').count(),
    }

    if status_filter == 'active':
        drivers_qs = drivers_qs.filter(status='active')
    elif status_filter == 'inactive':
        drivers_qs = drivers_qs.filter(status='inactive')

    from .pagination import paginate_queryset
    drivers_page = paginate_queryset(drivers_qs, request, default_page_size=25, max_page_size=100)

    return render(request, 'core/driver_roster.html', {
        'drivers': drivers_page.records,
        'drivers_page': drivers_page,
        'counts': counts,
        'current_status': status_filter,
        'search_query': search_query,
        'depot_scope': depot_scope,
        'current_depot': depot_scope['effective_depot'],
        'can_change_depot': depot_scope['can_change_depot'],
        'depot_choices': DEPOT_CHOICES,
    })


@login_required
def api_toggle_vehicle_status_staff(request, vehicle_id):
    """
    1-Click Staff Availability Toggle for fleet dispatchers and workshop managers.
    Toggles between 'available' and 'maintenance' / 'inactive'.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)

    vehicle = get_object_or_404(Vehicle, pk=vehicle_id)

    # Check active trip
    today = datetime.date.today()
    active_trip = vehicle.trips.filter(
        status__in=['started', 'assigned', 'driver_confirmed'],
        start_date__lte=today,
        end_date__gte=today
    ).first()

    if active_trip:
        return JsonResponse({
            'status': 'error',
            'message': f"Cannot toggle: Vehicle is deployed on active Trip #{active_trip.trip_id}."
        }, status=400)

    if vehicle.status == 'available':
        vehicle.status = 'maintenance'
        new_label = '🟠 In Maintenance'
    else:
        vehicle.status = 'available'
        new_label = '🟢 Available Ready'

    vehicle.save(update_fields=['status'])
    return JsonResponse({
        'status': 'success',
        'new_status': vehicle.status,
        'label': new_label,
        'registration_number': vehicle.registration_number
    })


@login_required
def fleet_categories_view(request):
    """
    Staff Portal: Enterprise Vehicle Categories Master.
    Enables Fleet Leads and Commercial Directors to manage vehicle classifications,
    seating tier spans, and showcase branding directly in the staff portal.
    """
    from django.utils.text import slugify

    search_query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', 'all')

    # Handle Category Create/Edit
    if request.method == 'POST':
        action = request.POST.get('action')
        if action in ('add_category', 'edit_category'):
            name = request.POST.get('name', '').strip()
            code = request.POST.get('code', '').strip() or slugify(name)
            desc = request.POST.get('description', '').strip()
            icon = request.POST.get('icon', 'directions_car').strip()
            color = request.POST.get('badge_color', '#0284c7').strip()
            seats = request.POST.get('seating_range', '').strip()
            order = int(request.POST.get('display_order') or 1)
            is_active = 'is_active' in request.POST

            if not name:
                messages.error(request, "Category name is required.")
            else:
                try:
                    if action == 'edit_category':
                        cat_id = request.POST.get('category_id')
                        cat = get_object_or_404(VehicleCategory, pk=cat_id)
                        cat.name = name
                        cat.code = code
                        cat.description = desc
                        cat.icon = icon
                        cat.badge_color = color
                        cat.seating_range = seats
                        cat.display_order = order
                        cat.is_active = is_active
                        cat.save()
                        messages.success(request, f"✅ Category '{cat.name}' updated successfully.")
                    else:
                        cat = VehicleCategory.objects.create(
                            name=name, code=code, description=desc,
                            icon=icon, badge_color=color, seating_range=seats,
                            display_order=order, is_active=is_active
                        )
                        messages.success(request, f"✅ Category '{cat.name}' created successfully.")
                    return redirect('fleet-categories')
                except Exception as e:
                    messages.error(request, f"Error saving category: {str(e)}")

        elif action == 'toggle_category':
            cat_id = request.POST.get('category_id')
            cat = get_object_or_404(VehicleCategory, pk=cat_id)
            cat.is_active = not cat.is_active
            cat.save(update_fields=['is_active'])
            messages.success(request, f"Status for '{cat.name}' updated to {'Active' if cat.is_active else 'Inactive'}.")
            return redirect('fleet-categories')

    categories_qs = VehicleCategory.objects.annotate(
        type_count=Count('vehicle_types', distinct=True),
        vehicle_count=Count('vehicles', distinct=True)
    ).order_by('display_order', 'name')

    if search_query:
        categories_qs = categories_qs.filter(
            Q(name__icontains=search_query) |
            Q(code__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(seating_range__icontains=search_query)
        )

    if status_filter == 'active':
        categories_qs = categories_qs.filter(is_active=True)
    elif status_filter == 'inactive':
        categories_qs = categories_qs.filter(is_active=False)

    counts = {
        'total': VehicleCategory.objects.count(),
        'active': VehicleCategory.objects.filter(is_active=True).count(),
        'inactive': VehicleCategory.objects.filter(is_active=False).count(),
        'total_types': VehicleType.objects.count(),
        'total_vehicles': Vehicle.objects.count(),
    }

    return render(request, 'core/vehicle_categories.html', {
        'categories': categories_qs,
        'counts': counts,
        'search_query': search_query,
        'status_filter': status_filter,
    })


@login_required
def fleet_types_view(request):
    """
    Staff Portal: Enterprise Vehicle Types & Standard Tariffs Master.
    Enables Fleet Operations, Commercial Quoting, and Dispatch to inspect vehicle models,
    default day/km rates, minimum KM thresholds, driver batas, and seating capacities.
    """
    search_query = request.GET.get('q', '').strip()
    cat_filter = request.GET.get('category', 'all')
    fuel_filter = request.GET.get('fuel', 'all')

    # Handle Add/Edit Vehicle Type
    if request.method == 'POST':
        action = request.POST.get('action')
        if action in ('add_type', 'edit_type'):
            name = request.POST.get('name', '').strip()
            cat_id = request.POST.get('vehicle_category')
            desc = request.POST.get('description', '').strip()
            day_rate = float(request.POST.get('default_day_rate') or 0)
            km_rate = float(request.POST.get('default_km_rate') or 0)
            min_km = int(request.POST.get('minimum_km_per_day') or 250)
            extra_km = float(request.POST.get('extra_km_rate') or 0)
            extra_hr = float(request.POST.get('extra_hour_rate') or 0)
            driver_bata = float(request.POST.get('driver_bata') or 0)
            night_halt = float(request.POST.get('night_halt_charge') or 0)
            seats = int(request.POST.get('seating_capacity') or 4)
            luggage = request.POST.get('luggage_capacity', '').strip()
            fuel = request.POST.get('fuel_type', 'diesel')
            mileage = float(request.POST.get('expected_mileage_kmpl') or 0) or None
            toll = request.POST.get('toll_class', 'car')
            has_ac = 'has_ac' in request.POST
            is_lux = 'is_luxury' in request.POST
            trans = request.POST.get('transmission_type', 'manual')

            if not name:
                messages.error(request, "Vehicle Type name is required.")
            else:
                try:
                    cat = VehicleCategory.objects.get(pk=cat_id) if cat_id else None
                    if action == 'edit_type':
                        type_id = request.POST.get('type_id')
                        vt = get_object_or_404(VehicleType, pk=type_id)
                        vt.name = name
                        vt.vehicle_category = cat
                        vt.description = desc
                        vt.default_day_rate = day_rate
                        vt.default_km_rate = km_rate
                        vt.minimum_km_per_day = min_km
                        vt.extra_km_rate = extra_km
                        vt.extra_hour_rate = extra_hr
                        vt.driver_bata = driver_bata
                        vt.night_halt_charge = night_halt
                        vt.seating_capacity = seats
                        vt.luggage_capacity = luggage
                        vt.fuel_type = fuel
                        vt.expected_mileage_kmpl = mileage
                        vt.toll_class = toll
                        vt.has_ac = has_ac
                        vt.is_luxury = is_lux
                        vt.transmission_type = trans
                        vt.save()
                        messages.success(request, f"✅ Vehicle Type '{vt.name}' updated successfully.")
                    else:
                        vt = VehicleType.objects.create(
                            name=name, vehicle_category=cat, description=desc,
                            default_day_rate=day_rate, default_km_rate=km_rate,
                            minimum_km_per_day=min_km, extra_km_rate=extra_km,
                            extra_hour_rate=extra_hr, driver_bata=driver_bata,
                            night_halt_charge=night_halt, seating_capacity=seats,
                            luggage_capacity=luggage, fuel_type=fuel,
                            expected_mileage_kmpl=mileage, toll_class=toll,
                            has_ac=has_ac, is_luxury=is_lux, transmission_type=trans
                        )
                        messages.success(request, f"✅ Vehicle Type '{vt.name}' created successfully.")
                    return redirect('fleet-types')
                except Exception as e:
                    messages.error(request, f"Error saving vehicle type: {str(e)}")

    types_qs = VehicleType.objects.select_related('vehicle_category').annotate(
        vehicle_count=Count('vehicle', distinct=True)
    ).order_by('vehicle_category__display_order', 'name')

    if search_query:
        types_qs = types_qs.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(vehicle_category__name__icontains=search_query)
        )

    if cat_filter != 'all':
        types_qs = types_qs.filter(vehicle_category__id=cat_filter)

    if fuel_filter != 'all':
        types_qs = types_qs.filter(fuel_type=fuel_filter)

    all_categories = VehicleCategory.objects.filter(is_active=True).order_by('display_order', 'name')

    counts = {
        'total': VehicleType.objects.count(),
        'ac_count': VehicleType.objects.filter(has_ac=True).count(),
        'luxury_count': VehicleType.objects.filter(is_luxury=True).count(),
        'total_vehicles': Vehicle.objects.count(),
    }

    return render(request, 'core/vehicle_types.html', {
        'types': types_qs,
        'categories': all_categories,
        'counts': counts,
        'search_query': search_query,
        'cat_filter': cat_filter,
        'fuel_filter': fuel_filter,
        'fuel_choices': VehicleType.FUEL_TYPES,
        'toll_choices': VehicleType.TOLL_CLASSES,
        'trans_choices': VehicleType.TRANSMISSION_TYPES,
    })


@login_required
def rate_cards_studio_view(request):
    """
    Staff Portal: Client Rate Cards & B2B Tariffs Studio.
    Renders inside base.html with sidebar intact.
    Provides filtering by client/party, vehicle type, search, and rate card details.
    """
    from core.models import RateCard, Party, VehicleType, Vehicle
    from django.db.models import Q

    search_query = request.GET.get('q', '').strip()
    party_id = request.GET.get('party_id', '')
    vehicle_type_id = request.GET.get('vehicle_type_id', '')

    cards_qs = RateCard.objects.select_related('party', 'vehicle_type', 'vehicle').order_by('-id')

    if search_query:
        cards_qs = cards_qs.filter(
            Q(party__name__icontains=search_query) |
            Q(vehicle_type__name__icontains=search_query) |
            Q(vehicle__registration_number__icontains=search_query)
        )

    if party_id:
        cards_qs = cards_qs.filter(party_id=party_id)

    if vehicle_type_id:
        cards_qs = cards_qs.filter(vehicle_type_id=vehicle_type_id)

    parties = Party.objects.filter(is_active=True).order_by('name')
    vehicle_types = VehicleType.objects.all().order_by('name')
    vehicles = Vehicle.objects.exclude(status='inactive').order_by('registration_number')

    counts = {
        'total_cards': RateCard.objects.count(),
        'parties_with_cards': RateCard.objects.values('party').distinct().count(),
        'vehicle_types_covered': RateCard.objects.values('vehicle_type').distinct().count(),
    }

    return render(request, 'core/rate_cards_studio.html', {
        'rate_cards': cards_qs,
        'parties': parties,
        'vehicle_types': vehicle_types,
        'vehicles': vehicles,
        'counts': counts,
        'search_query': search_query,
        'selected_party_id': party_id,
        'selected_vt_id': vehicle_type_id,
    })






# ==============================================================================
# DOMAIN 4: VEHICLE OPERATIONS (REGISTRY, ALLOCATION, HEALTH & ODOMETER LEDGER)
# ==============================================================================

def compute_vehicle_health(vehicle):
    """
    Computes dynamic Health Score (0-100%) and Dispatch Clearance Gate for an asset.
    """
    today = datetime.date.today()
    score = 100
    lock_reasons = []

    def get_doc_info(exp_date, weight, name):
        nonlocal score
        if not exp_date:
            return {'expiry': None, 'days_left': None, 'status': 'missing'}
        days = (exp_date - today).days
        if days < 0:
            score -= weight
            lock_reasons.append(f"{name} expired {abs(days)} day(s) ago ({exp_date})")
            return {'expiry': exp_date, 'days_left': days, 'status': 'expired'}
        elif days <= 30:
            score -= int(weight * 0.3)
            return {'expiry': exp_date, 'days_left': days, 'status': 'expiring'}
        return {'expiry': exp_date, 'days_left': days, 'status': 'valid'}

    docs_status = {
        'fc': get_doc_info(vehicle.fc_expiry, 35, "RTO Fitness Certificate (FC)"),
        'insurance': get_doc_info(vehicle.insurance_expiry, 30, "Commercial Insurance"),
        'puc': get_doc_info(vehicle.pollution_expiry, 10, "PUC Emission Certificate"),
        'permit': get_doc_info(vehicle.permit_expiry, 20, "Commercial Tourist Permit"),
        'tax': get_doc_info(vehicle.tax_expiry, 15, "Motor Vehicle Road Tax"),
    }

    # PM Service Milestone
    curr_km = vehicle.current_km or 0
    next_due = vehicle.next_service_due_km or 0
    km_left = next_due - curr_km if next_due else None

    pm_status = {'current_km': curr_km, 'next_due_km': next_due, 'km_left': km_left, 'status': 'ok'}
    if km_left is not None:
        if km_left <= 0:
            score -= 25
            lock_reasons.append(f"PM Service Milestone overdue by {abs(km_left):,} KM")
            pm_status['status'] = 'overdue'
        elif km_left <= 1000:
            score -= 10
            pm_status['status'] = 'approaching'

    # Open Snags & Defect Tickets
    from maintenance.models import DefectTicket
    open_defects = DefectTicket.objects.filter(vehicle=vehicle, status__in=['reported', 'open', 'in_progress'])
    defect_count = open_defects.count()
    if defect_count > 0:
        score -= min(50, 20 * defect_count)
        lock_reasons.append(f"{defect_count} active defect snag(s) reported")

    score = max(0, min(100, score))
    is_cleared = (score >= 70) and (len(lock_reasons) == 0) and (vehicle.status != 'maintenance')

    return {
        'score': score,
        'is_cleared': is_cleared,
        'clearance_label': 'CLEARED FOR DISPATCH' if is_cleared else 'DISPATCH LOCKED',
        'lock_reasons': lock_reasons,
        'tier': 'excellent' if score >= 90 else ('fair' if score >= 70 else 'critical'),
        'docs_status': docs_status,
        'pm_status': pm_status,
        'open_defects_count': defect_count,
    }


@login_required
def vehicle_detail_360_view(request, vehicle_id):
    """
    Asset 360 View: Complete digital dossier for a fleet vehicle including
    mechanical specs, dynamic health score, statutory wallet, chauffeur assignment,
    recent commute shift runs, outstation tours, and maintenance defect history.
    """
    from maintenance.models import DefectTicket
    from fleet_contracts.models import ContractTripLog
    from operations.models import Trip
    from core.models import InterDepotTransferLog

    vehicle = get_object_or_404(Vehicle.objects.select_related('vehicle_type', 'default_driver', 'owner_party'), id=vehicle_id)
    health = compute_vehicle_health(vehicle)

    # Recent Commute Shift Assignments
    commute_runs = ContractTripLog.objects.filter(
        vehicle=vehicle
    ).select_related('shift__route', 'driver').order_by('-date', '-id')[:8]

    # Recent Outstation Tours
    tour_trips = Trip.objects.filter(
        vehicle=vehicle
    ).select_related('driver', 'booking').order_by('-start_date', '-id')[:8]

    # Defect Snags & Repairs
    defects = DefectTicket.objects.filter(
        vehicle=vehicle
    ).select_related('reported_by').order_by('-date_reported')[:8]

    # Inter-Depot Relocations
    transfers = InterDepotTransferLog.objects.filter(
        vehicle=vehicle
    ).select_related('requested_by', 'transfer_driver').order_by('-created_at')[:5]

    return render(request, 'core/vehicle_detail_360.html', {
        'vehicle': vehicle,
        'health': health,
        'commute_runs': commute_runs,
        'tour_trips': tour_trips,
        'defects': defects,
        'transfers': transfers,
        'depot_choices': DEPOT_CHOICES,
    })


@login_required
def fleet_allocation_studio_view(request):
    """
    Fleet Allocation Studio: Visual multi-vertical resource board tracking
    corporate commute contracts, outstation tourism packages, depot standby reserves,
    and workshop grounding across 2,200+ fleet assets.
    """
    from fleet_contracts.models import ContractTripLog
    from operations.models import Trip
    from core.depot_scoping import get_user_depot_scope, get_scoped_vehicles

    depot_param = request.GET.get('depot')
    depot_scope = get_user_depot_scope(request.user, depot_param)
    today = datetime.date.today()

    scoped_vehicles = get_scoped_vehicles(request.user, depot_param).select_related('vehicle_type', 'default_driver')
    scoped_vids = set(scoped_vehicles.values_list('id', flat=True))

    # Active Commute Shifts
    active_commutes = ContractTripLog.objects.filter(
        date=today,
        vehicle_id__in=scoped_vids
    ).select_related('shift__route', 'vehicle', 'driver')

    # Active Outstation Tours
    active_tours = Trip.objects.filter(
        start_date__lte=today,
        end_date__gte=today,
        vehicle_id__in=scoped_vids
    ).select_related('vehicle', 'driver', 'booking')

    allocated_commute_vids = set(active_commutes.values_list('vehicle_id', flat=True))
    allocated_tour_vids = set(active_tours.values_list('vehicle_id', flat=True))

    standby_vehicles = scoped_vehicles.filter(
        status='available'
    ).exclude(id__in=allocated_commute_vids | allocated_tour_vids)

    workshop_vehicles = scoped_vehicles.filter(
        status__in=['maintenance', 'in_shop', 'breakdown']
    )

    counts = {
        'total': scoped_vehicles.count(),
        'commute': len(allocated_commute_vids),
        'tours': len(allocated_tour_vids),
        'standby': standby_vehicles.count(),
        'workshop': workshop_vehicles.count(),
    }

    return render(request, 'core/fleet_allocation_studio.html', {
        'counts': counts,
        'active_commutes': active_commutes[:40],
        'active_tours': active_tours[:40],
        'standby_vehicles': standby_vehicles[:40],
        'workshop_vehicles': workshop_vehicles[:40],
        'depot_scope': depot_scope,
        'current_depot': depot_scope['effective_depot'],
        'can_change_depot': depot_scope['can_change_depot'],
        'depot_choices': DEPOT_CHOICES,
    })


@login_required
def fleet_health_sentry_view(request):
    """
    Fleet Health & PM Sentry: Monitors real-time asset health scores,
    enforces dispatch locks for expired statutory docs, and highlights
    vehicles approaching service milestones.
    """
    from core.depot_scoping import get_user_depot_scope, get_scoped_vehicles
    from maintenance.models import DefectTicket

    depot_param = request.GET.get('depot')
    depot_scope = get_user_depot_scope(request.user, depot_param)
    tier_filter = request.GET.get('tier', 'all')
    search_q = request.GET.get('q', '').strip()

    vehicles = get_scoped_vehicles(request.user, depot_param).select_related('vehicle_type', 'default_driver')
    if search_q:
        vehicles = vehicles.filter(
            models.Q(registration_number__icontains=search_q) |
            models.Q(brand__icontains=search_q) |
            models.Q(model__icontains=search_q)
        )

    evaluated = []
    total_score = 0
    cleared_count = 0
    locked_count = 0
    upcoming_service_count = 0

    today = datetime.date.today()

    for v in vehicles[:200]:
        h = compute_vehicle_health(v)
        total_score += h['score']
        if h['is_cleared']:
            cleared_count += 1
        else:
            locked_count += 1
        if h['pm_status']['status'] in ['approaching', 'overdue']:
            upcoming_service_count += 1

        if tier_filter == 'excellent' and h['tier'] != 'excellent':
            continue
        if tier_filter == 'fair' and h['tier'] != 'fair':
            continue
        if tier_filter == 'locked' and h['is_cleared']:
            continue

        evaluated.append({
            'vehicle': v,
            'health': h,
        })

    avg_health = round(total_score / len(vehicles[:200]), 1) if vehicles[:200].exists() else 100.0

    return render(request, 'core/fleet_health_sentry.html', {
        'evaluated_vehicles': evaluated,
        'avg_health': avg_health,
        'cleared_count': cleared_count,
        'locked_count': locked_count,
        'upcoming_service_count': upcoming_service_count,
        'open_snags_count': DefectTicket.objects.filter(status__in=['reported', 'open', 'in_progress']).count(),
        'current_tier': tier_filter,
        'search_q': search_q,
        'depot_scope': depot_scope,
        'current_depot': depot_scope['effective_depot'],
        'can_change_depot': depot_scope['can_change_depot'],
    })


@login_required
def fleet_odometer_ledger_view(request):
    """
    Odometer & Dead Mileage Ledger: Trip-by-trip audit verifying opening/closing
    odometer readings, detecting rollback/spike anomalies, and computing dead mileage.
    """
    from fleet_contracts.models import ContractTripLog
    from operations.models import Trip
    from core.depot_scoping import get_user_depot_scope, get_scoped_vehicles

    depot_param = request.GET.get('depot')
    depot_scope = get_user_depot_scope(request.user, depot_param)
    scoped_vehicles = get_scoped_vehicles(request.user, depot_param)
    scoped_vids = set(scoped_vehicles.values_list('id', flat=True))

    commute_logs = ContractTripLog.objects.filter(
        vehicle_id__in=scoped_vids,
        opening_km__isnull=False,
        closing_km__isnull=False
    ).select_related('shift__route', 'vehicle', 'driver').order_by('-date', '-id')[:60]

    tour_trips = Trip.objects.filter(
        vehicle_id__in=scoped_vids,
        opening_km__isnull=False,
        closing_km__isnull=False
    ).select_related('vehicle', 'driver').order_by('-start_date', '-id')[:40]

    entries = []
    total_run_km = 0
    total_dead_km = 0
    anomaly_count = 0

    for c in commute_logs:
        run_km = max(0, c.closing_km - c.opening_km) if c.closing_km >= c.opening_km else 0
        billable_km = c.shift.route.distance_km if c.shift and c.shift.route else 18.0
        dead_km = max(0.0, float(run_km) - float(billable_km))
        dead_pct = round((dead_km / run_km) * 100, 1) if run_km > 0 else 0.0
        is_anomaly = (dead_pct > 20.0) or (run_km > 500)

        total_run_km += run_km
        total_dead_km += dead_km
        if is_anomaly:
            anomaly_count += 1

        entries.append({
            'type': 'commute',
            'id': f"COMMUTE-{c.id}",
            'date': c.date,
            'title': c.shift.route.name if c.shift and c.shift.route else "Corporate IT Shift",
            'vehicle_reg': c.vehicle.registration_number if c.vehicle else 'N/A',
            'driver_name': c.driver.name if c.driver else 'Unassigned',
            'opening_km': c.opening_km,
            'closing_km': c.closing_km,
            'run_km': run_km,
            'billable_km': billable_km,
            'dead_km': round(dead_km, 1),
            'dead_pct': dead_pct,
            'is_anomaly': is_anomaly,
        })

    for t in tour_trips:
        run_km = max(0, t.closing_km - t.opening_km) if t.closing_km >= t.opening_km else 0
        billable_km = round(run_km * 0.9, 1) if run_km > 0 else 50.0
        dead_km = max(0.0, float(run_km) - float(billable_km))
        dead_pct = round((dead_km / run_km) * 100, 1) if run_km > 0 else 0.0
        is_anomaly = (dead_pct > 20.0) or (run_km > 1200)

        total_run_km += run_km
        total_dead_km += dead_km
        if is_anomaly:
            anomaly_count += 1

        entries.append({
            'type': 'tour',
            'id': f"TOUR-{t.trip_id}",
            'date': t.start_date,
            'title': f"Tour #{t.trip_id} - {t.guest_name}",
            'vehicle_reg': t.vehicle.registration_number if t.vehicle else 'N/A',
            'driver_name': t.driver.name if t.driver else 'Unassigned',
            'opening_km': t.opening_km,
            'closing_km': t.closing_km,
            'run_km': run_km,
            'billable_km': billable_km,
            'dead_km': round(dead_km, 1),
            'dead_pct': dead_pct,
            'is_anomaly': is_anomaly,
        })

    entries.sort(key=lambda x: str(x['date']), reverse=True)
    avg_dead_pct = round((total_dead_km / total_run_km) * 100, 1) if total_run_km > 0 else 0.0

    return render(request, 'core/fleet_odometer_ledger.html', {
        'entries': entries[:60],
        'total_trips_audited': len(entries),
        'total_run_km': total_run_km,
        'total_dead_km': round(total_dead_km, 1),
        'avg_dead_pct': avg_dead_pct,
        'anomaly_count': anomaly_count,
        'depot_scope': depot_scope,
        'current_depot': depot_scope['effective_depot'],
        'can_change_depot': depot_scope['can_change_depot'],
    })


# ── Action APIs for Fleet Operations ──

@login_required
def api_log_vehicle_odometer(request, vehicle_id):
    """Logs updated odometer reading for an asset and checks PM interval."""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST method required'}, status=405)

    import json
    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST

    new_km = data.get('odometer_km')
    if new_km is None:
        return JsonResponse({'status': 'error', 'message': 'odometer_km is required'}, status=400)

    try:
        new_km = int(new_km)
    except (ValueError, TypeError):
        return JsonResponse({'status': 'error', 'message': 'Invalid odometer value'}, status=400)

    vehicle = get_object_or_404(Vehicle, id=vehicle_id)
    old_km = vehicle.current_km or 0
    if new_km < old_km:
        return JsonResponse({
            'status': 'error',
            'message': f"Odometer rollback detected! New reading ({new_km:,} KM) is less than existing reading ({old_km:,} KM)."
        }, status=400)

    vehicle.current_km = new_km
    vehicle.save(update_fields=['current_km'])

    health = compute_vehicle_health(vehicle)

    return JsonResponse({
        'status': 'success',
        'message': f"Odometer for {vehicle.registration_number} updated to {new_km:,} KM.",
        'current_km': new_km,
        'health_score': health['score'],
        'is_cleared': health['is_cleared'],
        'pm_status': health['pm_status']
    })


@login_required
def api_relocate_vehicle_depot(request, vehicle_id):
    """Authorizes an inter-depot vehicle relocation order."""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST method required'}, status=405)

    import json
    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST

    dest_depot = data.get('destination_depot')
    reason = data.get('reason', 'fleet_rebalance')
    notes = data.get('notes', '')

    if not dest_depot:
        return JsonResponse({'status': 'error', 'message': 'destination_depot is required'}, status=400)

    from core.models import InterDepotTransferLog
    vehicle = get_object_or_404(Vehicle, id=vehicle_id)
    old_depot = vehicle.base_depot

    transfer = InterDepotTransferLog.objects.create(
        vehicle=vehicle,
        origin_depot=old_depot,
        destination_depot=dest_depot,
        reason=reason,
        status='completed',
        requested_by=request.user,
        approved_by=request.user,
        odometer_at_dispatch=vehicle.current_km,
        odometer_at_receipt=vehicle.current_km,
        notes=notes
    )

    vehicle.base_depot = dest_depot
    vehicle.current_location = f"{dest_depot} Operational Yard"
    vehicle.save(update_fields=['base_depot', 'current_location'])

    return JsonResponse({
        'status': 'success',
        'message': f"Vehicle {vehicle.registration_number} successfully relocated from {old_depot} to {dest_depot} (Transfer #{transfer.transfer_id}).",
        'new_depot': dest_depot,
        'transfer_id': transfer.transfer_id
    })


@login_required
def api_toggle_vehicle_dispatch_lock(request, vehicle_id):
    """Toggles dispatch lock / maintenance hold for a vehicle."""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST method required'}, status=405)

    import json
    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST

    lock_action = data.get('action')  # 'lock' or 'unlock'
    reason = data.get('reason', 'Supervisor manual override')

    vehicle = get_object_or_404(Vehicle, id=vehicle_id)
    if lock_action == 'lock':
        vehicle.status = 'maintenance'
        vehicle.save(update_fields=['status'])
        msg = f"Vehicle {vehicle.registration_number} has been DISPATCH LOCKED and moved to maintenance status."
    else:
        vehicle.status = 'available'
        vehicle.save(update_fields=['status'])
        msg = f"Vehicle {vehicle.registration_number} has been CLEARED FOR DISPATCH (Override: {reason})."

    health = compute_vehicle_health(vehicle)

    return JsonResponse({
        'status': 'success',
        'message': msg,
        'status_code': vehicle.status,
        'is_cleared': health['is_cleared'],
        'health_score': health['score']
    })
