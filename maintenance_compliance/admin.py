from django.contrib import admin
from django.utils.html import format_html, mark_safe
from django.utils import timezone
import datetime

from .models import ComplianceDocument, InsuranceClaim


# ==========================================================================
#  Filters
# ==========================================================================

class ExpiryStatusFilter(admin.SimpleListFilter):
    title = 'Expiry Status'
    parameter_name = 'expiry_status'

    def lookups(self, request, model_admin):
        return [
            ('expired', '🔴 Expired'),
            ('expiring_soon', '🟡 Expiring in 30 Days'),
            ('valid', '🟢 Valid'),
        ]

    def queryset(self, request, queryset):
        today = timezone.now().date()
        soon = today + datetime.timedelta(days=30)
        if self.value() == 'expired':
            return queryset.filter(expiry_date__lt=today)
        elif self.value() == 'expiring_soon':
            return queryset.filter(expiry_date__gte=today, expiry_date__lte=soon)
        elif self.value() == 'valid':
            return queryset.filter(expiry_date__gt=soon)
        return queryset


# ==========================================================================
#  1. ComplianceDocument Admin
# ==========================================================================

@admin.register(ComplianceDocument)
class ComplianceDocumentAdmin(admin.ModelAdmin):
    list_display = (
        'vehicle_link', 'document_type_badge', 'document_number',
        'issue_date', 'expiry_date', 'days_remaining_display',
        'status_badge', 'attachment_link',
    )
    list_filter = (ExpiryStatusFilter, 'document_type')
    search_fields = ('vehicle__registration_number', 'document_number', 'insurance_provider')
    autocomplete_fields = ['vehicle']
    date_hierarchy = 'expiry_date'
    list_per_page = 30

    fieldsets = (
        ('Basic Info', {
            'fields': ('vehicle', 'document_type', 'document_number', 'issue_date', 'expiry_date', 'attachment', 'notes')
        }),
        ('Insurance Specifics', {
            'fields': ('insurance_provider', 'premium_amount', 'coverage_type')
        }),
        ('Permit Specifics', {
            'fields': ('permit_states',)
        }),
    )

    class Media:
        js = ('admin/js/compliance_document_admin.js',)

    @admin.display(description="Vehicle", ordering='vehicle__registration_number')
    def vehicle_link(self, obj):
        from django.urls import reverse
        url = reverse('admin:core_vehicle_change', args=[obj.vehicle.pk])
        return format_html(
            '<a href="{}" style="color:#38bdf8; font-weight:700;">{}</a>',
            url, obj.vehicle.registration_number
        )

    @admin.display(description="Document Type", ordering='document_type')
    def document_type_badge(self, obj):
        colors = {
            'insurance':  ('#3b82f6', '#dbeafe', '🛡️'),
            'fc':         ('#f97316', '#fff7ed', '🔧'),
            'permit':     ('#8b5cf6', '#ede9fe', '📋'),
            'tax':        ('#eab308', '#fefce8', '💰'),
            'pollution':  ('#22c55e', '#f0fdf4', '💨'),
            'other':      ('#64748b', '#f1f5f9', '📄'),
        }
        bg, text_bg, icon = colors.get(obj.document_type, ('#64748b', '#f1f5f9', '📄'))
        label = obj.get_document_type_display()
        return format_html(
            '<span style="background:{}; color:#fff; padding:3px 10px; border-radius:12px; '
            'font-size:11px; font-weight:600; white-space:nowrap;">'
            '{} {}</span>',
            bg, icon, label
        )

    @admin.display(description="Days Left", ordering='expiry_date')
    def days_remaining_display(self, obj):
        days = obj.days_until_expiry
        if days < 0:
            return format_html(
                '<span style="color:#f87171; font-weight:700;">🔴 Expired {} day(s) ago</span>',
                abs(days)
            )
        elif days <= 30:
            return format_html(
                '<span style="color:#fbbf24; font-weight:700;">⏰ {} day(s) left</span>',
                days
            )
        else:
            return format_html(
                '<span style="color:#4ade80;">{} days</span>',
                days
            )

    @admin.display(description="Status")
    def status_badge(self, obj):
        if obj.is_expired:
            return mark_safe(
                '<span style="background:#dc2626; color:#fff; padding:3px 10px; border-radius:12px; '
                'font-size:11px; font-weight:700;">🔴 EXPIRED</span>'
            )
        days = obj.days_until_expiry
        if days <= 30:
            return mark_safe(
                '<span style="background:#d97706; color:#fff; padding:3px 10px; border-radius:12px; '
                'font-size:11px; font-weight:700;">🟡 Expiring Soon</span>'
            )
        return mark_safe(
            '<span style="background:#16a34a; color:#fff; padding:3px 10px; border-radius:12px; '
            'font-size:11px; font-weight:700;">🟢 Valid</span>'
        )

    @admin.display(description="📎")
    def attachment_link(self, obj):
        if obj.attachment:
            return format_html(
                '<a href="{}" target="_blank" style="color:#38bdf8; font-size:16px;" '
                'title="Download Document">📥</a>',
                obj.attachment.url
            )
        return mark_safe('<span style="color:#475569;">—</span>')


