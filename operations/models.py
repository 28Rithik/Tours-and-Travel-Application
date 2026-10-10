from decimal import Decimal
from django.db import models
from django.utils import timezone
from django.core.serializers.json import DjangoJSONEncoder
from core.models import Cleaner, Party, Driver, Vehicle, Client


class Booking(models.Model):
	JOURNEY_TYPES = [('local', 'Local'), ('outstation', 'Outstation'), ('airport', 'Airport'), ('one_way', 'One way'), ('round_trip', 'Round trip')]
	STATUS_CHOICES = [('pending', 'Pending'), ('confirmed', 'Confirmed'), ('completed', 'Completed'), ('cancelled', 'Cancelled')]
	HOTEL_CONFIRMATION_CHOICES = [('pending', 'Pending'), ('confirmed', 'Confirmed'), ('changed', 'Changed')]
	HOTEL_PAID_BY_CHOICES = [('company', 'Included in Package (We Pay)'), ('customer', 'Customer Pays Directly')]
	BILLING_TYPES = [('km', 'Per KM'), ('day', 'Per Day'), ('package', 'Fixed Package')]
	PAYMENT_TERMS_CHOICES = [('default', 'Use Client Default'), ('trip', 'Trip-by-trip'), ('weekly', 'Weekly'), ('fortnightly', 'Fortnightly'), ('monthly', 'Monthly'), ('bimonthly', 'Bi-monthly (Every 2 Months)'), ('quarterly', 'Quarterly (Every 3 Months)')]
	
	# Customer Details
	booking_number = models.CharField(max_length=30, unique=True, blank=True)
	party = models.ForeignKey(Client, on_delete=models.PROTECT, related_name='bookings')
	guest_name = models.CharField(max_length=255)
	guest_phone = models.CharField(max_length=30, blank=True)
	booking_date = models.DateField(auto_now_add=True)
	
	# Journey Details
	pickup_location = models.CharField(max_length=255)
	destination = models.CharField(max_length=255)
	pickup_date = models.DateField()
	pickup_time = models.TimeField()
	reporting_time = models.TimeField(null=True, blank=True, help_text="Time the driver needs to report")
	drop_date = models.DateField(null=True, blank=True)
	travel_pnr = models.CharField(max_length=50, blank=True, help_text="Flight/Train PNR or details")
	
	# Vehicle & Journey Reqs
	journey_type = models.CharField(max_length=20, choices=JOURNEY_TYPES)
	vehicle_type = models.ForeignKey('core.VehicleType', on_delete=models.PROTECT, null=True, blank=True)
	pax_count = models.PositiveIntegerField(null=True, blank=True, help_text="Number of passengers")
	luggage_count = models.PositiveIntegerField(null=True, blank=True, help_text="Number of luggage pieces")
	special_requirements = models.TextField(blank=True)
	
	# Financials
	billing_type = models.CharField(max_length=20, choices=BILLING_TYPES, default='package')
	quoted_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
	payment_terms_override = models.CharField(max_length=20, choices=Party.BILLING_CYCLES, null=True, blank=True)
	expected_km = models.PositiveIntegerField(null=True, blank=True, help_text="Estimated KMs or Package limit")
	gst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
	
	# Itinerary & Status
	package = models.ForeignKey('packages.Package', on_delete=models.SET_NULL, null=True, blank=True, related_name='bookings')
	package_inventory = models.ForeignKey('packages.PackageInventory', on_delete=models.SET_NULL, null=True, blank=True, related_name='bookings')
	plan_details = models.TextField(blank=True)
	status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="Booking Status")
	hotel_confirmation_status = models.CharField(max_length=20, choices=HOTEL_CONFIRMATION_CHOICES, default='pending')
	hotel_paid_by = models.CharField(max_length=20, choices=HOTEL_PAID_BY_CHOICES, default='company')
	notes = models.TextField(blank=True)

	class Meta:
		constraints = [
			models.CheckConstraint(
				check=models.Q(drop_date__isnull=True) | models.Q(pickup_date__isnull=True) | models.Q(drop_date__gte=models.F('pickup_date')),
				name='booking_drop_date_gte_pickup_date'
			),
			models.CheckConstraint(
				check=models.Q(quoted_price__isnull=True) | models.Q(quoted_price__gte=0),
				name='booking_quoted_price_non_negative'
			),
		]
		indexes = [
			models.Index(fields=['status', 'pickup_date'], name='idx_bk_status_pickup'),
			models.Index(fields=['party', 'booking_date'], name='idx_bk_party_date'),
			models.Index(fields=['booking_date'], name='idx_bk_date'),
		]

	def __str__(self):
		return self.booking_number

	@property
	def advance_received(self):
		from finance.models import Payment
		payment_total = Payment.objects.filter(booking=self, payment_type='customer_receipt').aggregate(total=models.Sum('amount'))['total']
		return payment_total or 0

	def clean(self):
		from django.core.exceptions import ValidationError
		if self.drop_date and self.pickup_date and self.drop_date < self.pickup_date:
			raise ValidationError({'drop_date': 'Drop date cannot be before pickup date.'})

	def save(self, *args, **kwargs):
		if not self.booking_number:
			last_booking = Booking.objects.order_by('-id').first()
			next_number = (last_booking.id + 1) if last_booking else 1
			self.booking_number = f'BK-{next_number:04d}'
		super().save(*args, **kwargs)
		# Auto-sync package inventory seat count whenever a booking is saved
		if self.package_inventory_id:
			sync_package_inventory_seats(self.package_inventory)


def sync_package_inventory_seats(inv):
	if not inv:
		return
	try:
		pax_sum = Booking.objects.filter(
			package_inventory=inv
		).exclude(status='cancelled').aggregate(total=models.Sum('pax_count'))['total']
		booked = pax_sum if pax_sum is not None else Booking.objects.filter(
			package_inventory=inv
		).exclude(status='cancelled').count()
		inv.booked_seats = booked
		inv.available_seats = max(0, inv.total_seats - booked)
		if inv.available_seats == 0 and inv.status == 'open':
			inv.status = 'sold_out'
		elif inv.available_seats <= 5 and inv.status == 'open':
			inv.status = 'fast_filling'
		elif inv.available_seats > 5 and inv.status in ['sold_out', 'fast_filling']:
			inv.status = 'open'
		inv.save(update_fields=['booked_seats', 'available_seats', 'status'])
	except Exception:
		pass


from django.db.models.signals import post_delete
from django.dispatch import receiver

@receiver(post_delete, sender=Booking)
def on_booking_deleted(sender, instance, **kwargs):
	if instance.package_inventory_id:
		sync_package_inventory_seats(instance.package_inventory)


