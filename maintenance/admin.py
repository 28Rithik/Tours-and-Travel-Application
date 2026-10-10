from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline
from django.utils.html import format_html, mark_safe
from django.utils import timezone
from django.db.models import Q
import datetime

from .models import (
    ServiceRecord, SparePart, PartInventory,
    VehicleAsset, AssetRotationLog, TireInspectionLog, DefectTicket, ServiceReminder,
    PreTripInspectionChecklist,
    VehicleDamageInspection, VehicleDamageMarker,
)


# ==========================================================================
#  Bulk Actions
# ==========================================================================

@admin.action(description="✅ Mark selected defects as Resolved")
def mark_defects_resolved(modeladmin, request, queryset):
    today = timezone.now().date()
    updated = queryset.filter(status__in=['open', 'in_progress']).update(
        status='resolved', resolved_date=today
    )
    modeladmin.message_user(request, f"{updated} defect ticket(s) marked as resolved.")


@admin.action(description="✅ Mark selected service reminders as Inactive")
def mark_reminders_inactive(modeladmin, request, queryset):
    updated = queryset.update(is_active=False)
    modeladmin.message_user(request, f"{updated} reminder(s) deactivated.")


@admin.action(description="✅ Mark selected service records as Completed")
def mark_services_completed(modeladmin, request, queryset):
    updated = 0
    for record in queryset.filter(status__in=['pending', 'in_progress']):
        record.status = 'completed'
        record.save()  # triggers vehicle status change & inventory deduction
        updated += 1
    modeladmin.message_user(request, f"{updated} service record(s) marked as completed.")


# ==========================================================================
#  Custom Filters
# ==========================================================================



class ServiceDueFilter(admin.SimpleListFilter):
    title = 'Service Due Status'
    parameter_name = 'service_due'

    def lookups(self, request, model_admin):
        return [
            ('overdue', '🔴 Overdue'),
            ('due_soon', '🟡 Due within 2,000 km'),
            ('healthy', '🟢 Healthy'),
        ]

    def queryset(self, request, queryset):
        ids_overdue = []
        ids_due_soon = []
        ids_healthy = []
        for reminder in queryset.select_related('vehicle'):
            km_left = reminder.km_until_due
            if km_left <= 0:
                ids_overdue.append(reminder.pk)
            elif km_left <= 2000:
                ids_due_soon.append(reminder.pk)
            else:
                ids_healthy.append(reminder.pk)
        if self.value() == 'overdue':
            return queryset.filter(pk__in=ids_overdue)
        elif self.value() == 'due_soon':
            return queryset.filter(pk__in=ids_due_soon)
        elif self.value() == 'healthy':
            return queryset.filter(pk__in=ids_healthy)
        return queryset


class StockLevelFilter(admin.SimpleListFilter):
    title = 'Stock Level'
    parameter_name = 'stock_level'

    def lookups(self, request, model_admin):
        return [
            ('below', '🔴 Below Minimum'),
            ('near', '🟡 Near Minimum (within 20%)'),
            ('ok', '🟢 Well Stocked'),
        ]

    def queryset(self, request, queryset):
        from django.db.models import F
        if self.value() == 'below':
            return queryset.filter(current_stock__lte=F('minimum_stock_level'))
        elif self.value() == 'near':
            return queryset.filter(
                current_stock__gt=F('minimum_stock_level'),
                current_stock__lte=F('minimum_stock_level') * 1.2
            )
        elif self.value() == 'ok':
            return queryset.filter(current_stock__gt=F('minimum_stock_level') * 1.2)
        return queryset


class AssetReplacementFilter(admin.SimpleListFilter):
    title = 'Replacement Status'
    parameter_name = 'replacement_status'

    def lookups(self, request, model_admin):
        return [
            ('replace', '🔴 Needs Replacement (>90%)'),
            ('warning', '🟡 Approaching (70-90%)'),
            ('healthy', '🟢 Healthy (<70%)'),
        ]

    def queryset(self, request, queryset):
        ids_replace = []
        ids_warning = []
        ids_healthy = []
        for asset in queryset.select_related('vehicle').filter(status='in_use'):
            if asset.expected_life_km and asset.expected_life_km > 0:
                pct = (asset.current_run_km / asset.expected_life_km) * 100
                if pct >= 90:
                    ids_replace.append(asset.pk)
                elif pct >= 70:
                    ids_warning.append(asset.pk)
                else:
                    ids_healthy.append(asset.pk)
            else:
                ids_healthy.append(asset.pk)

        if self.value() == 'replace':
            return queryset.filter(pk__in=ids_replace)
        elif self.value() == 'warning':
            return queryset.filter(pk__in=ids_warning)
        elif self.value() == 'healthy':
            return queryset.filter(pk__in=ids_healthy)
        return queryset




# ==========================================================================
#  2. ServiceRecord Admin
# ==========================================================================

class SparePartInline(TabularInline):
    model = SparePart
    extra = 1
    autocomplete_fields = ['inventory_item']


