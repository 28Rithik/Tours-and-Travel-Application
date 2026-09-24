from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils import timezone
import json

from .models import (
    InstallmentPlanProxy, PaymentLinkProxy, PaymentWebhookEventProxy,
    CustomerAccountProxy, CustomerDocumentProxy,
)


# ==========================================================================
#  1. InstallmentPlan Proxy Admin
# ==========================================================================

@admin.register(InstallmentPlanProxy)
class InstallmentPlanProxyAdmin(admin.ModelAdmin):
    list_display = ('booking_link', 'total_amount_display', 'installments_badge', 'active_badge', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('booking__booking_number',)

    @admin.display(description='Booking')
    def booking_link(self, obj):
        return format_html(
            '<a href="/admin/operations/booking/{}/change/" style="color: #38bdf8; text-decoration: none; font-weight: 600;">'
            '<i class="fas fa-calendar-check mr-1"></i>{}'
            '</a>',
            obj.booking.id, obj.booking.booking_number
        )

    @admin.display(description='Total Amount')
    def total_amount_display(self, obj):
        return format_html(
            '<span style="color: #10b981; font-weight: 700; font-size: 13px;">₹{}</span>',
            f"{obj.total_amount:,.0f}"
        )

    @admin.display(description='Installments')
    def installments_badge(self, obj):
        return format_html(
            '<span class="badge" style="background-color: #334155; color: #93c5fd; border: 1px solid #475569; padding: 4px 8px; font-size: 12px;">'
            '<i class="fas fa-calendar-alt mr-1"></i>{} EMIs'
            '</span>',
            obj.number_of_installments
        )

    @admin.display(description='Status')
    def active_badge(self, obj):
        if obj.is_active:
            return mark_safe(
                '<span class="badge" style="background-color: #10b981; color: #fff; padding: 3px 8px;">✅ Active</span>'
            )
        return mark_safe(
            '<span class="badge" style="background-color: #64748b; color: #fff; padding: 3px 8px;">Closed</span>'
        )


# ==========================================================================
#  2. PaymentLink Proxy Admin
# ==========================================================================

@admin.register(PaymentLinkProxy)
class PaymentLinkProxyAdmin(admin.ModelAdmin):
    list_display = (
        'booking_link', 'amount_display', 'razorpay_display',
        'status_badge', 'expiry_display', 'created_at',
    )
    list_filter = ('status',)
    search_fields = ('booking__booking_number', 'razorpay_link_id')

    @admin.display(description='Booking')
    def booking_link(self, obj):
        return format_html(
            '<a href="/admin/operations/booking/{}/change/" style="color: #38bdf8; text-decoration: none; font-weight: 500;">'
            '<i class="fas fa-calendar-check mr-1"></i>{}'
            '</a>',
            obj.booking.id, obj.booking.booking_number
        )

    @admin.display(description='Amount')
    def amount_display(self, obj):
        return format_html(
            '<span style="color: #10b981; font-weight: 700; font-size: 13px;">₹{}</span>',
            f"{obj.amount:,.0f}"
        )

    @admin.display(description='Razorpay Link')
    def razorpay_display(self, obj):
        return format_html(
            '<span style="color: #94a3b8; font-family: monospace; font-size: 11px; '
            'background: #1e293b; padding: 3px 6px; border-radius: 3px;">'
            '<i class="fas fa-link mr-1"></i>{}'
            '</span>',
            obj.razorpay_link_id[:20]
        )

    @admin.display(description='Payment Status')
    def status_badge(self, obj):
        styles = {
            'created': ('#3b82f6', 'fas fa-clock', '⏳ Created'),
            'paid': ('#10b981', 'fas fa-check-circle', '✅ Paid'),
            'expired': ('#f59e0b', 'fas fa-exclamation-circle', '⏰ Expired'),
            'cancelled': ('#ef4444', 'fas fa-times-circle', '❌ Cancelled'),
        }
        color, icon, label = styles.get(obj.status, ('#64748b', 'fas fa-question', obj.status))
        return format_html(
            '<span class="badge" style="background-color: {}; color: #fff; padding: 5px 10px; font-size: 12px; font-weight: 600;">'
            '<i class="{} mr-1"></i>{}'
            '</span>',
            color, icon, label
        )

    @admin.display(description='Expires')
    def expiry_display(self, obj):
        if not obj.expires_at:
            return mark_safe('<span style="color: #94a3b8;">—</span>')
        now = timezone.now()
        if obj.expires_at < now:
            return format_html(
                '<span style="color: #ef4444; font-weight: 500;">Expired {}</span>',
                obj.expires_at.strftime('%d/%m/%Y %H:%M')
            )
        return format_html(
            '<span style="color: #94a3b8; font-size: 12px;">{}</span>',
            obj.expires_at.strftime('%d/%m/%Y %H:%M')
        )


# ==========================================================================
#  3. PaymentWebhookEvent Proxy Admin
# ==========================================================================

@admin.register(PaymentWebhookEventProxy)
class PaymentWebhookEventProxyAdmin(admin.ModelAdmin):
    list_display = ('event_id_display', 'event_type_badge', 'processed_badge', 'created_at')
    list_filter = ('event_type', 'processed')
    search_fields = ('event_id',)
    readonly_fields = ('event_id', 'event_type', 'payload_formatted', 'processed', 'created_at')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    @admin.display(description='Event ID')
    def event_id_display(self, obj):
        return format_html(
            '<span style="color: #94a3b8; font-family: monospace; font-size: 11px; '
            'background: #0f172a; padding: 3px 6px; border-radius: 3px;">{}</span>',
            obj.event_id
        )

    @admin.display(description='Event Type')
    def event_type_badge(self, obj):
        if 'payment' in obj.event_type.lower():
            color = '#10b981'
        elif 'refund' in obj.event_type.lower():
            color = '#f59e0b'
        else:
            color = '#3b82f6'
        return format_html(
            '<span class="badge" style="background-color: {}; color: #fff; padding: 3px 8px; font-size: 11px;">{}</span>',
            color, obj.event_type
        )

    @admin.display(description='Processed')
    def processed_badge(self, obj):
        if obj.processed:
            return mark_safe(
                '<span class="badge" style="background-color: #10b981; color: #fff; padding: 3px 8px;">✅ Processed</span>'
            )
        return mark_safe(
            '<span class="badge" style="background-color: #f59e0b; color: #fff; padding: 3px 8px;">⏳ Pending</span>'
        )

    @admin.display(description='Payload (JSON)')
    def payload_formatted(self, obj):
        try:
            formatted = json.dumps(obj.payload, indent=2)
            return format_html(
                '<pre style="background: #0f172a; color: #38bdf8; padding: 12px; border-radius: 8px; '
                'max-height: 400px; overflow-y: auto; font-size: 11px; white-space: pre-wrap;">{}</pre>',
                formatted
            )
        except Exception:
            return str(obj.payload)


# ==========================================================================
#  4. CustomerAccount Proxy Admin
# ==========================================================================

@admin.register(CustomerAccountProxy)
class CustomerAccountProxyAdmin(admin.ModelAdmin):
    list_display = ('user_display', 'client_link', 'verification_badge', 'created_at')
    list_filter = ('is_email_verified',)
    search_fields = ('user__username', 'client_record__name')

    @admin.display(description='Portal User')
    def user_display(self, obj):
        return format_html(
            '<span style="color: #f1f5f9; font-weight: 600;">'
            '<i class="fas fa-user-circle mr-1" style="color: #8b5cf6;"></i>{}'
            '</span>',
            obj.user.username
        )

    @admin.display(description='Linked Client')
    def client_link(self, obj):
        return format_html(
            '<a href="/admin/core_partners/client/{}/change/" style="color: #93c5fd; text-decoration: none;">'
            '<i class="fas fa-building mr-1"></i>{}'
            '</a>',
            obj.client_record.id, obj.client_record.name
        )

    @admin.display(description='Email Verified')
    def verification_badge(self, obj):
        if obj.is_email_verified:
            return mark_safe(
                '<span class="badge" style="background-color: #10b981; color: #fff; padding: 3px 8px;">'
                '<i class="fas fa-check-circle mr-1"></i>Verified</span>'
            )
        return mark_safe(
            '<span class="badge" style="background-color: #f59e0b; color: #fff; padding: 3px 8px;">'
            '<i class="fas fa-exclamation-triangle mr-1"></i>Unverified</span>'
        )


# ==========================================================================
#  5. CustomerDocument Proxy Admin
# ==========================================================================

@admin.register(CustomerDocumentProxy)
class CustomerDocumentProxyAdmin(admin.ModelAdmin):
    list_display = ('title_display', 'customer_link', 'booking_link', 'doc_type_badge', 'uploaded_at')
    list_filter = ('document_type', 'uploaded_at')
    search_fields = ('title', 'customer__name', 'booking__booking_number')

    @admin.display(description='Document')
    def title_display(self, obj):
        return format_html(
            '<span style="color: #f1f5f9; font-weight: 600;">'
            '<i class="fas fa-file-alt mr-1" style="color: #38bdf8;"></i>{}'
            '</span>',
            obj.title
        )

    @admin.display(description='Customer')
    def customer_link(self, obj):
        return format_html(
            '<a href="/admin/core_partners/client/{}/change/" style="color: #93c5fd; text-decoration: none;">'
            '<i class="fas fa-user mr-1"></i>{}'
            '</a>',
            obj.customer.id, obj.customer.name
        )

    @admin.display(description='Booking')
    def booking_link(self, obj):
        if not obj.booking:
            return mark_safe('<span style="color: #94a3b8;">—</span>')
        return format_html(
            '<a href="/admin/operations/booking/{}/change/" style="color: #38bdf8; text-decoration: none;">{}</a>',
            obj.booking.id, obj.booking.booking_number
        )

    @admin.display(description='Type')
    def doc_type_badge(self, obj):
        styles = {
            'visa': ('#8b5cf6', 'fas fa-passport', 'Visa'),
            'ticket': ('#3b82f6', 'fas fa-ticket-alt', 'E-Ticket'),
            'voucher': ('#10b981', 'fas fa-receipt', 'Voucher'),
            'insurance': ('#f59e0b', 'fas fa-shield-alt', 'Insurance'),
            'other': ('#64748b', 'fas fa-file', 'Other'),
        }
        color, icon, label = styles.get(obj.document_type, styles['other'])
        return format_html(
            '<span class="badge" style="background-color: {}; color: #fff; padding: 3px 8px; font-size: 11px;">'
            '<i class="{} mr-1"></i>{}'
            '</span>',
            color, icon, label
        )
