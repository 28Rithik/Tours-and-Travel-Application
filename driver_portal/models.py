from decimal import Decimal
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from core.models import Driver


class DriverPortalAccount(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='driver_portal_account')
    driver = models.OneToOneField(Driver, on_delete=models.CASCADE, related_name='portal_account')
    quick_pin = models.CharField(max_length=6, default='1234', help_text="4 or 6-digit login PIN")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_login_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Driver Portal Account"
        verbose_name_plural = "Driver Portal Accounts"

    def __str__(self):
        return f"Portal: {self.driver.name} ({self.driver.phone})"


class DriverAttendanceLog(models.Model):
    """
    Driver Duty & Shift Attendance tracking for compliance and payroll.
    Tracks clock-in, clock-out, shift window, active duty hours, and statutory rest.
    """
    SHIFT_CHOICES = [
        ('morning', 'Morning Shift (05:00 - 14:00)'),
        ('general', 'General Shift (09:00 - 18:00)'),
        ('evening', 'Evening Shift (14:00 - 23:00)'),
        ('night', 'Night Shift (22:00 - 07:00)'),
        ('outstation', 'Outstation Tour Duty'),
    ]
    STATUS_CHOICES = [
        ('on_duty', '🟢 On Duty / Active'),
        ('on_break', '☕ On Break'),
        ('off_duty', '🏁 Off Duty / Completed'),
    ]

    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, related_name='attendance_logs')
    date = models.DateField(default=timezone.now, db_index=True)
    shift_name = models.CharField(max_length=50, choices=SHIFT_CHOICES, default='general')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='on_duty')

    clock_in_time = models.DateTimeField(default=timezone.now)
    clock_out_time = models.DateTimeField(null=True, blank=True)
    clock_in_location = models.CharField(max_length=255, default='Coimbatore Central Depot Gate')
    clock_out_location = models.CharField(max_length=255, blank=True)

    odometer_start = models.IntegerField(null=True, blank=True, help_text="Starting Odometer KM")
    odometer_end = models.IntegerField(null=True, blank=True, help_text="Closing Odometer KM")

    duty_hours = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'), help_text="Total elapsed duty hours")
    rest_break_minutes = models.IntegerField(default=0)

    fatigue_rest_compliant = models.BooleanField(default=True, help_text="Compliant with statutory 8h rest interval")
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-clock_in_time']
        verbose_name = "Driver Duty & Attendance Log"
        verbose_name_plural = "Driver Duty & Attendance Logs"

    def calculate_duty_hours(self):
        end = self.clock_out_time or timezone.now()
        duration = end - self.clock_in_time
        hours = max(Decimal('0.00'), Decimal(f"{duration.total_seconds() / 3600:.2f}"))
        return hours

    def __str__(self):
        return f"{self.driver.name} - {self.date} ({self.get_status_display()})"


class RouteIssueReport(models.Model):
    """
    Real-time delay, hazard, and route issue reported by drivers during active trips.
    Notifies the Transport Control Center and updates passenger ETAs.
    """
    ISSUE_CHOICES = [
        ('traffic_jam', '🚗 Heavy Traffic / Congestion'),
        ('road_closure', '🚧 Road Closed / Detour'),
        ('waterlogging', '🌧️ Waterlogging / Heavy Rain'),
        ('mechanical_warning', '⚠️ Vehicle Warning / Slow Run'),
        ('passenger_delay', '⏱️ Passenger Late at Stop'),
        ('accident_ahead', '🚨 Accident / Gridlock Ahead'),
        ('other', 'ℹ️ Other Operational Delay'),
    ]
    STATUS_CHOICES = [
        ('reported', 'Reported to Control Room'),
        ('acknowledged', 'Acknowledged by Dispatch'),
        ('resolved', 'Resolved / Route Cleared'),
    ]

    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, related_name='route_issues')
    trip = models.ForeignKey('operations.Trip', on_delete=models.SET_NULL, null=True, blank=True, related_name='route_issues')
    contract_trip_log = models.ForeignKey('fleet_contracts.ContractTripLog', on_delete=models.SET_NULL, null=True, blank=True, related_name='route_issues')

    issue_type = models.CharField(max_length=40, choices=ISSUE_CHOICES, default='traffic_jam')
    delay_minutes = models.IntegerField(default=15, help_text="Estimated delay in minutes")
    current_location = models.CharField(max_length=255, default='Highway Corridor')
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='reported')

    reported_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-reported_at']
        verbose_name = "Route Delay & Incident Report"
        verbose_name_plural = "Route Delay & Incident Reports"

    def __str__(self):
        return f"Issue #{self.pk}: {self.get_issue_type_display()} (+{self.delay_minutes}m) by {self.driver.name}"