@admin.register(ServiceRecord)
class ServiceRecordAdmin(ModelAdmin):
    list_display = (
        'vehicle_link', 'service_type_badge', 'date', 'garage_name',
        'odometer_reading', 'parts_count_display', 'total_cost_display',
        'status_badge',
    )
    list_filter = ('service_type', 'status', 'date')
    search_fields = ('vehicle__registration_number', 'garage_name', 'description')
    autocomplete_fields = ['vehicle']
    date_hierarchy = 'date'
    inlines = [SparePartInline]
    list_per_page = 30
    actions = [mark_services_completed]

    @admin.display(description="Vehicle", ordering='vehicle__registration_number')
    def vehicle_link(self, obj):
        from django.urls import reverse
        url = reverse('admin:core_vehicle_change', args=[obj.vehicle.pk])
        return format_html(
            '<a href="{}" style="color:#38bdf8; font-weight:700;">{}</a>',
            url, obj.vehicle.registration_number
        )

    @admin.display(description="Type", ordering='service_type')
    def service_type_badge(self, obj):
        colors = {
            'routine':    ('#16a34a', '🔧'),
            'breakdown':  ('#dc2626', '🚨'),
            'accidental': ('#be123c', '💥'),
            'bodywork':   ('#7c3aed', '🎨'),
            'tyre':       ('#ea580c', '🛞'),
            'other':      ('#64748b', '🔩'),
        }
        bg, icon = colors.get(obj.service_type, ('#64748b', '🔩'))
        label = obj.get_service_type_display()
        return format_html(
            '<span style="background:{}; color:#fff; padding:3px 10px; border-radius:12px; '
            'font-size:11px; font-weight:600; white-space:nowrap;">'
            '{} {}</span>',
            bg, icon, label
        )

    @admin.display(description="Parts Used")
    def parts_count_display(self, obj):
        count = obj.spare_parts.count()
        if count == 0:
            return mark_safe('<span style="color:#64748b;">None</span>')
        return format_html(
            '<span style="color:#38bdf8; font-weight:600;">{} part{}</span>',
            count, 's' if count > 1 else ''
        )

    @admin.display(description="Cost", ordering='total_cost')
    def total_cost_display(self, obj):
        cost = obj.total_cost
        if cost >= 20000:
            color = '#f87171'  # Red for high cost
        elif cost >= 5000:
            color = '#fbbf24'  # Orange for medium
        else:
            color = '#4ade80'  # Green for low
        cost_str = f"₹{cost:,.2f}"
        return format_html(
            '<span style="color:{}; font-weight:700;">{}</span>',
            color, cost_str
        )

    @admin.display(description="Status", ordering='status')
    def status_badge(self, obj):
        colors = {
            'pending':     ('#eab308', '#422006', '⏳'),
            'in_progress': ('#3b82f6', '#ffffff', '🔧'),
            'completed':   ('#16a34a', '#ffffff', '✅'),
        }
        bg, text, icon = colors.get(obj.status, ('#64748b', '#ffffff', '❓'))
        label = obj.get_status_display()
        return format_html(
            '<span style="background:{}; color:{}; padding:3px 10px; border-radius:12px; '
            'font-size:11px; font-weight:700; white-space:nowrap;">'
            '{} {}</span>',
            bg, text, icon, label
        )


# ==========================================================================
#  3. VehicleAsset Admin (Tyres & Batteries)
# ==========================================================================

class AssetRotationLogInline(TabularInline):
    model = AssetRotationLog
    extra = 1


class TireInspectionLogInline(TabularInline):
    model = TireInspectionLog
    extra = 0
    readonly_fields = ('created_at',)
    fields = ('inspection_date', 'odometer', 'tread_depth_mm', 'psi_pressure', 'inspector_name', 'action_taken', 'has_irregular_wear')


