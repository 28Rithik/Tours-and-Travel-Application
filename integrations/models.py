import datetime
from decimal import Decimal
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class IntegrationSettings(models.Model):
    """
    Centralized Enterprise Configuration for External Communication Channels,
    Meta Lead Ads, WhatsApp Gateways, Google Sheets, and Email SMTP/SES.
    """
    # 1. Email Service Configuration (SES / SMTP)
    SMTP_HOST_CHOICES = [
        ('smtp.gmail.com', 'Google Gmail / Google Workspace (smtp.gmail.com)'),
        ('email-smtp.us-east-1.amazonaws.com', 'Amazon SES US-East-1 (AWS)'),
        ('email-smtp.ap-south-1.amazonaws.com', 'Amazon SES Mumbai (AWS India)'),
        ('smtp.sendgrid.net', 'Twilio SendGrid (smtp.sendgrid.net)'),
        ('smtp.zoho.com', 'Zoho Mail (smtp.zoho.com)'),
        ('smtp.office365.com', 'Microsoft 365 / Outlook (smtp.office365.com)'),
        ('custom', 'Custom Dedicated SMTP Host'),
    ]
    ENCRYPTION_CHOICES = [
        ('tls', 'TLS (Recommended, Port 587)'),
        ('ssl', 'SSL (Port 465)'),
        ('none', 'None (Unencrypted, Port 25)'),
    ]

    smtp_host = models.CharField(max_length=255, default='smtp.gmail.com')
    smtp_port = models.PositiveIntegerField(default=587)
    smtp_encryption = models.CharField(max_length=10, choices=ENCRYPTION_CHOICES, default='tls')
    smtp_username = models.CharField(max_length=255, blank=True, help_text="e.g. sapnasharma3355@gmail.com")
    smtp_password = models.CharField(max_length=255, blank=True, help_text="SMTP Application Password")
    sender_email = models.EmailField(default='notifications@sivagayathiritravels.com')
    sender_name = models.CharField(max_length=255, default='Customer Support')
    email_active = models.BooleanField(default=True, verbose_name="Email Service Active")
    email_daily_limit = models.PositiveIntegerField(default=10000)
    emails_sent_today = models.PositiveIntegerField(default=0)
    last_email_sent_at = models.DateTimeField(null=True, blank=True)

    # 2. Meta Lead Ads (Facebook & Instagram Webhook)
    meta_app_id = models.CharField(max_length=100, blank=True)
    meta_app_secret = models.CharField(max_length=100, blank=True)
    meta_verify_token = models.CharField(max_length=100, default='siva_meta_lead_verify_token')
    meta_page_access_token = models.TextField(blank=True)
    meta_form_id = models.CharField(max_length=100, blank=True, help_text="Target Meta Lead Form ID")
    meta_active = models.BooleanField(default=True, verbose_name="Meta Lead Ads Active")
    meta_leads_imported = models.PositiveIntegerField(default=0)
    last_meta_lead_at = models.DateTimeField(null=True, blank=True)

    # 3. Google Sheets 5-Minute Auto-Import
    google_sheet_url = models.URLField(
        blank=True,
        default='https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/export?format=csv',
        help_text="Google Sheet Published CSV URL or Public Sharing Link"
    )
    google_sheet_name = models.CharField(max_length=100, default='Inquiries')
    google_sheet_sync_minutes = models.PositiveIntegerField(default=5)
    google_sheet_active = models.BooleanField(default=True, verbose_name="Google Sheet Sync Active")
    google_sheet_last_synced = models.DateTimeField(null=True, blank=True)
    google_sheet_rows_imported = models.PositiveIntegerField(default=0)

    # 4. WhatsApp Multi-Vendor Gateway
    WHATSAPP_VENDOR_CHOICES = [
        ('simulator', 'Internal Simulator (Zero Setup Cost)'),
        ('meta_cloud', 'Official WhatsApp Business (Meta Cloud API)'),
        ('aisensy', 'AiSensy Partner Gateway (https://aisensy.com)'),
        ('msg91', 'MSG91 Enterprise WhatsApp (https://msg91.com)'),
        ('wati', 'WATI WhatsApp Team Inbox (https://wati.io)'),
    ]
    whatsapp_vendor = models.CharField(max_length=30, choices=WHATSAPP_VENDOR_CHOICES, default='simulator')
    whatsapp_api_key = models.CharField(max_length=255, blank=True)
    whatsapp_phone_number_id = models.CharField(max_length=100, blank=True, help_text="Meta Phone Number ID or Vendor Sender ID")
    whatsapp_business_account_id = models.CharField(max_length=100, blank=True)
    whatsapp_active = models.BooleanField(default=True, verbose_name="WhatsApp Gateway Active")
    whatsapp_messages_sent = models.PositiveIntegerField(default=0)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Integration & Channel Settings'
        verbose_name_plural = 'Integration & Channel Settings'

    def __str__(self):
        return f"Sivagayathiri Omnichannel Integration Hub (SMTP: {self.smtp_host} | WA: {self.get_whatsapp_vendor_display()})"

    @classmethod
    def get_settings(cls):
        """Singleton getter: ensures an instance always exists."""
        obj, created = cls.objects.get_or_create(id=1)
        return obj


