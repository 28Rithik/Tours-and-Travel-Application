from django.db import models
from core.models import Vehicle

class ComplianceDocument(models.Model):
	DOCUMENT_TYPES = [
		('insurance', 'Insurance Policy'),
		('fc', 'Fitness Certificate (FC)'),
		('permit', 'National/State Permit'),
		('tax', 'Road Tax'),
		('pollution', 'Pollution / Emission (PUC)'),
		('other', 'Other Document')
	]
	
	vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='compliance_documents')
	document_type = models.CharField(max_length=50, choices=DOCUMENT_TYPES)
	document_number = models.CharField(max_length=100, blank=True)
	issue_date = models.DateField(null=True, blank=True)
	expiry_date = models.DateField()
	attachment = models.FileField(upload_to='compliance_docs/', null=True, blank=True)
	notes = models.TextField(blank=True)
	
	insurance_provider = models.CharField(max_length=255, blank=True)
	premium_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
	coverage_type = models.CharField(max_length=50, choices=[('comprehensive', 'Comprehensive'), ('third_party', 'Third-Party')], blank=True)
	permit_states = models.CharField(max_length=255, blank=True, help_text="e.g. TN, KA, KL")

	@property
	def is_expired(self):
		from django.utils import timezone
		return self.expiry_date < timezone.now().date()

	@property
	def days_until_expiry(self):
		from django.utils import timezone
		delta = self.expiry_date - timezone.now().date()
		return delta.days

	def clean(self):
		from django.core.exceptions import ValidationError
		from django.utils import timezone
		import datetime
		
		if self.issue_date and self.expiry_date <= self.issue_date:
			raise ValidationError('Expiry date must be after the issue date.')
			
		if self.document_type != 'other' and not self.document_number:
			raise ValidationError('Document number is required for this document type.')
			
		if not self.pk:
			grace_period = timezone.now().date() + datetime.timedelta(days=30)
			existing = ComplianceDocument.objects.filter(
				vehicle=self.vehicle, 
				document_type=self.document_type,
				expiry_date__gt=grace_period
			).exists()
			if existing:
				raise ValidationError(f'An active {self.get_document_type_display()} already exists for this vehicle that does not expire within 30 days.')

	class Meta:
		ordering = ['expiry_date']
		verbose_name = 'Compliance Document'
		verbose_name_plural = 'Compliance Documents'

	def __str__(self):
		return f"{self.get_document_type_display()} - {self.vehicle.registration_number}"

	def save(self, *args, **kwargs):
		super().save(*args, **kwargs)
		# Automatically sync with Vehicle model fields for quick access
		if self.document_type == 'insurance':
			self.vehicle.insurance_expiry = self.expiry_date
		elif self.document_type == 'fc':
			self.vehicle.fc_expiry = self.expiry_date
		elif self.document_type == 'permit':
			self.vehicle.permit_expiry = self.expiry_date
		elif self.document_type == 'tax':
			self.vehicle.tax_expiry = self.expiry_date
		elif self.document_type == 'pollution':
			self.vehicle.pollution_expiry = self.expiry_date
		self.vehicle.save()


class PartInventory(models.Model):
	part_name = models.CharField(max_length=255, unique=True)
	sku = models.CharField(max_length=100, blank=True)
	current_stock = models.PositiveIntegerField(default=0)
	minimum_stock_level = models.PositiveIntegerField(default=5)
	default_unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)

	class Meta:
		verbose_name = 'Part Inventory'
		verbose_name_plural = 'Part Inventories'
		ordering = ['part_name']

	def __str__(self):
		return f"{self.part_name} (Stock: {self.current_stock})"


