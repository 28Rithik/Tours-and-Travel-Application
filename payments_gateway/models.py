from django.db import models
from operations.models import Booking

class InstallmentPlan(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='installment_plans')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    number_of_installments = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Installment Plan for {self.booking.booking_number}"

class PaymentLink(models.Model):
    STATUS_CHOICES = [('created', 'Created'), ('paid', 'Paid'), ('expired', 'Expired'), ('cancelled', 'Cancelled')]
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='payment_links')
    installment_plan = models.ForeignKey(InstallmentPlan, on_delete=models.SET_NULL, null=True, blank=True, related_name='payment_links')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    razorpay_link_id = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='created')
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Payment Link {self.razorpay_link_id} for {self.booking.booking_number}"

class PaymentWebhookEvent(models.Model):
    event_id = models.CharField(max_length=100, unique=True)
    event_type = models.CharField(max_length=100)
    payload = models.JSONField()
    processed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.event_id
