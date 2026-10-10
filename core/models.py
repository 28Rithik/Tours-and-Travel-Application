from django.db import models


class Party(models.Model):
	PARTY_TYPES = [('travel_agency', 'Travel agency'), ('corporate', 'Corporate'), ('hotel', 'Hotel'), ('individual', 'Individual'), ('supplier', 'Supplier'), ('other', 'Other')]
	BILLING_CYCLES = [('trip', 'Trip-by-trip'), ('weekly', 'Weekly'), ('fortnightly', 'Fortnightly'), ('monthly', 'Monthly'), ('bimonthly', 'Bi-monthly (Every 2 Months)'), ('quarterly', 'Quarterly (Every 3 Months)')]
	name = models.CharField(max_length=255)
	party_type = models.CharField(max_length=30, choices=PARTY_TYPES)
	phone = models.CharField(max_length=20, blank=True)
	email = models.EmailField(blank=True)
	address = models.TextField(blank=True)
	billing_cycle = models.CharField(max_length=20, choices=BILLING_CYCLES, default='monthly')
	credit_period_days = models.PositiveIntegerField(default=30)
	gstin = models.CharField(max_length=15, blank=True)
	state_code = models.CharField(max_length=2, blank=True, help_text="e.g. 33 for TN")
	tds_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text="Default TDS deduction percentage (e.g. 2.0 for 194C)")
	default_day_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
	default_km_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
	opening_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
	is_active = models.BooleanField(default=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		constraints = [
			models.CheckConstraint(
				check=models.Q(default_day_rate__gte=0) & models.Q(default_km_rate__gte=0) & models.Q(tds_rate__gte=0),
				name='party_rates_non_negative'
			),
		]
		indexes = [
			models.Index(fields=['is_active', 'party_type'], name='idx_party_active_type'),
		]

	def __str__(self):
		return self.name

class Client(Party):
	class Meta:
		proxy = True
		verbose_name = 'Client'
		verbose_name_plural = 'Clients'

class Supplier(Party):
	class Meta:
		proxy = True
		verbose_name = 'Supplier'
		verbose_name_plural = 'Suppliers'


class VehicleType(models.Model):
	TRANSMISSION_TYPES = [('manual', 'Manual'), ('automatic', 'Automatic')]
	TOLL_CLASSES = [('car', 'Car / Jeep / Van'), ('lcv', 'LCV / Mini Bus'), ('bus_2_axle', 'Bus (2 Axle)'), ('bus_3_axle', 'Bus (3 Axle)'), ('multi_axle', 'Multi Axle')]
	FUEL_TYPES = [('petrol', 'Petrol'), ('diesel', 'Diesel'), ('cng', 'CNG'), ('electric', 'Electric')]
	
	# Basic Info
	name = models.CharField(max_length=100, unique=True)
	category = models.CharField(max_length=50, blank=True)
	description = models.TextField(blank=True, help_text="Short description for customer portal")
	
	# Pricing & Rates
	default_day_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
	default_km_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
	minimum_km_per_day = models.PositiveIntegerField(default=250, help_text="Standard daily minimum billing km")
	extra_km_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
	extra_hour_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
	driver_bata = models.DecimalField(max_digits=10, decimal_places=2, default=0)
	night_halt_charge = models.DecimalField(max_digits=10, decimal_places=2, default=0)
	
	# Operations & Specs
	seating_capacity = models.PositiveIntegerField(default=4)
	luggage_capacity = models.CharField(max_length=100, blank=True)
	fuel_type = models.CharField(max_length=20, choices=FUEL_TYPES, blank=True, default='diesel')
	expected_mileage_kmpl = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="Average expected km/l")
	toll_class = models.CharField(max_length=20, choices=TOLL_CLASSES, blank=True)
	
	# Customer Features
	has_ac = models.BooleanField(default=True, verbose_name="AC")
	is_luxury = models.BooleanField(default=False)
	transmission_type = models.CharField(max_length=20, choices=TRANSMISSION_TYPES, blank=True)
	is_wheelchair_accessible = models.BooleanField(default=False)
	amenities = models.TextField(blank=True, help_text="e.g. WiFi, TV, Reclining Seats")
	stock_photo = models.ImageField(upload_to='vehicle_types/', null=True, blank=True)

	def __str__(self):
		return self.name