# ==========================================================================
#  2. InsuranceClaim Admin
# ==========================================================================

@admin.register(InsuranceClaim)
class InsuranceClaimAdmin(admin.ModelAdmin):
    list_display = (
        'claim_id_display', 'vehicle_link', 'date_of_accident', 'fir_display',
        'amounts_display', 'out_of_pocket_display', 'status_badge', 'surveyor_display',
    )
    list_filter = ('status', 'date_of_accident')
    search_fields = ('vehicle__registration_number', 'fir_number', 'surveyor_name')
    autocomplete_fields = ['vehicle']
    list_per_page = 30

    @admin.display(description="Claim #", ordering='pk')
    def claim_id_display(self, obj):
        cid = f"#IC-{obj.pk:04d}" if obj.pk else "#IC-NEW"
        return format_html(
            '<span style="background:#334155; color:#e2e8f0; padding:2px 8px; border-radius:6px; '
            'font-family:monospace; font-size:12px; font-weight:700; border:1px solid #475569;">'
            '{}</span>',
            cid
        )

    @admin.display(description="Vehicle", ordering='vehicle__registration_number')
    def vehicle_link(self, obj):
        from django.urls import reverse
        url = reverse('admin:core_vehicle_change', args=[obj.vehicle.pk])
        return format_html(
            '<a href="{}" style="color:#38bdf8; font-weight:700;">{}</a>',
            url, obj.vehicle.registration_number
        )

    @admin.display(description="FIR")
    def fir_display(self, obj):
        if obj.fir_number:
            return format_html(
                '<span style="background:#1e293b; color:#fbbf24; padding:2px 8px; border-radius:4px; '
                'font-family:monospace; font-size:11px; font-weight:600; border:1px solid #475569;">'
                '📋 {}</span>',
                obj.fir_number
            )
        return mark_safe(
            '<span style="color:#64748b; font-style:italic;">No FIR</span>'
        )

    @admin.display(description="Amounts")
    def amounts_display(self, obj):
        est = f"₹{obj.estimated_repair_cost:,.0f}" if obj.estimated_repair_cost else "₹0"
        clm = f"₹{obj.claimed_amount:,.0f}" if obj.claimed_amount else "₹0"
        app = f"₹{obj.approved_amount:,.0f}" if obj.approved_amount else "₹0"
        return format_html(
            '<div style="font-size:11px; line-height:1.6;">'
            '<span style="color:#94a3b8;">Est:</span> '
            '<span style="color:#e2e8f0; font-weight:600;">{}</span><br>'
            '<span style="color:#94a3b8;">Claimed:</span> '
            '<span style="color:#38bdf8; font-weight:600;">{}</span><br>'
            '<span style="color:#94a3b8;">Approved:</span> '
            '<span style="color:#4ade80; font-weight:600;">{}</span>'
            '</div>',
            est, clm, app
        )

    @admin.display(description="Out-of-Pocket")
    def out_of_pocket_display(self, obj):
        oop = obj.out_of_pocket_expense
        if obj.status == 'settled' and oop > 0:
            oop_str = f"₹{oop:,.0f}"
            return format_html(
                '<span style="color:#f87171; font-weight:700;">{}</span>',
                oop_str
            )
        elif obj.status == 'settled' and oop == 0:
            return mark_safe(
                '<span style="color:#4ade80; font-weight:600;">₹0 (Fully Covered)</span>'
            )
        return mark_safe('<span style="color:#64748b;">—</span>')

    @admin.display(description="Status", ordering='status')
    def status_badge(self, obj):
        colors = {
            'pending':  ('#eab308', '#422006', '⏳ Pending Survey'),
            'surveyed': ('#3b82f6', '#ffffff', '🔍 Surveyed'),
            'approved': ('#22c55e', '#ffffff', '✅ Approved'),
            'rejected': ('#dc2626', '#ffffff', '❌ Rejected'),
            'settled':  ('#059669', '#ffffff', '💰 Settled'),
        }
        bg, text, label = colors.get(obj.status, ('#64748b', '#ffffff', obj.get_status_display()))
        return format_html(
            '<span style="background:{}; color:{}; padding:3px 10px; border-radius:12px; '
            'font-size:11px; font-weight:700; white-space:nowrap;">{}</span>',
            bg, text, label
        )

    @admin.display(description="Surveyor")
    def surveyor_display(self, obj):
        if not obj.surveyor_name:
            return mark_safe('<span style="color:#475569;">—</span>')
        phone_html = ''
        if obj.surveyor_phone:
            phone_html = format_html(
                ' <a href="tel:{}" style="color:#38bdf8; font-size:13px;" title="Call {}">📞</a>',
                obj.surveyor_phone, obj.surveyor_name
            )
        return format_html(
            '<span style="color:#e2e8f0; font-weight:600;">{}</span>{}',
            obj.surveyor_name, phone_html
        )
