from decimal import Decimal
from django.db import models
from django.utils import timezone
from core.models import Client, Vehicle, Driver


# ==============================================================================
# 1. Transport Contract (Master Agreement)
# ==============================================================================

class TransportContract(models.Model):
    STATUSES = [
        ('draft', 'Draft / In Discussion'),
        ('active', 'Active & Operational'),
        ('completed', 'Completed / Expired'),
        ('cancelled', 'Terminated / Cancelled'),
    ]
    CONTRACT_CATEGORIES = [
        ('corporate', '🏢 Corporate / IT / BPO (Staff Commute)'),
        ('school', '🎒 School / College Student Transport'),
        ('factory', '🏭 Manufacturing / Factory Shift Shuttle'),
        ('hospital', '🏥 Hospital / Healthcare Staff Shuttle'),
        ('government', '🏛️ Government / PSU Official Duty'),
        ('other', '📋 Other Long-Duration Bulk Contract'),
    ]
    BILLING_MODELS = [
        ('per_trip', 'Per Trip Rate'),
        ('per_km', 'Per KM Rate'),
        ('fixed_monthly', 'Fixed Monthly Lump Sum'),
    ]
    BILLING_CYCLES = [
        ('calendar_month', 'Calendar Month (1st to Last Day)'),
        ('custom_cycle', 'Custom 30-Day Cycle'),
    ]

    contract_category = models.CharField(
        max_length=50,
        choices=CONTRACT_CATEGORIES,
        default='corporate',
        help_text="Operational vertical (Corporate ETS, School Bus, Factory Shift, etc.)"
    )
    name = models.CharField(max_length=255, help_text="e.g. Infosys Campus Shuttle 2026-27")
    customer = models.ForeignKey(
        Client,
        on_delete=models.PROTECT,
        related_name='fleet_contracts',
        help_text="Corporate/School client organization"
    )
    start_date = models.DateField()
    end_date = models.DateField()
    
    # Billing & Financial Terms
    billing_model = models.CharField(max_length=20, choices=BILLING_MODELS, default='per_trip')
    billing_cycle = models.CharField(max_length=30, choices=BILLING_CYCLES, default='calendar_month')
    default_rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Base rate for billing (per trip rate, per km rate, or monthly lumpsum)"
    )
    gst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=5.00, help_text="GST percentage (e.g. 5% or 12%)")
    payment_credit_days = models.PositiveIntegerField(default=30, help_text="Credit period in days (e.g. 30, 45, 60 days)")

    # Committed Dedicated Fleet
    committed_vehicle_count = models.PositiveIntegerField(
        default=1,
        help_text="Committed primary vehicles dedicated exclusively to this contract"
    )
    standby_vehicle_count = models.PositiveIntegerField(
        default=0,
        help_text="Guaranteed backup/spare standby vehicles for breakdown cover"
    )

    # Fuel Escalation Clause
    fuel_escalation_enabled = models.BooleanField(
        default=False,
        help_text="Check if contract includes fuel price revision clause"
    )
    base_diesel_price = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0,
        help_text="Base diesel price per liter at time of signing (e.g. ₹92.50)"
    )
    fuel_revision_factor = models.DecimalField(
        max_digits=6,
        decimal_places=4,
        default=0,
        help_text="Adjustment factor per ₹1 change in diesel (e.g. ₹0.25 per km)"
    )

    # SLA Terms
    sla_penalty_cap_pct = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=10.00,
        help_text="Maximum monthly SLA penalty deduction ceiling as % of monthly billing"
    )

    # Contact & Status
    contact_person = models.CharField(max_length=150, blank=True, help_text="Transport Desk / Admin Manager Name")
    contact_phone = models.CharField(max_length=30, blank=True, help_text="Direct phone / Emergency desk")
    status = models.CharField(max_length=20, choices=STATUSES, default='draft')
    notes = models.TextField(blank=True, help_text="Special terms, escort rules, penalty clauses")
    category_specifications = models.JSONField(
        default=dict,
        blank=True,
        help_text="Vertical-specific operational rules, compliance checklists, and SLA parameters"
    )

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.end_date and self.start_date and self.end_date < self.start_date:
            raise ValidationError('Contract end date cannot be before start date.')
            
        if self.status == 'active' and self.customer_id and self.start_date and self.end_date:
            overlapping_contracts = TransportContract.objects.filter(
                customer=self.customer,
                status='active',
                start_date__lte=self.end_date,
                end_date__gte=self.start_date
            )
            if self.pk:
                overlapping_contracts = overlapping_contracts.exclude(pk=self.pk)
                
            if overlapping_contracts.exists():
                raise ValidationError('An active contract for this customer already exists in this date range.')

    def __str__(self):
        return f"{self.name} - {self.customer.name}"