@admin.register(VehicleAsset)
class VehicleAssetAdmin(ModelAdmin):
    list_display = (
        'asset_type_badge', 'serial_number', 'brand_model_display', 'vehicle_link', 'position_display',
        'tread_gauge_display', 'retread_badge', 'lifecycle_display', 'status_badge', 'replacement_alert',
    )
    list_filter = ('asset_type', 'status', AssetReplacementFilter, 'position')
    search_fields = ('serial_number', 'vehicle__registration_number', 'brand', 'vendor_name')
    autocomplete_fields = ['vehicle']
    inlines = [AssetRotationLogInline, TireInspectionLogInline]
    list_per_page = 30

    fieldsets = (
        ('Asset Identity', {
            'fields': ('asset_type', 'serial_number', 'brand', 'model_or_size', 'dot_code', 'vehicle', 'position', 'status')
        }),
        ('Tire Tread & Inflation', {
            'fields': ('original_tread_depth_mm', 'current_tread_depth_mm', 'psi_pressure', 'retread_count', 'max_retread_cycles', 'last_inspected_date', 'last_inspected_odometer'),
        }),
        ('Purchase & Warranty Info', {
            'fields': ('purchase_price', 'vendor_name', 'warranty_expiry_date', 'warranty_expiry_km'),
            'classes': ('collapse',)
        }),
        ('Installation & Lifecycle', {
            'fields': ('installed_date', 'installed_odometer', 'expected_life_km')
        }),
    )

    class Media:
        js = ('admin/js/vehicle_asset_admin.js',)

    @admin.display(description="Type", ordering='asset_type')
    def asset_type_badge(self, obj):
        if obj.asset_type == 'tyre':
            return mark_safe(
                '<span style="background:#ea580c; color:#fff; padding:3px 10px; border-radius:12px; '
                'font-size:11px; font-weight:700;">🛞 Tyre</span>'
            )
        return mark_safe(
            '<span style="background:#0ea5e9; color:#fff; padding:3px 10px; border-radius:12px; '
            'font-size:11px; font-weight:700;">🔋 Battery</span>'
        )

    @admin.display(description="Vehicle", ordering='vehicle__registration_number')
    def vehicle_link(self, obj):
        from django.urls import reverse
        url = reverse('admin:core_vehicle_change', args=[obj.vehicle.pk])
        return format_html(
            '<a href="{}" class="font-bold text-primary-600 dark:text-primary-400 hover:underline">{}</a>',
            url, obj.vehicle.registration_number
        )

    @admin.display(description="Position", ordering='position')
    def position_display(self, obj):
        if not obj.position:
            return mark_safe('<span class="text-slate-400 dark:text-slate-500">—</span>')
        icons = {
            'front_left': '⬅️ FL', 'front_right': '➡️ FR',
            'rear_left_outer': '⬅️ RLO', 'rear_left_inner': '⬅️ RLI',
            'rear_right_outer': '➡️ RRO', 'rear_right_inner': '➡️ RRI',
            'spare': '🔄 Spare', 'engine_bay': '⚙️ Engine',
        }
        label = icons.get(obj.position, obj.get_position_display())
        return format_html(
            '<span class="badge-position-pill inline-flex items-center px-2.5 py-1 rounded-md text-xs font-bold font-mono shadow-sm" '
            'style="background:#f0f9ff; color:#0369a1; border:1px solid #7dd3fc;">'
            '{}</span>',
            label
        )

    @admin.display(description="Lifecycle (km)")
    def lifecycle_display(self, obj):
        run = obj.current_run_km
        life = obj.expected_life_km
        if not life or life == 0:
            return mark_safe('<span style="color:#64748b;">N/A</span>')
        pct = min(100, int((run / life) * 100))
        if pct >= 90:
            bar_color = '#ef4444'  # Red
        elif pct >= 70:
            bar_color = '#eab308'  # Yellow
        else:
            bar_color = '#22c55e'  # Green
        info_text = f"{run:,} / {life:,} km ({pct}%)"
        return format_html(
            '<div style="min-width:120px;">'
            '<div style="background:#e2e8f0; border-radius:6px; height:8px; width:100%; '
            'border:1px solid #cbd5e1; overflow:hidden; margin-bottom:3px;">'
            '<div style="background:{}; height:100%; width:{}%; border-radius:6px;"></div>'
            '</div>'
            '<span style="color:#475569; font-size:11px; font-weight:600;">{}</span>'
            '</div>',
            bar_color, pct, info_text
        )

    @admin.display(description="Warranty")
    def warranty_status(self, obj):
        today = timezone.now().date()
        # Check date warranty
        if obj.warranty_expiry_date and obj.warranty_expiry_date >= today:
            days_left = (obj.warranty_expiry_date - today).days
            return format_html(
                '<span style="color:#4ade80; font-weight:600;">✅ {} days left</span>',
                days_left
            )
        # Check km warranty
        if obj.warranty_expiry_km and obj.current_run_km < obj.warranty_expiry_km:
            km_left = obj.warranty_expiry_km - obj.current_run_km
            km_str = f"✅ {km_left:,} km left"
            return format_html(
                '<span style="color:#4ade80; font-weight:600;">{}</span>',
                km_str
            )
        # No warranty or expired
        if obj.warranty_expiry_date or obj.warranty_expiry_km:
            return mark_safe(
                '<span style="color:#64748b;">Warranty Expired</span>'
            )
        return mark_safe('<span style="color:#475569;">No Warranty</span>')

    @admin.display(description="Status", ordering='status')
    def status_badge(self, obj):
        colors = {
            'in_use':      ('#16a34a', '🟢'),
            'spare':       ('#3b82f6', '🔵'),
            'retreading':  ('#eab308', '🟡'),
            'scrapped':    ('#6b7280', '⚫'),
            'sold':        ('#64748b', '💲'),
        }
        bg, icon = colors.get(obj.status, ('#64748b', '❓'))
        label = obj.get_status_display()
        return format_html(
            '<span style="background:{}; color:#fff; padding:3px 10px; border-radius:12px; '
            'font-size:11px; font-weight:700; white-space:nowrap;">{} {}</span>',
            bg, icon, label
        )

    @admin.display(description="Alert")
    def replacement_alert(self, obj):
        if obj.status != 'in_use':
            return mark_safe('<span style="color:#475569;">—</span>')
        run = obj.current_run_km
        life = obj.expected_life_km
        if not life or life == 0:
            return mark_safe('<span style="color:#64748b;">N/A</span>')
        pct = (run / life) * 100
        if pct >= 95:
            return mark_safe(
                '<span style="background:#dc2626; color:#fff; padding:3px 10px; border-radius:12px; '
                'font-size:11px; font-weight:700;">🚨 REPLACE NOW!</span>'
            )
        elif pct >= 90:
            return mark_safe(
                '<span style="background:#ea580c; color:#fff; padding:3px 10px; border-radius:12px; '
                'font-size:11px; font-weight:700;">⚠️ Replace Soon</span>'
            )
        elif pct >= 70:
            return format_html(
                '<span style="color:#fbbf24; font-weight:600;">🟡 Monitor ({}%)</span>',
                f"{pct:.0f}"
            )
        return mark_safe(
            '<span style="color:#4ade80;">🟢 Healthy</span>'
        )

    @admin.display(description="Brand / Size")
    def brand_model_display(self, obj):
        parts = []
        if obj.brand:
            parts.append(f"<b>{obj.brand}</b>")
        if obj.model_or_size:
            parts.append(f"<span style='color:#64748b; font-size:11px;'>{obj.model_or_size}</span>")
        return format_html(" ".join(parts)) if parts else "—"

    @admin.display(description="Tread (mm)", ordering='current_tread_depth_mm')
    def tread_gauge_display(self, obj):
        if obj.asset_type != 'tyre':
            return "—"
        td = float(obj.current_tread_depth_mm or 0)
        color = "#10b981" if td > 6.0 else ("#f59e0b" if td > 2.5 else "#ef4444")
        return format_html(
            '<span style="background:{}; color:#fff; padding:2px 8px; border-radius:10px; font-weight:700; font-size:11px;">{} mm</span>',
            color, f"{td:.1f}"
        )

    @admin.display(description="Retread")
    def retread_badge(self, obj):
        if obj.asset_type != 'tyre':
            return "—"
        rc = obj.retread_count or 0
        if rc == 0:
            return format_html('<span style="color:#059669; font-weight:700; font-size:11px;">Virgin Casing</span>')
        return format_html('<span style="background:#e0e7ff; color:#4338ca; padding:2px 7px; border-radius:6px; font-weight:700; font-size:11px;">Retread #{}</span>', rc)