class Trip(models.Model):
	STATUSES = [('booked', 'Booked'), ('assigned', 'Assigned'), ('driver_confirmed', 'Driver confirmed'), ('started', 'Started'), ('completed', 'Completed'), ('billed', 'Billed'), ('settled', 'Settled'), ('cancelled', 'Cancelled')]
	BILLING_MODELS = [('km', 'Kilometre'), ('day', 'Day'), ('day_km', 'Day + kilometre'), ('fixed', 'Fixed'), ('custom', 'Custom')]
	HOTEL_CONFIRMATION_CHOICES = [('pending', 'Pending'), ('confirmed', 'Confirmed'), ('changed', 'Changed')]
	HOTEL_PAID_BY_CHOICES = [('company', 'Included in Package (We Pay)'), ('customer', 'Customer Pays Directly')]
	trip_id = models.CharField(max_length=30, unique=True, blank=True)
	booking = models.ForeignKey(Booking, on_delete=models.PROTECT, related_name='trips', null=True, blank=True)
	bulk_contract_day = models.ForeignKey('BulkContractDay', on_delete=models.PROTECT, related_name='trips', null=True, blank=True)
	party = models.ForeignKey(Party, on_delete=models.PROTECT, related_name='trips', null=True, blank=True)
	guest_name = models.CharField(max_length=255, null=True, blank=True)
	travel_pnr = models.CharField(max_length=50, blank=True, help_text="Flight/Train PNR")
	pax_count = models.PositiveIntegerField(null=True, blank=True, help_text="Number of passengers")
	luggage_count = models.PositiveIntegerField(null=True, blank=True, help_text="Number of luggage pieces")
	package = models.ForeignKey('packages.Package', on_delete=models.SET_NULL, null=True, blank=True, related_name='trips')
	package_inventory = models.ForeignKey('packages.PackageInventory', on_delete=models.SET_NULL, null=True, blank=True, related_name='trips')
	vehicle = models.ForeignKey(Vehicle, on_delete=models.SET_NULL, null=True, blank=True, related_name='trips')
	driver = models.ForeignKey(Driver, on_delete=models.SET_NULL, null=True, blank=True, related_name='trips')
	status = models.CharField(max_length=30, choices=STATUSES, default='booked')
	start_date = models.DateField(null=True, blank=True)
	end_date = models.DateField(null=True, blank=True)
	start_time = models.TimeField(null=True, blank=True)
	end_time = models.TimeField(null=True, blank=True)
	opening_km = models.PositiveIntegerField(null=True, blank=True)
	closing_km = models.PositiveIntegerField(null=True, blank=True)
	billing_model = models.CharField(max_length=20, choices=BILLING_MODELS, default='day_km')
	day_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
	km_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
	fixed_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
	days_count = models.PositiveIntegerField(default=1)
	driver_bata = models.DecimalField(max_digits=10, decimal_places=2, default=0)
	driver_bata_breakdown = models.JSONField(default=dict, blank=True, encoder=DjangoJSONEncoder, help_text="Detailed itemization of driver allowances: base bata, night halt, early morning, overtime, outstation")
	commission = models.DecimalField(max_digits=10, decimal_places=2, default=0)
	partner_handover_notes = models.TextField(blank=True)
	notes = models.TextField(blank=True)
	tracking_token = models.CharField(max_length=64, unique=True, blank=True, null=True, db_index=True)

	# WhatsApp & Driver Handover Digital Twin
	opening_odometer_photo = models.ImageField(upload_to='trip_odometers/opening/', null=True, blank=True, help_text="Start duty photo of vehicle odometer")
	closing_odometer_photo = models.ImageField(upload_to='trip_odometers/closing/', null=True, blank=True, help_text="End duty photo of vehicle odometer")
	driver_handover_status = models.CharField(
		max_length=25,
		choices=[
			('pending', 'Pending Start Handover'),
			('started', 'Trip Started & Handover Verified'),
			('ended', 'Trip Ended & Handover Submitted'),
			('approved', 'Handover Audit Approved'),
			('flagged', 'Handover Discrepancy Flagged')
		],
		default='pending',
		help_text="Digital vehicle handover audit workflow state"
	)
	whatsapp_broadcast_count = models.PositiveIntegerField(default=0, help_text="Count of automated WhatsApp broadcasts sent for this trip")

	# 7-Milestone Tour Lifecycle Digital Twin
	TOUR_MILESTONES = [
		('car_pickup', '1. Car Pickup'),
		('driver_reached', '2. Driver Reached'),
		('guest_pickup', '3. Guest Pickup & PIN'),
		('on_trip', '4. On Trip'),
		('guest_drop', '5. Guest Drop'),
		('expenses_photo', '6. Expenses Photo'),
		('car_drop', '7. Car Drop'),
	]
	pickup_pin = models.CharField(max_length=6, blank=True, help_text="Secure 4-digit passenger verification PIN")
	is_pin_verified = models.BooleanField(default=False, help_text="True once passenger 4-digit PIN is verified")
	current_milestone = models.CharField(
		max_length=30,
		choices=TOUR_MILESTONES,
		default='car_pickup',
		help_text="Current stage in the 7-milestone tour lifecycle"
	)
	car_pickup_at = models.DateTimeField(null=True, blank=True)
	driver_reached_at = models.DateTimeField(null=True, blank=True)
	guest_pickup_at = models.DateTimeField(null=True, blank=True)
	on_trip_at = models.DateTimeField(null=True, blank=True)
	guest_drop_at = models.DateTimeField(null=True, blank=True)
	expenses_photo_at = models.DateTimeField(null=True, blank=True)
	car_drop_at = models.DateTimeField(null=True, blank=True)
	driver_handover_at = models.DateTimeField(null=True, blank=True, help_text="Timestamp of latest handover action")
	customer_signature_data = models.TextField(blank=True, help_text="Base64 DataURL PNG of customer digital signature")
	customer_signature_at = models.DateTimeField(null=True, blank=True, help_text="Timestamp when customer signed on driver's mobile device")
	guest_rating = models.PositiveSmallIntegerField(null=True, blank=True, help_text="Customer satisfaction rating 1 to 5 stars")
	guest_feedback = models.TextField(blank=True, help_text="Customer satisfaction feedback remarks")

	@property
	def milestone_index(self):
		mapping = {
			'car_pickup': 1,
			'driver_reached': 2,
			'guest_pickup': 3,
			'on_trip': 4,
			'guest_drop': 5,
			'expenses_photo': 6,
			'car_drop': 7,
		}
		return mapping.get(self.current_milestone, 1)

	@property
	def milestone_progress_percent(self):
		return int((self.milestone_index / 7.0) * 100)

	@property
	def lifecycle_url(self):
		return f"/trip/{self.pk}/lifecycle/"

	@property
	def handover_url(self):
		return f"/trip/{self.pk}/handover/"

	@property
	def tracking_url(self):
		return f"/track/{self.tracking_token}/" if self.tracking_token else ""

	@property
	def itinerary_builder_url(self):
		return f"/admin/operations/trip/{self.pk}/itinerary-builder/"

	@property
	def guest_itinerary_url(self):
		if self.tracking_token:
			return f"/tour/itinerary/{self.tracking_token}/"
		return f"/trip/{self.pk}/itinerary/"

	@property
	def active_itinerary_day(self):
		days = list(self.itinerary_days.all())
		if not days:
			return None
		from django.utils import timezone
		today = timezone.localtime().date()
		for d in days:
			if d.date == today or d.is_active_today:
				return d
		return days[0]

	def import_package_itinerary(self, package=None):
		from datetime import timedelta
		pkg = package or self.package
		if not pkg:
			return 0
		pkg_days = pkg.itinerary_days.all().order_by('day_number')
		if not pkg_days.exists():
			return 0
		self.itinerary_days.all().delete()
		created_count = 0
		start = self.start_date
		for pkg_day in pkg_days:
			day_num = pkg_day.day_number
			cal_date = None
			if start:
				cal_date = start + timedelta(days=max(0, day_num - 1))
			TripItineraryDay.objects.create(
				trip=self,
				day_number=day_num,
				date=cal_date,
				title=pkg_day.title or f"Day {day_num} Tour",
				route_segment=pkg_day.route_segment or "",
				morning_plan=pkg_day.morning_activity or pkg_day.activities or "",
				sightseeing_spots=pkg_day.sightseeing_spots or "",
				evening_plan=pkg_day.evening_night_activity or "",
				night_stay_location=pkg_day.night_stay_location or "",
				hotel_name=pkg_day.hotel_info or "",
				hotel_booking_status='pending',
				meals_included=pkg_day.meals_included or "Breakfast, Lunch, Dinner",
				transport_mode=pkg_day.transport_info or "",
			)
			created_count += 1
		if created_count > self.days_count:
			self.days_count = created_count
			self.save(update_fields=['days_count'])
		return created_count

	@property
	def pickup_location(self):
		return self.booking.pickup_location if self.booking else ""

	@property
	def destination(self):
		return self.booking.destination if self.booking else ""

	@property
	def first_hotel(self):
		if self.pk:
			return self.hotels.first()
		return None

	@property
	def customer_confirmation_message(self):
		amount = self.fixed_amount or 0
		balance = max(amount - self.received_amount, 0)
		hotel_obj = self.first_hotel
		hotel_str = hotel_obj.hotel_name if hotel_obj else "To be confirmed"
		hotel_status_str = hotel_obj.get_confirmation_status_display() if hotel_obj else "Pending"
		tracking_line = f"- Live GPS Vehicle Tracking: http://127.0.0.1:8000/track/{self.tracking_token}/\n" if self.tracking_token else ""
		guest = self.guest_name or (self.booking.guest_name if self.booking else "Valued Guest")
		pickup_loc = self.booking.pickup_location if self.booking else "TBD"
		dest = self.booking.destination if self.booking else "TBD"
		p_date = self.booking.pickup_date if self.booking else "TBD"
		p_time = self.booking.pickup_time if self.booking else "TBD"
		veh = self.vehicle or (self.booking.vehicle_type if self.booking else "TBD")
		
		return (
			f'Hello {guest},\n\n'
			+ 'Your trip has been confirmed.\n\n'
			+ f'Details:\n'
			+ f'- Travel dates: {self.start_date or p_date} to {self.end_date or p_date}\n'
			+ f'- Pickup: {self.start_time or p_time}, {pickup_loc}\n'
			+ f'- Destination: {dest}\n'
			+ f'- Vehicle: {veh}\n'
			+ f'- Driver: {self.driver or "To be assigned"}\n'
			+ f'- Hotel: {hotel_str}\n'
			+ f'- Hotel status: {hotel_status_str}\n'
			+ (f'{tracking_line}' if tracking_line else '')
			+ (f'- Guest Security PIN: {self.pickup_pin} (Share with driver at pickup)\n' if self.pickup_pin else '') + '\n'
			+ f'Payment Summary:\n'
			+ f'- Total: Rs. {amount}\n'
			+ f'- Advance paid: Rs. {self.received_amount}\n'
			+ f'- Balance due: Rs. {balance}\n\n'
			+ 'Please keep your phone reachable for pickup coordination.\n'
			+ 'We will confirm the final hotel and driver timing shortly.'
		)

	@property
	def final_bill_message(self):
		amount = self.total_amount or 0
		advance = self.received_amount or 0
		balance = max(amount - advance, 0)
		guest = self.guest_name or (self.booking.guest_name if self.booking else "Valued Guest")
		
		msg = (
			f'Hello {guest},\n\n'
			f'Thank you for traveling with us! Your trip has been completed.\n\n'
			f'*Trip Summary:*\n'
			f'- Dates: {self.start_date} to {self.end_date}\n'
			f'- Vehicle: {self.vehicle or "N/A"}\n'
			f'- Start KM: {self.opening_km or 0}\n'
			f'- End KM: {self.closing_km or 0}\n'
			f'- Total Distance: {self.used_km} KM\n\n'
			f'*Billing Details:*\n'
			f'- Base Trip Rate: Rs. {self.bill_value}\n'
		)
		if self.total_expenses > 0:
			msg += f'- Tolls & Travel Expenses: Rs. {self.total_expenses}\n'
		if self.customer_billable_fines > 0:
			msg += f'- Traffic Violations / Fines (Billed to Passenger): Rs. {self.customer_billable_fines}\n'
		if self.gst_amount > 0:
			msg += f'- GST: Rs. {self.gst_amount}\n'
		msg += (
			f'- Total Bill Value: Rs. {amount}\n'
			f'- Advance Paid: Rs. {advance}\n'
			f'- *Balance Due: Rs. {balance}*\n\n'
			f'Please let us know if you need an official invoice.\n'
			f'We hope to serve you again!'
		)
		return msg

	@property
	def handover_message(self):
		hotel_obj = self.first_hotel
		hotel_line = hotel_obj.hotel_name if hotel_obj else '[Hotel pending]'
		hotel_status = hotel_obj.get_confirmation_status_display() if hotel_obj else "Pending"
		guest = self.guest_name or (self.booking.guest_name if self.booking else "Valued Guest")
		pickup_loc = self.booking.pickup_location if self.booking else "TBD"
		dest = self.booking.destination if self.booking else "TBD"
		p_date = self.booking.pickup_date if self.booking else "TBD"
		p_time = self.booking.pickup_time if self.booking else "TBD"
		guest_ph = self.booking.guest_phone if self.booking and self.booking.guest_phone else "N/A"
		veh = self.vehicle or (self.booking.vehicle_type if self.booking else "TBD")
		
		message = [
			'Hello Team,',
			'',
			f'Please note the below trip assignment for {guest}.',
			'',
			'Trip Details:',
			f'- Date: {self.start_date or p_date} to {self.end_date or p_date}',
			f'- Vehicle: {veh}',
			f'- Guest Contact: {guest_ph}',
			f'- Pickup: {self.start_time or p_time} AM, {pickup_loc}',
			f'- Route: {pickup_loc} to {dest}',
			f'- Driver: {self.driver or "[Name]"}',
			f'- Hotel: {hotel_line}',
			f'- Hotel Status: {hotel_status}',
			'',
			'Payment:',
			f'- Total: Rs. {self.fixed_amount or "0"}',
			f'- Advance: Rs. {self.received_amount}',
			f'- Balance: Rs. {max((self.fixed_amount or 0) - self.received_amount, 0)}',
			'',
			'Please confirm driver, vehicle, and hotel details.',
		]
		if self.partner_handover_notes:
			message.extend(['', 'Special Instructions:', self.partner_handover_notes])
		return '\n'.join(message)

	@property
	def used_km(self):
		if self.opening_km is None or self.closing_km is None:
			return 0
		return max(0, self.closing_km - self.opening_km)

	@property
	def extra_km(self):
		if self.booking_id and self.booking.expected_km:
			limit = self.booking.expected_km
			return max(0, self.used_km - limit)
		return 0

	@property
	def km_amount(self):
		return Decimal(self.used_km) * self.km_rate

	@property
	def day_amount(self):
		return self.days_count * self.day_rate

	@property
	def bill_value(self):
		if self.billing_model == 'km':
			return self.km_amount
		if self.billing_model == 'day':
			return self.day_amount
		if self.billing_model == 'day_km':
			return self.day_amount + self.km_amount
		return self.fixed_amount

	@property
	def total_expenses(self):
		if not self.pk:
			return Decimal('0')
		if hasattr(self, '_prefetched_objects_cache') and 'expenses' in self._prefetched_objects_cache:
			return sum((expense.amount for expense in self.expenses.all() if expense.billable_to_customer), Decimal('0'))
		return sum((expense.amount for expense in self.expenses.filter(billable_to_customer=True)), Decimal('0'))

	@property
	def customer_billable_fines(self):
		if not self.pk:
			return Decimal('0')
		if hasattr(self, '_prefetched_objects_cache') and 'traffic_fines' in self._prefetched_objects_cache:
			return sum((fine.fine_amount for fine in self.traffic_fines.all() if fine.financial_responsibility == 'customer' and fine.paid_by in ['company', 'unpaid']), Decimal('0'))
		return sum((fine.fine_amount for fine in self.traffic_fines.filter(financial_responsibility='customer', paid_by__in=['company', 'unpaid'])), Decimal('0'))

	@property
	def total_supplier_cost(self):
		if not self.pk:
			return Decimal('0')
		return sum((cost.amount for cost in self.supplier_costs.all()), Decimal('0'))

	@property
	def gst_amount(self):
		rate = Decimal('0')
		if self.booking_id:
			rate = self.booking.gst_rate
		elif self.bulk_contract_day_id:
			rate = self.bulk_contract_day.contract.gst_rate
		taxable = self.bill_value + self.total_expenses + self.customer_billable_fines
		return round(taxable * (rate / Decimal('100')), 2)

	@property
	def total_amount(self):
		return self.bill_value + self.total_expenses + self.customer_billable_fines + self.gst_amount

	@property
	def company_paid_expenses(self):
		if hasattr(self, '_prefetched_objects_cache') and 'expenses' in self._prefetched_objects_cache:
			return sum((expense.amount for expense in self.expenses.all() if expense.paid_by in ['company', 'driver']), Decimal('0'))
		return sum((expense.amount for expense in self.expenses.filter(paid_by__in=['company', 'driver'])), Decimal('0'))

	@property
	def total_fuel_cost(self):
		return sum((f.amount for f in self.fuel_records.all()), Decimal('0'))

	@property
	def is_theft_suspected(self):
		if self.mileage > 0 and self.vehicle.expected_mileage > 0:
			if self.mileage < (self.vehicle.expected_mileage * Decimal('0.8')):
				return True
		return False


	@property
	def net_profit(self):
		revenue = self.total_amount
		cost = self.total_supplier_cost + self.total_fuel_cost + self.company_paid_expenses + self.driver_bata
		return revenue - cost

	@property
	def balance(self):
		return self.total_amount - self.received_amount

	@property
	def received_amount(self):
		from finance.models import Payment

		if not self.pk:
			return Decimal('0')

		payment_total = Payment.objects.filter(trip=self, payment_type='customer_receipt').aggregate(total=models.Sum('amount'))['total']
		if payment_total:
			return payment_total
		if self.booking_id:
			booking_payment_total = Payment.objects.filter(booking_id=self.booking_id, payment_type='customer_receipt').aggregate(total=models.Sum('amount'))['total']
			return booking_payment_total or Decimal('0')
		return Decimal('0')

	def __str__(self):
		return self.trip_id

	def clean(self):
		from django.core.exceptions import ValidationError
		
		if not self.booking_id and not self.bulk_contract_day_id:
			raise ValidationError('A trip must belong to either a Booking or a Bulk Contract Day.')
		if self.booking_id and self.bulk_contract_day_id:
			raise ValidationError('A trip cannot belong to both a Booking and a Bulk Contract Day.')

		if getattr(self, 'booking_id', None) and hasattr(self, 'booking'):
			if not self.start_date: self.start_date = self.booking.pickup_date
			if not self.end_date: self.end_date = self.booking.drop_date or self.start_date
		elif getattr(self, 'bulk_contract_day_id', None) and hasattr(self, 'bulk_contract_day'):
			if not self.start_date: self.start_date = self.bulk_contract_day.date
			if not self.end_date: self.end_date = self.bulk_contract_day.date

		if self.start_date and self.end_date and self.end_date < self.start_date:
			raise ValidationError('The trip end date cannot be before its start date.')
		
		active_statuses = ['assigned', 'driver_confirmed', 'started', 'completed', 'billed', 'settled']
		if self.status in active_statuses:
			if not self.start_date:
				raise ValidationError({'start_date': 'Start date is required for assigned trips.'})
			if not self.end_date:
				raise ValidationError({'end_date': 'End date is required for assigned trips.'})

		if self.opening_km is not None and self.closing_km is not None and self.closing_km < self.opening_km:
			raise ValidationError('Closing kilometres cannot be lower than opening kilometres.')
		
		if self.status in ['completed', 'billed', 'settled'] and self.closing_km is None:
			raise ValidationError({'closing_km': 'Closing kilometres are required to complete or bill a trip.'})

		if self.vehicle_id and self.driver_id:
			if self.vehicle.ownership_type == 'outsourced' and self.driver.driver_type == 'owned':
				raise ValidationError({'driver': 'Cannot assign an owned driver to an outsourced supplier vehicle.'})
			if self.vehicle.ownership_type == 'owned' and self.driver.driver_type == 'supplier':
				raise ValidationError({'driver': 'Cannot assign a supplier driver to an owned vehicle.'})

		if self.booking_id and self.party_id and self.booking.party_id != self.party_id:
			raise ValidationError({'party': 'Trip party must match booking party.'})
		if self.booking_id and self.guest_name and self.guest_name != self.booking.guest_name:
			raise ValidationError({'guest_name': 'Trip guest must match booking guest.'})
		
		if self.start_date and self.end_date:
			from datetime import datetime, time
			s_time = self.start_time or time.min
			e_time = self.end_time or time.max
			my_start = datetime.combine(self.start_date, s_time)
			my_end = datetime.combine(self.end_date, e_time)

			if self.vehicle_id:
				overlapping_vehicles = Trip.objects.filter(
					vehicle=self.vehicle,
					status__in=['assigned', 'driver_confirmed', 'started'],
					start_date__lte=self.end_date,
					end_date__gte=self.start_date
				).exclude(pk=self.pk)
				for conflict in overlapping_vehicles:
					c_s_time = conflict.start_time or time.min
					c_e_time = conflict.end_time or time.max
					c_start = datetime.combine(conflict.start_date, c_s_time)
					c_end = datetime.combine(conflict.end_date, c_e_time)
					if my_start < c_end and my_end > c_start:
						raise ValidationError({'vehicle': f'Conflict! This vehicle is already assigned to active Trip {conflict.trip_id} from {c_start.strftime("%b %d %H:%M")} to {c_end.strftime("%b %d %H:%M")}.'})

			if self.driver_id:
				overlapping_drivers = Trip.objects.filter(
					driver=self.driver,
					status__in=['assigned', 'driver_confirmed', 'started'],
					start_date__lte=self.end_date,
					end_date__gte=self.start_date
				).exclude(pk=self.pk)
				for conflict in overlapping_drivers:
					c_s_time = conflict.start_time or time.min
					c_e_time = conflict.end_time or time.max
					c_start = datetime.combine(conflict.start_date, c_s_time)
					c_end = datetime.combine(conflict.end_date, c_e_time)
					if my_start < c_end and my_end > c_start:
						raise ValidationError({'driver': f'Conflict! This driver is already assigned to active Trip {conflict.trip_id} from {c_start.strftime("%b %d %H:%M")} to {c_end.strftime("%b %d %H:%M")}.'})
		if self.pk and self.status in ['settled', 'billed'] and self.vehicle_id and self.vehicle.ownership_type == 'outsourced':
			if not self.supplier_costs.exists():
				raise ValidationError({'status': 'Cannot settle or bill an outsourced trip without entering supplier costs.'})

		if self.vehicle_id:
			trip_date = self.start_date or (self.booking.pickup_date if self.booking_id else None) or (self.bulk_contract_day.date if self.bulk_contract_day_id else None)
			if trip_date:
				if self.vehicle.insurance_expiry and self.vehicle.insurance_expiry < trip_date:
					raise ValidationError({'vehicle': f'Cannot assign {self.vehicle.registration_number}: Insurance is expired.'})
				if self.vehicle.fc_expiry and self.vehicle.fc_expiry < trip_date:
					raise ValidationError({'vehicle': f'Cannot assign {self.vehicle.registration_number}: Fitness Certificate (FC) is expired.'})
				if self.vehicle.permit_expiry and self.vehicle.permit_expiry < trip_date:
					raise ValidationError({'vehicle': f'Cannot assign {self.vehicle.registration_number}: Permit is expired.'})
				if self.vehicle.tax_expiry and self.vehicle.tax_expiry < trip_date:
					raise ValidationError({'vehicle': f'Cannot assign {self.vehicle.registration_number}: Road Tax is expired.'})
				if self.vehicle.pollution_expiry and self.vehicle.pollution_expiry < trip_date:
					raise ValidationError({'vehicle': f'Cannot assign {self.vehicle.registration_number}: Pollution (PUC) certificate is expired.'})
				if self.vehicle.status == 'maintenance':
					raise ValidationError({'vehicle': f'Cannot assign {self.vehicle.registration_number}: Vehicle is currently under workshop maintenance.'})

		if self.driver_id:
			trip_date = self.start_date or (self.booking.pickup_date if self.booking_id else None) or (self.bulk_contract_day.date if self.bulk_contract_day_id else None)
			if trip_date:
				if self.driver.status != 'active':
					raise ValidationError({'driver': f'Cannot assign {self.driver.name}: Driver status is {self.driver.get_status_display()}, not active.'})
				validity = self.driver.license_validity_tr or self.driver.license_validity_nt
				if validity and validity < trip_date:
					raise ValidationError({'driver': f'Cannot assign {self.driver.name}: Commercial driving license expired on {validity}.'})

	def save(self, *args, **kwargs):
		is_new = self.pk is None
		if not self.trip_id:
			last_trip = Trip.objects.order_by('-id').first()
			next_number = (last_trip.id + 1) if last_trip else 1
			self.trip_id = f'TR-{next_number:04d}'
		
		if not self.tracking_token:
			import uuid
			self.tracking_token = uuid.uuid4().hex

		if not self.pickup_pin:
			import random
			self.pickup_pin = f"{random.randint(1000, 9999)}"
		
		# Smart Status Progression
		if self.status == 'booked' and self.driver_id:
			self.status = 'assigned'
		if self.status == 'assigned' and self.opening_km is not None:
			self.status = 'started'
		if self.status == 'started' and self.closing_km is not None:
			self.status = 'completed'
		
		# Auto-fill missing fields based on parent
		if not self.party_id:
			if self.booking_id:
				self.party = self.booking.party
			elif self.bulk_contract_day_id:
				self.party = self.bulk_contract_day.contract.customer
		if not self.guest_name:
			if self.booking_id:
				self.guest_name = self.booking.guest_name
			elif self.bulk_contract_day_id:
				self.guest_name = 'Bulk Contract Trip'
		if not self.travel_pnr and self.booking_id:
			self.travel_pnr = self.booking.travel_pnr
		if self.pax_count is None and self.booking_id:
			self.pax_count = self.booking.pax_count
		if self.luggage_count is None and self.booking_id:
			self.luggage_count = self.booking.luggage_count
				
		if is_new:
			if not self.start_date:
				if self.booking_id:
					self.start_date = self.booking.pickup_date
				elif self.bulk_contract_day_id:
					self.start_date = self.bulk_contract_day.date
			if not self.end_date:
				if self.booking_id:
					self.end_date = self.booking.drop_date or self.start_date
				elif self.bulk_contract_day_id:
					self.end_date = self.bulk_contract_day.date
					if self.start_time and self.end_time and self.end_time < self.start_time:
						from datetime import timedelta
						self.end_date += timedelta(days=1)
					
			if not self.day_rate and not self.km_rate:
				from .services import get_active_rate_card
				v_type = self.booking.vehicle_type if self.booking_id else self.vehicle.vehicle_type if self.vehicle else None
				rate_card = get_active_rate_card(self.party, v_type, self.start_date, vehicle=self.vehicle)
				if rate_card:
					self.day_rate = rate_card.day_rate
					self.km_rate = rate_card.km_rate
					self.driver_bata = rate_card.driver_bata
				elif self.bulk_contract_day_id:
					v_type = self.vehicle.vehicle_type if self.vehicle else None
					if v_type:
						rate_obj = self.bulk_contract_day.contract.vehicle_rates.filter(vehicle_type=v_type).first()
						if rate_obj:
							self.day_rate = rate_obj.agreed_day_rate

		if is_new and self.days_count == 1 and self.start_date and self.end_date:
			self.days_count = max(1, (self.end_date - self.start_date).days + 1)
		
		# Sync booking status
		if self.booking_id:
			if self.status in ['assigned', 'driver_confirmed', 'started']:
				if self.booking.status == 'confirmed':
					self.booking.status = 'dispatched'
					self.booking.save(update_fields=['status'])
			elif self.status == 'completed':
				if self.booking.status in ['confirmed', 'dispatched']:
					self.booking.status = 'completed'
					self.booking.save(update_fields=['status'])
			elif self.status == 'cancelled':
				if self.booking.status in ['confirmed', 'dispatched']:
					self.booking.status = 'cancelled'
					self.booking.save(update_fields=['status'])
		
		super().save(*args, **kwargs)
		if self.vehicle:
			if self.closing_km is not None:
				self.vehicle.current_km = max(self.vehicle.current_km, self.closing_km)
				self.vehicle.save(update_fields=['current_km'])
			if self.status == 'started' and self.vehicle.status != 'on_trip':
				self.vehicle.status = 'on_trip'
				self.vehicle.save(update_fields=['status'])
			elif self.status in ['completed', 'cancelled'] and self.vehicle.status == 'on_trip':
				self.vehicle.status = 'available'
				self.vehicle.save(update_fields=['status'])

		if self.driver_id and self.driver_bata and self.days_count:
			from finance.models import DriverSettlement
			total_batta = self.driver_bata * self.days_count
			settlement = DriverSettlement.objects.filter(trip=self, driver=self.driver).first()
			if not settlement:
				settlement = DriverSettlement.objects.create(
					trip=self,
					driver=self.driver,
					total_days=self.days_count,
					batta=total_batta,
				)
			elif not settlement.settled_on:
				update_needed = False
				if settlement.total_days != self.days_count:
					settlement.total_days = self.days_count
					update_needed = True
				if settlement.batta != total_batta:
					settlement.batta = total_batta
					update_needed = True
				if update_needed:
					settlement.save(update_fields=['total_days', 'batta'])

	def calculate_auto_bata(self, save=False):
		"""
		Calculate and itemize multi-component driver allowance (base bata, night halt,
		early morning, overtime, outstation) using operations.driver_bata_engine.
		"""
		from operations.driver_bata_engine import calculate_trip_driver_bata
		res = calculate_trip_driver_bata(self)
		self.driver_bata = res['total_bata']
		self.driver_bata_breakdown = {
			k: float(v) if isinstance(v, Decimal) else v
			for k, v in res.items()
		}
		if save and self.pk:
			self.save(update_fields=['driver_bata', 'driver_bata_breakdown'])
		return res

	@property
	def pickup_location(self):
		if self.booking:
			return self.booking.pickup_location
		return "Base Yard"

	@property
	def destination(self):
		if self.booking:
			return self.booking.destination
		return "Duty Route"

	@property
	def total_km(self):
		if self.opening_km is not None and self.closing_km is not None:
			return max(0, self.closing_km - self.opening_km)
		return 0

	class Meta:
		constraints = [
			models.CheckConstraint(
				check=models.Q(end_date__isnull=True) | models.Q(start_date__isnull=True) | models.Q(end_date__gte=models.F('start_date')),
				name='trip_end_date_gte_start_date'
			),
			models.CheckConstraint(
				check=models.Q(closing_km__isnull=True) | models.Q(opening_km__isnull=True) | models.Q(closing_km__gte=models.F('opening_km')),
				name='trip_closing_km_gte_opening_km'
			),
			models.CheckConstraint(
				check=models.Q(day_rate__gte=0),
				name='trip_day_rate_non_negative'
			),
			models.CheckConstraint(
				check=models.Q(km_rate__gte=0),
				name='trip_km_rate_non_negative'
			),
			models.CheckConstraint(
				check=models.Q(fixed_amount__gte=0),
				name='trip_fixed_amount_non_negative'
			),
			models.CheckConstraint(
				check=models.Q(driver_bata__gte=0),
				name='trip_driver_bata_non_negative'
			),
		]
		indexes = [
			models.Index(fields=['status', 'start_date'], name='idx_trip_status_start'),
			models.Index(fields=['vehicle', 'status'], name='idx_trip_vehicle_status'),
			models.Index(fields=['driver', 'status'], name='idx_trip_driver_status'),
			models.Index(fields=['party', 'status'], name='idx_trip_party_status'),
			models.Index(fields=['start_date', 'end_date'], name='idx_trip_date_range'),
		]


