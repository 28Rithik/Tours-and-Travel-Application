from django.db import models
from django.utils import timezone
from decimal import Decimal
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


class Account(models.Model):
	ACCOUNT_TYPES = [
		('asset', 'Asset'),
		('liability', 'Liability'),
		('equity', 'Equity'),
		('income', 'Income'),
		('expense', 'Expense'),
	]
	code = models.CharField(max_length=20, unique=True, help_text="e.g. 1010, 1020, 1030, 1100, 2010, 4010, 5010")
	name = models.CharField(max_length=150)
	account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPES)
	currency = models.CharField(max_length=10, default='INR')
	description = models.TextField(blank=True)
	is_active = models.BooleanField(default=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['code']
		verbose_name = 'Chart of Account'
		verbose_name_plural = 'Chart of Accounts'

	def __str__(self):
		return f"{self.code} - {self.name} ({self.get_account_type_display()})"

	@property
	def current_balance(self):
		from django.db.models import Sum
		from decimal import Decimal
		debits = self.journal_items.aggregate(total=Sum('debit'))['total'] or Decimal('0.00')
		credits = self.journal_items.aggregate(total=Sum('credit'))['total'] or Decimal('0.00')
		if self.account_type in ['asset', 'expense']:
			return debits - credits
		else:
			return credits - debits


class JournalEntry(models.Model):
	ENTRY_TYPES = [
		('payment_receipt', 'Payment Receipt'),
		('invoice_billing', 'Invoice Billing'),
		('gateway_settlement', 'Gateway Settlement'),
		('supplier_payout', 'Supplier Payout'),
		('driver_salary', 'Driver Salary'),
		('fuel_expense', 'Fuel Expense'),
		('toll_charge', 'Toll Charge'),
		('general', 'General Journal'),
	]
	entry_number = models.CharField(max_length=50, unique=True, blank=True)
	date = models.DateField()
	entry_type = models.CharField(max_length=30, choices=ENTRY_TYPES, default='payment_receipt')
	reference_id = models.CharField(max_length=100, blank=True, help_text="Reference Booking #, RZP ID, UTR, etc.")
	narration = models.TextField(help_text="Detailed transaction narration")
	is_posted = models.BooleanField(default=False)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ['-date', '-id']
		verbose_name = 'General Ledger Journal Entry'
		verbose_name_plural = 'General Ledger Journal Entries'

	def __str__(self):
		return f"{self.entry_number or f'JE-{self.pk}'} - {self.date} ({self.get_entry_type_display()})"

	def save(self, *args, **kwargs):
		if not self.entry_number:
			from django.utils import timezone
			super().save(*args, **kwargs)
			today_str = timezone.now().strftime('%Y%m')
			self.entry_number = f"JE-{today_str}-{self.pk:05d}"
			super().save(update_fields=['entry_number'])
		else:
			super().save(*args, **kwargs)

	@property
	def total_debit(self):
		from decimal import Decimal
		return sum((item.debit for item in self.items.all()), Decimal('0.00'))

	@property
	def total_credit(self):
		from decimal import Decimal
		return sum((item.credit for item in self.items.all()), Decimal('0.00'))

	@property
	def is_balanced(self):
		from decimal import Decimal
		return abs(self.total_debit - self.total_credit) < Decimal('0.01')


class JournalItem(models.Model):
	entry = models.ForeignKey(JournalEntry, on_delete=models.CASCADE, related_name='items')
	account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name='journal_items')
	party = models.ForeignKey('core.Party', on_delete=models.SET_NULL, null=True, blank=True, related_name='journal_items')
	debit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
	credit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
	memo = models.CharField(max_length=255, blank=True)

	class Meta:
		verbose_name = 'Journal Line Item'
		verbose_name_plural = 'Journal Line Items'

	def __str__(self):
		dr_cr = f"DR: ₹{self.debit}" if self.debit > 0 else f"CR: ₹{self.credit}"
		return f"{self.account.name} | {dr_cr}"


# ==============================================================================
# CORPORATE GST B2B INVOICE & NIC E-WAY BILL SYSTEM
# ==============================================================================