@admin.register(TireInspectionLog)
class TireInspectionLogAdmin(ModelAdmin):
    list_display = (
        'log_id_display', 'asset_link', 'vehicle_reg', 'inspection_date',
        'odometer_display', 'tread_depth_badge', 'psi_display', 'inspector_name', 'action_badge'
    )
    list_filter = ('action_taken', 'has_irregular_wear', 'inspection_date')
    search_fields = ('asset__serial_number', 'asset__vehicle__registration_number', 'inspector_name')
    readonly_fields = ('created_at',)
    list_per_page = 30

    @admin.display(description="Log #")
    def log_id_display(self, obj):
        return format_html('<b>#{}</b>', obj.pk)

    @admin.display(description="Tyre Serial")
    def asset_link(self, obj):
        from django.urls import reverse
        url = reverse('admin:maintenance_vehicleasset_change', args=[obj.asset.pk])
        return format_html('<a href="{}" class="font-bold text-primary-600 hover:underline">🛞 {}</a>', url, obj.asset.serial_number)

    @admin.display(description="Vehicle")
    def vehicle_reg(self, obj):
        return obj.asset.vehicle.registration_number if obj.asset.vehicle else "—"

    @admin.display(description="Odometer")
    def odometer_display(self, obj):
        return f"{obj.odometer:,} km"

    @admin.display(description="Tread Depth")
    def tread_depth_badge(self, obj):
        td = float(obj.tread_depth_mm)
        color = "#10b981" if td > 6.0 else ("#f59e0b" if td > 2.5 else "#ef4444")
        return format_html('<span style="background:{}; color:#fff; padding:2px 8px; border-radius:10px; font-weight:700; font-size:11px;">{} mm</span>', color, f"{td:.1f}")

    @admin.display(description="Pressure")
    def psi_display(self, obj):
        return f"{obj.psi_pressure} PSI" if obj.psi_pressure else "—"

    @admin.display(description="Action Taken")
    def action_badge(self, obj):
        colors = {
            'none': '#64748b',
            'pressure_adjusted': '#0284c7',
            'rotated': '#8b5cf6',
            'sent_retread': '#f59e0b',
            'scrapped': '#ef4444',
        }
        bg = colors.get(obj.action_taken, '#64748b')
        return format_html('<span style="background:{}; color:#fff; padding:2px 8px; border-radius:10px; font-weight:700; font-size:11px;">{}</span>', bg, obj.get_action_taken_display())


# ==========================================================================
#  4. DefectTicket Admin
# ==========================================================================