class ServiceRecord(models.Model):
	SERVICE_TYPES = [
		('routine', 'Routine Service'),
		('breakdown', 'Breakdown Repair'),
		('accidental', 'Accidental Repair'),
		('bodywork', 'Bodywork / Tinkering'),
		('tyre', 'Tyre Replacement/Puncture'),
		('other', 'Other Maintenance')
	]
	STATUS_CHOICES = [
		('pending', 'Pending Approval'),
		('in_progress', 'In Progress (In Workshop)'),
		('completed', 'Completed')
	]
	
	vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='service_records')
	service_type = models.CharField(max_length=30, choices=SERVICE_TYPES, default='routine')
	status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='in_progress')
	
	date = models.DateField()
	odometer_reading = models.PositiveIntegerField(help_text="KM reading when given for service")
	garage_name = models.CharField(max_length=255)
	
	description = models.TextField(help_text="Details of complaints and work done")
	total_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
	invoice_attachment = models.FileField(upload_to='service_invoices/', null=True, blank=True)
	
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-date']

	def __str__(self):
		return f"{self.vehicle.registration_number} - {self.get_service_type_display()} on {self.date}"

	def save(self, *args, **kwargs):
		old_status = None
		if self.pk:
			old_record = ServiceRecord.objects.filter(pk=self.pk).first()
			if old_record:
				old_status = old_record.status

		if self.status == 'in_progress':
			self.vehicle.status = 'maintenance'
		elif self.status == 'completed' and self.vehicle.status == 'maintenance':
			self.vehicle.status = 'active'
		self.vehicle.save(update_fields=['status'] if self.vehicle.pk else None)
		super().save(*args, **kwargs)

		# Inventory deduction
		if self.status == 'completed' and old_status != 'completed':
			for part in self.spare_parts.all():
				if part.inventory_item:
					part.inventory_item.current_stock = max(0, part.inventory_item.current_stock - part.quantity)
					part.inventory_item.save(update_fields=['current_stock'])


class SparePart(models.Model):
	service_record = models.ForeignKey(ServiceRecord, on_delete=models.CASCADE, related_name='spare_parts')
	inventory_item = models.ForeignKey(PartInventory, on_delete=models.PROTECT, null=True, blank=True, help_text="Select from inventory")
	part_name = models.CharField(max_length=255, blank=True, help_text="Or type name manually if not in inventory")
	quantity = models.PositiveIntegerField(default=1)
	unit_price = models.DecimalField(max_digits=10, decimal_places=2)
	
	@property
	def total_price(self):
		return self.quantity * self.unit_price

	def __str__(self):
		name = self.inventory_item.part_name if self.inventory_item else self.part_name
		return f"{self.quantity}x {name} for {self.service_record.vehicle}"

	def clean(self):
		from django.core.exceptions import ValidationError
		if not self.inventory_item and not self.part_name:
			raise ValidationError("Please provide either an inventory item or a part name.")
		if self.inventory_item and self.quantity > self.inventory_item.current_stock:
			raise ValidationError({'quantity': f'Not enough stock. Only {self.inventory_item.current_stock} left.'})

	def save(self, *args, **kwargs):
		if self.inventory_item and not self.unit_price:
			self.unit_price = self.inventory_item.default_unit_price
		super().save(*args, **kwargs)