class LicenseClass(models.Model):
	code = models.CharField(max_length=20, unique=True, help_text="e.g., LMV-TR")
	name = models.CharField(max_length=100, help_text="e.g., Light Motor Vehicle - Transport")
	example_vehicles = models.CharField(max_length=255, blank=True, help_text="e.g., Taxi, small commercial vehicle")

	class Meta:
		ordering = ['code']
		verbose_name = 'License Class'
		verbose_name_plural = 'License Classes'

	def __str__(self):
		return f"{self.code} - {self.name}"

class Driver(models.Model):
	STATUSES = [('active', 'Active'), ('inactive', 'Inactive'), ('on_leave', 'On leave')]
	DRIVER_TYPES = [
		('owned', 'Own Driver (Salary)'),
		('supplier', 'Supplier Driver'),
		('temporary', 'Temporary Contract Driver')
	]
	
	# Basic Info
	name = models.CharField(max_length=255)
	driver_type = models.CharField(max_length=20, choices=DRIVER_TYPES, default='owned')
	employer_party = models.ForeignKey('Party', on_delete=models.PROTECT, null=True, blank=True, related_name='employed_drivers')
	phone = models.CharField(max_length=20, blank=True)
	address = models.TextField(blank=True)
	joining_date = models.DateField(null=True, blank=True)
	status = models.CharField(max_length=20, choices=STATUSES, default='active')
	
	# Identity & Background
	date_of_birth = models.DateField(null=True, blank=True)
	father_or_spouse_name = models.CharField(max_length=255, blank=True, verbose_name="Son/Daughter/Wife of")
	aadhar_number = models.CharField(max_length=20, blank=True)
	profile_picture = models.ImageField(upload_to='drivers/profiles/', null=True, blank=True)
	
	# Driving License Details
	license_number = models.CharField(max_length=50, blank=True)
	license_classes = models.ManyToManyField(LicenseClass, blank=True)
	licensing_authority = models.CharField(max_length=100, blank=True, help_text="e.g., TN52 SANKARI RTO")
	license_issue_date = models.DateField(null=True, blank=True)
	license_validity_nt = models.DateField(null=True, blank=True, verbose_name="Validity (NT)")
	license_validity_tr = models.DateField(null=True, blank=True, verbose_name="Validity (TR)")
	badge_number = models.CharField(max_length=50, blank=True)
	license_document = models.FileField(upload_to='drivers/licenses/', null=True, blank=True)
	is_volvo_certified = models.BooleanField(default=False, verbose_name="Volvo Multi-Axle Certified", help_text="Has completed official Volvo multi-axle training")
	
	# Safety & Emergencies
	emergency_contact_name = models.CharField(max_length=255, blank=True)
	emergency_contact_phone = models.CharField(max_length=20, blank=True)
	blood_group = models.CharField(max_length=10, blank=True)
	
	# Financial Settlements
	bank_account_number = models.CharField(max_length=50, blank=True)
	ifsc_code = models.CharField(max_length=20, blank=True)
	bank_name = models.CharField(max_length=100, blank=True)
	upi_id = models.CharField(max_length=100, blank=True)
	
	# Customer Experience
	languages_spoken = models.CharField(max_length=255, blank=True, help_text='e.g., English, Hindi, Tamil')
	hill_station_experience = models.BooleanField(default=False)

	def clean(self):
		from django.core.exceptions import ValidationError
		
		errors = {}
		if self.driver_type == 'owned':
			if not self.aadhar_number:
				errors['aadhar_number'] = 'Aadhar number is required for owned drivers.'
			if not self.bank_account_number:
				errors['bank_account_number'] = 'Bank account number is required for owned drivers.'
			if not self.joining_date:
				errors['joining_date'] = 'Joining date is required for owned drivers.'
				
		elif self.driver_type == 'supplier':
			if not self.employer_party:
				errors['employer_party'] = 'Supplier party must be selected for supplier drivers.'
			elif self.employer_party.party_type != 'supplier':
				errors['employer_party'] = 'Employer party must have type "Supplier".'
					
		elif self.driver_type == 'temporary':
			if not self.upi_id:
				errors['upi_id'] = 'UPI ID is required for temporary drivers.'
				
		if errors:
			raise ValidationError(errors)

	@property
	def license_status(self):
		from django.utils import timezone
		today = timezone.localdate()
		validity = self.license_validity_tr or self.license_validity_nt
		if not validity:
			return {'status': 'missing', 'label': 'No Expiry Set', 'color': '#6c757d', 'days': None}
		days_left = (validity - today).days
		if days_left < 0:
			return {'status': 'expired', 'label': f'Expired ({validity.strftime("%d/%m/%Y")})', 'color': '#dc3545', 'days': days_left}
		elif days_left <= 30:
			return {'status': 'expiring_soon', 'label': f'Expiring in {days_left}d', 'color': '#f59e0b', 'days': days_left}
		else:
			return {'status': 'valid', 'label': f'Valid ({validity.strftime("%d/%m/%Y")})', 'color': '#16a34a', 'days': days_left}

	@property
	def active_trip(self):
		from operations.models import Trip
		from django.utils import timezone
		today = timezone.localdate()
		return self.trips.filter(
			status__in=['started', 'assigned', 'driver_confirmed'],
			start_date__lte=today,
			end_date__gte=today
		).first()

	class Meta:
		indexes = [
			models.Index(fields=['status', 'driver_type'], name='idx_drv_status_type'),
		]

	def __str__(self):
		return self.name


