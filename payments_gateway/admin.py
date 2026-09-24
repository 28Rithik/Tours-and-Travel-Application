from django.contrib import admin
from .models import InstallmentPlan, PaymentLink, PaymentWebhookEvent

# ──────────────────────────────────────────────────────────────────────────
# HIDDEN: These models now appear under "Digital Collections & Guest Portal"
# via proxy models in digital_services/models.py. Registrations kept for
# autocomplete and foreign-key lookups.
# ──────────────────────────────────────────────────────────────────────────

@admin.register(InstallmentPlan)
class InstallmentPlanAdmin(admin.ModelAdmin):
    list_display = ('booking', 'total_amount', 'number_of_installments', 'is_active')
    list_filter = ('is_active',)

    def has_module_permission(self, request):
        return False


@admin.register(PaymentLink)
class PaymentLinkAdmin(admin.ModelAdmin):
    list_display = ('booking', 'amount', 'status', 'razorpay_link_id', 'created_at')
    list_filter = ('status',)
    search_fields = ('booking__booking_number', 'razorpay_link_id')

    def has_module_permission(self, request):
        return False


@admin.register(PaymentWebhookEvent)
class PaymentWebhookEventAdmin(admin.ModelAdmin):
    list_display = ('event_id', 'event_type', 'processed', 'created_at')
    list_filter = ('event_type', 'processed')
    search_fields = ('event_id',)

    def has_module_permission(self, request):
        return False