@admin.register(DefectTicket)
class DefectTicketAdmin(ModelAdmin):
    list_display = (
        'ticket_id_display', 'vehicle_link', 'description_preview',
        'reported_by', 'date_reported', 'age_display', 'status_badge',
    )
    list_filter = ('status', 'date_reported')
    search_fields = ('vehicle__registration_number', 'reported_by', 'description')
    autocomplete_fields = ['vehicle']
    date_hierarchy = 'date_reported'
    actions = [mark_defects_resolved]
    list_per_page = 30

    @admin.display(description="Ticket #", ordering='pk')
    def ticket_id_display(self, obj):
        tid = f"#DT-{obj.pk:04d}" if obj.pk else "#DT-NEW"
        return format_html(
            '<span class="badge-ticket-pill inline-flex items-center px-2.5 py-1 rounded-md text-xs font-bold font-mono shadow-sm" '
            'style="background:#f0f9ff; color:#0369a1; border:1px solid #7dd3fc;">'
            '{}</span>',
            tid
        )

    @admin.display(description="Vehicle", ordering='vehicle__registration_number')
    def vehicle_link(self, obj):
        from django.urls import reverse
        url = reverse('admin:core_vehicle_change', args=[obj.vehicle.pk])
        return format_html(
            '<a href="{}" class="font-bold text-primary-600 dark:text-primary-400 hover:underline">{}</a>',
            url, obj.vehicle.registration_number
        )

    @admin.display(description="Issue")
    def description_preview(self, obj):
        text = obj.description[:60]
        if len(obj.description) > 60:
            text += '…'
        return format_html(
            '<span class="text-xs text-slate-700 dark:text-slate-300 font-medium" title="{}">{}</span>',
            obj.description, text
        )

    @admin.display(description="Age")
    def age_display(self, obj):
        today = timezone.now().date()
        if obj.status == 'resolved' and obj.resolved_date:
            delta = (obj.resolved_date - obj.date_reported).days
            return format_html(
                '<span style="color:#4ade80;">Resolved in {} day(s)</span>',
                delta
            )
        delta = (today - obj.date_reported).days
        if delta >= 30:
            return format_html(
                '<span style="color:#f87171; font-weight:700;">⚠️ {}+ days!</span>',
                delta
            )
        elif delta >= 7:
            weeks = delta // 7
            return format_html(
                '<span style="color:#fbbf24; font-weight:600;">{} week(s) old</span>',
                weeks
            )
        elif delta >= 1:
            return format_html(
                '<span style="color:#e2e8f0;">{} day(s) old</span>',
                delta
            )
        return mark_safe('<span style="color:#38bdf8;">Today</span>')

    @admin.display(description="Status", ordering='status')
    def status_badge(self, obj):
        colors = {
            'open':        ('#dc2626', '🔴'),
            'in_progress': ('#3b82f6', '🔧'),
            'resolved':    ('#16a34a', '✅'),
        }
        bg, icon = colors.get(obj.status, ('#64748b', '❓'))
        label = obj.get_status_display()
        return format_html(
            '<span style="background:{}; color:#fff; padding:3px 10px; border-radius:12px; '
            'font-size:11px; font-weight:700; white-space:nowrap;">{} {}</span>',
            bg, icon, label
        )


# ==========================================================================
#  5. ServiceReminder Admin
# ==========================================================================

@admin.register(ServiceReminder)
class ServiceReminderAdmin(ModelAdmin):
    list_display = (
        'vehicle_link', 'service_task', 'last_service_km_display',
        'due_km_display', 'km_remaining_display', 'is_active', 'service_alert',
    )
    list_editable = ('is_active',)
    list_filter = (ServiceDueFilter, 'is_active')
    search_fields = ('vehicle__registration_number', 'service_task')
    autocomplete_fields = ['vehicle']
    actions = [mark_reminders_inactive]
    list_per_page = 30

    @admin.display(description="Vehicle", ordering='vehicle__registration_number')
    def vehicle_link(self, obj):
        from django.urls import reverse
        url = reverse('admin:core_vehicle_change', args=[obj.vehicle.pk])
        return format_html(
            '<a href="{}" style="color:#38bdf8; font-weight:700;">{}</a>',
            url, obj.vehicle.registration_number
        )

    @admin.display(description="Last Service", ordering='last_service_km')
    def last_service_km_display(self, obj):
        last_str = f"{obj.last_service_km:,} km" if obj.last_service_km is not None else "—"
        return format_html(
            '<span style="color:#94a3b8;">{}</span>',
            last_str
        )

    @admin.display(description="Due At")
    def due_km_display(self, obj):
        due_str = f"{obj.due_km:,} km" if obj.due_km is not None else "—"
        return format_html(
            '<span style="color:#e2e8f0; font-weight:600;">{}</span>',
            due_str
        )

    @admin.display(description="KM Remaining")
    def km_remaining_display(self, obj):
        km_left = obj.km_until_due
        if km_left <= 0:
            overdue = abs(obj.due_km - obj.vehicle.current_km)
            overdue_str = f"🔴 Overdue by {overdue:,} km!"
            return format_html(
                '<span style="color:#f87171; font-weight:700;">{}</span>',
                overdue_str
            )
        elif km_left <= 2000:
            due_str = f"🟡 {km_left:,} km left"
            return format_html(
                '<span style="color:#fbbf24; font-weight:700;">{}</span>',
                due_str
            )
        due_str = f"🟢 {km_left:,} km left"
        return format_html(
            '<span style="color:#4ade80;">{}</span>',
            due_str
        )

    @admin.display(description="Alert")
    def service_alert(self, obj):
        if not obj.is_active:
            return mark_safe('<span style="color:#475569;">Inactive</span>')
        km_left = obj.km_until_due
        if km_left <= 0:
            return mark_safe(
                '<span style="background:#dc2626; color:#fff; padding:3px 10px; border-radius:12px; '
                'font-size:11px; font-weight:700;">🚨 OVERDUE</span>'
            )
        elif km_left <= 2000:
            return mark_safe(
                '<span style="background:#d97706; color:#fff; padding:3px 10px; border-radius:12px; '
                'font-size:11px; font-weight:700;">⚠️ Due Soon</span>'
            )
        return mark_safe(
            '<span style="background:#16a34a; color:#fff; padding:3px 10px; border-radius:12px; '
            'font-size:11px; font-weight:700;">✅ Healthy</span>'
        )


