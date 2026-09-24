from django.db import models
from core.models import Cleaner, Driver, Vehicle, Party
from operations.models import Trip


class TripExpense(models.Model):
	EXPENSE_TYPES = [('toll', 'Toll'), ('permit', 'Permit'), ('parking', 'Parking'), ('epass', 'E-Pass'), ('border_tax', 'Border tax'), ('driver_food', 'Driver food'), ('hotel', 'Hotel'), ('water', 'Water bottles'), ('snacks', 'Snacks'), ('repair', 'Repair'), ('other', 'Other')]
	PAID_BY = [('company', 'Company'), ('driver', 'Driver'), ('customer', 'Customer')]
	trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='expenses', null=True, blank=True)
	contract_trip = models.ForeignKey('fleet_contracts.ContractTripLog', on_delete=models.CASCADE, related_name='expenses', null=True, blank=True)
	expense_type = models.CharField(max_length=20, choices=EXPENSE_TYPES)
	amount = models.DecimalField(max_digits=10, decimal_places=2)
	date = models.DateField()
	description = models.CharField(max_length=255, blank=True)
	receipt = models.FileField(upload_to='receipts/', blank=True)
	paid_by = models.CharField(max_length=20, choices=PAID_BY, default='company')
	billable_to_customer = models.BooleanField(default=True)

	def clean(self):
		from django.core.exceptions import ValidationError
		if not self.trip_id and not self.contract_trip_id:
			raise ValidationError('Expense must belong to either a regular trip or a contract trip.')
		if self.trip_id and self.contract_trip_id:
			raise ValidationError('Expense cannot belong to both a regular trip and a contract trip.')


class SupplierTripCost(models.Model):
	trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='supplier_costs', null=True, blank=True)
	contract_trip = models.ForeignKey('fleet_contracts.ContractTripLog', on_delete=models.CASCADE, related_name='supplier_costs', null=True, blank=True)
	supplier = models.ForeignKey(Party, on_delete=models.PROTECT, related_name='supplier_trip_costs')
	vehicle = models.ForeignKey(Vehicle, on_delete=models.PROTECT, related_name='supplier_costs')
	date = models.DateField()
	amount = models.DecimalField(max_digits=12, decimal_places=2)
	description = models.CharField(max_length=255, blank=True)

	def clean(self):
		from django.core.exceptions import ValidationError

		if self.vehicle_id and self.vehicle.ownership_type != 'outsourced':
			raise ValidationError('Supplier trip cost must use an outsourced vehicle.')
		if self.vehicle_id and self.vehicle.owner_party_id and self.supplier_id != self.vehicle.owner_party_id:
			raise ValidationError('Supplier must match the outsourced vehicle owner.')
		if not self.trip_id and not self.contract_trip_id:
			raise ValidationError('Cost must belong to either a regular trip or a contract trip.')
		if self.trip_id and self.contract_trip_id:
			raise ValidationError('Cost cannot belong to both a regular trip and a contract trip.')
		
		trip_vehicle_id = self.trip.vehicle_id if self.trip_id else self.contract_trip.vehicle_id
		if trip_vehicle_id and trip_vehicle_id != self.vehicle_id:
			raise ValidationError({'vehicle': 'Supplier cost vehicle must match the trip vehicle.'})
		if self.supplier_id and self.supplier.party_type != 'supplier':
			raise ValidationError({'supplier': 'Supplier trip cost must use a supplier party.'})

	def __str__(self):
		return f'{self.trip} - {self.supplier} - {self.amount}'