class DriverEmploymentPeriod(models.Model):
	driver = models.ForeignKey(Driver, on_delete=models.CASCADE, related_name='employment_periods')
	joined_on = models.DateField()
	left_on = models.DateField(null=True, blank=True)
	notes = models.CharField(max_length=255, blank=True)

	class Meta:
		ordering = ['-joined_on']

	def clean(self):
		from django.core.exceptions import ValidationError

		if self.left_on and self.left_on < self.joined_on:
			raise ValidationError('Leaving date cannot be before joining date.')
		if self.driver_id and self.left_on is None:
			other_active = DriverEmploymentPeriod.objects.filter(driver=self.driver, left_on__isnull=True).exclude(pk=self.pk)
			if other_active.exists():
				raise ValidationError('A driver can have only one active employment period.')

	def __str__(self):
		return f'{self.driver} ({self.joined_on} - {self.left_on or "current"})'


class Cleaner(models.Model):
	STATUSES = [('active', 'Active'), ('inactive', 'Inactive'), ('on_leave', 'On leave')]
	
	# Basic Info
	name = models.CharField(max_length=255)
	employer_party = models.ForeignKey(Party, on_delete=models.PROTECT, null=True, blank=True, related_name='employed_cleaners')
	phone = models.CharField(max_length=20, blank=True)
	address = models.TextField(blank=True)
	joining_date = models.DateField(null=True, blank=True)
	status = models.CharField(max_length=20, choices=STATUSES, default='active')
	default_daily_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
	can_drive = models.BooleanField(default=False)
	
	# Identity & Background
	date_of_birth = models.DateField(null=True, blank=True)
	aadhar_number = models.CharField(max_length=20, blank=True)
	profile_picture = models.ImageField(upload_to='cleaners/profiles/', null=True, blank=True)
	
	# License Details (if can_drive is true)
	license_number = models.CharField(max_length=50, blank=True)
	license_validity = models.DateField(null=True, blank=True)
	
	# Safety & Emergencies
	emergency_contact_name = models.CharField(max_length=255, blank=True)
	emergency_contact_phone = models.CharField(max_length=20, blank=True)
	blood_group = models.CharField(max_length=10, blank=True)
	
	# Financial Settlements
	bank_account_number = models.CharField(max_length=50, blank=True)
	ifsc_code = models.CharField(max_length=20, blank=True)
	bank_name = models.CharField(max_length=100, blank=True)
	upi_id = models.CharField(max_length=100, blank=True)

	def __str__(self):
		return self.name

	def clean(self):
		from django.core.exceptions import ValidationError
		if self.can_drive:
			if not self.license_number:
				raise ValidationError({'license_number': 'License number is required if cleaner can drive.'})
			if not self.license_validity:
				raise ValidationError({'license_validity': 'License validity date is required if cleaner can drive.'})

class CleanerEmploymentPeriod(models.Model):
	cleaner = models.ForeignKey(Cleaner, on_delete=models.CASCADE, related_name='employment_periods')
	joined_on = models.DateField()
	left_on = models.DateField(null=True, blank=True)
	notes = models.TextField(blank=True)

	class Meta:
		ordering = ['-joined_on']

	def clean(self):
		from django.core.exceptions import ValidationError

		if self.left_on and self.left_on < self.joined_on:
			raise ValidationError('Leaving date cannot be before joining date.')
		if self.cleaner_id and self.left_on is None:
			other_active = CleanerEmploymentPeriod.objects.filter(cleaner=self.cleaner, left_on__isnull=True).exclude(pk=self.pk)
			if other_active.exists():
				raise ValidationError('A cleaner can have only one active employment period.')

	def __str__(self):
		return f'{self.cleaner} ({self.joined_on} - {self.left_on or "current"})'