class VehicleAsset(models.Model):
	ASSET_TYPES = [('tyre', 'Tyre'), ('battery', 'Battery')]
	POSITIONS = [
		('front_left', 'Front Left'), ('front_right', 'Front Right'),
		('rear_left_outer', 'Rear Left Outer'), ('rear_left_inner', 'Rear Left Inner'),
		('rear_right_outer', 'Rear Right Outer'), ('rear_right_inner', 'Rear Right Inner'),
		('spare', 'Spare / Stepney'), ('engine_bay', 'Engine Bay')
	]
	
	asset_type = models.CharField(max_length=20, choices=ASSET_TYPES)
	serial_number = models.CharField(max_length=100, unique=True)
	vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='assets')
	position = models.CharField(max_length=50, choices=POSITIONS, blank=True)
	
	installed_date = models.DateField()
	installed_odometer = models.PositiveIntegerField()
	expected_life_km = models.PositiveIntegerField(help_text="e.g., 40000 for tyres")
	
	STATUS_CHOICES = [
		('in_use', 'In Use'),
		('spare', 'Spare'),
		('retreading', 'Sent for Retreading'),
		('scrapped', 'Scrapped'),
		('sold', 'Sold')
	]
	
	status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='in_use')
	purchase_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
	vendor_name = models.CharField(max_length=255, blank=True)
	warranty_expiry_date = models.DateField(null=True, blank=True)
	warranty_expiry_km = models.PositiveIntegerField(null=True, blank=True)
	
	def clean(self):
		from django.core.exceptions import ValidationError
		if self.asset_type == 'battery' and self.position and self.position != 'engine_bay':
			raise ValidationError("Batteries must be positioned in the Engine Bay.")
		if self.asset_type == 'tyre' and self.position == 'engine_bay':
			raise ValidationError("Tyres cannot be positioned in the Engine Bay.")
			
	class Meta:
		verbose_name = 'Vehicle Asset'
		verbose_name_plural = 'Vehicle Assets'

	def __str__(self):
		veh_str = str(self.vehicle) if self.vehicle_id else "No Vehicle"
		return f"{self.get_asset_type_display()} - {self.serial_number} on {veh_str}"

	@property
	def current_run_km(self):
		if self.vehicle_id and getattr(self.vehicle, 'current_km', None) is not None and self.installed_odometer is not None:
			if self.vehicle.current_km >= self.installed_odometer:
				return self.vehicle.current_km - self.installed_odometer
		return 0
		
	@property
	def needs_replacement(self):
		if self.expected_life_km and self.current_run_km >= (self.expected_life_km * 0.9):
			return True
		return False


class DefectTicket(models.Model):
	STATUS_CHOICES = [
		('open', 'Open / Unresolved'),
		('in_progress', 'In Progress (Mechanic Assigned)'),
		('resolved', 'Resolved')
	]

	vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='defect_tickets')
	reported_by = models.CharField(max_length=255, help_text="Driver name or dispatcher who reported it")
	date_reported = models.DateField(auto_now_add=True)
	description = models.TextField(help_text="Describe the issue, e.g., 'AC not cooling'")
	status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
	resolved_date = models.DateField(null=True, blank=True)
	notes = models.TextField(blank=True, help_text="Mechanic notes upon resolution")

	class Meta:
		ordering = ['-date_reported']
		verbose_name = 'Defect Ticket'
		verbose_name_plural = 'Defect Tickets'

	def __str__(self):
		return f"Defect on {self.vehicle}: {self.get_status_display()}"

class ServiceReminder(models.Model):
	vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='service_reminders')
	service_task = models.CharField(max_length=255, help_text="e.g. Oil Change, General Service")
	interval_km = models.PositiveIntegerField(help_text="e.g. 10000")
	last_service_km = models.PositiveIntegerField()
	is_active = models.BooleanField(default=True)
	notes = models.TextField(blank=True)

	@property
	def due_km(self):
		return self.last_service_km + self.interval_km

	@property
	def is_due(self):
		return self.vehicle.current_km >= self.due_km
		
	@property
	def km_until_due(self):
		return max(0, self.due_km - self.vehicle.current_km)
		
	def __str__(self):
		return f"{self.service_task} for {self.vehicle}"

class InsuranceClaim(models.Model):
	STATUSES = [
		('pending', 'Pending Survey'),
		('surveyed', 'Surveyed'),
		('approved', 'Approved / Processing'),
		('rejected', 'Rejected'),
		('settled', 'Settled')
	]
	vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='insurance_claims')
	date_of_accident = models.DateField()
	fir_number = models.CharField(max_length=255, blank=True)
	surveyor_name = models.CharField(max_length=255, blank=True)
	surveyor_phone = models.CharField(max_length=50, blank=True)
	
	estimated_repair_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
	claimed_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
	approved_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
	
	status = models.CharField(max_length=50, choices=STATUSES, default='pending')
	notes = models.TextField(blank=True)
	
	@property
	def out_of_pocket_expense(self):
		if self.status == 'settled':
			return max(0, self.estimated_repair_cost - self.approved_amount)
		return 0

	def __str__(self):
		return f"Claim for {self.vehicle} on {self.date_of_accident}"

