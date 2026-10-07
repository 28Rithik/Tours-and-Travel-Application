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

    def __str__(self):
        return f"{self.code} ({self.discount_percent}% / ₹{self.flat_discount})"


class EmailCampaign(models.Model):
    name = models.CharField(max_length=255)
    subject = models.CharField(max_length=255)
    body_html = models.TextField()
    sent_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class UpsellRecommendation(models.Model):
    package = models.ForeignKey(Package, on_delete=models.CASCADE, related_name='upsells')
    title = models.CharField(max_length=255)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.title} (₹{self.price})"


class PromotionCampaign(models.Model):
    """
    Automated customer re-engagement & seasonal festival marketing campaign studio
    (Diwali, Pongal, Summer Holidays, Sabarimala, Corporate Retreats).
    """
    CHANNEL_CHOICES = [
        ('whatsapp', 'WhatsApp Broadcast'),
        ('sms', 'SMS Broadcast'),
        ('email', 'Email Newsletter'),
    ]
    AUDIENCE_CHOICES = [
        ('all_tourists', 'All Past Holiday Tour Customers'),
        ('corporate_clients', 'Corporate & Institution Coordinators'),
        ('cold_inquiries', 'Unconverted CRM Leads (Last 90 Days)'),
        ('frequent_cabs', 'Frequent Outstation Cab Renters'),
    ]
    STATUS_CHOICES = [
        ('draft', 'Draft Campaign'),
        ('scheduled', 'Scheduled'),
        ('active', 'Active / In Progress'),
        ('completed', 'Completed'),
    ]

    name = models.CharField(max_length=255)
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES, default='whatsapp')
    target_audience = models.CharField(max_length=30, choices=AUDIENCE_CHOICES, default='all_tourists')
    headline = models.CharField(max_length=255)
    message_body = models.TextField()
    coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True, related_name='campaigns')
    target_count = models.PositiveIntegerField(default=0)
    sent_count = models.PositiveIntegerField(default=0)
    click_count = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.channel}) - {self.status}"
