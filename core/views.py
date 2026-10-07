from django.shortcuts import render
from django.http import JsonResponse
from django.db import models
import datetime

from .models import VehicleType, Vehicle


def api_get_vehicle_types(request):
    rates = {
        str(vt.id): {
            'default_day_rate': str(vt.default_day_rate),
            'default_km_rate': str(vt.default_km_rate)
        }
        for vt in VehicleType.objects.all()
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

    # Search for vehicle ignoring spaces and hyphens
    target_vehicle = None
    for v in Vehicle.objects.all():
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

