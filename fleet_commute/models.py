from django.db import models
from fleet_contracts.models import (
    Route as BaseRoute,
    RouteStop as BaseRouteStop,
    Shift as BaseShift,
    CommuterManifest as BaseCommuterManifest,
    ContractTripLog as BaseContractTripLog,
    NightSafetyEscortLog as BaseNightSafetyEscortLog,
)


class CommuteRoute(BaseRoute):
    class Meta:
        proxy = True
        app_label = 'fleet_commute'
        verbose_name = 'Commute Route'
        verbose_name_plural = 'Routes & Waypoints'


class RouteStop(BaseRouteStop):
    class Meta:
        proxy = True
        app_label = 'fleet_commute'
        verbose_name = 'Route Stop / Pickup Node'
        verbose_name_plural = 'Route Stops & Nodes'


class CommuteShift(BaseShift):
    class Meta:
        proxy = True
        app_label = 'fleet_commute'
        verbose_name = 'Shift & Timetable'
        verbose_name_plural = 'Shifts & Timetables'


class CommuterManifestProxy(BaseCommuterManifest):
    class Meta:
        proxy = True
        app_label = 'fleet_commute'
        verbose_name = 'Commuter & Student Passenger'
        verbose_name_plural = 'Commuter & Student Manifest'


class DailyTripLog(BaseContractTripLog):
    class Meta:
        proxy = True
        app_label = 'fleet_commute'
        verbose_name = 'Daily Trip Execution Log'
        verbose_name_plural = 'Daily Trip Logs'


class NightSafetyEscort(BaseNightSafetyEscortLog):
    class Meta:
        proxy = True
        app_label = 'fleet_commute'
        verbose_name = 'Night Safety & Escort Guard Log'
        verbose_name_plural = 'Night Safety & Escort Logs'
