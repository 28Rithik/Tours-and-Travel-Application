from django.db import models
from django.contrib.auth.models import User
from core.models import Client

class CustomerAccount(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='customer_profile')
    client_record = models.OneToOneField(Client, on_delete=models.CASCADE, related_name='portal_account')
    is_email_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Portal Account for {self.client_record.name}"