class CorporateGSTInvoice(models.Model):
	INVOICE_TYPES = [
		('regular_b2b', 'Regular B2B Tax Invoice'),
		('b2c', 'B2C Retail Invoice'),
		('sez_with_payment', 'SEZ Unit / Developer (With Tax Payment)'),
		('sez_without_payment', 'SEZ Unit / Developer (Without Tax Payment / LUT)'),
		('deemed_export', 'Deemed Export'),
	]
	SUPPLY_TYPES = [
		('intra_state', 'Intra-State (CGST + SGST)'),
		('inter_state', 'Inter-State (IGST)'),
	]
	PAYMENT_STATUSES = [
		('unpaid', 'Unpaid'),
		('partially_paid', 'Partially Paid'),
		('paid', 'Paid'),
	]

	invoice_number = models.CharField(max_length=50, unique=True, blank=True)
	invoice_date = models.DateField(default=timezone.now)
	due_date = models.DateField(blank=True, null=True)
	invoice_type = models.CharField(max_length=30, choices=INVOICE_TYPES, default='regular_b2b')

	# Linkages
	party = models.ForeignKey('core.Party', on_delete=models.PROTECT, related_name='corporate_invoices')
	trip = models.ForeignKey('operations.Trip', on_delete=models.SET_NULL, null=True, blank=True, related_name='gst_invoices')
	transport_contract = models.ForeignKey('fleet_contracts.TransportContract', on_delete=models.SET_NULL, null=True, blank=True, related_name='gst_invoices')
	statement = models.ForeignKey('statements.GeneratedStatement', on_delete=models.SET_NULL, null=True, blank=True, related_name='gst_invoices')

	# Supplier Info (Siva Gayathiri Tours & Travels)
	supplier_legal_name = models.CharField(max_length=255, default="Siva Gayathiri Tours & Travels")
	supplier_trade_name = models.CharField(max_length=255, default="Sivagayathiri Travels")
	supplier_gstin = models.CharField(max_length=15, default="33AAAAA0000A1Z5")
	supplier_state_code = models.CharField(max_length=2, default="33", help_text="e.g. 33 for Tamil Nadu")
	supplier_address = models.TextField(default="12/4, Gandhi Road, Chennai, Tamil Nadu - 600001")
	supplier_pincode = models.CharField(max_length=6, default="600001")

	# Recipient / Corporate Customer Info
	recipient_legal_name = models.CharField(max_length=255)
	recipient_trade_name = models.CharField(max_length=255, blank=True)
	recipient_gstin = models.CharField(max_length=15, blank=True, help_text="15-character GSTIN. Blank if unregistered / B2C")
	recipient_state_code = models.CharField(max_length=2, default="33", help_text="2-digit state code of place of supply")
	recipient_address = models.TextField(blank=True)
	recipient_pincode = models.CharField(max_length=6, blank=True)
	place_of_supply = models.CharField(max_length=100, default="33-Tamil Nadu")

	# Taxation Terms
	is_reverse_charge = models.BooleanField(default=False, help_text="Tax payable under Reverse Charge (RCM)")
	sac_code = models.CharField(max_length=10, default="996601", help_text="Transport Service Accounting Code (SAC)")
	supply_type = models.CharField(max_length=20, choices=SUPPLY_TYPES, default='intra_state')

	# Monetary Breakdown
	taxable_value = models.DecimalField(max_digits=12, decimal_places=2, default=0)
	gst_rate_percent = models.DecimalField(max_digits=5, decimal_places=2, default=5.00)
	cgst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=2.50)
	cgst_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
	sgst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=2.50)
	sgst_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
	igst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
	igst_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
	cess_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
	total_tax = models.DecimalField(max_digits=12, decimal_places=2, default=0)
	round_off = models.DecimalField(max_digits=6, decimal_places=2, default=0)
	total_invoice_value = models.DecimalField(max_digits=12, decimal_places=2, default=0)

	# Payment & GL Sync
	payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUSES, default='unpaid')
	paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
	gl_journal_entry = models.ForeignKey(JournalEntry, on_delete=models.SET_NULL, null=True, blank=True, related_name='gst_invoices')
	qr_code_data = models.TextField(blank=True, help_text="B2B digital verification payload")
	qr_code_svg = models.TextField(blank=True, help_text="Vector SVG QR code representation")

	# Timestamps
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ['-invoice_date', '-id']
		verbose_name = 'Corporate GST B2B Invoice'
		verbose_name_plural = 'Corporate GST B2B Invoices'

	def __str__(self):
		return f"{self.invoice_number or f'INV-{self.pk}'} - {self.recipient_legal_name} (₹{self.total_invoice_value})"

	def compute_taxes(self):
		"""Computes CGST, SGST, IGST based on place of supply alignment."""
		supp_state = (self.supplier_state_code or "33").strip()
		recip_state = (self.recipient_state_code or "33").strip()

		if supp_state == recip_state:
			self.supply_type = 'intra_state'
			self.cgst_rate = self.gst_rate_percent / Decimal('2.00')
			self.sgst_rate = self.gst_rate_percent / Decimal('2.00')
			self.igst_rate = Decimal('0.00')
			self.cgst_amount = (self.taxable_value * self.cgst_rate) / Decimal('100.00')
			self.sgst_amount = (self.taxable_value * self.sgst_rate) / Decimal('100.00')
			self.igst_amount = Decimal('0.00')
		else:
			self.supply_type = 'inter_state'
			self.cgst_rate = Decimal('0.00')
			self.sgst_rate = Decimal('0.00')
			self.igst_rate = self.gst_rate_percent
			self.cgst_amount = Decimal('0.00')
			self.sgst_amount = Decimal('0.00')
			self.igst_amount = (self.taxable_value * self.igst_rate) / Decimal('100.00')

		self.total_tax = self.cgst_amount + self.sgst_amount + self.igst_amount + (self.cess_amount or Decimal('0.00'))
		unrounded = self.taxable_value + self.total_tax
		rounded = unrounded.quantize(Decimal('1'), rounding='ROUND_HALF_UP')
		self.round_off = rounded - unrounded
		self.total_invoice_value = rounded

	def save(self, *args, **kwargs):
		self.compute_taxes()
		is_new = self.pk is None
		super().save(*args, **kwargs)
		if not self.invoice_number:
			year_str = timezone.now().strftime('%y')
			next_year = str(int(year_str) + 1).zfill(2)
			fy_str = f"{year_str}-{next_year}"
			self.invoice_number = f"SGT/{fy_str}/{self.pk:05d}"
			super().save(update_fields=['invoice_number'])