class TripHotel(models.Model):
	trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='hotels')
	hotel_name = models.CharField(max_length=255)
	hotel_room_type = models.CharField(max_length=100, blank=True)
	check_in_date = models.DateField(null=True, blank=True)
	check_out_date = models.DateField(null=True, blank=True)
	confirmation_status = models.CharField(max_length=20, choices=Trip.HOTEL_CONFIRMATION_CHOICES, default='pending')
	paid_by = models.CharField(max_length=20, choices=Trip.HOTEL_PAID_BY_CHOICES, default='company')
	notes = models.CharField(max_length=255, blank=True)

	def __str__(self):
		return f"{self.hotel_name} ({self.trip})"

class TrafficFine(models.Model):
	VIOLATION_TYPES = [
		('speeding', '⚡ Overspeeding'),
		('seatbelt', '💺 Seatbelt Not Worn (General)'),
		('seatbelt_passenger', '💺 Seatbelt Not Worn (Passenger / Customer)'),
		('seatbelt_driver', '💺 Seatbelt Not Worn (Driver)'),
		('signal', '🚦 Signal Jump / Red Light'),
		('parking', '🅿️ Illegal / No Parking'),
		('smoking', '🚭 Smoking in Vehicle (Customer Violation)'),
		('documents', '📄 Vehicle Documents (Expired / Missing)'),
		('overloading', '👥 Overloading / Extra Passengers'),
		('rash_driving', '⚠️ Reckless / Rash Driving'),
		('other', '📝 Other Violation'),
	]
	PAID_BY_CHOICES = [
		('unpaid', '⏳ Unpaid (Challan Pending)'),
		('company', '🏢 Paid by Company'),
		('driver', '🧑‍✈️ Paid by Driver on Spot'),
		('customer', '👤 Paid by Customer on Spot'),
	]
	RESPONSIBILITY_CHOICES = [
		('customer', '👤 Customer (Bill to Customer in Trip Invoice)'),
		('driver', '🧑‍✈️ Driver (Deduct from Driver Settlement)'),
		('supplier', '🏢 Supplier / Vehicle Owner (Outsourced Fleet Issue)'),
		('company', '🏛️ Company Expense (Absorb in Trip P&L)'),
	]

	trip = models.ForeignKey(Trip, on_delete=models.SET_NULL, null=True, blank=True, related_name='traffic_fines', help_text="Optional: link fine to the specific trip where it occurred")
	vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='traffic_fines')
	driver = models.ForeignKey(Driver, on_delete=models.SET_NULL, null=True, blank=True, related_name='traffic_fines')
	date_of_offence = models.DateTimeField()
	challan_number = models.CharField(max_length=100, unique=True)
	violation_type = models.CharField(max_length=50, choices=VIOLATION_TYPES)
	fine_amount = models.DecimalField(max_digits=8, decimal_places=2)
	
	paid_by = models.CharField(max_length=20, choices=PAID_BY_CHOICES, default='unpaid')
	financial_responsibility = models.CharField(
		max_length=20,
		choices=RESPONSIBILITY_CHOICES,
		default='driver',
		help_text="Select who is financially responsible. 'Customer' adds fine to customer invoice; 'Driver' deducts from driver settlement; 'Supplier' is for outsourced fleet issues; 'Company' absorbs as expense."
	)
	
	receipt_file = models.FileField(upload_to='traffic_fines/', blank=True, null=True)
	notes = models.TextField(blank=True)

	def save(self, *args, **kwargs):
		if self.trip_id:
			if not self.vehicle_id and self.trip.vehicle_id:
				self.vehicle = self.trip.vehicle
			if not self.driver_id and self.trip.driver_id:
				self.driver = self.trip.driver
		
		# Smart assignment if responsibility not explicitly overridden or on first save
		if not self.pk and self.financial_responsibility == 'driver':
			if self.violation_type in ['seatbelt_passenger', 'smoking']:
				self.financial_responsibility = 'customer'
			elif self.violation_type == 'documents' and self.vehicle and self.vehicle.ownership_type == 'outsourced':
				self.financial_responsibility = 'supplier'

		super().save(*args, **kwargs)

	def __str__(self):
		return f"Challan {self.challan_number} for {self.vehicle}"

	class Meta:
		ordering = ['-date_of_offence']
		indexes = [
			models.Index(fields=['vehicle', 'date_of_offence'], name='idx_tf_veh_date'),
			models.Index(fields=['driver', 'date_of_offence'], name='idx_tf_drv_date'),
		]


