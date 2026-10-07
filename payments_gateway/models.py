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


class PaymentGatewayConfig(models.Model):
    PROVIDER_CHOICES = [
        ('razorpay', 'Razorpay Payments'),
        ('cashfree', 'Cashfree Payments'),
        ('direct_upi', 'Direct Dynamic UPI'),
        ('offline', 'Offline / Cash Desk'),
    ]
    provider = models.CharField(max_length=30, choices=PROVIDER_CHOICES, unique=True)
    name = models.CharField(max_length=150)
    is_active = models.BooleanField(default=True)
    is_sandbox = models.BooleanField(default=True, help_text="Toggle between Sandbox/Test and Production Live mode")
    api_key = models.CharField(max_length=150, blank=True, help_text="Key ID / App ID")
    api_secret = models.CharField(max_length=150, blank=True, help_text="Key Secret / Secret Key")
    webhook_secret = models.CharField(max_length=150, blank=True, help_text="Shared secret for HMAC verification")
    upi_vpa = models.CharField(max_length=100, default='sivagayathiritravels@icici', help_text="Virtual Payment Address / UPI ID")
    merchant_name = models.CharField(max_length=150, default='Sivagayathiri Travels', help_text="Merchant Name displayed on UPI checkout apps")
    mcc_code = models.CharField(max_length=10, default='4121', help_text="Merchant Category Code (4121 = Passenger Transport)")
    gateway_fee_percent = models.DecimalField(max_digits=5, decimal_places=2, default=1.75, help_text="Default MDR fee percentage (e.g. 1.75%)")
    gst_on_fee_percent = models.DecimalField(max_digits=5, decimal_places=2, default=18.00, help_text="GST percentage on gateway fee (usually 18%)")
    auto_post_to_gl = models.BooleanField(default=True, help_text="Automatically post balanced Journal Entry to General Ledger on successful capture")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Payment Gateway Configuration'
        verbose_name_plural = 'Payment Gateway Configurations'

    def __str__(self):
        env = "Sandbox" if self.is_sandbox else "Live"
        status = "Active" if self.is_active else "Disabled"
        return f"{self.name} ({env} · {status})"


class GatewayTransaction(models.Model):
    STATUS_CHOICES = [
        ('created', 'Created'),
        ('pending', 'Pending Verification'),
        ('authorized', 'Authorized'),
        ('captured', 'Captured & Cleared'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    PROVIDER_CHOICES = [
        ('razorpay', 'Razorpay'),
        ('cashfree', 'Cashfree'),
        ('direct_upi', 'Direct Dynamic UPI'),
    ]
    transaction_id = models.CharField(max_length=100, unique=True)
    provider = models.CharField(max_length=30, choices=PROVIDER_CHOICES)
    gateway_order_id = models.CharField(max_length=100, blank=True)
    gateway_payment_id = models.CharField(max_length=100, blank=True, help_text="External payment ID or UPI 12-digit UTR/RRN")
    booking = models.ForeignKey(Booking, on_delete=models.SET_NULL, null=True, blank=True, related_name='gateway_transactions')
    trip = models.ForeignKey('operations.Trip', on_delete=models.SET_NULL, null=True, blank=True, related_name='gateway_transactions')
    statement = models.ForeignKey('statements.GeneratedStatement', on_delete=models.SET_NULL, null=True, blank=True, related_name='gateway_transactions')
    party = models.ForeignKey('core.Party', on_delete=models.PROTECT, null=True, blank=True, related_name='gateway_transactions')
    gross_amount = models.DecimalField(max_digits=12, decimal_places=2)
    fee_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    net_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency = models.CharField(max_length=10, default='INR')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='created')
    upi_intent_url = models.TextField(blank=True, help_text="Indian NPCI UPI intent URL")
    payment_record = models.OneToOneField('finance.Payment', on_delete=models.SET_NULL, null=True, blank=True, related_name='gateway_transaction')
    journal_entry = models.OneToOneField('finance.JournalEntry', on_delete=models.SET_NULL, null=True, blank=True, related_name='gateway_transaction')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    raw_response = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Gateway Transaction'
        verbose_name_plural = 'Gateway Transactions'

    def __str__(self):
        return f"{self.transaction_id} - ₹{self.gross_amount} ({self.get_status_display()})"

