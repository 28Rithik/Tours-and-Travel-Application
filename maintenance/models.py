from decimal import Decimal
from django.db import models
from django.utils import timezone
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
		indexes = [
			models.Index(fields=['vehicle', 'document_type', 'expiry_date'], name='idx_comp_veh_doc_exp'),
			models.Index(fields=['expiry_date'], name='idx_comp_exp'),
		]

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
		indexes = [
			models.Index(fields=['vehicle', 'status', 'date'], name='idx_srv_veh_status_date'),
			models.Index(fields=['vehicle', 'date'], name='idx_srv_veh_date'),
		]

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

	# Phase 6: Tire & Asset Engineering Specifications
	brand = models.CharField(max_length=100, blank=True, help_text="e.g. Apollo, MRF, Bridgestone, Michelin, Exide")
	model_or_size = models.CharField(max_length=100, blank=True, help_text="e.g. 215/75 R15, 295/80 R22.5, 12V 100Ah")
	dot_code = models.CharField(max_length=20, blank=True, help_text="DOT manufacture code e.g. 2423")
	original_tread_depth_mm = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('12.00'), help_text="Brand new tread depth in mm")
	current_tread_depth_mm = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('12.00'), help_text="Latest measured tread depth in mm")
	psi_pressure = models.PositiveIntegerField(null=True, blank=True, help_text="Current cold inflation PSI")
	retread_count = models.PositiveIntegerField(default=0, help_text="Number of retread cycles completed")
	max_retread_cycles = models.PositiveIntegerField(default=2, help_text="Max retreadings allowed before scrap")
	last_inspected_date = models.DateField(null=True, blank=True)
	last_inspected_odometer = models.PositiveIntegerField(null=True, blank=True)
	
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

	@property
	def tread_wear_percent(self):
		if not self.original_tread_depth_mm or self.original_tread_depth_mm <= 0:
			return 0.0
		worn = max(Decimal('0.00'), self.original_tread_depth_mm - (self.current_tread_depth_mm or self.original_tread_depth_mm))
		pct = (worn / self.original_tread_depth_mm) * Decimal('100.0')
		return float(round(pct, 1))

	@property
	def is_critical_tread(self):
		if self.asset_type != 'tyre':
			return False
		return (self.current_tread_depth_mm or Decimal('12.00')) <= Decimal('2.50')

	@property
	def is_warning_tread(self):
		if self.asset_type != 'tyre':
			return False
		td = self.current_tread_depth_mm or Decimal('12.00')
		return Decimal('2.50') < td <= Decimal('4.00')

	@property
	def cost_per_km(self):
		if not self.purchase_price or self.purchase_price <= 0:
			return Decimal('0.00')
		run = max(self.current_run_km, 1)
		return (Decimal(str(self.purchase_price)) / Decimal(str(run))).quantize(Decimal('0.01'))

	@property
	def health_status(self):
		if self.status != 'in_use':
			return self.status
		if self.is_critical_tread or self.needs_replacement:
			return 'critical'
		if self.is_warning_tread or (self.expected_life_km and self.current_run_km >= (self.expected_life_km * 0.75)):
			return 'warning'
		return 'good'