# ==========================================================================
#  6. PartInventory Admin
# ==========================================================================

@admin.register(PartInventory)
class PartInventoryAdmin(ModelAdmin):
    list_display = (
        'part_name', 'sku_display', 'stock_display', 'minimum_stock_level',
        'default_unit_price_display', 'stock_status', 'reorder_alert',
    )
    list_filter = ('current_stock',)
    search_fields = ('part_name', 'sku')
    list_per_page = 30

    @admin.display(description="SKU")
    def sku_display(self, obj):
        if not obj.sku:
            return mark_safe('<span style="color:#475569;">—</span>')
        return format_html(
            '<span style="background:#1e293b; color:#93c5fd; padding:2px 8px; border-radius:4px; '
            'font-family:monospace; font-size:12px; font-weight:600; border:1px solid #334155;">'
            '{}</span>',
            obj.sku
        )

    @admin.display(description="Stock", ordering='current_stock')
    def stock_display(self, obj):
        stock = obj.current_stock
        minimum = obj.minimum_stock_level
        if minimum > 0:
            pct = min(100, int((stock / max(minimum * 2, 1)) * 100))
        else:
            pct = 100
        if stock <= minimum:
            bar_color = '#ef4444'
            text_color = '#f87171'
        elif stock <= minimum * 1.2:
            bar_color = '#eab308'
            text_color = '#fbbf24'
        else:
            bar_color = '#22c55e'
            text_color = '#4ade80'
        return format_html(
            '<div style="min-width:80px;">'
            '<div style="background:#1e293b; border-radius:6px; height:6px; width:100%; '
            'border:1px solid #475569; overflow:hidden; margin-bottom:3px;">'
            '<div style="background:{}; height:100%; width:{}%; border-radius:6px;"></div>'
            '</div>'
            '<span style="color:{}; font-weight:700; font-size:12px;">{} units</span>'
            '</div>',
            bar_color, pct, text_color, stock
        )

    @admin.display(description="Unit Price", ordering='default_unit_price')
    def default_unit_price_display(self, obj):
        price_str = f"₹{obj.default_unit_price:,.2f}" if obj.default_unit_price else "₹0.00"
        return format_html(
            '<span style="color:#e2e8f0; font-weight:600;">{}</span>',
            price_str
        )

    @admin.display(description="Status")
    def stock_status(self, obj):
        if obj.current_stock <= obj.minimum_stock_level:
            return mark_safe(
                '<span style="background:#dc2626; color:#fff; padding:3px 10px; border-radius:12px; '
                'font-size:11px; font-weight:700;">🔴 Low Stock</span>'
            )
        elif obj.current_stock <= obj.minimum_stock_level * 1.2:
            return mark_safe(
                '<span style="background:#d97706; color:#fff; padding:3px 10px; border-radius:12px; '
                'font-size:11px; font-weight:700;">🟡 Near Minimum</span>'
            )
        return mark_safe(
            '<span style="background:#16a34a; color:#fff; padding:3px 10px; border-radius:12px; '
            'font-size:11px; font-weight:700;">🟢 In Stock</span>'
        )

    @admin.display(description="Reorder?")
    def reorder_alert(self, obj):
        if obj.current_stock <= obj.minimum_stock_level:
            deficit = obj.minimum_stock_level - obj.current_stock + obj.minimum_stock_level  # reorder to 2x min
            return format_html(
                '<span style="color:#f87171; font-weight:700;">⚠️ Reorder ~{} units</span>',
                deficit
            )
        return mark_safe('<span style="color:#4ade80;">✅ Sufficient</span>')