class TripJourney(models.Model):
	trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='journeys')
	start_location = models.CharField(max_length=255)
	end_location = models.CharField(max_length=255)
	start_km = models.PositiveIntegerField(null=True, blank=True)
	end_km = models.PositiveIntegerField(null=True, blank=True)
	start_time = models.DateTimeField(null=True, blank=True)
	end_time = models.DateTimeField(null=True, blank=True)

	def clean(self):
		from django.core.exceptions import ValidationError
		if self.start_time and self.trip.start_date and self.start_time.date() < self.trip.start_date:
			raise ValidationError({'start_time': 'Journey start time cannot be before trip start date.'})
		if self.end_time and self.start_time and self.end_time < self.start_time:
			raise ValidationError({'end_time': 'Journey end time cannot be before its start time.'})

	def __str__(self):
		return f'{self.trip} / {self.start_location} - {self.end_location}'


class TripCrewAssignment(models.Model):
	ROLES = [('driver', 'Driver'), ('cleaner', 'Cleaner'), ('driver_cleaner', 'Driver + cleaner'), ('additional_driver', 'Additional driver')]
	trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='crew_assignments')
	role = models.CharField(max_length=20, choices=ROLES)
	driver = models.ForeignKey(Driver, on_delete=models.PROTECT, null=True, blank=True, related_name='trip_crew_assignments')
	cleaner = models.ForeignKey(Cleaner, on_delete=models.PROTECT, null=True, blank=True, related_name='trip_crew_assignments')
	start_time = models.DateTimeField(null=True, blank=True)
	end_time = models.DateTimeField(null=True, blank=True)
	notes = models.CharField(max_length=255, blank=True)

	def clean(self):
		from django.core.exceptions import ValidationError

		if bool(self.driver_id) == bool(self.cleaner_id):
			raise ValidationError('Assign exactly one driver or cleaner to a crew row.')
		if self.role in {'driver', 'additional_driver'} and self.cleaner_id and not self.cleaner.can_drive:
			raise ValidationError('A cleaner assigned as a driver must be marked as able to drive.')
		if self.role == 'driver_cleaner' and not self.driver_id:
			raise ValidationError({'driver': 'A driver-cleaner assignment must use a driver.'})
		if self.role == 'driver_cleaner' and self.cleaner_id:
			raise ValidationError({'cleaner': 'Use the driver field for a driver who also acts as cleaner.'})
		if self.trip_id and self.driver_id and self.trip.driver_id and self.role == 'driver' and self.trip.driver_id != self.driver_id:
			raise ValidationError('The primary driver crew row must match Trip.driver.')

	def __str__(self):
		worker = self.driver or self.cleaner
		return f'{self.trip} / {self.role} / {worker}'