# ==============================================================================
# 2. Route & Route Stops
# ==============================================================================

class Route(models.Model):
    contract = models.ForeignKey(TransportContract, on_delete=models.CASCADE, related_name='routes')
    name = models.CharField(max_length=255, help_text="e.g. Route A: Tambaram to OMR Campus")
    origin = models.CharField(max_length=255, blank=True, help_text="Depot / Starting Point (e.g. Tambaram Bus Stand)")
    destination = models.CharField(max_length=255, blank=True, help_text="Drop Location / Campus Gate (e.g. Sholinganallur Tech Park)")
    distance_km = models.PositiveIntegerField(null=True, blank=True, help_text="One-way route distance in KMs")
    estimated_travel_minutes = models.PositiveIntegerField(null=True, blank=True, help_text="Estimated travel duration in minutes")
    rate_override = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Overrides contract default rate specifically for this route"
    )
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.contract.name} - {self.name}"


class RouteStop(models.Model):
    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name='stops')
    stop_order = models.PositiveIntegerField(default=1, help_text="Stop sequence (1, 2, 3...)")
    name = models.CharField(max_length=255, help_text="Stop Name / Pickup Point (e.g. Velachery MRTS Gate)")
    scheduled_offset_minutes = models.PositiveIntegerField(
        default=0,
        help_text="Minutes from route start time (e.g. 0 for start, 15 for stop 2)"
    )
    pickup_landmark = models.CharField(max_length=255, blank=True, help_text="Key landmark / GPS reference")
    expected_passenger_count = models.PositiveIntegerField(default=0, help_text="Expected commuters boarding here")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['route', 'stop_order']
        unique_together = ('route', 'stop_order')

    def __str__(self):
        return f"#{self.stop_order} {self.name} (+{self.scheduled_offset_minutes}m)"


# ==============================================================================
# 3. Shifts & Timetables
# ==============================================================================

class Shift(models.Model):
    DIRECTIONS = [
        ('pickup', '⬆️ Pickup (To Campus / Plant)'),
        ('drop', '⬇️ Drop (From Campus / Plant)'),
    ]
    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name='shifts')
    shift_name = models.CharField(
        max_length=100,
        blank=True,
        help_text="e.g. Shift 1 Morning, General 9 AM, Night Drop BPO"
    )
    direction = models.CharField(max_length=20, choices=DIRECTIONS)
    timing = models.TimeField(help_text="Scheduled departure/login time (e.g. 07:00 AM)")
    days_of_week = models.CharField(
        max_length=50,
        default='Mon-Fri',
        help_text="Operating days (e.g. Mon-Fri, Mon-Sat, All 7 Days)"
    )
    grace_period_minutes = models.PositiveIntegerField(
        default=10,
        help_text="Permissible delay margin before SLA penalty triggers"
    )
    escort_guard_required = models.BooleanField(
        default=False,
        help_text="Security escort guard legally mandatory (e.g. female drops 8 PM - 6 AM)"
    )

    def __str__(self):
        label = self.shift_name if self.shift_name else self.get_direction_display()
        return f"{self.route.name} - {label} @ {self.timing.strftime('%I:%M %p')}"


