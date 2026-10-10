from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from .models import (
    FuelRecord,
    CorporatePetroAccount,
    PetroRecharge,
    CorporateFastagAccount,
    FastagRecharge,
    FastagTollDeduction,
)


# ── Custom Filters ─────────────────────────────────────────────────────────────

class TheftAlertFilter(admin.SimpleListFilter):
    title = _('Fuel Theft / Anomaly Alert')
    parameter_name = 'theft_alert'

    def lookups(self, request, model_admin):
        return [
            ('theft', _('⚠️ Low Mileage / Theft Suspected')),
            ('normal', _('✓ Normal Mileage')),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'theft':
            # Collect IDs of records where theft is suspected
            pks = [r.pk for r in queryset.select_related('vehicle') if r.is_theft_suspected]
            return queryset.filter(pk__in=pks)
        if self.value() == 'normal':
            pks = [r.pk for r in queryset.select_related('vehicle') if not r.is_theft_suspected]
            return queryset.filter(pk__in=pks)
        return queryset


class LowBalanceFilter(admin.SimpleListFilter):
    title = _('Balance Status')
    parameter_name = 'balance_status'

    def lookups(self, request, model_admin):
        return [
            ('low', _('⚠️ Low Balance (< ₹5,000)')),
            ('healthy', _('✓ Healthy Balance (≥ ₹5,000)')),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'low':
            return queryset.filter(balance__lt=5000)
        if self.value() == 'healthy':
            return queryset.filter(balance__gte=5000)
        return queryset


# ── Inlines ───────────────────────────────────────────────────────────────────

class PetroRechargeInline(TabularInline):
    model = PetroRecharge
    extra = 1
    fields = ('date', 'amount', 'reference_number', 'notes')


class FastagRechargeInline(TabularInline):
    model = FastagRecharge
    extra = 1
    fields = ('date', 'amount', 'reference_number', 'notes')


class FastagTollDeductionInline(TabularInline):
    model = FastagTollDeduction
    extra = 0
    fields = ('date', 'vehicle', 'trip', 'amount', 'toll_plaza')
    readonly_fields = ('date', 'vehicle', 'trip', 'amount', 'toll_plaza')
    can_delete = False
    show_change_link = True


# ── Admins ────────────────────────────────────────────────────────────────────

@admin.register(FuelRecord)
class FuelRecordAdmin(ModelAdmin):
    list_display = (
        'date',
        'vehicle_badge',
        'trip_or_contract',
        'fuel_quantity_display',
        'fuel_price_display',
        'total_cost_display',
        'distance_display',
        'mileage_display',
        'theft_alert_badge',
        'petro_account_badge',
        'receipt_link',
    )
    list_filter = (TheftAlertFilter, 'vehicle__vehicle_type', 'petro_account', 'date')
    search_fields = (
        'vehicle__registration_number',
        'trip__trip_id',
        'contract_trip__shift__route__name',
        'fuel_station',
        'api_reference_number',
    )
    autocomplete_fields = ['vehicle', 'trip']
    date_hierarchy = 'date'
    readonly_fields = ('amount', 'distance', 'mileage', 'is_theft_suspected')

    @admin.display(description='Vehicle', ordering='vehicle')
    def vehicle_badge(self, obj):
        if obj.vehicle:
            return format_html(
                '<a href="/admin/core/vehicle/{}/change/" class="font-weight-bold">🚌 {}</a>',
                obj.vehicle.pk,
                obj.vehicle.registration_number,
            )
        return '—'

    @admin.display(description='Trip / Shift')
    def trip_or_contract(self, obj):
        if obj.trip:
            return format_html(
                '<a href="/admin/operations/trip/{}/change/">Trip #{}</a>',
                obj.trip.pk,
                obj.trip.trip_id,
            )
        if obj.contract_trip:
            return format_html(
                '<a href="/admin/fleet_contracts/contracttriplog/{}/change/">Shift: {}</a>',
                obj.contract_trip.pk,
                obj.contract_trip,
            )
        return mark_safe('<span class="text-muted">Yard / Non-trip</span>')

    @admin.display(description='Qty (Litres)', ordering='fuel_quantity')
    def fuel_quantity_display(self, obj):
        return format_html('<span class="font-mono text-xs font-semibold text-slate-800 dark:text-slate-200 bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 px-2 py-0.5 rounded">{}</span>', f'{obj.fuel_quantity:,.2f} L')

    @admin.display(description='Rate', ordering='fuel_price')
    def fuel_price_display(self, obj):
        return format_html('<span class="font-mono text-xs text-slate-600 dark:text-slate-400">{}</span>', f'₹{obj.fuel_price:,.2f}/L')

    @admin.display(description='Total Cost', ordering='amount')
    def total_cost_display(self, obj):
        return format_html(
            '<span class="inline-flex items-center px-2.5 py-0.5 rounded font-mono font-bold text-xs bg-amber-50 dark:bg-amber-950/50 text-amber-800 dark:text-amber-300 border border-amber-300 dark:border-amber-800">{}</span>',
            f'₹{obj.amount:,.2f}',
        )

    @admin.display(description='Distance')
    def distance_display(self, obj):
        dist = obj.distance
        if dist > 0:
            return format_html('<span class="font-mono text-xs font-semibold text-sky-700 dark:text-sky-300 bg-sky-50 dark:bg-sky-950/50 border border-sky-300 dark:border-sky-800 px-2 py-0.5 rounded">{}</span>', f'{dist:,} km')
        return mark_safe('<span class="text-slate-400">—</span>')

    @admin.display(description='Mileage')
    def mileage_display(self, obj):
        m = obj.mileage
        if m > 0:
            color_class = "bg-emerald-50 text-emerald-800 border-emerald-300 dark:bg-emerald-950/50 dark:text-emerald-300 dark:border-emerald-800" if m >= 4.0 else "bg-rose-50 text-rose-800 border-rose-300 dark:bg-rose-950/50 dark:text-rose-300 dark:border-rose-800"
            return format_html('<span class="inline-flex items-center px-2 py-0.5 rounded font-mono text-xs font-bold border {}">{}</span>', color_class, f'{m:.2f} km/L')
        return mark_safe('<span class="text-slate-400">—</span>')

    @admin.display(description='Theft Alert')
    def theft_alert_badge(self, obj):
        if obj.is_theft_suspected:
            return mark_safe(
                '<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-bold bg-rose-100 text-rose-800 border border-rose-300 dark:bg-rose-950/60 dark:text-rose-300 dark:border-rose-800 animate-pulse">⚠️ Low Mileage (Theft?)</span>'
            )
        return mark_safe('<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-emerald-50 text-emerald-800 border border-emerald-300 dark:bg-emerald-950/50 dark:text-emerald-300 dark:border-emerald-800">✓ Normal</span>')

    @admin.display(description='Petro Card')
    def petro_account_badge(self, obj):
        if obj.petro_account:
            return format_html(
                '<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-sky-50 text-sky-800 border border-sky-300 dark:bg-sky-950/50 dark:text-sky-300 dark:border-sky-800">💳 {}</span>',
                obj.petro_account.account_name,
            )
        return mark_safe('<span class="inline-flex items-center px-2 py-0.5 rounded text-xs text-slate-500 bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700">Cash / Local</span>')

    @admin.display(description='Receipt')
    def receipt_link(self, obj):
        if obj.receipt:
            return format_html(
                '<a href="{}" target="_blank" class="btn btn-xs btn-outline-info">'
                '<i class="fas fa-file-invoice mr-1"></i>View</a>',
                obj.receipt.url,
            )
        return '—'


@admin.register(CorporatePetroAccount)
class CorporatePetroAccountAdmin(ModelAdmin):
    list_display = (
        'account_name',
        'account_number',
        'balance_badge',
        'is_active_badge',
        'recharges_count',
    )
    list_filter = (LowBalanceFilter, 'is_active')
    search_fields = ('account_name', 'account_number')
    inlines = [PetroRechargeInline]

    @admin.display(description='Wallet Balance', ordering='balance')
    def balance_badge(self, obj):
        if obj.balance < 5000:
            return format_html(
                '<span class="badge badge-danger" style="font-size: 13px;">'
                '<i class="fas fa-exclamation-circle mr-1"></i>{} (Low)</span>',
                f'₹{obj.balance:,.2f}',
            )
        return format_html(
            '<span class="badge badge-success" style="font-size: 13px;">'
            '<i class="fas fa-wallet mr-1"></i>{}</span>',
            f'₹{obj.balance:,.2f}',
        )

    @admin.display(description='Status')
    def is_active_badge(self, obj):
        if obj.is_active:
            return mark_safe('<span class="badge badge-success">✓ Active</span>')
        return mark_safe('<span class="badge badge-secondary">Inactive</span>')

    @admin.display(description='Recharges')
    def recharges_count(self, obj):
        count = obj.recharges.count()
        return format_html('<span class="badge badge-info">{} recharge(s)</span>', count)


@admin.register(CorporateFastagAccount)
class CorporateFastagAccountAdmin(ModelAdmin):
    list_display = (
        'account_name',
        'account_number',
        'balance_badge',
        'is_active_badge',
        'deductions_count',
    )
    list_filter = (LowBalanceFilter, 'is_active')
    search_fields = ('account_name', 'account_number')
    inlines = [FastagRechargeInline, FastagTollDeductionInline]

    @admin.display(description='Master Balance', ordering='balance')
    def balance_badge(self, obj):
        if obj.balance < 3000:
            return format_html(
                '<span class="badge badge-danger" style="font-size: 13px;">'
                '<i class="fas fa-exclamation-circle mr-1"></i>{} (Low)</span>',
                f'₹{obj.balance:,.2f}',
            )
        return format_html(
            '<span class="badge badge-success" style="font-size: 13px;">'
            '<i class="fas fa-wallet mr-1"></i>{}</span>',
            f'₹{obj.balance:,.2f}',
        )

    @admin.display(description='Status')
    def is_active_badge(self, obj):
        if obj.is_active:
            return mark_safe('<span class="badge badge-success">✓ Active</span>')
        return mark_safe('<span class="badge badge-secondary">Inactive</span>')

    @admin.display(description='Toll Deductions')
    def deductions_count(self, obj):
        count = obj.deductions.count()
        return format_html('<span class="badge badge-primary">{} plaza hits</span>', count)


@admin.register(FastagTollDeduction)
class FastagTollDeductionAdmin(ModelAdmin):
    list_display = (
        'date',
        'vehicle_badge',
        'toll_plaza_badge',
        'amount_display',
        'account_badge',
        'trip_link',
    )
    list_filter = ('account', 'date', 'vehicle')
    search_fields = ('vehicle__registration_number', 'toll_plaza')
    date_hierarchy = 'date'
    autocomplete_fields = ['vehicle', 'trip']

    @admin.display(description='Vehicle', ordering='vehicle')
    def vehicle_badge(self, obj):
        if obj.vehicle:
            return format_html(
                '<a href="/admin/core/vehicle/{}/change/" class="font-weight-bold">🚌 {}</a>',
                obj.vehicle.pk,
                obj.vehicle.registration_number,
            )
        return '—'

    @admin.display(description='Toll Plaza')
    def toll_plaza_badge(self, obj):
        return format_html(
            '<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-slate-100 text-slate-700 border border-slate-300 dark:bg-slate-800 dark:text-slate-300 dark:border-slate-700">🛣️ {}</span>',
            obj.toll_plaza or 'National Highway Toll',
        )

    @admin.display(description='Amount', ordering='amount')
    def amount_display(self, obj):
        return format_html(
            '<span class="inline-flex items-center px-2.5 py-0.5 rounded font-mono font-bold text-xs bg-rose-50 dark:bg-rose-950/50 text-rose-800 dark:text-rose-300 border border-rose-300 dark:border-rose-800">{}</span>',
            f'₹{obj.amount:,.2f}',
        )

    @admin.display(description='FASTag Account')
    def account_badge(self, obj):
        if obj.account:
            return format_html(
                '<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-sky-50 text-sky-800 border border-sky-300 dark:bg-sky-950/50 dark:text-sky-300 dark:border-sky-800">💳 {}</span>',
                obj.account.account_name,
            )
        return mark_safe('<span class="text-slate-400">—</span>')

    @admin.display(description='Linked Trip / Shift')
    def trip_link(self, obj):
        if obj.trip:
            return format_html(
                '<a href="/admin/operations/trip/{}/change/">Trip #{}</a>',
                obj.trip.pk,
                obj.trip.trip_id,
            )
        if obj.contract_trip:
            return format_html(
                '<a href="/admin/fleet_contracts/contracttriplog/{}/change/">Shift: {}</a>',
                obj.contract_trip.pk,
                obj.contract_trip,
            )
        return mark_safe('<span class="text-muted">—</span>')
