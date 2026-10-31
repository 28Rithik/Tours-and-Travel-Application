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