class BulkContract(models.Model):
	STATUSES = [('draft', 'Draft'), ('active', 'Active'), ('completed', 'Completed'), ('cancelled', 'Cancelled')]
	CONTRACT_TYPES = [('cinema', 'Cinema / Film Shoot'), ('wedding', 'Wedding & Functions'), ('event', 'Events & Conferences'), ('government', 'Government Duty'), ('other', 'Other Bulk Contract')]
	contract_type = models.CharField(max_length=50, choices=CONTRACT_TYPES, default='cinema')
	name = models.CharField(max_length=255)
	customer = models.ForeignKey(Client, on_delete=models.PROTECT, related_name='bulk_contracts')
	start_date = models.DateField()
	end_date = models.DateField()
	billing_model = models.CharField(max_length=20, choices=[('per_vehicle_day', 'Per vehicle day'), ('fixed', 'Fixed'), ('custom', 'Custom')], default='per_vehicle_day')
	status = models.CharField(max_length=20, choices=STATUSES, default='draft')
	gst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
	notes = models.TextField(blank=True)

	def clean(self):
		from django.core.exceptions import ValidationError
		if self.end_date and self.start_date and self.end_date < self.start_date:
			raise ValidationError('Contract end date cannot be before start date.')

	class Meta:
		verbose_name = 'Bulk Contract'
		verbose_name_plural = 'Bulk Contracts'

	def __str__(self):
		return self.name


