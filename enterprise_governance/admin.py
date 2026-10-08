from django.contrib import admin
from unfold.admin import ModelAdmin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils import timezone
import json
import datetime

from .models import SupplierContractProxy, CommissionRuleProxy, AuditLogEntryProxy


# ==========================================================================
#  Custom Filters
# ==========================================================================

class ContractHealthFilter(admin.SimpleListFilter):
    title = 'Contract Health'
    parameter_name = 'contract_health'

    def lookups(self, request, model_admin):
        return [
            ('expired', '🔴 Expired'),
            ('expiring_30d', '🟡 Expiring in 30 Days'),
            ('active_healthy', '🟢 Active & Healthy'),
        ]

    def queryset(self, request, queryset):
        today = timezone.now().date()
        soon = today + datetime.timedelta(days=30)
        if self.value() == 'expired':
            return queryset.filter(is_active=True, valid_to__lt=today)
        elif self.value() == 'expiring_30d':
            return queryset.filter(is_active=True, valid_to__gte=today, valid_to__lte=soon)
        elif self.value() == 'active_healthy':
            return queryset.filter(is_active=True, valid_to__gt=soon)
        return queryset


# ==========================================================================
#  1. SupplierContract Proxy Admin
# ==========================================================================

@admin.register(SupplierContractProxy)
class SupplierContractProxyAdmin(ModelAdmin):
    list_display = ('title_display', 'supplier_link', 'validity_display', 'sla_badge', 'document_link', 'active_badge')
    list_filter = (ContractHealthFilter, 'is_active', 'supplier')
    search_fields = ('title', 'supplier__name')
    date_hierarchy = 'valid_from'

    @admin.display(description='Contract Title')
    def title_display(self, obj):
        return format_html(
            '<span class="font-semibold text-slate-900 dark:text-slate-100">'
            '<i class="fas fa-file-contract mr-1 text-sky-600 dark:text-sky-400"></i>{}'
            '</span>',
            obj.title
        )

    @admin.display(description='Supplier')
    def supplier_link(self, obj):
        return format_html(
            '<a href="/admin/core_partners/supplier/{}/change/" class="text-sky-700 dark:text-sky-400 font-medium hover:underline">'
            '<i class="fas fa-truck-loading mr-1"></i>{}'
            '</a>',
            obj.supplier.id, obj.supplier.name
        )

    @admin.display(description='Validity Period')
    def validity_display(self, obj):
        total_days = (obj.valid_to - obj.valid_from).days
        return format_html(
            '<span style="color: #f8fafc;">{} → {}</span>'
            ' <small style="color: #94a3b8;">({} days)</small>',
            obj.valid_from.strftime('%d/%m/%Y'), obj.valid_to.strftime('%d/%m/%Y'), total_days
        )

    @admin.display(description='SLA / Expiry')
    def sla_badge(self, obj):
        today = timezone.now().date()
        remaining = (obj.valid_to - today).days
        if remaining < 0:
            return format_html(
                '<span class="badge" style="background-color: #ef4444; color: #fff; padding: 4px 8px; font-size: 11px;">'
                '<i class="fas fa-exclamation-triangle mr-1"></i>Expired {} days ago</span>',
                abs(remaining)
            )
        elif remaining <= 30:
            return format_html(
                '<span class="badge" style="background-color: #f59e0b; color: #fff; padding: 4px 8px; font-size: 11px;">'
                '<i class="fas fa-clock mr-1"></i>{}d remaining ⚠️</span>',
                remaining
            )
        return format_html(
            '<span class="badge" style="background-color: #10b981; color: #fff; padding: 4px 8px; font-size: 11px;">'
            '<i class="fas fa-check-circle mr-1"></i>{}d remaining</span>',
            remaining
        )

    @admin.display(description='Document')
    def document_link(self, obj):
        if not obj.contract_document:
            return mark_safe('<span style="color: #94a3b8;">No File</span>')
        return format_html(
            '<a href="{}" target="_blank" style="color: #38bdf8; text-decoration: none;">'
            '<i class="fas fa-download mr-1"></i>Download</a>',
            obj.contract_document.url
        )

    @admin.display(description='Status')
    def active_badge(self, obj):
        if obj.is_active:
            return mark_safe(
                '<span class="badge" style="background-color: #10b981; color: #fff; padding: 3px 8px;">✅ Active</span>'
            )
        return mark_safe(
            '<span class="badge" style="background-color: #64748b; color: #fff; padding: 3px 8px;">Inactive</span>'
        )


# ==========================================================================
#  2. CommissionRule Proxy Admin
# ==========================================================================