# ==============================================================================
# 4. Dedicated Fleet & Crew Roster (Monthly Allocation)
# ==============================================================================

class ContractFleetRoster(models.Model):
    contract = models.ForeignKey(TransportContract, on_delete=models.CASCADE, related_name='roster_allocations')
    route = models.ForeignKey(Route, on_delete=models.SET_NULL, null=True, blank=True, related_name='roster_allocations')
    shift = models.ForeignKey(Shift, on_delete=models.SET_NULL, null=True, blank=True, related_name='roster_allocations')
    primary_vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.PROTECT,
        related_name='roster_primary',
        help_text="Dedicated primary bus/cab assigned to this duty"
    )
    primary_driver = models.ForeignKey(
        Driver,
        on_delete=models.PROTECT,
        related_name='roster_primary',
        help_text="Regular driver assigned to this route"
    )
    standby_vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='roster_standby',
        help_text="Designated backup vehicle in case primary breaks down"
    )
    start_date = models.DateField(default=timezone.now)
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = 'Dedicated Fleet Roster Allocation'
        verbose_name_plural = 'Dedicated Fleet & Crew Roster'

    def clean(self):
        from django.core.exceptions import ValidationError
        errors = {}

        if self.end_date and self.end_date < self.start_date:
            errors['end_date'] = 'Roster end date cannot be earlier than start date.'

        # 1. Roster Conflict & Overlap Check
        if self.is_active and self.primary_vehicle_id:
            vehicle_conflicts = ContractFleetRoster.objects.filter(
                is_active=True,
                primary_vehicle=self.primary_vehicle
            )
            if self.pk:
                vehicle_conflicts = vehicle_conflicts.exclude(pk=self.pk)
            
            for conflict in vehicle_conflicts:
                conflict_end = conflict.end_date
                has_date_overlap = (
                    (self.end_date is None or conflict.start_date <= self.end_date) and
                    (conflict_end is None or conflict_end >= self.start_date)
                )
                if has_date_overlap:
                    if not self.shift or not conflict.shift or self.shift == conflict.shift:
                        errors['primary_vehicle'] = (
                            f"Double-Booking Conflict: Vehicle {self.primary_vehicle.registration_number} is already actively assigned "
                            f"to '{conflict.contract.name}' (Roster #{conflict.pk}) during this operating period."
                        )
                        break

        if self.is_active and self.primary_driver_id:
            driver_conflicts = ContractFleetRoster.objects.filter(
                is_active=True,
                primary_driver=self.primary_driver
            )
            if self.pk:
                driver_conflicts = driver_conflicts.exclude(pk=self.pk)

            for conflict in driver_conflicts:
                conflict_end = conflict.end_date
                has_date_overlap = (
                    (self.end_date is None or conflict.start_date <= self.end_date) and
                    (conflict_end is None or conflict_end >= self.start_date)
                )
                if has_date_overlap:
                    if not self.shift or not conflict.shift or self.shift == conflict.shift:
                        errors['primary_driver'] = (
                            f"Double-Booking Conflict: Driver {self.primary_driver.name} is already actively assigned "
                            f"to '{conflict.contract.name}' (Roster #{conflict.pk}) during this operating period."
                        )
                        break

        # 2. Pre-Flight Statutory Compliance Gate
        today = timezone.now().date()
        if self.primary_vehicle_id:
            v = self.primary_vehicle
            if v.fc_expiry and v.fc_expiry < today:
                errors['primary_vehicle'] = f"Compliance Block: Fitness Certificate (FC) for {v.registration_number} expired on {v.fc_expiry.strftime('%d/%m/%Y')}."
            elif v.insurance_expiry and v.insurance_expiry < today:
                errors['primary_vehicle'] = f"Compliance Block: Commercial Insurance for {v.registration_number} expired on {v.insurance_expiry.strftime('%d/%m/%Y')}."

        if self.primary_driver_id:
            d = self.primary_driver
            validity = d.license_validity_tr or d.license_validity_nt
            if validity and validity < today:
                errors['primary_driver'] = f"Compliance Block: Commercial Driving License for {d.name} expired on {validity.strftime('%d/%m/%Y')}."

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.contract.name} — {self.primary_vehicle.registration_number} ({self.primary_driver.name})"