class BulkContractDay(models.Model):
	contract = models.ForeignKey(BulkContract, on_delete=models.CASCADE, related_name='days')
	date = models.DateField()
	notes = models.CharField(max_length=255, blank=True)

	class Meta:
		unique_together = ('contract', 'date')
		verbose_name = 'Bulk Contract Day'
		verbose_name_plural = 'Bulk Contract Days'

	def clean(self):
		from django.core.exceptions import ValidationError
		if self.contract_id and not (self.contract.start_date <= self.date <= self.contract.end_date):
			raise ValidationError('The operating day must fall inside the contract dates.')

	def __str__(self):
		return f'{self.contract} / {self.date}'


class ContractVehicleRate(models.Model):
	contract = models.ForeignKey(BulkContract, on_delete=models.CASCADE, related_name='vehicle_rates')
	vehicle_type = models.ForeignKey('core.VehicleType', on_delete=models.PROTECT, null=True)
	agreed_day_rate = models.DecimalField(max_digits=10, decimal_places=2)

	class Meta:
		unique_together = ('contract', 'vehicle_type')

	def __str__(self):
		return f"{self.vehicle_type} @ {self.agreed_day_rate}"


class ContractDayRequirement(models.Model):
	contract_day = models.ForeignKey(BulkContractDay, on_delete=models.CASCADE, related_name='requirements')
	vehicle_type = models.ForeignKey('core.VehicleType', on_delete=models.PROTECT, null=True)
	quantity = models.PositiveIntegerField(default=1)

	class Meta:
		unique_together = ('contract_day', 'vehicle_type')

	def __str__(self):
		return f"{self.quantity} x {self.vehicle_type}"


def generate_incident_id():
	from django.utils import timezone
	import random
	ts = timezone.now().strftime('%Y%m%d%H%M')
	rn = random.randint(100, 999)
	return f"INC-{ts}-{rn}"