class AssetRotationLog(models.Model):
	asset = models.ForeignKey(VehicleAsset, on_delete=models.CASCADE, related_name='rotation_logs')
	date = models.DateField()
	odometer = models.PositiveIntegerField()
	from_position = models.CharField(max_length=50, choices=VehicleAsset.POSITIONS)
	to_position = models.CharField(max_length=50, choices=VehicleAsset.POSITIONS)
	mechanic_notes = models.TextField(blank=True)

	def clean(self):
		from django.core.exceptions import ValidationError
		if hasattr(self, 'asset') and self.asset and self.asset.status in ['scrapped', 'sold']:
			raise ValidationError("Cannot rotate an asset that has been scrapped or sold.")

	def save(self, *args, **kwargs):
		super().save(*args, **kwargs)
		if self.asset.position != self.to_position:
			self.asset.position = self.to_position
			self.asset.save(update_fields=['position'])

	def __str__(self):
		return f"Rotated {self.asset} from {self.get_from_position_display()} to {self.get_to_position_display()}"


def generate_inspection_number():
	from django.utils import timezone
	import random
	ts = timezone.now().strftime('%Y%m%d%H%M')
	rn = random.randint(100, 999)
	return f"INSP-{ts}-{rn}"


class PreTripInspectionChecklist(models.Model):
	STATUS_CHOICES = [
		('passed', 'Passed - Fit for Operation'),
		('conditional_pass', 'Conditional Pass - Minor Issue Noted'),
		('failed', 'Failed - Safety Risk / Vehicle Grounded'),
	]

	inspection_number = models.CharField(max_length=50, unique=True, default=generate_inspection_number)
	vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='pre_trip_inspections')
	driver = models.ForeignKey('core.Driver', on_delete=models.CASCADE, related_name='pre_trip_inspections')
	trip = models.ForeignKey('operations.Trip', on_delete=models.SET_NULL, null=True, blank=True, related_name='inspections')
	contract_trip = models.ForeignKey('fleet_contracts.ContractTripLog', on_delete=models.SET_NULL, null=True, blank=True, related_name='inspections')
	inspection_date = models.DateTimeField(default=models.functions.datetime.timezone.now if hasattr(models.functions, 'datetime') else timezone.now)
	odometer_reading = models.PositiveIntegerField(help_text="Current vehicle odometer (KM)")
	odometer_photo = models.FileField(upload_to='inspections/odometer/', null=True, blank=True)

	# 1. Critical Mechanical & Fluid Checks
	tyres_tread_and_pressure = models.BooleanField(default=True, verbose_name="Tyres Condition & Air Pressure OK")
	brakes_functional = models.BooleanField(default=True, verbose_name="Foot Brakes & Handbrake Functional")
	engine_oil_level = models.BooleanField(default=True, verbose_name="Engine Oil Level Normal")
	coolant_level = models.BooleanField(default=True, verbose_name="Radiator Coolant Level Normal")
	brake_fluid_level = models.BooleanField(default=True, verbose_name="Brake Fluid Level Normal")
	battery_and_wiring = models.BooleanField(default=True, verbose_name="Battery Terminals & Starting OK")

	# 2. Lights & Visibility Checks
	headlights_and_highbeam = models.BooleanField(default=True, verbose_name="Headlights & High Beam OK")
	taillights_and_brakelights = models.BooleanField(default=True, verbose_name="Tail Lights & Brake Lights OK")
	indicators_and_hazard = models.BooleanField(default=True, verbose_name="Turn Indicators & Hazard Lights OK")
	wipers_and_washer_fluid = models.BooleanField(default=True, verbose_name="Wipers & Washer Fluid OK")
	horn_and_mirrors = models.BooleanField(default=True, verbose_name="Horn & Rear-view Mirrors OK")

	# 3. Mandatory Safety & Emergency Gear
	first_aid_kit_present = models.BooleanField(default=True, verbose_name="First Aid Kit Present & Stocked")
	fire_extinguisher_present = models.BooleanField(default=True, verbose_name="Fire Extinguisher Valid & Present")
	spare_wheel_and_jack = models.BooleanField(default=True, verbose_name="Spare Wheel, Jack & Tool Kit Present")
	ac_or_fans_working = models.BooleanField(default=True, verbose_name="AC / Blower Fans Working")
	cabin_cleanliness = models.BooleanField(default=True, verbose_name="Cabin & Passenger Seats Clean")

	# 4. Defect Escalation & Status
	has_visible_body_scratches = models.BooleanField(default=False, verbose_name="Visible Exterior Scratches/Dents")
	exterior_condition_notes = models.TextField(blank=True, help_text="Notes on exterior condition / dents")
	defect_notes = models.TextField(blank=True, help_text="Notes on failed safety or fluid items")
	defect_ticket = models.ForeignKey('maintenance.DefectTicket', on_delete=models.SET_NULL, null=True, blank=True, related_name='originated_from_inspection')
	overall_status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='passed')
	driver_signature_name = models.CharField(max_length=150, help_text="Name of driver completing inspection")
	supervisor_approved = models.BooleanField(default=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-inspection_date']
		verbose_name = "Pre-Trip Inspection Checklist"
		verbose_name_plural = "Pre-Trip Inspection Checklists"

	def auto_evaluate_status(self):
		critical_passed = (
			self.brakes_functional and 
			self.tyres_tread_and_pressure and 
			self.engine_oil_level and 
			self.coolant_level and 
			self.headlights_and_highbeam and 
			self.taillights_and_brakelights
		)
		if not critical_passed:
			self.overall_status = 'failed'
		elif not (self.first_aid_kit_present and self.fire_extinguisher_present and self.wipers_and_washer_fluid and self.spare_wheel_and_jack):
			self.overall_status = 'conditional_pass'
		else:
			self.overall_status = 'passed'

	def save(self, *args, **kwargs):
		from django.utils import timezone
		if self.vehicle and self.odometer_reading:
			if self.odometer_reading > (self.vehicle.current_km or 0):
				self.vehicle.current_km = self.odometer_reading
				self.vehicle.save(update_fields=['current_km'])

		if self.overall_status == 'failed' and not self.defect_ticket:
			desc = f"Pre-Trip Inspection {self.inspection_number} FAILED for vehicle {self.vehicle.registration_number}.\n"
			if not self.brakes_functional: desc += "- Brakes not functional\n"
			if not self.tyres_tread_and_pressure: desc += "- Tyres tread/pressure unsafe\n"
			if not self.engine_oil_level: desc += "- Engine oil level low/abnormal\n"
			if not self.coolant_level: desc += "- Coolant level low/leak\n"
			if not self.headlights_and_highbeam: desc += "- Headlights defective\n"
			if not self.taillights_and_brakelights: desc += "- Brake lights defective\n"
			if self.defect_notes: desc += f"Driver Notes: {self.defect_notes}\n"

			ticket = DefectTicket.objects.create(
				vehicle=self.vehicle,
				reported_by=self.driver.name if self.driver else "Driver Inspection",
				date_reported=self.inspection_date.date() if self.inspection_date else timezone.now().date(),
				description=desc,
				status='open',
				notes=f"Auto-generated by Pre-Trip Inspection #{self.inspection_number}"
			)
			self.defect_ticket = ticket

		super().save(*args, **kwargs)

	def __str__(self):
		return f"{self.inspection_number} - {self.vehicle} ({self.get_overall_status_display()})"

