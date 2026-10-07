import random
import secrets
from decimal import Decimal
from django.db import models
from django.utils import timezone
from core.models import Vehicle, Driver
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


# ==============================================================================
# Helper generators for OTP and Pass Tokens
# ==============================================================================
def generate_4digit_otp():
    return f"{random.randint(1000, 9999)}"


def generate_pass_token():
    return secrets.token_urlsafe(24)


# ==============================================================================
# Phase 1, 2 & 4: Commuter Boarding Pass & IVR Safety Tracking
# ==============================================================================
class CommuterBoardingPass(models.Model):
    IVR_STATUSES = [
        ('pending', '⏳ Pending Drop'),
        ('initiated', '📞 IVR Call Ringing'),
        ('safe_confirmed', '✅ Safe Drop Confirmed (Key 1)'),
        ('sos_escalated', '🚨 SOS Escalated to Control Room (Key 2)'),
        ('unanswered', '⚠️ Call Unanswered / Auto-Escalated'),
    ]

    commuter = models.ForeignKey(
        BaseCommuterManifest,
        on_delete=models.CASCADE,
        related_name='boarding_passes'
    )
    trip_log = models.ForeignKey(
        BaseContractTripLog,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='commuter_passes'
    )
    trip = models.ForeignKey(
        'operations.Trip',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='commute_passes'
    )
    date = models.DateField(default=timezone.now, db_index=True)
    shift = models.ForeignKey(
        BaseShift,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='passes'
    )
    boarding_otp = models.CharField(
        max_length=6,
        default=generate_4digit_otp,
        help_text="Dynamic 4-digit verification code"
    )
    pass_token = models.CharField(
        max_length=64,
        unique=True,
        default=generate_pass_token,
        db_index=True,
        help_text="Secure unguessable URL token for Mobile Web Pass"
    )

    # Boarding verification
    is_boarded = models.BooleanField(default=False)
    boarded_at = models.DateTimeField(null=True, blank=True)
    boarded_stop = models.ForeignKey(
        BaseRouteStop,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    boarded_by_driver = models.ForeignKey(
        Driver,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    # Phase 1: Women Safety IVR & Commute Buddy
    commute_buddy = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='buddy_of',
        help_text="Designated co-passenger buddy dropping at same or subsequent stop"
    )
    is_isolated_night_drop = models.BooleanField(
        default=False,
        help_text="Flagged: Female commuter dropped last on night shift (8 PM - 6 AM)"
    )
    escort_assigned = models.BooleanField(
        default=False,
        help_text="Physical security guard escort assigned"
    )
    ivr_status = models.CharField(
        max_length=30,
        choices=IVR_STATUSES,
        default='pending'
    )
    ivr_confirmed_at = models.DateTimeField(null=True, blank=True)
    ivr_recording_notes = models.CharField(max_length=255, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Commuter Boarding Pass & Safety Record'
        verbose_name_plural = 'Commuter Boarding Passes'
        ordering = ['-date', 'commuter__name']

    def __str__(self):
        return f"{self.commuter.name} (OTP: {self.boarding_otp}) — {self.date}"


# ==============================================================================
# Phase 5: ESG Sustainability & Carbon Footprint Metric
# ==============================================================================
class ESGCarbonMetric(models.Model):
    FUEL_FACTORS = {
        'electric': Decimal('0.00'),
        'cng': Decimal('0.15'),
        'diesel': Decimal('0.26'),
        'petrol': Decimal('0.23'),
    }
    # Average private vehicle baseline emission (single occupant car/bike average: ~0.18 kg CO2/km per commuter)
    PRIVATE_COMMUTE_BASELINE_FACTOR = Decimal('0.18')

    date = models.DateField(default=timezone.now, db_index=True)
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='carbon_metrics')
    trip_log = models.ForeignKey(BaseContractTripLog, on_delete=models.SET_NULL, null=True, blank=True)
    trip_km = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    passenger_count = models.PositiveIntegerField(default=1)
    fuel_type = models.CharField(max_length=20, default='diesel')
    
    co2_emitted_kg = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    co2_saved_kg = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    green_efficiency_score = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('85.00'))

    def compute_emissions(self):
        factor = self.FUEL_FACTORS.get(self.fuel_type.lower(), Decimal('0.26'))
        self.co2_emitted_kg = round(self.trip_km * factor, 2)
        
        # Savings = (Individual commuters traveling separately) - Actual group vehicle emissions
        individual_emissions = self.trip_km * Decimal(str(self.passenger_count)) * self.PRIVATE_COMMUTE_BASELINE_FACTOR
        self.co2_saved_kg = max(Decimal('0.00'), round(individual_emissions - self.co2_emitted_kg, 2))
        
        # Green efficiency score: 0 to 100 based on passenger loading & savings
        if self.passenger_count > 10:
            self.green_efficiency_score = Decimal('95.00')
        elif self.passenger_count > 4:
            self.green_efficiency_score = Decimal('88.00')
        else:
            self.green_efficiency_score = Decimal('72.00')

    def save(self, *args, **kwargs):
        self.compute_emissions()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'ESG Carbon Footprint Metric'
        verbose_name_plural = 'ESG Carbon Metrics'
        ordering = ['-date']

    def __str__(self):
        return f"{self.vehicle.registration_number} on {self.date}: {self.co2_saved_kg} kg CO2 avoided"
