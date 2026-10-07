from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import IntegrationSettings, LeadIngestionLog, ApprovalRequest


@admin.register(IntegrationSettings)
class IntegrationSettingsAdmin(ModelAdmin):
    list_display = ('__str__', 'smtp_host', 'sender_email', 'whatsapp_vendor', 'meta_active', 'google_sheet_active', 'updated_at')
    fieldsets = (
        ("Email Service Configuration (SES / SMTP)", {
            "fields": (
                "email_active",
                ("smtp_host", "smtp_port", "smtp_encryption"),
                ("smtp_username", "smtp_password"),
                ("sender_email", "sender_name"),
                ("email_daily_limit", "emails_sent_today", "last_email_sent_at"),
            )
        }),
        ("Meta Lead Ads (Facebook & Instagram Webhook)", {
            "fields": (
                "meta_active",
                ("meta_app_id", "meta_app_secret"),
                ("meta_verify_token", "meta_form_id"),
                "meta_page_access_token",
                ("meta_leads_imported", "last_meta_lead_at"),
            )
        }),
        ("Google Sheets 5-Minute Auto-Import", {
            "fields": (
                "google_sheet_active",
                ("google_sheet_url", "google_sheet_name"),
                ("google_sheet_sync_minutes", "google_sheet_rows_imported", "google_sheet_last_synced"),
            )
        }),
        ("WhatsApp Multi-Vendor Gateway", {
            "fields": (
                "whatsapp_active",
                "whatsapp_vendor",
                ("whatsapp_phone_number_id", "whatsapp_business_account_id"),
                "whatsapp_api_key",
                "whatsapp_messages_sent",
            )
        }),
    )


@admin.register(LeadIngestionLog)
class LeadIngestionLogAdmin(ModelAdmin):
    list_display = ('lead_name', 'lead_phone', 'lead_email', 'source', 'status', 'created_inquiry', 'received_at')
    list_filter = ('source', 'status', 'received_at')
    search_fields = ('lead_name', 'lead_phone', 'lead_email', 'external_lead_id', 'destination')
    readonly_fields = ('received_at',)


@admin.register(ApprovalRequest)
class ApprovalRequestAdmin(ModelAdmin):
    list_display = ('approval_number', 'title', 'approval_type', 'requested_amount_or_pct', 'requested_by', 'status', 'approved_by', 'created_at')
    list_filter = ('approval_type', 'status', 'created_at')
    search_fields = ('approval_number', 'title', 'requested_by__username', 'description')
    readonly_fields = ('approval_number', 'created_at', 'actioned_at')