# ==============================================================================
# 5. Commuter & Student Manifest
# ==============================================================================

class CommuterManifest(models.Model):
    COMMUTER_TYPES = [
        ('employee', '🏢 Corporate / IT Employee'),
        ('student', '🎒 School / College Student'),
        ('worker', '🏭 Factory / Plant Worker'),
        ('staff', '👨‍🏫 Faculty / Hospital Staff'),
    ]
    GENDERS = [
        ('female', 'Female'),
        ('male', 'Male'),
        ('other', 'Other'),
    ]

    contract = models.ForeignKey(TransportContract, on_delete=models.CASCADE, related_name='commuters')
    commuter_type = models.CharField(max_length=20, choices=COMMUTER_TYPES, default='employee')
    commuter_id = models.CharField(max_length=50, help_text="Employee ID / Student Roll Number")
    name = models.CharField(max_length=200)
    gender = models.CharField(max_length=10, choices=GENDERS, default='female')
    phone = models.CharField(max_length=30, blank=True, help_text="Passenger contact number")
    emergency_contact_name = models.CharField(max_length=100, blank=True, help_text="Parent / Spouse / Emergency Contact")
    emergency_contact_phone = models.CharField(max_length=30, blank=True)
    department_or_grade = models.CharField(max_length=100, blank=True, help_text="e.g. IT Dept / Grade 8-A / Assembly Line 2")
    boarding_stop = models.ForeignKey(
        RouteStop,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_commuters',
        help_text="Designated pickup/drop stop"
    )
    requires_night_escort = models.BooleanField(
        default=False,
        help_text="Flagged for female night drops requiring escort security confirmation"
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Commuter & Student Passenger'
        verbose_name_plural = 'Commuter & Student Manifest'

    def __str__(self):
        return f"{self.name} ({self.commuter_id}) - {self.contract.name}"


# ==============================================================================
# 6. Daily Trip Logs (Execution)
# ==============================================================================

class ContractTripLog(models.Model):
    STATUSES = [
        ('scheduled', '📅 Scheduled'),
        ('en_route', '🚍 En Route'),
        ('completed', '✅ Completed'),
        ('delayed', '⚠️ Completed with Delay'),
        ('breakdown', '🔴 Vehicle Breakdown'),
        ('cancelled', '❌ Cancelled'),
    ]
    shift = models.ForeignKey(Shift, on_delete=models.PROTECT, related_name='logs')
    date = models.DateField()
    vehicle = models.ForeignKey(Vehicle, on_delete=models.SET_NULL, null=True, blank=True)
    driver = models.ForeignKey(Driver, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUSES, default='scheduled')

    # Metrics
    passenger_count = models.PositiveIntegerField(default=0)
    opening_km = models.PositiveIntegerField(null=True, blank=True)
    closing_km = models.PositiveIntegerField(null=True, blank=True)
    driver_bata = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Bata specifically for this trip"
    )
    toll_parking_charges = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Toll / Parking / Municipal entry incurred on this trip"
    )

    # Delay & Breakdown Management
    scheduled_departure_time = models.TimeField(null=True, blank=True)
    actual_departure_time = models.TimeField(null=True, blank=True)
    actual_arrival_time = models.TimeField(null=True, blank=True)
    delay_minutes = models.PositiveIntegerField(
        default=0,
        help_text="Minutes delayed beyond permissible grace period"
    )
    delay_reason = models.CharField(
        max_length=255,
        blank=True,
        help_text="e.g. Heavy highway gridlock, Tyre flat, Route detour"
    )

    # Standby / Replacement Tracking
    is_replacement_vehicle = models.BooleanField(
        default=False,
        help_text="True if dispatched as a standby backup vehicle due to breakdown"
    )
    replaced_vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='replaced_trips',
        help_text="Primary vehicle that broke down"
    )

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.opening_km is not None and self.closing_km is not None and self.closing_km < self.opening_km:
            raise ValidationError('Closing KMs cannot be less than opening KMs.')

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.driver_id and self.driver_bata:
            from finance.models import DriverSettlement
            settlement, created = DriverSettlement.objects.get_or_create(
                contract_trip=self,
                driver=self.driver,
                defaults={
                    'total_days': 1,
                    'batta': self.driver_bata,
                }
            )
            if not created and not settlement.settled_on:
                if settlement.batta != self.driver_bata:
                    settlement.batta = self.driver_bata
                    settlement.save(update_fields=['batta'])

    def __str__(self):
        return f"{self.shift} on {self.date}"


