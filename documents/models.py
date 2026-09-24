from django.db import models
from core.models import Client
from operations.models import Booking

class CustomerDocument(models.Model):
    DOCUMENT_TYPES = [
        ('visa', 'Visa Copy'),
        ('ticket', 'E-Ticket'),
        ('voucher', 'Booking Voucher'),
        ('insurance', 'Travel Insurance'),
        ('other', 'Other Document')
    ]
    customer = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='documents')
    booking = models.ForeignKey(Booking, on_delete=models.SET_NULL, null=True, blank=True, related_name='documents')
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES, default='other')
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='customer_documents/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} for {self.customer.name}"