class EmergencyIncidentAlert(models.Model):
	INCIDENT_TYPES = [
		('breakdown', 'Mechanical Breakdown'),
		('accident', 'Road Accident / Collision'),
		('tyre_burst', 'Tyre Burst / Puncture'),
		('engine_overheat', 'Engine Overheating'),
		('medical', 'Medical Emergency'),
		('sos_panic', 'Women Safety SOS / Panic Trigger'),
		('fuel_exhaustion', 'Out of Fuel / DEF'),
		('geofence_breach', 'Geofence Boundary Breach'),
		('corridor_deviation', 'Route Corridor Deviation'),
		('overspeed_violation', 'Severe Over-Speeding Violation'),
		('other', 'Other Incident'),
	]
	SEVERITY_LEVELS = [
		('critical', 'Critical (Immediate Dispatch)'),
		('high', 'High Priority'),
		('medium', 'Medium'),
		('low', 'Low'),
	]
	STATUS_CHOICES = [
		('reported', 'Reported / SOS Triggered'),
		('acknowledged', 'Acknowledged by Dispatch'),
		('standby_dispatched', 'Standby Vehicle Dispatched'),
		('resolved', 'Resolved on Site'),
		('closed', 'Closed & Completed'),
	]
	SAFETY_STATUSES = [
		('all_safe', 'All Passengers Safe & Unharmed'),
		('minor_injuries', 'Minor First-Aid Required'),
		('hospitalized', 'Medical Attention / Hospitalized'),
		('stranded_safe', 'Safe but Stranded Roadside'),
	]

	incident_id = models.CharField(max_length=50, unique=True, default=generate_incident_id)
	incident_type = models.CharField(max_length=30, choices=INCIDENT_TYPES, default='breakdown')
	severity = models.CharField(max_length=20, choices=SEVERITY_LEVELS, default='critical')
	vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='incident_alerts')
	driver = models.ForeignKey(Driver, on_delete=models.CASCADE, related_name='incident_alerts')
	trip = models.ForeignKey('operations.Trip', on_delete=models.SET_NULL, null=True, blank=True, related_name='incident_alerts')
	contract_trip = models.ForeignKey('fleet_contracts.ContractTripLog', on_delete=models.SET_NULL, null=True, blank=True, related_name='incident_alerts')
	reported_at = models.DateTimeField(default=timezone.now)

	latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
	longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
	location_address = models.CharField(max_length=255, blank=True, help_text="Highway KM, landmark, or city")
	passenger_count = models.PositiveIntegerField(default=0)
	passengers_safety_status = models.CharField(max_length=30, choices=SAFETY_STATUSES, default='all_safe')
	description = models.TextField(help_text="Detailed problem description")

	status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='reported')
	standby_vehicle = models.ForeignKey(Vehicle, on_delete=models.SET_NULL, null=True, blank=True, related_name='standby_dispatched_incidents')
	standby_driver = models.ForeignKey(Driver, on_delete=models.SET_NULL, null=True, blank=True, related_name='standby_dispatched_incidents')
	standby_dispatched_at = models.DateTimeField(null=True, blank=True)
	standby_eta_minutes = models.PositiveIntegerField(null=True, blank=True)
	resolution_notes = models.TextField(blank=True)
	resolved_at = models.DateTimeField(null=True, blank=True)

	class Meta:
		ordering = ['-reported_at']
		verbose_name = "Emergency Incident / SOS Alert"
		verbose_name_plural = "Emergency Incident / SOS Alerts"

	def __str__(self):
		return f"{self.incident_id} - {self.get_incident_type_display()} ({self.vehicle.registration_number})"


class VehicleTelematicsPing(models.Model):
	vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='telematics_pings')
	trip = models.ForeignKey('operations.Trip', on_delete=models.SET_NULL, null=True, blank=True, related_name='telematics_pings')
	timestamp = models.DateTimeField(default=timezone.now, db_index=True)
	latitude = models.DecimalField(max_digits=10, decimal_places=7)
	longitude = models.DecimalField(max_digits=10, decimal_places=7)
	speed_kmh = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
	heading_degrees = models.FloatField(null=True, blank=True)
	altitude_m = models.FloatField(null=True, blank=True)
	ignition_on = models.BooleanField(default=True)
	fuel_level_pct = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
	odometer_km = models.PositiveIntegerField(null=True, blank=True)
	satellite_count = models.PositiveSmallIntegerField(null=True, blank=True)
	raw_telemetry = models.JSONField(default=dict, blank=True)

	class Meta:
		ordering = ['-timestamp']
		indexes = [
			models.Index(fields=['vehicle', '-timestamp']),
		]
		verbose_name = "Vehicle Telematics Ping"
		verbose_name_plural = "Vehicle Telematics Pings"

	def __str__(self):
		return f"{self.vehicle.registration_number} @ {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')} ({self.speed_kmh} km/h)"


class DriverBehaviorLog(models.Model):
	EVENT_TYPES = [
		('overspeeding', 'Overspeeding Violation'),
		('harsh_braking', 'Harsh / Panic Braking'),
		('harsh_acceleration', 'Harsh / Rapid Acceleration'),
		('excessive_idling', 'Excessive Engine Idling (>15 min)'),
		('sharp_cornering', 'Aggressive / Sharp Cornering'),
		('geofence_breach', 'Geofence Boundary Breach'),
	]
	SEVERITY_LEVELS = [
		('critical', 'Critical Hazard'),
		('high', 'High Risk'),
		('medium', 'Medium Risk'),
		('low', 'Minor Infraction'),
	]

	vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='behavior_events')
	driver = models.ForeignKey(Driver, on_delete=models.SET_NULL, null=True, blank=True, related_name='behavior_events')
	trip = models.ForeignKey('operations.Trip', on_delete=models.SET_NULL, null=True, blank=True, related_name='behavior_events')
	timestamp = models.DateTimeField(default=timezone.now, db_index=True)
	event_type = models.CharField(max_length=30, choices=EVENT_TYPES)
	severity = models.CharField(max_length=20, choices=SEVERITY_LEVELS, default='medium')
	recorded_speed_kmh = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
	speed_limit_kmh = models.DecimalField(max_digits=5, decimal_places=2, default=80.0)
	duration_seconds = models.PositiveIntegerField(default=0)
	latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
	longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
	location_address = models.CharField(max_length=255, blank=True)
	penalty_points = models.PositiveIntegerField(default=5, help_text="Points deducted from safety scorecard")
	notes = models.TextField(blank=True)

	class Meta:
		ordering = ['-timestamp']
		verbose_name = "Driver Behavior Event"
		verbose_name_plural = "Driver Behavior Events"
		indexes = [
			models.Index(fields=['driver', 'timestamp'], name='idx_drv_beh_driver_time'),
			models.Index(fields=['vehicle', 'timestamp'], name='idx_drv_beh_veh_time'),
		]

	def __str__(self):
		return f"{self.get_event_type_display()} - {self.vehicle.registration_number} ({self.recorded_speed_kmh} km/h)"


class GeofenceZone(models.Model):
	ZONE_TYPES = [
		('depot', 'Fleet Yard / Garage Depot'),
		('airport', 'Airport Terminal'),
		('school', 'School / Educational Campus'),
		('client_site', 'Corporate Tech Park / Client Office'),
		('fuel_station', 'Authorized Petro Station'),
		('restricted_zone', 'Restricted / High-Risk Area'),
	]

	name = models.CharField(max_length=150)
	zone_type = models.CharField(max_length=30, choices=ZONE_TYPES, default='depot')
	latitude = models.DecimalField(max_digits=10, decimal_places=7)
	longitude = models.DecimalField(max_digits=10, decimal_places=7)
	radius_meters = models.PositiveIntegerField(default=500, help_text="Circular geofence radius in meters")
	speed_limit_kmh = models.PositiveIntegerField(default=40, help_text="Max speed permitted inside zone (km/h)")
	alert_on_entry = models.BooleanField(default=True)
	alert_on_exit = models.BooleanField(default=True)
	is_active = models.BooleanField(default=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		verbose_name = "Geofence Zone"
		verbose_name_plural = "Geofence Zones"

	def __str__(self):
		return f"{self.name} ({self.get_zone_type_display()}) - Radius: {self.radius_meters}m"


class WhatsAppBotMessage(models.Model):
	DIRECTION_CHOICES = [
		('inbound', 'Inbound (Received)'),
		('outbound', 'Outbound (Sent)'),
	]
	STATUS_CHOICES = [
		('received', 'Received'),
		('sent', 'Sent'),
		('delivered', 'Delivered'),
		('read', 'Read'),
		('failed', 'Failed'),
		('simulated', 'Simulated'),
	]
	INTENT_CHOICES = [
		('dispatch_alert', 'Passenger Dispatch Alert'),
		('driver_briefing', 'Driver Trip Assignment'),
		('start_handover', 'Start Trip Handover'),
		('end_handover', 'End Trip Handover'),
		('sos_trigger', 'Emergency SOS Alert'),
		('trip_status', 'Trip Status / Live Track'),
		('payment_upi', 'UPI Payment Link / QR'),
		('geofence_breach_alert', 'Geofence Breach & Safety Alarm'),
		('general_query', 'General Bot Chat / Fallback'),
	]

	sender_phone = models.CharField(max_length=30, db_index=True)
	recipient_phone = models.CharField(max_length=30, db_index=True)
	message_direction = models.CharField(max_length=15, choices=DIRECTION_CHOICES, default='inbound')
	intent = models.CharField(max_length=30, choices=INTENT_CHOICES, default='general_query')
	message_body = models.TextField(blank=True)
	raw_payload = models.JSONField(default=dict, blank=True)
	status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='sent')
	trip = models.ForeignKey(Trip, on_delete=models.SET_NULL, null=True, blank=True, related_name='whatsapp_messages')
	driver = models.ForeignKey(Driver, on_delete=models.SET_NULL, null=True, blank=True, related_name='whatsapp_messages')
	message_id = models.CharField(max_length=120, blank=True, help_text="WhatsApp wamid or local message UUID")
	created_at = models.DateTimeField(auto_now_add=True, db_index=True)

	class Meta:
		ordering = ['-created_at']
		verbose_name = "WhatsApp Bot Message"
		verbose_name_plural = "WhatsApp Bot Messages"

	def __str__(self):
		return f"[{self.get_message_direction_display()}] {self.sender_phone} -> {self.recipient_phone} ({self.get_intent_display()})"