@admin.register(PreTripInspectionChecklist)
class PreTripInspectionChecklistAdmin(ModelAdmin):
    list_display = [
        'inspection_number',
        'vehicle_link',
        'driver_link',
        'inspection_date',
        'odometer_display',
        'status_badge',
        'defect_status',
        'trip_link',
    ]
    list_filter = ['overall_status', 'supervisor_approved', 'inspection_date']
    search_fields = ['inspection_number', 'vehicle__registration_number', 'driver__name', 'driver_signature_name']
    readonly_fields = ['inspection_number', 'created_at']
    date_hierarchy = 'inspection_date'

    fieldsets = (
        ("Inspection Meta", {
            "fields": (
                "inspection_number",
                ("vehicle", "driver"),
                ("trip", "contract_trip"),
                ("inspection_date", "odometer_reading", "odometer_photo"),
            )
        }),
        ("1. Critical Mechanical & Fluids (Failure Grounds Vehicle)", {
            "fields": (
                ("tyres_tread_and_pressure", "brakes_functional"),
                ("engine_oil_level", "coolant_level"),
                ("brake_fluid_level", "battery_and_wiring"),
            )
        }),
        ("2. Lights, Signals & Visibility", {
            "fields": (
                ("headlights_and_highbeam", "taillights_and_brakelights"),
                ("indicators_and_hazard", "wipers_and_washer_fluid"),
                ("horn_and_mirrors",),
            )
        }),
        ("3. Mandatory Safety & Emergency Gear", {
            "fields": (
                ("first_aid_kit_present", "fire_extinguisher_present"),
                ("spare_wheel_and_jack", "ac_or_fans_working"),
                ("cabin_cleanliness",),
            )
        }),
        ("4. Defects & Sign-off", {
            "fields": (
                "has_visible_body_scratches",
                "exterior_condition_notes",
                "defect_notes",
                "overall_status",
                "defect_ticket",
                ("driver_signature_name", "supervisor_approved"),
                "created_at",
            )
        }),
    )

    @admin.display(description="Vehicle", ordering='vehicle__registration_number')
    def vehicle_link(self, obj):
        return format_html(
            '<a href="/admin/core/vehicle/{}/change/" style="font-weight:700; color:#38bdf8;">🚗 {}</a>',
            obj.vehicle.pk, obj.vehicle.registration_number
        )

    @admin.display(description="Driver", ordering='driver__name')
    def driver_link(self, obj):
        return format_html(
            '<a href="/admin/core/driver/{}/change/" style="color:#e2e8f0;">👨‍✈️ {}</a>',
            obj.driver.pk, obj.driver.name
        )

    @admin.display(description="Odometer")
    def odometer_display(self, obj):
        return f"{obj.odometer_reading:,} KM"

    @admin.display(description="Safety Status", ordering='overall_status')
    def status_badge(self, obj):
        if obj.overall_status == 'passed':
            return mark_safe('<span style="background:#16a34a; color:#fff; padding:3px 10px; border-radius:12px; font-size:11px; font-weight:700;">🟢 PASSED - FIT</span>')
        elif obj.overall_status == 'conditional_pass':
            return mark_safe('<span style="background:#d97706; color:#fff; padding:3px 10px; border-radius:12px; font-size:11px; font-weight:700;">🟡 CONDITIONAL PASS</span>')
        return mark_safe('<span style="background:#dc2626; color:#fff; padding:3px 10px; border-radius:12px; font-size:11px; font-weight:700;">🔴 FAILED - GROUNDED</span>')

    @admin.display(description="Defect Ticket")
    def defect_status(self, obj):
        if obj.defect_ticket:
            return format_html(
                '<a href="/admin/maintenance/defectticket/{}/change/" style="color:#f87171; font-weight:700;">⚠️ Ticket #{}</a>',
                obj.defect_ticket.pk, obj.defect_ticket.pk
            )
        return mark_safe('<span style="color:#94a3b8;">None</span>')

    @admin.display(description="Linked Trip")
    def trip_link(self, obj):
        if obj.trip:
            return format_html('<a href="/trips/{}/">Trip #{}</a>', obj.trip.pk, obj.trip.trip_id)
        if obj.contract_trip:
            return format_html('<a href="/admin/fleet_contracts/contracttriplog/{}/change/">Shift Log #{}</a>', obj.contract_trip.pk, obj.contract_trip.pk)
        return "Ad-hoc / Yard"


# ==============================================================================
#  Interactive 2D Vehicle Damage Marker & Inspection Admins
# ==============================================================================

class VehicleDamageMarkerInline(TabularInline):
    model = VehicleDamageMarker
    extra = 0
    fields = ('marker_number', 'damage_type', 'severity', 'panel_zone', 'view_angle', 'x_percent', 'y_percent', 'is_new_damage', 'estimated_repair_cost', 'notes')
    ordering = ('marker_number',)


