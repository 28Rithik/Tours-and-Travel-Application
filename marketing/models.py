from django.db import models
from packages.models import Package

class Coupon(models.Model):
    code = models.CharField(max_length=20, unique=True)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    flat_discount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    applicable_package = models.ForeignKey(Package, on_delete=models.SET_NULL, null=True, blank=True)
    usage_limit = models.PositiveIntegerField(null=True, blank=True)
    used_count = models.PositiveIntegerField(default=0)
    expiry_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

class EmailCampaign(models.Model):
    name = models.CharField(max_length=255)
    subject = models.CharField(max_length=255)
    body_html = models.TextField()
    sent_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

class UpsellRecommendation(models.Model):
    package = models.ForeignKey(Package, on_delete=models.CASCADE, related_name='upsells')
    title = models.CharField(max_length=255)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