class Vehicle(models.Model):
	FUEL_TYPES = [('petrol', 'Petrol'), ('diesel', 'Diesel'), ('cng', 'CNG'), ('electric', 'Electric')]
	STATUSES = [('available', 'Available'), ('assigned', 'Assigned'), ('on_trip', 'On trip'), ('maintenance', 'Maintenance'), ('inactive', 'Inactive')]
	OWNERSHIP_TYPES = [('owned', 'Owned fleet'), ('outsourced', 'Outsourced / supplier')]
	
	# Basic Info
	registration_number = models.CharField(max_length=30, unique=True)
	vehicle_type = models.ForeignKey(VehicleType, on_delete=models.PROTECT, null=True, blank=True)
	ownership_type = models.CharField(max_length=20, choices=OWNERSHIP_TYPES, default='owned')
	owner_party = models.ForeignKey('Party', on_delete=models.PROTECT, null=True, blank=True, related_name='supplied_vehicles')
	status = models.CharField(max_length=20, choices=STATUSES, default='available')
	
	# Technical Specs
	brand = models.CharField(max_length=100, blank=True)
	model = models.CharField(max_length=100, blank=True)
	year = models.PositiveIntegerField(null=True, blank=True)
	color = models.CharField(max_length=50, blank=True)
	fuel_type = models.CharField(max_length=20, choices=FUEL_TYPES, default='diesel')
	fuel_tank_capacity = models.PositiveIntegerField(null=True, blank=True, help_text="Capacity in Liters")
	def_capacity = models.PositiveIntegerField(null=True, blank=True, verbose_name="DEF (AdBlue) Capacity", help_text="Capacity in Liters")
	seating_capacity = models.PositiveIntegerField(default=4)
	current_km = models.PositiveIntegerField(default=0)
	
	# Amenities
	has_ac = models.BooleanField(default=False, verbose_name="AC")
	is_sleeper = models.BooleanField(default=False, verbose_name="Sleeper / Pushback")
	has_air_suspension = models.BooleanField(default=False, verbose_name="Air Suspension")
	has_video_coach = models.BooleanField(default=False, verbose_name="Video Coach (TV/Music)")
	
	# Compliance & Expiries
	rc_expiry = models.DateField(null=True, blank=True, verbose_name="RC Expiry")
	insurance_expiry = models.DateField(null=True, blank=True)
	fc_expiry = models.DateField(null=True, blank=True)
	permit_expiry = models.DateField(null=True, blank=True)
	tax_expiry = models.DateField(null=True, blank=True)
	pollution_expiry = models.DateField(null=True, blank=True)
	next_service_due_km = models.PositiveIntegerField(null=True, blank=True, verbose_name="Next Service Due (KM)")
	
	default_driver = models.ForeignKey('core.Driver', on_delete=models.SET_NULL, null=True, blank=True, related_name='default_vehicles', help_text="Auto-assigned to this driver when selected for a trip")
	expected_mileage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="Expected km/litre for fuel theft detection")
	current_location = models.CharField(max_length=255, blank=True, help_text="Current home depot or parked location")
	
	# Ownership & Documents
	engine_number = models.CharField(max_length=100, blank=True)
	chassis_number = models.CharField(max_length=100, blank=True)
	rc_document = models.FileField(upload_to='vehicles/rc/', null=True, blank=True)
	gps_imei = models.CharField(max_length=100, blank=True, verbose_name="GPS IMEI Number")
	fastag_id = models.CharField(max_length=100, blank=True, verbose_name="FASTag ID")
	
	# Insurance Details
	insurance_provider = models.CharField(max_length=100, blank=True, help_text="e.g. Tata AIG, HDFC Ergo")
	insurance_policy_number = models.CharField(max_length=100, blank=True)
	insurance_document = models.FileField(upload_to='vehicles/insurance/', null=True, blank=True)
	
	# Financing Details
	is_financed = models.BooleanField(default=False)
	financier_name = models.CharField(max_length=100, blank=True, help_text="e.g. Cholamandalam Finance")
	emi_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
	loan_end_date = models.DateField(null=True, blank=True)

	# ── Supplier / Outsourced Vehicle Fields ──
	# Supplier Contact
	supplier_contact_person = models.CharField(max_length=100, blank=True, verbose_name="Supplier Contact Person", help_text="Primary contact at the supplier for this vehicle")
	supplier_driver_name = models.CharField(max_length=100, blank=True, verbose_name="Supplier's Driver Name")
	supplier_driver_phone = models.CharField(max_length=20, blank=True, verbose_name="Supplier's Driver Phone")

	# Supplier Terms & Rates
	SUPPLIER_PAYMENT_TERMS = [('advance', 'Advance'), ('credit', 'Credit'), ('cod', 'Cash on Delivery')]
	supplier_daily_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Supplier Daily Rate (₹)", help_text="What the supplier charges per day")
	supplier_km_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Supplier KM Rate (₹)", help_text="What the supplier charges per km")
	supplier_driver_bata = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Supplier Driver Bata (₹)", help_text="Driver allowance the supplier charges")
	supplier_min_hours = models.PositiveIntegerField(null=True, blank=True, verbose_name="Minimum Hours", help_text="Supplier's minimum commitment in hours")
	supplier_min_km = models.PositiveIntegerField(null=True, blank=True, verbose_name="Minimum KM", help_text="Supplier's minimum commitment in km")
	supplier_payment_terms = models.CharField(max_length=20, choices=SUPPLIER_PAYMENT_TERMS, default='credit', verbose_name="Payment Terms")

	# Supplier Agreement
	supplier_contract_ref = models.CharField(max_length=100, blank=True, verbose_name="Contract Reference", help_text="Agreement or contract number")
	supplier_contract_start = models.DateField(null=True, blank=True, verbose_name="Contract Start Date")
	supplier_contract_end = models.DateField(null=True, blank=True, verbose_name="Contract End Date")
	supplier_notes = models.TextField(blank=True, verbose_name="Notes / Remarks", help_text="Special terms, conditions, or notes about this supplier vehicle")

	def clean(self):
		from django.core.exceptions import ValidationError

		if self.ownership_type == 'outsourced' and not self.owner_party_id:
			raise ValidationError({'owner_party': 'An outsourced vehicle must have a supplier owner.'})
		if self.ownership_type == 'owned' and self.owner_party_id:
			raise ValidationError({'owner_party': 'An owned vehicle cannot have a supplier owner.'})

	@property
	def has_open_defects(self):
		if hasattr(self, 'defect_tickets'):
			return self.defect_tickets.filter(status__in=['open', 'in_progress']).exists()
		return False

	@property
	def compliance_status(self):
		from django.utils import timezone
		today = timezone.localdate()
		docs = [
			('Insurance', self.insurance_expiry),
			('Fitness (FC)', self.fc_expiry),
			('Permit', self.permit_expiry),
			('Pollution (PUC)', self.pollution_expiry),
			('Road Tax', self.tax_expiry),
			('RC', self.rc_expiry),
		]
		expired = []
		expiring_soon = []
		for name, date_val in docs:
			if date_val:
				days = (date_val - today).days
				if days < 0:
					expired.append((name, date_val, abs(days)))
				elif days <= 30:
					expiring_soon.append((name, date_val, days))
		if expired:
			name, d, overdue = expired[0]
			extra = f" (+{len(expired)-1} more)" if len(expired) > 1 else ""
			return {'status': 'expired', 'label': f'{name} Expired!{extra}', 'color': '#dc3545', 'count': len(expired)}
		elif expiring_soon:
			name, d, in_days = expiring_soon[0]
			return {'status': 'expiring_soon', 'label': f'{name} due in {in_days}d', 'color': '#f59e0b', 'count': len(expiring_soon)}
		else:
			return {'status': 'valid', 'label': 'Compliant', 'color': '#16a34a', 'count': 0}

	class Meta:
		indexes = [
			models.Index(fields=['status', 'vehicle_type'], name='idx_veh_status_type'),
			models.Index(fields=['ownership_type', 'status'], name='idx_veh_owner_status'),
		]

	def __str__(self):
		return f'{self.vehicle_type} ({self.registration_number})'