class FuelRecord(models.Model):
	vehicle = models.ForeignKey(Vehicle, on_delete=models.PROTECT, related_name='fuel_records')
	trip = models.ForeignKey(Trip, on_delete=models.SET_NULL, null=True, blank=True, related_name='fuel_records')
	contract_trip = models.ForeignKey('fleet_contracts.ContractTripLog', on_delete=models.SET_NULL, null=True, blank=True, related_name='fuel_records')
	date = models.DateField()
	opening_km = models.PositiveIntegerField(null=True, blank=True)
	closing_km = models.PositiveIntegerField(null=True, blank=True)
	petro_account = models.ForeignKey('CorporatePetroAccount', on_delete=models.SET_NULL, null=True, blank=True, related_name='fuel_deductions')
	api_reference_number = models.CharField(max_length=100, blank=True)
	fuel_quantity = models.DecimalField(max_digits=8, decimal_places=2)
	fuel_price = models.DecimalField(max_digits=8, decimal_places=2)
	fuel_station = models.CharField(max_length=255, blank=True)
	receipt = models.FileField(upload_to='fuel_receipts/', null=True, blank=True)

	def clean(self):
		from django.core.exceptions import ValidationError

		if self.closing_km is not None and self.opening_km is not None and self.closing_km < self.opening_km:
			raise ValidationError('Closing kilometres cannot be lower than opening kilometres.')
		if self.trip_id and self.contract_trip_id:
			raise ValidationError('Fuel record cannot belong to both a regular trip and a contract trip.')
		if self.trip_id and self.trip.status == 'settled':
			raise ValidationError('Cannot add fuel to a trip that is already settled with the supplier.')

	@property
	def amount(self):
		if self.fuel_quantity is not None and self.fuel_price is not None:
			return self.fuel_quantity * self.fuel_price
		return 0

	@property
	def distance(self):
		if self.closing_km is not None and self.opening_km is not None:
			return max(0, self.closing_km - self.opening_km)
		return 0

	@property
	def mileage(self):
		if self.distance and self.fuel_quantity:
			return self.distance / self.fuel_quantity
		return 0
		
	@property
	def is_theft_suspected(self):
		if self.vehicle_id and getattr(self.vehicle, 'expected_mileage', None) and self.mileage > 0:
			from decimal import Decimal
			if self.mileage < (self.vehicle.expected_mileage * Decimal('0.8')): # If mileage drops 20% below expected
				return True
		return False

	def save(self, *args, **kwargs):
		is_new = self.pk is None
		super().save(*args, **kwargs)
		if is_new and self.petro_account:
			self.petro_account.balance -= self.amount
			self.petro_account.save(update_fields=['balance'])

class CorporatePetroAccount(models.Model):
	account_name = models.CharField(max_length=255, help_text="e.g. HPCL DriveTrack")
	account_number = models.CharField(max_length=100, unique=True)
	balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
	is_active = models.BooleanField(default=True)

	def __str__(self):
		return f"{self.account_name} - Balance: {self.balance}"

class PetroRecharge(models.Model):
	account = models.ForeignKey(CorporatePetroAccount, on_delete=models.CASCADE, related_name='recharges')
	date = models.DateField()
	amount = models.DecimalField(max_digits=10, decimal_places=2)
	reference_number = models.CharField(max_length=100, blank=True)
	notes = models.TextField(blank=True)

	def save(self, *args, **kwargs):
		is_new = self.pk is None
		super().save(*args, **kwargs)
		if is_new:
			self.account.balance += self.amount
			self.account.save(update_fields=['balance'])

class DriverSalaryProfile(models.Model):
	driver = models.OneToOneField('core.Driver', on_delete=models.CASCADE, related_name='salary_profile')
	basic_salary = models.DecimalField(max_digits=10, decimal_places=2, default=0)
	allowances = models.DecimalField(max_digits=10, decimal_places=2, default=0)
	epf_number = models.CharField(max_length=50, blank=True)
	esi_number = models.CharField(max_length=50, blank=True)
	epf_deduction_rate = models.DecimalField(max_digits=5, decimal_places=2, default=12.00, help_text="Percentage of basic salary")
	esi_deduction_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.75, help_text="Percentage of gross salary")

	def __str__(self):
		return f"Salary Profile for {self.driver.name}"