# ==============================================================================
# 7. SLA Performance & Penalty Deductions
# ==============================================================================

class ContractSLAPenalty(models.Model):
    PENALTY_TYPES = [
        ('late_arrival', '⏱️ Late Arrival (>15 Mins Breach)'),
        ('breakdown_delay', '🔧 Breakdown Delay / Standby Deployment Failure'),
        ('ac_failure', '❄️ AC Failure in Bus / Cab'),
        ('unauthorized_driver', '👔 Unverified / Ununiformed Driver'),
        ('escort_missing', '🛡️ Missing Security Escort on Female Night Drop'),
        ('speed_violation', '⚠️ Speed Limit Violation (>50 km/h)'),
        ('missed_trip', '❌ Completely Missed / Unserved Trip'),
        ('other', '📋 Other Contractual SLA Infraction'),
    ]

    contract = models.ForeignKey(TransportContract, on_delete=models.CASCADE, related_name='sla_penalties')
    trip_log = models.ForeignKey(
        ContractTripLog,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sla_penalties',
        help_text="Specific trip log that incurred this penalty"
    )
    date = models.DateField(default=timezone.now)
    penalty_type = models.CharField(max_length=50, choices=PENALTY_TYPES, default='late_arrival')
    penalty_amount = models.DecimalField(max_digits=10, decimal_places=2, help_text="Amount deducted in ₹")
    description = models.TextField(blank=True, help_text="Incident details reported by client / supervisor")
    waived = models.BooleanField(
        default=False,
        help_text="Check if waived by mutual agreement with client"
    )
    waiver_reason = models.CharField(max_length=255, blank=True)
    applied_to_invoice = models.ForeignKey(
        'ContractMonthlyInvoice',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='deducted_penalties'
    )

    class Meta:
        verbose_name = 'SLA Penalty & Performance Deduction'
        verbose_name_plural = 'SLA Penalties & Deductions'

    def __str__(self):
        status_str = " (Waived)" if self.waived else ""
        amount = self.penalty_amount or Decimal('0.00')
        contract_name = self.contract.name if self.contract_id else "No Contract"
        return f"{contract_name} — {self.get_penalty_type_display()} : ₹{amount:,.0f}{status_str}"


# ==============================================================================
# 8. Monthly Contract Invoices (Auto Billing Generator)
# ==============================================================================