class LeadIngestionLog(models.Model):
    """
    Audit ledger tracking every inbound lead payload captured from Meta Ads,
    Google Sheets, WhatsApp, or Website booking forms.
    """
    SOURCE_CHOICES = [
        ('meta_lead_ads', '📱 Meta Lead Ads (Facebook / Instagram)'),
        ('google_sheets', '📊 Google Sheets 5-Min Sync'),
        ('whatsapp_inbound', '💬 WhatsApp Inbound Message'),
        ('website_form', '🌐 Website Inquiry Form'),
        ('manual', '🏢 Direct Manual Entry'),
    ]
    STATUS_CHOICES = [
        ('success', '🟢 Success (Inquiry Created)'),
        ('duplicate', '🟡 Duplicate (Merged/Skipped)'),
        ('failed', '🔴 Failed (Parsing Error)'),
    ]

    source = models.CharField(max_length=30, choices=SOURCE_CHOICES, default='meta_lead_ads')
    external_lead_id = models.CharField(max_length=100, blank=True, db_index=True)
    lead_name = models.CharField(max_length=255, blank=True)
    lead_phone = models.CharField(max_length=30, blank=True)
    lead_email = models.CharField(max_length=150, blank=True)
    destination = models.CharField(max_length=255, blank=True)
    raw_payload = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='success')
    error_message = models.TextField(blank=True)
    created_inquiry = models.ForeignKey(
        'crm.Inquiry',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ingestion_logs'
    )
    received_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-received_at']
        verbose_name = 'Lead Ingestion Log'
        verbose_name_plural = 'Lead Ingestion Logs'

    def __str__(self):
        return f"[{self.get_source_display()}] {self.lead_name} ({self.lead_phone}) - {self.get_status_display()}"


class ApprovalRequest(models.Model):
    """
    Enterprise Manager Approval Workflow for:
      1. High Quotation Discounts (> 15% discount)
      2. Corporate Credit Limit Overrides
      3. Driver & Fleet Emergency Petty Cash Advances
    """
    APPROVAL_TYPES = [
        ('discount_override', '🏷️ Quotation Discount Override (> 15%)'),
        ('credit_limit', '💳 Corporate Credit Extension / Unbilled Booking'),
        ('driver_advance', '⛽ Driver Emergency Petty Cash Advance'),
        ('rate_override', '📉 Custom Tariff Below Floor Price'),
    ]
    STATUS_CHOICES = [
        ('pending', '🟡 Pending Review'),
        ('approved', '🟢 Approved by Manager'),
        ('rejected', '🔴 Rejected'),
    ]

    approval_number = models.CharField(max_length=30, unique=True, blank=True)
    approval_type = models.CharField(max_length=30, choices=APPROVAL_TYPES, default='discount_override')
    title = models.CharField(max_length=255, help_text="e.g. 18% Special Discount for PSG College IV")
    description = models.TextField(blank=True)
    requested_amount_or_pct = models.CharField(max_length=50, help_text="e.g. 18.5% or ₹15,000")
    
    # Associated Entities
    related_quotation = models.ForeignKey('crm.Quotation', on_delete=models.SET_NULL, null=True, blank=True, related_name='approval_requests')
    related_party = models.ForeignKey('core.Party', on_delete=models.SET_NULL, null=True, blank=True, related_name='approval_requests')
    related_trip = models.ForeignKey('operations.Trip', on_delete=models.SET_NULL, null=True, blank=True, related_name='approval_requests')
    
    requested_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='requested_approvals')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='actioned_approvals')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    manager_notes = models.TextField(blank=True, help_text="Justification or conditions for approval/rejection")
    
    created_at = models.DateTimeField(auto_now_add=True)
    actioned_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Manager Approval Request'
        verbose_name_plural = 'Manager Approvals'

    def __str__(self):
        return f"{self.approval_number}: {self.title} [{self.get_status_display()}]"

    def save(self, *args, **kwargs):
        if not self.approval_number:
            year = timezone.now().year
            last_app = ApprovalRequest.objects.order_by('-id').first()
            next_idx = (last_app.id + 1) if last_app else 1
            self.approval_number = f"APP-{year}-{next_idx:04d}"
        super().save(*args, **kwargs)