@admin.register(VehicleDamageInspection)
class VehicleDamageInspectionAdmin(ModelAdmin):
    list_display = (
        'inspection_number_display',
        'vehicle_badge',
        'inspection_type_badge',
        'customer_name',
        'markers_summary',
        'deposit_display',
        'deductions_display',
        'deposit_status_badge',
        'created_at',
        'studio_link',
    )
    list_filter = ('inspection_type', 'vehicle_body_style', 'deposit_status', 'created_at')
    search_fields = ('inspection_number', 'vehicle__registration_number', 'customer_name', 'customer_phone', 'inspector_name')
    inlines = [VehicleDamageMarkerInline]
    date_hierarchy = 'created_at'

    @admin.display(description="Inspection #", ordering='inspection_number')
    def inspection_number_display(self, obj):
        return format_html(
            '<span class="badge-insp-num inline-flex items-center px-2 py-0.5 rounded font-mono text-xs font-bold shadow-sm" '
            'style="background:#f0f9ff; color:#0369a1; border:1px solid #bae6fd;">'
            '{}</span>',
            obj.inspection_number
        )

    @admin.display(description="Vehicle", ordering='vehicle__registration_number')
    def vehicle_badge(self, obj):
        return format_html(
            '<span class="font-bold text-slate-900 dark:text-sky-300 flex items-center gap-1.5">🚗 {}</span>',
            obj.vehicle.registration_number
        )

    @admin.display(description="Type", ordering='inspection_type')
    def inspection_type_badge(self, obj):
        if obj.inspection_type == 'checkout':
            return mark_safe(
                '<span class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold shadow-sm" '
                'style="background:#e0f2fe; color:#0369a1; border:1px solid #7dd3fc; white-space:nowrap;">'
                '🛫 Check-Out</span>'
            )
        elif obj.inspection_type == 'checkin':
            return mark_safe(
                '<span class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold shadow-sm" '
                'style="background:#ecfdf5; color:#047857; border:1px solid #a7f3d0; white-space:nowrap;">'
                '🛬 Return Check-In</span>'
            )
        return mark_safe(
            '<span class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold shadow-sm" '
            'style="background:#eef2ff; color:#4338ca; border:1px solid #c7d2fe; white-space:nowrap;">'
            '🔍 Routine</span>'
        )

    @admin.display(description="Damage Markers")
    def markers_summary(self, obj):
        total = obj.markers.count()
        new_cnt = obj.markers.filter(is_new_damage=True).count()
        if total == 0:
            return mark_safe('<span style="color:#10b981; font-weight:600;">✓ Pristine / Zero Damage</span>')
        if new_cnt > 0:
            return format_html(
                '<span style="color:#ef4444; font-weight:700;">⚠️ {} total ({} NEW)</span>',
                total, new_cnt
            )
        return format_html('<span class="text-slate-600 dark:text-slate-300 font-medium">{} pre-existing</span>', total)

    @admin.display(description="Deposit Held", ordering='security_deposit_held')
    def deposit_display(self, obj):
        val = obj.security_deposit_held or 0
        val_str = f"₹{val:,.2f}"
        return format_html(
            '<span class="font-mono text-xs font-bold px-2 py-0.5 rounded shadow-sm" '
            'style="background:#fffbeb; color:#b45309; border:1px solid #fde68a;">{}</span>',
            val_str
        )

    @admin.display(description="New Deductions", ordering='new_damage_deductions')
    def deductions_display(self, obj):
        val = obj.new_damage_deductions or 0
        val_str = f"₹{val:,.2f}"
        if val > 0:
            return format_html(
                '<span class="font-mono text-xs font-bold px-2 py-0.5 rounded shadow-sm" '
                'style="background:#fff1f2; color:#be123c; border:1px solid #fecdd3;">{}</span>',
                val_str
            )
        return format_html(
            '<span class="font-mono text-xs font-semibold px-2 py-0.5 rounded" '
            'style="background:#f8fafc; color:#64748b; border:1px solid #e2e8f0;">{}</span>',
            val_str
        )

    @admin.display(description="Deposit Status", ordering='deposit_status')
    def deposit_status_badge(self, obj):
        if obj.deposit_status == 'held':
            return mark_safe('<span style="background:#fef3c7; color:#92400e; border:1px solid #fde68a; padding:2px 8px; border-radius:8px; font-size:11px; font-weight:700;">HELD</span>')
        elif obj.deposit_status == 'settled_refund':
            return mark_safe('<span style="background:#ecfdf5; color:#065f46; border:1px solid #a7f3d0; padding:2px 8px; border-radius:8px; font-size:11px; font-weight:700;">REFUNDED</span>')
        elif obj.deposit_status == 'settled_deduction':
            return mark_safe('<span style="background:#fff1f2; color:#9f1239; border:1px solid #fecdd3; padding:2px 8px; border-radius:8px; font-size:11px; font-weight:700;">DEDUCTED</span>')
        return mark_safe('<span style="color:#94a3b8;">None</span>')

    @admin.display(description="Interactive Studio")
    def studio_link(self, obj):
        return format_html(
            '<a href="/maintenance/damage-marker/?inspection_id={}" style="display:inline-flex; align-items:center; gap:5px; background:linear-gradient(135deg, #4f46e5 0%, #4338ca 100%); color:#ffffff; padding:4px 10px; border-radius:6px; font-size:11px; font-weight:700; text-decoration:none; box-shadow:0 1px 3px rgba(79,70,229,0.3); transition:all 0.15s ease;">🎨 2D Studio &rarr;</a>',
            obj.pk
        )


@admin.register(VehicleDamageMarker)
class VehicleDamageMarkerAdmin(ModelAdmin):
    list_display = (
        'marker_number',
        'inspection_link',
        'damage_type',
        'severity_badge',
        'panel_zone',
        'is_new_damage',
        'estimated_repair_cost',
        'created_at',
    )
    list_filter = ('damage_type', 'severity', 'is_new_damage', 'panel_zone')
    search_fields = ('inspection__inspection_number', 'inspection__vehicle__registration_number', 'notes')

    @admin.display(description="Inspection")
    def inspection_link(self, obj):
        return format_html(
            '<a href="/admin/maintenance/vehicledamageinspection/{}/change/">{}</a>',
            obj.inspection.pk, obj.inspection.inspection_number
        )

    @admin.display(description="Severity", ordering='severity')
    def severity_badge(self, obj):
        if obj.severity == 'severe':
            return mark_safe('<span style="background:#dc2626; color:#fff; padding:2px 8px; border-radius:8px; font-size:11px; font-weight:700;">SEVERE</span>')
        elif obj.severity == 'moderate':
            return mark_safe('<span style="background:#d97706; color:#fff; padding:2px 8px; border-radius:8px; font-size:11px; font-weight:700;">MODERATE</span>')
        return mark_safe('<span style="background:#16a34a; color:#fff; padding:2px 8px; border-radius:8px; font-size:11px; font-weight:700;">MINOR</span>')




