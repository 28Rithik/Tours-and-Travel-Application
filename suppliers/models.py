from django.db import models
from core.models import Supplier

class SupplierContract(models.Model):
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='contracts')
    title = models.CharField(max_length=255)
    valid_from = models.DateField()
    valid_to = models.DateField()
    contract_document = models.FileField(upload_to='supplier_contracts/', null=True, blank=True)
    is_active = models.BooleanField(default=True)

class CommissionRule(models.Model):
    agent_name = models.CharField(max_length=255)
    commission_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    is_active = models.BooleanField(default=True)