class DriverHandoverSession(models.Model):
	SESSION_TYPES = [
		('start', 'Start Duty Handover'),
		('end', 'End Duty Handover'),
	]
	STATUS_CHOICES = [
		('submitted', 'Submitted by Driver'),
		('approved', 'Audit Approved'),
		('flagged', 'Flagged Discrepancy'),
	]

	trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='handover_sessions')
	driver = models.ForeignKey(Driver, on_delete=models.PROTECT, related_name='handover_sessions')
	vehicle = models.ForeignKey(Vehicle, on_delete=models.PROTECT, related_name='handover_sessions')
	session_type = models.CharField(max_length=10, choices=SESSION_TYPES, default='start')
	odometer_reading = models.PositiveIntegerField(help_text="Odometer reading in KM")
	odometer_photo = models.ImageField(upload_to='trip_odometers/sessions/', null=True, blank=True, help_text="Dashboard photo verifying odometer")
	fuel_level_percent = models.PositiveIntegerField(default=100, help_text="Fuel gauge level percentage (0-100%)")
	gps_latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
	gps_longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
	location_name = models.CharField(max_length=255, blank=True, help_text="GPS Reverse Geocoded or entered location")
	cleanliness_rating = models.PositiveSmallIntegerField(default=5, help_text="Vehicle cleanliness score 1-5")
	scratch_damage_notes = models.TextField(blank=True, help_text="Notes on any scratches, dents, or pre-existing marks")
	status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='submitted')
	verified_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_handovers')
	verified_at = models.DateTimeField(null=True, blank=True)
	audit_notes = models.TextField(blank=True)
	created_at = models.DateTimeField(auto_now_add=True, db_index=True)

	class Meta:
		ordering = ['-created_at']
		verbose_name = "Driver Handover Session"
		verbose_name_plural = "Driver Handover Sessions"

	def __str__(self):
		return f"{self.trip.trip_id} - {self.get_session_type_display()} ({self.odometer_reading} KM)"


class TripMilestoneEvent(models.Model):
	trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='milestone_events')
	milestone = models.CharField(max_length=30, choices=Trip.TOUR_MILESTONES)
	milestone_index = models.PositiveSmallIntegerField(default=1)
	timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
	odometer_reading = models.PositiveIntegerField(null=True, blank=True)
	odometer_photo = models.ImageField(upload_to='trip_odometers/milestones/', null=True, blank=True)
	gps_latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
	gps_longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
	location_name = models.CharField(max_length=255, blank=True)
	passenger_pin_entered = models.CharField(max_length=6, blank=True)
	is_pin_verified = models.BooleanField(default=False)
	notes = models.TextField(blank=True)
	actor_driver = models.ForeignKey(Driver, on_delete=models.SET_NULL, null=True, blank=True, related_name='milestone_events')

	class Meta:
		ordering = ['timestamp', 'milestone_index']
		verbose_name = 'Trip Milestone Event'
		verbose_name_plural = 'Trip Milestone Events'

	def __str__(self):
		return f"{self.trip.trip_id} - {self.get_milestone_display()} at {self.timestamp.strftime('%H:%M')}"


class TripItineraryDay(models.Model):
	HOTEL_STATUS_CHOICES = [
		('pending', '⏳ Pending Confirmation'),
		('confirmed', '✅ Confirmed Voucher'),
		('checked_in', '🏨 Checked In'),
	]

	trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='itinerary_days')
	day_number = models.PositiveIntegerField(default=1, help_text="Tour Day sequence number (1, 2, 3...)")
	date = models.DateField(null=True, blank=True, help_text="Specific calendar date for this itinerary day")
	title = models.CharField(max_length=255, help_text="Day headline e.g. Mysore Palace & Brindavan Gardens")
	route_segment = models.CharField(max_length=255, blank=True, help_text="e.g. Bangalore -> Mysore -> Coorg")
	morning_plan = models.TextField(blank=True, help_text="Morning activity, breakfast stop, departure")
	sightseeing_spots = models.TextField(blank=True, help_text="Key sightseeing spots, comma or newline separated")
	evening_plan = models.TextField(blank=True, help_text="Evening highlights, dinner, campfire, sunset view")
	night_stay_location = models.CharField(max_length=255, blank=True, help_text="City or resort area for overnight stay")
	hotel_name = models.CharField(max_length=255, blank=True, help_text="Assigned hotel / resort name")
	hotel_booking_status = models.CharField(max_length=20, choices=HOTEL_STATUS_CHOICES, default='pending')
	hotel_voucher_number = models.CharField(max_length=100, blank=True, help_text="Hotel confirmation voucher/booking ID")
	hotel_address = models.CharField(max_length=255, blank=True, help_text="Hotel location or address")
	meals_included = models.CharField(max_length=255, default="Breakfast, Lunch, Dinner", help_text="Meals provided e.g. Breakfast, Lunch, Dinner")
	transport_mode = models.CharField(max_length=255, blank=True, help_text="e.g. AC Luxury Coach / 4x4 Jeep Safari")
	special_notes = models.TextField(blank=True, help_text="Special instructions, timings, entry dress codes")
	is_active_today = models.BooleanField(default=False, help_text="Explicit flag for today's active tour day")
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ['day_number']
		unique_together = ('trip', 'day_number')
		verbose_name = 'Trip Itinerary Day'
		verbose_name_plural = 'Trip Itinerary Days'

	def __str__(self):
		day_str = f"Day {self.day_number:02d}"
		return f"{self.trip.trip_id} - {day_str}: {self.title}"

	@property
	def spots_list(self):
		"""Return non-empty list of sightseeing spots."""
		if not self.sightseeing_spots:
			return []
		import re
		spots = re.split(r'[,;\n\r]+', self.sightseeing_spots)
		return [s.strip() for s in spots if s.strip()]

	@property
	def meals_list(self):
		"""Return non-empty list of included meal badges."""
		if not self.meals_included:
			return []
		import re
		meals = re.split(r'[,;/+]+', self.meals_included)
		return [m.strip() for m in meals if m.strip()]

	@property
	def formatted_day_label(self):
		return f"Day {self.day_number:02d}"

	@property
	def linked_voucher(self):
		"""Find matching HotelConfirmationVoucher for this day if one exists."""
		if not self.trip_id:
			return None
		try:
			from suppliers.models import HotelConfirmationVoucher
			if self.hotel_voucher_number:
				v = HotelConfirmationVoucher.objects.filter(trip=self.trip, voucher_number=self.hotel_voucher_number.strip()).first()
				if v:
					return v
			if self.date:
				v = HotelConfirmationVoucher.objects.filter(
					trip=self.trip,
					check_in_date__lte=self.date,
					check_out_date__gte=self.date
				).first()
				if v:
					return v
			if self.hotel_name:
				v = HotelConfirmationVoucher.objects.filter(
					trip=self.trip,
					hotel_name__icontains=self.hotel_name.strip()
				).first()
				if v:
					return v
		except Exception:
			pass
		return None





