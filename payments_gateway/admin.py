from django.contrib import admin
from unfold.admin import ModelAdmin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from .models import (
    InstallmentPlan,
    PaymentLink,
    PaymentWebhookEvent,
    PaymentGatewayConfig,
    GatewayTransaction,
)

# ──────────────────────────────────────────────────────────────────────────
# HIDDEN: These models now appear under "Digital Collections & Guest Portal"
# via proxy models in digital_services/models.py. Registrations kept for
# autocomplete and foreign-key lookups.
# ──────────────────────────────────────────────────────────────────────────

@admin.register(InstallmentPlan)
class InstallmentPlanAdmin(ModelAdmin):
    list_display = ('booking', 'total_amount', 'number_of_installments', 'is_active')
    list_filter = ('is_active',)

    def has_module_permission(self, request):
        return False


@admin.register(PaymentLink)
class PaymentLinkAdmin(ModelAdmin):
    list_display = ('booking', 'amount', 'status', 'razorpay_link_id', 'created_at')
    list_filter = ('status',)
    search_fields = ('booking__booking_number', 'razorpay_link_id')

    def has_module_permission(self, request):
        return False


@admin.register(PaymentWebhookEvent)
class PaymentWebhookEventAdmin(ModelAdmin):
    list_display = ('event_id', 'event_type', 'processed', 'created_at')
    list_filter = ('event_type', 'processed')
    search_fields = ('event_id',)

    def has_module_permission(self, request):
        return False


@admin.register(PaymentGatewayConfig)
class PaymentGatewayConfigAdmin(ModelAdmin):
    list_display = ('name', 'provider_badge', 'is_sandbox_badge', 'upi_vpa', 'fee_display', 'auto_post_to_gl', 'is_active')
    list_filter = ('provider', 'is_sandbox', 'is_active', 'auto_post_to_gl')
    search_fields = ('name', 'upi_vpa', 'merchant_name')

    @admin.display(description='Provider')
    def provider_badge(self, obj):
        colors = {
            'razorpay': 'bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20',
            'cashfree': 'bg-purple-500/10 text-purple-600 dark:text-purple-400 border border-purple-500/20',
            'direct_upi': 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20',
            'offline': 'bg-gray-500/10 text-gray-600 dark:text-gray-400 border border-gray-500/20',
        }
        style = colors.get(obj.provider, 'bg-gray-100 text-gray-700')
        return format_html('<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold {}">{}</span>', style, obj.get_provider_display())

    @admin.display(description='Mode')
    def is_sandbox_badge(self, obj):
        if obj.is_sandbox:
            return mark_safe('<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-bold bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20">TEST / SANDBOX</span>')
        return mark_safe('<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-bold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">PRODUCTION LIVE</span>')

    @admin.display(description='MDR Fee')
    def fee_display(self, obj):
        return f"{obj.gateway_fee_percent}% (+{obj.gst_on_fee_percent}% GST)"


@admin.register(GatewayTransaction)
class GatewayTransactionAdmin(ModelAdmin):
    list_display = ('transaction_id', 'provider_badge', 'gross_amount_display', 'status_badge', 'booking_ref', 'payment_id_display', 'gl_status_badge', 'created_at')
    list_filter = ('provider', 'status', 'created_at')
    search_fields = ('transaction_id', 'gateway_order_id', 'gateway_payment_id', 'booking__booking_number')

    @admin.display(description='Provider')
    def provider_badge(self, obj):
        return format_html('<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-sky-500/10 text-sky-600 dark:text-sky-400">{}</span>', obj.get_provider_display())

    @admin.display(description='Gross Amount')
    def gross_amount_display(self, obj):
        return format_html('<span class="font-mono font-bold text-slate-800 dark:text-slate-100">{}</span>', f'₹{obj.gross_amount:,.2f}')

    @admin.display(description='Status')
    def status_badge(self, obj):
        colors = {
            'captured': 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20',
            'authorized': 'bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20',
            'pending': 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20',
            'failed': 'bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20',
            'refunded': 'bg-purple-500/10 text-purple-600 dark:text-purple-400 border border-purple-500/20',
        }
        style = colors.get(obj.status, 'bg-gray-100 text-gray-700')
        return format_html('<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold {}">{}</span>', style, obj.get_status_display())

    @admin.display(description='Booking')
    def booking_ref(self, obj):
        if obj.booking:
            return format_html('<a href="/admin/operations/booking/{}/change/" class="text-primary-600 font-medium hover:underline">{}</a>', obj.booking.pk, obj.booking.booking_number)
        return "-"

    @admin.display(description='Gateway Ref / UTR')
    def payment_id_display(self, obj):
        return obj.gateway_payment_id or obj.gateway_order_id or "-"

    @admin.display(description='Double-Entry GL')
    def gl_status_badge(self, obj):
        if obj.journal_entry:
            return format_html('<a href="/admin/finance/journalentry/{}/change/" class="inline-flex items-center px-2 py-0.5 rounded text-xs font-bold bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border border-indigo-500/20">POSTED: {}</a>', obj.journal_entry.pk, obj.journal_entry.entry_number)
        return mark_safe('<span class="text-xs text-gray-400">UNPOSTED</span>')