class DriverPayslip(models.Model):
	driver = models.ForeignKey('core.Driver', on_delete=models.CASCADE, related_name='payslips')
	month = models.PositiveIntegerField()
	year = models.PositiveIntegerField()
	days_present = models.PositiveIntegerField(default=30)
	
	basic_salary = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
	allowances = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
	
	epf_deduction = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
	esi_deduction = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
	traffic_fines_deduction = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
	advances_recovered = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
	
	def save(self, *args, **kwargs):
		if not self.pk and hasattr(self.driver, 'salary_profile'):
			profile = self.driver.salary_profile
			from decimal import Decimal
			
			# Prorate salary based on days present
			proration = Decimal(self.days_present) / Decimal(30)
			if not self.basic_salary:
				self.basic_salary = round(profile.basic_salary * proration, 2)
			if not self.allowances:
				self.allowances = round(profile.allowances * proration, 2)
			
			gross = self.basic_salary + self.allowances
			
			if profile.epf_number and not self.epf_deduction:
				self.epf_deduction = round(self.basic_salary * (profile.epf_deduction_rate / Decimal(100)), 2)
			if profile.esi_number and not self.esi_deduction:
				self.esi_deduction = round(gross * (profile.esi_deduction_rate / Decimal(100)), 2)
				
		super().save(*args, **kwargs)

	@property
	def gross_earnings(self):
		return self.basic_salary + self.allowances

	@property
	def total_deductions(self):
		return self.epf_deduction + self.esi_deduction + self.traffic_fines_deduction + self.advances_recovered

	@property
	def net_payable(self):
		from decimal import Decimal
		return max(Decimal('0.00'), self.gross_earnings - self.total_deductions)

	def __str__(self):
		return f"Payslip for {self.driver.name} - {self.month}/{self.year}"

class DriverAdvance(models.Model):
	driver = models.ForeignKey(Driver, on_delete=models.PROTECT, related_name='advances')
	trip = models.ForeignKey(Trip, on_delete=models.SET_NULL, null=True, blank=True, related_name='driver_advances')
	contract_trip = models.ForeignKey('fleet_contracts.ContractTripLog', on_delete=models.SET_NULL, null=True, blank=True, related_name='driver_advances')
	date = models.DateField()
	amount = models.DecimalField(max_digits=10, decimal_places=2)
	notes = models.CharField(max_length=255, blank=True)

	def clean(self):
		from django.core.exceptions import ValidationError
		if self.trip_id and self.contract_trip_id:
			raise ValidationError('Driver advance cannot belong to both a regular trip and a contract trip.')

	class Meta:
		ordering = ['-date', '-id']
		verbose_name = 'Driver money request'
		verbose_name_plural = 'Driver money requests'

	def __str__(self):
		return f'{self.driver} - {self.amount} on {self.date}'

	@property
	def allocated_amount(self):
		return sum((allocation.amount for allocation in self.allocations.all()), 0)

	@property
	def remaining_amount(self):
		return self.amount - self.allocated_amount