@admin.register(CommissionRuleProxy)
class CommissionRuleProxyAdmin(ModelAdmin):
    list_display = ('agent_display', 'commission_badge', 'active_badge')
    list_filter = ('is_active',)
    search_fields = ('agent_name',)

    @admin.display(description='Agent / Partner')
    def agent_display(self, obj):
        return format_html(
            '<span class="font-semibold text-slate-900 dark:text-slate-100">'
            '<i class="fas fa-user-tie mr-1 text-purple-600 dark:text-purple-400"></i>{}'
            '</span>',
            obj.agent_name
        )

    @admin.display(description='Commission Rate')
    def commission_badge(self, obj):
        color = '#10b981' if obj.commission_percentage <= 10 else '#f59e0b' if obj.commission_percentage <= 20 else '#ef4444'
        return format_html(
            '<span class="badge" style="background-color: {}; color: #fff; padding: 5px 10px; font-size: 14px; font-weight: 700;">'
            '{}%</span>',
            color, obj.commission_percentage
        )

    @admin.display(description='Status')
    def active_badge(self, obj):
        if obj.is_active:
            return mark_safe(
                '<span class="badge" style="background-color: #10b981; color: #fff; padding: 3px 8px;">✅ Active</span>'
            )
        return mark_safe(
            '<span class="badge" style="background-color: #64748b; color: #fff; padding: 3px 8px;">Inactive</span>'
        )


# ==========================================================================
#  3. AuditLogEntry Proxy Admin
# ==========================================================================

@admin.register(AuditLogEntryProxy)
class AuditLogEntryProxyAdmin(ModelAdmin):
    list_display = ('timestamp_display', 'action_badge', 'user_display', 'target_display', 'changes_preview')
    list_filter = ('action', 'content_type', 'timestamp')
    search_fields = ('action', 'user__username')
    readonly_fields = ('action', 'content_type', 'object_id', 'user', 'changes_formatted', 'timestamp')
    date_hierarchy = 'timestamp'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    @admin.display(description='Timestamp')
    def timestamp_display(self, obj):
        return format_html(
            '<span style="color: #94a3b8; font-size: 12px; font-family: monospace;">{}</span>',
            obj.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        )

    @admin.display(description='Action')
    def action_badge(self, obj):
        styles = {
            'create': ('#10b981', 'fas fa-plus-circle', 'Created'),
            'update': ('#3b82f6', 'fas fa-edit', 'Updated'),
            'delete': ('#ef4444', 'fas fa-trash-alt', 'Deleted'),
        }
        action_key = obj.action.lower()
        for key in styles:
            if key in action_key:
                color, icon, label = styles[key]
                break
        else:
            color, icon, label = '#64748b', 'fas fa-info-circle', obj.action
        return format_html(
            '<span class="badge" style="background-color: {}; color: #fff; padding: 4px 8px; font-size: 11px;">'
            '<i class="{} mr-1"></i>{}'
            '</span>',
            color, icon, label
        )

    @admin.display(description='User')
    def user_display(self, obj):
        if not obj.user:
            return mark_safe('<span style="color: #64748b;">System</span>')
        return format_html(
            '<span class="font-medium text-slate-900 dark:text-slate-100">'
            '<i class="fas fa-user mr-1 text-purple-600 dark:text-purple-400"></i>{}'
            '</span>',
            obj.user.username
        )

    @admin.display(description='Target Object')
    def target_display(self, obj):
        return format_html(
            '<span class="text-sky-700 dark:text-sky-300 font-medium">{}</span>'
            ' <span class="text-slate-500">#{}</span>',
            obj.content_type, obj.object_id
        )

    @admin.display(description='Changes')
    def changes_preview(self, obj):
        if not obj.changes:
            return mark_safe('<span style="color: #64748b;">—</span>')
        try:
            preview = json.dumps(obj.changes)[:80]
            return format_html(
                '<span class="text-xs font-mono text-slate-700 dark:text-slate-300 bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 px-2 py-1 rounded">{}</span>',
                preview
            )
        except Exception:
            return mark_safe('<span style="color: #94a3b8;">…</span>')

    @admin.display(description='Full Changes (JSON)')
    def changes_formatted(self, obj):
        if not obj.changes:
            return mark_safe('<span style="color: #94a3b8;">No changes recorded</span>')
        try:
            formatted = json.dumps(obj.changes, indent=2)
            return format_html(
                '<pre style="background: #0f172a; color: #38bdf8; padding: 12px; border-radius: 8px; '
                'max-height: 400px; overflow-y: auto; font-size: 11px; white-space: pre-wrap;">{}</pre>',
                formatted
            )
        except Exception:
            return str(obj.changes)
