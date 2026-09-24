from django.db import models
from core.models import Driver, Party, Vehicle


class GeneratedStatement(models.Model):
	FORMATS = [('pdf', 'PDF'), ('excel', 'Excel')]
	party = models.ForeignKey(Party, on_delete=models.PROTECT, related_name='generated_statements', null=True, blank=True)
	transport_contract = models.ForeignKey('fleet_contracts.TransportContract', on_delete=models.PROTECT, related_name='generated_statements', null=True, blank=True)
	from_date = models.DateField()
	to_date = models.DateField()
	file_format = models.CharField(max_length=10, choices=FORMATS)
	generated_at = models.DateTimeField(auto_now_add=True)
	
	subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
	cgst_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
	sgst_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
	igst_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
	tds_deducted = models.DecimalField(max_digits=12, decimal_places=2, default=0)
	tcs_collected = models.DecimalField(max_digits=12, decimal_places=2, default=0)
	
	opening_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
	closing_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
	vehicle = models.ForeignKey(Vehicle, on_delete=models.SET_NULL, null=True, blank=True, related_name='generated_statements')
	driver = models.ForeignKey(Driver, on_delete=models.SET_NULL, null=True, blank=True, related_name='generated_statements')
	PAYMENT_STATUSES = [('unpaid', 'Unpaid'), ('partially_paid', 'Partially Paid'), ('paid', 'Paid')]
	status = models.CharField(max_length=30, choices=PAYMENT_STATUSES, default='unpaid')

	@property
	def amount_due(self):
		from finance.models import Payment
		total_received = Payment.objects.filter(statement=self).aggregate(total=models.Sum('amount'))['total'] or 0
		return max(0, self.closing_balance - total_received)
