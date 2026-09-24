from django.db import models
from django.contrib.auth.models import User
from core.models import Driver


class DriverPortalAccount(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='driver_portal_account')
    driver = models.OneToOneField(Driver, on_delete=models.CASCADE, related_name='portal_account')
    quick_pin = models.CharField(max_length=6, default='1234', help_text="4 or 6-digit login PIN")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_login_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Driver Portal Account"
        verbose_name_plural = "Driver Portal Accounts"

    def __str__(self):
        return f"Portal: {self.driver.name} ({self.driver.phone})"