class EmployeePayment(models.Model):
	PAYMENT_TYPES = [('advance', 'Advance'), ('daily_pay', 'Daily pay'), ('settlement', 'Settlement'), ('salary', 'Salary')]
	PAYMENT_MODES = [('cash', 'Cash'), ('upi', 'UPI'), ('bank_transfer', 'Bank transfer'), ('cheque', 'Cheque'), ('card', 'Card'), ('other', 'Other')]
	date = models.DateField()
	driver = models.ForeignKey(Driver, on_delete=models.PROTECT, null=True, blank=True, related_name='employee_payments')
	cleaner = models.ForeignKey(Cleaner, on_delete=models.PROTECT, null=True, blank=True, related_name='employee_payments')
	trip = models.ForeignKey(Trip, on_delete=models.SET_NULL, null=True, blank=True, related_name='employee_payments')
	contract_trip = models.ForeignKey('fleet_contracts.ContractTripLog', on_delete=models.SET_NULL, null=True, blank=True, related_name='employee_payments')
	amount = models.DecimalField(max_digits=12, decimal_places=2)
	payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPES)
	payment_mode = models.CharField(max_length=20, choices=PAYMENT_MODES)
	notes = models.CharField(max_length=255, blank=True)

	def clean(self):
		from django.core.exceptions import ValidationError

		if bool(self.driver_id) == bool(self.cleaner_id):
			raise ValidationError('Employee payment must belong to exactly one driver or cleaner.')
		if self.amount <= 0:
			raise ValidationError({'amount': 'Employee payment must be greater than zero.'})
		if self.trip_id and self.contract_trip_id:
			raise ValidationError('Employee payment cannot belong to both a regular trip and a contract trip.')
		
		trip_driver_id = self.trip.driver_id if self.trip_id else self.contract_trip.driver_id if self.contract_trip_id else None
		if trip_driver_id and self.driver_id and trip_driver_id != self.driver_id:
			raise ValidationError({'driver': 'Payment driver must match the trip driver.'})

	def __str__(self):
		return f'{self.driver or self.cleaner} - {self.amount} on {self.date}'


class DriverAdvanceAllocation(models.Model):
	advance = models.ForeignKey(DriverAdvance, on_delete=models.CASCADE, related_name='allocations')
	trip = models.ForeignKey(Trip, on_delete=models.PROTECT, related_name='advance_allocations', null=True, blank=True)
	contract_trip = models.ForeignKey('fleet_contracts.ContractTripLog', on_delete=models.PROTECT, related_name='advance_allocations', null=True, blank=True)
	amount = models.DecimalField(max_digits=10, decimal_places=2)

	class Meta:
		unique_together = ('advance', 'trip')

	def clean(self):
		from django.core.exceptions import ValidationError

		if not self.trip_id and not self.contract_trip_id:
			raise ValidationError('Allocation must belong to either a regular trip or a contract trip.')
		if self.trip_id and self.contract_trip_id:
			raise ValidationError('Allocation cannot belong to both a regular trip and a contract trip.')

		trip_driver_id = self.trip.driver_id if self.trip_id else self.contract_trip.driver_id
		if trip_driver_id and self.advance_id and trip_driver_id != self.advance.driver_id:
			raise ValidationError('The allocation driver must match the advance driver.')
		allocated_elsewhere = sum((allocation.amount for allocation in self.advance.allocations.exclude(pk=self.pk)), 0)
		if allocated_elsewhere + self.amount > self.advance.amount:
			raise ValidationError('Allocations cannot exceed the driver advance amount.')

	def __str__(self):
		return f'{self.advance} -> {self.trip} ({self.amount})'


class DriverSettlement(models.Model):
	driver = models.ForeignKey(Driver, on_delete=models.PROTECT, related_name='settlements')
	trip = models.ForeignKey(Trip, on_delete=models.PROTECT, related_name='settlements', null=True, blank=True)
	contract_trip = models.ForeignKey('fleet_contracts.ContractTripLog', on_delete=models.PROTECT, related_name='settlements', null=True, blank=True)
	total_days = models.DecimalField(max_digits=5, decimal_places=2)
	batta = models.DecimalField(max_digits=10, decimal_places=2)
	advance_adjusted = models.DecimalField(max_digits=10, decimal_places=2, default=0)
	settled_on = models.DateField(null=True, blank=True)

	def clean(self):
		from django.core.exceptions import ValidationError

		if not self.trip_id and not self.contract_trip_id:
			raise ValidationError('Settlement must belong to either a regular trip or a contract trip.')
		if self.trip_id and self.contract_trip_id:
			raise ValidationError('Settlement cannot belong to both a regular trip and a contract trip.')

		trip_driver_id = self.trip.driver_id if self.trip_id else self.contract_trip.driver_id
		if trip_driver_id and self.driver_id and trip_driver_id != self.driver_id:
			raise ValidationError({'driver': 'Settlement driver must match the trip driver.'})
		if self.advance_adjusted > self.batta:
			raise ValidationError({'advance_adjusted': 'Advance adjusted cannot exceed driver batta.'})

	@property
	def cash_collected(self):
		from finance.models import Payment
		if self.trip_id:
			cash_payments = Payment.objects.filter(trip=self.trip, payment_type='customer_receipt', collected_by='driver')
		else:
			cash_payments = Payment.objects.filter(contract_trip=self.contract_trip, payment_type='customer_receipt', collected_by='driver')
		return sum(p.amount for p in cash_payments)

	@property
	def driver_expenses(self):
		trip_obj = self.trip if self.trip_id else self.contract_trip
		return sum(e.amount for e in trip_obj.expenses.filter(paid_by='driver'))

	@property
	def traffic_fines_deduction(self):
		from operations.models import TrafficFine
		if self.trip_id:
			fines = TrafficFine.objects.filter(
				trip=self.trip,
				driver=self.driver,
				paid_by__in=['company', 'unpaid'],
				financial_responsibility='driver'
			)
			return sum(f.fine_amount for f in fines)
		return 0

	@property
	def balance(self):
		return self.batta + self.driver_expenses - self.advance_adjusted - self.cash_collected - self.traffic_fines_deduction


