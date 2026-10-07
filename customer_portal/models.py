from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from core.models import Client

class CustomerAccount(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='customer_profile')
    client_record = models.OneToOneField(Client, on_delete=models.CASCADE, related_name='portal_account')
    is_email_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Portal Account for {self.client_record.name}"


class CustomerOTP(models.Model):
    """
    Stores 6-digit one-time passwords for mobile phone self-registration and passwordless login.
    Valid for 10 minutes.
    """
    phone = models.CharField(max_length=20, db_index=True)
    otp_code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_verified = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Customer Mobile OTP'
        verbose_name_plural = 'Customer Mobile OTPs'

    def is_valid(self):
        return not self.is_verified and timezone.now() <= self.expires_at

    def __str__(self):
        return f"OTP for {self.phone} - {'Verified' if self.is_verified else 'Pending'}"