class ContractMonthlyInvoice(models.Model):
    STATUSES = [
        ('draft', '📝 Draft / Calculating'),
        ('generated', '📤 Generated / Sent to Client'),
        ('paid', '✅ Paid in Full'),
        ('partially_paid', '🟡 Partially Paid'),
        ('disputed', '⚠️ Disputed by Client'),
    ]

    contract = models.ForeignKey(TransportContract, on_delete=models.PROTECT, related_name='monthly_invoices')
    invoice_number = models.CharField(max_length=50, unique=True, help_text="e.g. INV-ETS-2026-09-001")
    billing_month = models.DateField(help_text="First date of billing month (e.g. 2026-09-01)")
    from_date = models.DateField()
    to_date = models.DateField()

    # Trip Execution Stats
    total_trips_completed = models.PositiveIntegerField(default=0)
    total_kms_run = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Billing Components
    base_contract_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Base billing (Fixed monthly fee or Trips * Per Trip Rate)"
    )
    extra_km_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    fuel_escalation_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Net fuel adjustment per escalation formula"
    )
    toll_parking_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    sla_penalty_deduction = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Total SLA penalties deducted"
    )

    # Net & Taxes
    net_taxable_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    gst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=5.00)
    gst_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    grand_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # Status & Payment
    status = models.CharField(max_length=20, choices=STATUSES, default='draft')
    due_date = models.DateField(null=True, blank=True)
    payment_reference = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Contract Monthly Invoice'
        verbose_name_plural = 'Contract Monthly Invoices'

    def calculate_totals(self):
        """Helper to calculate taxable and grand total."""
        taxable = (
            self.base_contract_amount +
            self.extra_km_amount +
            self.fuel_escalation_amount +
            self.toll_parking_amount -
            self.sla_penalty_deduction
        )
        if taxable < 0:
            taxable = Decimal('0.00')
        self.net_taxable_amount = taxable
        gst_r = Decimal(str(self.gst_rate if self.gst_rate is not None else '5.00'))
        self.gst_amount = round((taxable * gst_r) / Decimal('100.0'), 2)
        self.grand_total = self.net_taxable_amount + self.gst_amount

    def save(self, *args, **kwargs):
        self.calculate_totals()
        super().save(*args, **kwargs)

    def __str__(self):
        total = self.grand_total or Decimal('0.00')
        contract_name = self.contract.name if self.contract_id else "No Contract"
        return f"{self.invoice_number} — {contract_name} (₹{total:,.0f})"


# ==============================================================================
# 9. Night Safety & Escort Guard Logs (IT / BPO Mandatory Compliance)
# ==============================================================================

class NightSafetyEscortLog(models.Model):
    VERIFICATION_STATUSES = [
        ('verified_call', '📞 Verified via Phone Call to Employee'),
        ('verified_sms', '📱 Verified via Safe-Drop SMS / OTP'),
        ('supervisor_signoff', '✍️ Transport Supervisor Sign-off'),
        ('pending', '⏳ Verification Pending Confirmation'),
    ]

    trip_log = models.ForeignKey(
        ContractTripLog,
        on_delete=models.CASCADE,
        related_name='escort_logs',
        help_text="Trip log requiring female employee night security"
    )
    escort_guard_name = models.CharField(max_length=150, help_text="Security Escort Guard Full Name")
    security_agency = models.CharField(
        max_length=150,
        blank=True,
        help_text="Contracted security agency (e.g. SIS, G4S, Tops Security)"
    )
    guard_badge_number = models.CharField(max_length=50, blank=True, help_text="Security Guard ID / Badge")
    guard_contact_phone = models.CharField(max_length=30, blank=True)
    female_passengers_count = models.PositiveIntegerField(default=1)

    first_pickup_time = models.TimeField(null=True, blank=True, help_text="First female employee pickup time")
    last_female_drop_time = models.TimeField(null=True, blank=True, help_text="Last female employee drop time")
    last_drop_verification_status = models.CharField(
        max_length=30,
        choices=VERIFICATION_STATUSES,
        default='verified_call'
    )
    safe_drop_confirmed_by = models.CharField(
        max_length=150,
        blank=True,
        help_text="Employee or supervisor confirmation signature / name"
    )
    remarks = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Night Escort & Women Safety Log'
        verbose_name_plural = 'Night Safety & Escort Logs'

    def __str__(self):
        return f"Escort: {self.escort_guard_name} for Trip #{self.trip_log.pk} on {self.trip_log.date}"