class TireInspectionLog(models.Model):
	ACTION_CHOICES = [
		('none', 'Routine Inspection (No Action)'),
		('pressure_adjusted', 'Cold Pressure Adjusted'),
		('rotated', 'Position Rotated'),
		('sent_retread', 'Sent for Retreading'),
		('scrapped', 'Condemned & Scrapped'),
	]

	asset = models.ForeignKey(VehicleAsset, on_delete=models.CASCADE, related_name='inspections')
	inspection_date = models.DateField(default=timezone.now)
	odometer = models.PositiveIntegerField(help_text="Vehicle odometer at inspection")
	tread_depth_mm = models.DecimalField(max_digits=5, decimal_places=2, help_text="Measured tread depth in mm")
	psi_pressure = models.PositiveIntegerField(null=True, blank=True, help_text="Cold inflation pressure PSI")
	inspector_name = models.CharField(max_length=100, blank=True)
	has_irregular_wear = models.BooleanField(default=False, help_text="Check if feathering, camber, or cupping detected")
	action_taken = models.CharField(max_length=30, choices=ACTION_CHOICES, default='none')
	condition_notes = models.TextField(blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-inspection_date', '-id']
		verbose_name = 'Tire Inspection Log'
		verbose_name_plural = 'Tire Inspection Logs'

	def __str__(self):
		return f"{self.asset.serial_number} - {self.tread_depth_mm}mm on {self.inspection_date}"


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


# ==============================================================================
# INTERACTIVE 2D VEHICLE DAMAGE MARKER & RENTAL INSPECTION MODELS
# ==============================================================================

def generate_damage_inspection_number():
	import random
	from django.utils import timezone
	ts = timezone.now().strftime('%Y%m%d%H%M')
	rn = random.randint(100, 999)
	return f"DMG-{ts}-{rn}"


class VehicleDamageInspection(models.Model):
	INSPECTION_TYPES = [
		('checkout', 'Departure / Check-out Handover'),
		('checkin', 'Return / Check-in Handover'),
		('routine', 'Depot Routine Inspection / Audit'),
	]
	BODY_STYLES = [
		('suv', 'SUV (Innova Crysta / Ertiga)'),
		('sedan', 'Sedan (Dzire / Etios)'),
		('tempo', 'Tempo Traveller (12/17/26 Seater)'),
		('bus', 'Coach Bus / Volvo Multi-Axle'),
	]
	DEPOSIT_STATUSES = [
		('none', 'No Deposit Held'),
		('held', 'Security Deposit Held'),
		('settled_refund', 'Settled - Full Refund Issued'),
		('settled_deduction', 'Settled - Damage Deducted & Balance Refunded'),
		('forfeited', 'Forfeited / Unsettled Dispute'),
	]

	inspection_number = models.CharField(max_length=50, unique=True, default=generate_damage_inspection_number)
	vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='damage_inspections')
	trip = models.ForeignKey('operations.Trip', on_delete=models.SET_NULL, null=True, blank=True, related_name='damage_inspections')
	booking = models.ForeignKey('operations.Booking', on_delete=models.SET_NULL, null=True, blank=True, related_name='damage_inspections')

	customer_name = models.CharField(max_length=150, blank=True, help_text="Guest or self-drive renter name")
	customer_phone = models.CharField(max_length=30, blank=True)
	inspection_type = models.CharField(max_length=20, choices=INSPECTION_TYPES, default='checkout')
	vehicle_body_style = models.CharField(max_length=20, choices=BODY_STYLES, default='suv')

	odometer_reading = models.PositiveIntegerField(default=0, help_text="Odometer reading in KM")
	fuel_level_percent = models.PositiveIntegerField(default=100, help_text="Fuel gauge percentage (0-100%)")
	cleanliness_interior = models.PositiveSmallIntegerField(default=5, help_text="Interior cleanliness 1-5")
	cleanliness_exterior = models.PositiveSmallIntegerField(default=5, help_text="Exterior cleanliness 1-5")

	# Baseline checkout reference for automatic Diff comparison
	baseline_checkout = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='return_inspections', help_text="Linked checkout inspection to calculate damage diff")

	# Security Deposit & Damage Financials
	security_deposit_held = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="Deposit collected before handover (₹)")
	new_damage_deductions = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="Total estimated deductions for new damages (₹)")
	deposit_refund_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="Net refund amount to customer (₹)")
	deposit_status = models.CharField(max_length=30, choices=DEPOSIT_STATUSES, default='none')

	inspector_name = models.CharField(max_length=150, blank=True, help_text="Staff or driver conducting inspection")
	customer_signature_data = models.TextField(blank=True, help_text="Base64 canvas signature of customer")
	inspector_signature_data = models.TextField(blank=True, help_text="Base64 canvas signature of inspector")
	notes = models.TextField(blank=True, help_text="General handover observations")
	created_at = models.DateTimeField(auto_now_add=True, db_index=True)

	class Meta:
		ordering = ['-created_at']
		verbose_name = "Vehicle Damage Inspection"
		verbose_name_plural = "Vehicle Damage Inspections"

	def __str__(self):
		return f"{self.inspection_number} - {self.vehicle.registration_number} ({self.get_inspection_type_display()})"

	def compute_damage_totals(self):
		"""Computes total cost of new damage markers and recalculates refund."""
		new_markers = self.markers.filter(is_new_damage=True)
		total_new = sum(m.estimated_repair_cost for m in new_markers)
		self.new_damage_deductions = total_new
		if self.security_deposit_held > 0:
			self.deposit_refund_amount = max(0.00, float(self.security_deposit_held) - float(total_new))
			if total_new > 0:
				self.deposit_status = 'settled_deduction'
			else:
				self.deposit_status = 'settled_refund'
		self.save(update_fields=['new_damage_deductions', 'deposit_refund_amount', 'deposit_status'])