class VehiclePhoto(models.Model):
	vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='photos')
	photo = models.ImageField(upload_to='vehicles/gallery/')
	description = models.CharField(max_length=100, blank=True, help_text="e.g., Interior view, Front view")

	def __str__(self):
		return f"Photo of {self.vehicle}"


class RateCard(models.Model):
	party = models.ForeignKey(Party, on_delete=models.CASCADE, related_name='rate_cards')
	vehicle = models.ForeignKey('Vehicle', on_delete=models.CASCADE, null=True, blank=True, related_name='rate_cards')
	vehicle_type = models.ForeignKey(VehicleType, on_delete=models.PROTECT, null=True, blank=True)
	day_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
	km_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
	extra_km_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
	driver_bata = models.DecimalField(max_digits=10, decimal_places=2, default=0)
	night_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0)
	airport_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0)
	permit_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0)
	other_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0)
	effective_from = models.DateField()
	effective_to = models.DateField(null=True, blank=True)

	def clean(self):
		from django.core.exceptions import ValidationError
		from datetime import date

		if self.vehicle_id:
			self.vehicle_type = self.vehicle.vehicle_type

		if self.effective_from and self.effective_to and self.effective_from > self.effective_to:
			raise ValidationError({'effective_to': 'Effective to date cannot be before effective from date.'})
			
		if self.effective_from:
			overlapping = RateCard.objects.filter(
				party=self.party,
				vehicle_type=self.vehicle_type,
				vehicle=self.vehicle
			).exclude(pk=self.pk)
			
			r1_start = self.effective_from
			r1_end = self.effective_to or date.max
			for rc in overlapping:
				r2_start = rc.effective_from
				r2_end = rc.effective_to or date.max
				if max(r1_start, r2_start) <= min(r1_end, r2_end):
					raise ValidationError('A rate card with overlapping dates already exists for this party and vehicle.')

	def __str__(self):
		target = self.vehicle.registration_number if self.vehicle_id else self.vehicle_type
		return f'{self.party} / {target} / {self.effective_from}'

