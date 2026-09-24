from django.shortcuts import render

from django.http import JsonResponse
from .models import VehicleType

def api_get_vehicle_types(request):
    rates = {
        str(vt.id): {
            'default_day_rate': str(vt.default_day_rate),
            'default_km_rate': str(vt.default_km_rate)
        }
        for vt in VehicleType.objects.all()
    }
    return JsonResponse(rates)