class VehicleDamageMarker(models.Model):
	DAMAGE_TYPES = [
		('scratch', 'Scratch / Paint Abrasion'),
		('dent', 'Dent / Body Depression'),
		('crack', 'Crack / Fracture / Puncture'),
		('paint_chip', 'Paint Chip / Peeling'),
		('broken_glass', 'Broken Light / Glass'),
		('missing_accessory', 'Missing Accessory / Spare Wheel'),
		('interior_tear', 'Interior Tear / Burn / Stain'),
		('other', 'Other Exterior Blemish'),
	]
	SEVERITY_LEVELS = [
		('minor', 'Minor (Surface / Polishable / < 2 in)'),
		('moderate', 'Moderate (Noticeable Dent / Deep Scratch)'),
		('severe', 'Severe (Panel Replacement / Structural)'),
	]
	PANEL_ZONES = [
		('front_bumper', 'Front Bumper'),
		('rear_bumper', 'Rear Bumper'),
		('hood', 'Engine Hood / Bonnet'),
		('roof', 'Roof Panel'),
		('windshield', 'Front Windshield'),
		('rear_windshield', 'Rear Windshield'),
		('door_fl', 'Front Left Door'),
		('door_fr', 'Front Right Door'),
		('door_rl', 'Rear Left Door'),
		('door_rr', 'Rear Right Door'),
		('quarter_panel_l', 'Left Quarter Panel / Fender'),
		('quarter_panel_r', 'Right Quarter Panel / Fender'),
		('mirror_l', 'Left Wing Mirror'),
		('mirror_r', 'Right Wing Mirror'),
		('trunk', 'Trunk / Boot Lid / Tailgate'),
		('wheel_rim', 'Wheel Rim / Alloy'),
		('interior', 'Interior / Seats'),
	]

	inspection = models.ForeignKey(VehicleDamageInspection, on_delete=models.CASCADE, related_name='markers')
	marker_number = models.PositiveIntegerField(default=1)
	damage_type = models.CharField(max_length=30, choices=DAMAGE_TYPES, default='scratch')
	severity = models.CharField(max_length=20, choices=SEVERITY_LEVELS, default='minor')
	panel_zone = models.CharField(max_length=30, choices=PANEL_ZONES, default='front_bumper')

	# Pinpoint coordinates on vehicle 2D schematic (percentage 0.00 to 100.00%)
	x_percent = models.DecimalField(max_digits=5, decimal_places=2, default=50.00)
	y_percent = models.DecimalField(max_digits=5, decimal_places=2, default=50.00)
	view_angle = models.CharField(max_length=20, default='top')

	is_pre_existing = models.BooleanField(default=False, help_text="True if present prior to customer checkout")
	is_new_damage = models.BooleanField(default=False, help_text="True if inflicted during trip / checkout duration")
	estimated_repair_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

	photo = models.ImageField(upload_to='damage_markers/photos/', null=True, blank=True)
	photo_data_url = models.TextField(blank=True, help_text="Base64 captured photo from mobile camera")
	notes = models.CharField(max_length=255, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['marker_number']
		verbose_name = "Vehicle Damage Marker"
		verbose_name_plural = "Vehicle Damage Markers"

	def __str__(self):
		return f"#{self.marker_number} {self.get_damage_type_display()} on {self.get_panel_zone_display()} ({self.inspection.vehicle.registration_number})"