from django.contrib.auth.models import User


class StaffProfile(models.Model):
	ROLE_CHOICES = [
		('admin', 'System Director / Super Admin'),
		('manager', 'General / Branch Manager'),
		('sales_executive', 'Senior Sales Executive & Tour Designer'),
		('sales', 'Corporate Sales Representative'),
		('operations', 'Fleet & Dispatch Operations Lead'),
		('operation_account', 'Operations Accounts & Billing Officer'),
		('driver', 'Senior Fleet Chauffeur'),
		('customer_service', 'Guest Experience & Support Specialist'),
	]

	user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='staff_profile')
	role = models.CharField(max_length=30, choices=ROLE_CHOICES, default='sales_executive')
	employee_id = models.CharField(max_length=30, unique=True, help_text="e.g. SGT-ADM-01")
	branch = models.CharField(max_length=100, default='Chennai Central HQ')
	department = models.CharField(max_length=100, default='Operations')
	designation = models.CharField(max_length=100, blank=True)
	phone = models.CharField(max_length=20, blank=True)
	emergency_contact = models.CharField(max_length=20, blank=True)
	approval_limit_inr = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Max discount or expense approval ceiling")
	monthly_sales_target_inr = models.DecimalField(max_digits=12, decimal_places=2, default=0)
	is_on_duty = models.BooleanField(default=True)
	avatar_color = models.CharField(max_length=20, default='#0284c7')
	linked_driver = models.ForeignKey('Driver', on_delete=models.SET_NULL, null=True, blank=True, related_name='staff_accounts')
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ['employee_id']
		verbose_name = 'Staff Profile'
		verbose_name_plural = 'Staff Profiles'

	def __str__(self):
		return f"{self.employee_id} - {self.user.get_full_name() or self.user.username} ({self.get_role_display()})"

	@property
	def display_name(self):
		return self.user.get_full_name() or self.user.username

	@property
	def role_badge_color(self):
		colors = {
			'admin': '#e11d48',
			'manager': '#8b5cf6',
			'sales_executive': '#10b981',
			'sales': '#059669',
			'operations': '#0284c7',
			'operation_account': '#d97706',
			'driver': '#f97316',
			'customer_service': '#06b6d4',
		}
		return colors.get(self.role, '#64748b')

	@property
	def role_icon(self):
		icons = {
			'admin': '👑',
			'manager': '🏢',
			'sales_executive': '📑',
			'sales': '💼',
			'operations': '🚛',
			'operation_account': '💰',
			'driver': '👨‍✈️',
			'customer_service': '🎧',
		}
		return icons.get(self.role, '👤')