class Payment(models.Model):
	PAYMENT_TYPES = [('customer_receipt', 'Customer receipt'), ('supplier_payment', 'Supplier payment'), ('advance', 'Advance'), ('adjustment', 'Adjustment'), ('tds_receivable', 'TDS Receivable')]
	PAYMENT_MODES = [('cash', 'Cash'), ('upi', 'UPI'), ('bank_transfer', 'Bank transfer'), ('cheque', 'Cheque'), ('card', 'Card'), ('other', 'Other')]
	COLLECTED_BY_CHOICES = [('company', 'Company Cashier'), ('driver', 'Driver')]
	party = models.ForeignKey(Party, on_delete=models.PROTECT, related_name='payments')
	booking = models.ForeignKey('operations.Booking', on_delete=models.PROTECT, null=True, blank=True, related_name='payments')
	trip = models.ForeignKey('operations.Trip', on_delete=models.PROTECT, null=True, blank=True, related_name='payments')
	contract_trip = models.ForeignKey('fleet_contracts.ContractTripLog', on_delete=models.PROTECT, null=True, blank=True, related_name='payments')
	statement = models.ForeignKey('statements.GeneratedStatement', on_delete=models.SET_NULL, null=True, blank=True, related_name='payments')
	date = models.DateField()
	amount = models.DecimalField(max_digits=12, decimal_places=2)
	payment_type = models.CharField(max_length=30, choices=PAYMENT_TYPES)
	payment_mode = models.CharField(max_length=20, choices=PAYMENT_MODES)
	collected_by = models.CharField(max_length=20, choices=COLLECTED_BY_CHOICES, default='company')
	reference_number = models.CharField(max_length=100, blank=True)
	bank = models.CharField(max_length=100, blank=True)
	notes = models.CharField(max_length=255, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	def clean(self):
		from django.core.exceptions import ValidationError

		# Guard against None before numeric comparison
		if self.amount is not None and self.amount <= 0:
			raise ValidationError({'amount': 'Payment amount must be greater than zero.'})
		if self.trip_id and self.contract_trip_id:
			raise ValidationError('Payment cannot belong to both a regular trip and a contract trip.')

		if self.booking_id and self.party_id and self.booking.party_id != self.party_id:
			raise ValidationError({'booking': 'Booking does not belong to the selected party.'})
		if self.trip_id and self.party_id and self.trip.party_id != self.party_id:
			raise ValidationError({'trip': 'Trip does not belong to the selected party.'})
		if self.contract_trip_id and self.party_id and self.contract_trip.shift.route.contract.customer_id != self.party_id:
			raise ValidationError({'contract_trip': 'Contract trip does not belong to the selected party.'})
		if self.statement_id and self.party_id and self.statement.party_id != self.party_id:
			raise ValidationError({'statement': 'Statement does not belong to the selected party.'})

	def save(self, *args, **kwargs):
		super().save(*args, **kwargs)
		if self.statement_id:
			total_received = Payment.objects.filter(statement=self.statement).aggregate(total=models.Sum('amount'))['total'] or 0
			if total_received == 0:
				new_status = 'unpaid'
			elif total_received >= self.statement.closing_balance:
				new_status = 'paid'
			else:
				new_status = 'partially_paid'
			
			if self.statement.status != new_status:
				self.statement.status = new_status
				self.statement.save(update_fields=['status'])
				
		if self.booking_id and self.payment_type == 'customer_receipt' and self.booking.status == 'pending':
			self.booking.status = 'confirmed'
			self.booking.save(update_fields=['status'])


class LedgerAdjustment(models.Model):
	party = models.ForeignKey(Party, on_delete=models.PROTECT, related_name='ledger_adjustments')
	date = models.DateField()
	amount = models.DecimalField(max_digits=12, decimal_places=2)
	description = models.CharField(max_length=255)

class CorporateFastagAccount(models.Model):
	account_name = models.CharField(max_length=255, help_text="e.g. ICICI Corporate Master Wallet")
	account_number = models.CharField(max_length=100, unique=True)
	balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
	is_active = models.BooleanField(default=True)

	def __str__(self):
		return f"{self.account_name} - Balance: {self.balance}"

class FastagRecharge(models.Model):
	account = models.ForeignKey(CorporateFastagAccount, on_delete=models.CASCADE, related_name='recharges')
	date = models.DateField()
	amount = models.DecimalField(max_digits=10, decimal_places=2)
	reference_number = models.CharField(max_length=100, blank=True)
	notes = models.TextField(blank=True)

	def save(self, *args, **kwargs):
		is_new = self.pk is None
		super().save(*args, **kwargs)
		if is_new:
			self.account.balance += self.amount
			self.account.save(update_fields=['balance'])

class FastagTollDeduction(models.Model):
	account = models.ForeignKey(CorporateFastagAccount, on_delete=models.CASCADE, related_name='deductions')
	date = models.DateTimeField()
	vehicle = models.ForeignKey('core.Vehicle', on_delete=models.PROTECT, related_name='toll_deductions')
	trip = models.ForeignKey('operations.Trip', on_delete=models.SET_NULL, null=True, blank=True, related_name='toll_deductions')
	contract_trip = models.ForeignKey('fleet_contracts.ContractTripLog', on_delete=models.SET_NULL, null=True, blank=True, related_name='toll_deductions')
	amount = models.DecimalField(max_digits=8, decimal_places=2)
	toll_plaza = models.CharField(max_length=255, blank=True)

	def save(self, *args, **kwargs):
		is_new = self.pk is None
		super().save(*args, **kwargs)
		if is_new:
			self.account.balance -= self.amount
			self.account.save(update_fields=['balance'])

class VehicleLoan(models.Model):
	vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='loans')
	financier_name = models.CharField(max_length=255, help_text="e.g. HDFC Bank, Cholamandalam")
	loan_account_number = models.CharField(max_length=100, unique=True)
	total_loan_amount = models.DecimalField(max_digits=12, decimal_places=2)
	interest_rate = models.DecimalField(max_digits=5, decimal_places=2, help_text="Percentage (e.g. 8.5)")
	emi_amount = models.DecimalField(max_digits=10, decimal_places=2)
	start_date = models.DateField()
	end_date = models.DateField()
	emi_date_of_month = models.PositiveIntegerField(help_text="Day of the month the EMI is deducted (1-31)")
	is_active = models.BooleanField(default=True)
	
	def __str__(self):
		return f"Loan for {self.vehicle} ({self.financier_name})"

class TripProfitReport(Trip):
	class Meta:
		proxy = True
		verbose_name = 'Trip P&L Report'
		verbose_name_plural = 'Trip P&L Reports'