class InvoiceLineItem(models.Model):
	invoice = models.ForeignKey(CorporateGSTInvoice, on_delete=models.CASCADE, related_name='line_items')
	item_description = models.CharField(max_length=255)
	sac_code = models.CharField(max_length=10, default="996601")
	vehicle = models.ForeignKey('core.Vehicle', on_delete=models.SET_NULL, null=True, blank=True)
	trip = models.ForeignKey('operations.Trip', on_delete=models.SET_NULL, null=True, blank=True)
	quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
	unit = models.CharField(max_length=10, default="TRIP")
	rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
	taxable_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
	cgst_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
	sgst_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
	igst_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
	total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

	class Meta:
		verbose_name = 'Invoice Line Item'
		verbose_name_plural = 'Invoice Line Items'

	def __str__(self):
		return f"{self.item_description} (₹{self.total_amount})"


class EWayBill(models.Model):
	STATUS_CHOICES = [
		('draft', 'Draft / Generated'),
		('active', 'Active & Valid'),
		('expired', 'Expired'),
		('cancelled', 'Cancelled'),
	]
	eway_bill_number = models.CharField(max_length=12, unique=True, blank=True, null=True, help_text="12-digit NIC E-Way Bill Number")
	eway_bill_date = models.DateTimeField(default=timezone.now)
	valid_until = models.DateTimeField(blank=True, null=True)
	status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')

	invoice = models.OneToOneField(CorporateGSTInvoice, on_delete=models.CASCADE, related_name='eway_bill')

	supply_type = models.CharField(max_length=10, default="O", help_text="O - Outward, I - Inward")
	sub_supply_type = models.CharField(max_length=5, default="1", help_text="1 - Supply")
	doc_type = models.CharField(max_length=5, default="INV", help_text="INV - Tax Invoice")

	transporter_id = models.CharField(max_length=15, blank=True, default="33AAAAA0000A1Z5")
	transporter_name = models.CharField(max_length=100, default="Siva Gayathiri Tours & Travels")
	trans_distance_km = models.PositiveIntegerField(default=50, help_text="Approximate transportation distance in KM")
	trans_mode = models.CharField(max_length=2, default="1", help_text="1 - Road")
	vehicle_number = models.CharField(max_length=20)
	vehicle_type = models.CharField(max_length=2, default="R", choices=[('R', 'Regular'), ('O', 'Over Dimensional Cargo')])

	nic_payload_json = models.JSONField(default=dict, help_text="NIC E-Way Bill Schema v1.04 JSON")
	nic_response_json = models.JSONField(default=dict, blank=True)
	qr_code_svg = models.TextField(blank=True)

	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ['-eway_bill_date', '-id']
		verbose_name = 'NIC E-Way Bill'
		verbose_name_plural = 'NIC E-Way Bills'

	def __str__(self):
		return f"EWB #{self.eway_bill_number or 'Draft'} - {self.vehicle_number} ({self.get_status_display()})"

	def save(self, *args, **kwargs):
		if not self.valid_until:
			# Rule 138(10): For normal cargo, 1 day for every 200 km or part thereof, min 24h
			days = max(1, (self.trans_distance_km + 199) // 200)
			self.valid_until = timezone.now() + timezone.timedelta(days=days)
		if not self.eway_bill_number:
			# 12-digit NIC format: State Code (2 digits) + 10 digits
			import time
			state = (self.invoice.supplier_state_code or "33").zfill(2)
			suffix = str(int(time.time() * 1000))[-10:]
			self.eway_bill_number = f"{state}{suffix}"
		super().save(*args, **kwargs)


# ==============================================================================
# Phase 5: Petty Cash Float Register & Driver/Tour Manager Cash Wallet Digital Twin
# ==============================================================================

class PettyCashAccount(models.Model):
	ACCOUNT_TYPES = [
		('branch', '🏢 Branch / Garage Float'),
		('driver', '🧑‍✈️ Driver / Tour Pilot Float'),
		('tour_manager', '🧭 Tour Manager / Guide Float'),
		('dispatcher', '📡 Dispatcher Emergency Float'),
	]

	account_name = models.CharField(max_length=255, help_text="e.g. Coimbatore Main Depot Float or Driver Karthik Murugan")
	account_type = models.CharField(max_length=30, choices=ACCOUNT_TYPES, default='driver')
	holder_user = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='held_petty_cash_accounts')
	holder_driver = models.ForeignKey('core.Driver', on_delete=models.SET_NULL, null=True, blank=True, related_name='held_petty_cash_accounts')
	allocated_limit = models.DecimalField(max_digits=12, decimal_places=2, default=10000, help_text="Maximum sanctioned float cap (₹)")
	opening_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Initial float deposit (₹)")
	current_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Live running available cash balance (₹)")
	warning_threshold = models.DecimalField(max_digits=12, decimal_places=2, default=1500, help_text="Low cash balance alert trigger (₹)")
	is_active = models.BooleanField(default=True)
	notes = models.TextField(blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ['account_type', 'account_name']
		verbose_name = 'Petty Cash Account'
		verbose_name_plural = 'Petty Cash Accounts (Floats)'

	def __str__(self):
		return f"{self.account_name} ({self.get_account_type_display()}): ₹{self.current_balance:,.2f}"

	@property
	def is_low_balance(self):
		return self.current_balance <= self.warning_threshold

	def recalculate_balance(self):
		"""Recalculate balance from all approved/submitted transactions."""
		inflow = self.transactions.filter(
			transaction_type__in=['top_up', 'settlement_refund', 'adjustment'],
			status__in=['approved', 'submitted']
		).aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')

		outflow = self.transactions.filter(
			transaction_type__in=['expense', 'trip_advance'],
			status__in=['approved', 'submitted']
		).aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')

		self.current_balance = (self.opening_balance or Decimal('0.00')) + inflow - outflow
		self.save(update_fields=['current_balance', 'updated_at'])
		return self.current_balance

	def save(self, *args, **kwargs):
		if self.pk is None and not self.opening_balance and self.current_balance:
			self.opening_balance = self.current_balance
		super().save(*args, **kwargs)


class PettyCashTransaction(models.Model):
	TRANSACTION_TYPES = [
		('top_up', '📥 Cash Top-Up / Replenishment (Inflow)'),
		('expense', '📤 Out-of-Pocket Expense (Outflow)'),
		('trip_advance', '🛣️ Trip Cash Advance Issued (Outflow)'),
		('settlement_refund', '🔁 Cash Surrender / Return (Inflow)'),
		('adjustment', '⚖️ Audit Balance Adjustment'),
	]

	EXPENSE_CATEGORIES = [
		('fuel', '⛽ Emergency Fuel / Diesel'),
		('toll_parking', '🛣️ Highway Toll & Airport/Station Parking'),
		('police_challan', '🚨 Spot Traffic Police Challan / Fine'),
		('vehicle_repair', '🔧 Emergency Tyre Puncture / Bulb / Breakdown'),
		('driver_food', '🍱 Driver Food / Batta / Night Halt Refreshment'),
		('hotel_misc', '🏨 Guest Porterage / Emergency Lodging / Tea'),
		('office_supplies', '📎 Stationery / Garage Cleaning / Consumables'),
		('client_entertain', '☕ Client Courtesy / Welcome Drinks'),
		('top_up_receipt', '💵 Cash Handover / Float Replenishment'),
		('other', '📝 Other Discretionary Expense'),
	]

	STATUS_CHOICES = [
		('draft', 'Draft Entry'),
		('submitted', 'Pending Audit Review'),
		('approved', '✅ Audit Approved'),
		('rejected', '❌ Rejected'),
	]

	voucher_number = models.CharField(max_length=50, unique=True, blank=True, help_text="e.g. PCV-2026-0001")
	account = models.ForeignKey(PettyCashAccount, on_delete=models.CASCADE, related_name='transactions')
	transaction_type = models.CharField(max_length=30, choices=TRANSACTION_TYPES, default='expense')
	category = models.CharField(max_length=30, choices=EXPENSE_CATEGORIES, default='toll_parking')
	amount = models.DecimalField(max_digits=12, decimal_places=2, help_text="Amount in ₹")
	balance_after = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Running float balance after transaction")
	date = models.DateField(default=timezone.now)
	recipient_or_vendor = models.CharField(max_length=255, blank=True, help_text="Vendor or person paid/received e.g. NHAI Fastag Cash, Tyre Works")
	trip = models.ForeignKey('operations.Trip', on_delete=models.SET_NULL, null=True, blank=True, related_name='petty_cash_expenses')
	receipt_photo = models.ImageField(upload_to='petty_cash_receipts/', null=True, blank=True, help_text="Bill receipt or voucher photograph")
	notes = models.TextField(blank=True, help_text="Detailed explanation of purchase / reason")
	status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='approved')
	authorized_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='authorized_petty_cash_txns')
	audit_notes = models.TextField(blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ['-date', '-created_at']
		verbose_name = 'Petty Cash Voucher Transaction'
		verbose_name_plural = 'Petty Cash Voucher Transactions'

	def __str__(self):
		sign = "+" if self.transaction_type in ['top_up', 'settlement_refund', 'adjustment'] else "-"
		return f"{self.voucher_number or 'Voucher'} [{self.get_category_display()}]: {sign}₹{self.amount} ({self.account.account_name})"

	def save(self, *args, **kwargs):
		if not self.voucher_number:
			import time
			year = timezone.now().year
			seq = int(time.time() * 1000) % 100000
			self.voucher_number = f"PCV-{year}-{seq:05d}"

		super().save(*args, **kwargs)
		# Automatically update account balance
		self.account.recalculate_balance()
		if self.balance_after != self.account.current_balance:
			PettyCashTransaction.objects.filter(pk=self.pk).update(balance_after=self.account.current_balance)



