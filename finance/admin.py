from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from .models import (
    TripExpense,
    SupplierTripCost,
    DriverAdvance,
    DriverAdvanceAllocation,
    DriverSettlement,
    DriverSalaryProfile,
    DriverPayslip,
)


# ── Bulk Actions ──────────────────────────────────────────────────────────────

@admin.action(description="💼 Mark selected expenses as Billable to Customer")
def mark_billable(modeladmin, request, queryset):
    updated = queryset.update(billable_to_customer=True)
    modeladmin.message_user(request, f"{updated} expense(s) marked as billable.")


@admin.action(description="🚫 Mark selected expenses as Non-Billable (Company Cost)")
def mark_non_billable(modeladmin, request, queryset):
    updated = queryset.update(billable_to_customer=False)
    modeladmin.message_user(request, f"{updated} expense(s) marked as non-billable.")


@admin.action(description="✅ Mark selected settlements as Settled Today")
def mark_settled_today(modeladmin, request, queryset):
    today = timezone.now().date()
    updated = queryset.update(settled_on=today)
    modeladmin.message_user(request, f"{updated} settlement(s) marked as settled on {today}.")


# ── Custom Filters ─────────────────────────────────────────────────────────────

class UnallocatedAdvanceFilter(admin.SimpleListFilter):
    title = _('Allocation Status')
    parameter_name = 'allocation_status'

    def lookups(self, request, model_admin):
        return [
            ('unallocated', _('🔴 Fully Unallocated')),
            ('partial', _('🟡 Partially Allocated')),
            ('settled', _('🟢 Fully Allocated / Settled')),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'unallocated':
            pks = [a.pk for a in queryset if a.remaining_amount == a.amount]
            return queryset.filter(pk__in=pks)
        if self.value() == 'partial':
            pks = [a.pk for a in queryset if 0 < a.remaining_amount < a.amount]
            return queryset.filter(pk__in=pks)
        if self.value() == 'settled':
            pks = [a.pk for a in queryset if a.remaining_amount == 0]
            return queryset.filter(pk__in=pks)
        return queryset


class SettlementStatusFilter(admin.SimpleListFilter):
    title = _('Settlement Status')
    parameter_name = 'settlement_status'

    def lookups(self, request, model_admin):
        return [
            ('pending', _('⏳ Pending Settlement')),
            ('settled', _('✓ Settled')),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'pending':
            return queryset.filter(settled_on__isnull=True)
        if self.value() == 'settled':
            return queryset.filter(settled_on__isnull=False)
        return queryset


# ── Inlines ───────────────────────────────────────────────────────────────────

class DriverAdvanceAllocationInline(admin.TabularInline):
    model = DriverAdvanceAllocation
    extra = 1
    autocomplete_fields = ['trip']


# ── Admins ────────────────────────────────────────────────────────────────────

@admin.register(TripExpense)
class TripExpenseAdmin(admin.ModelAdmin):
    list_display = (
        'trip_or_contract',
        'date',
        'expense_type_badge',
        'amount_display',
        'paid_by_badge',
        'billable_badge',
        'receipt_link',
    )
    list_filter = ('expense_type', 'paid_by', 'billable_to_customer', 'date')
    search_fields = (
        'trip__trip_id',
        'contract_trip__shift__route__name',
        'description',
    )
    autocomplete_fields = ['trip']
    date_hierarchy = 'date'
    actions = [mark_billable, mark_non_billable]

    @admin.display(description='Trip / Shift')
    def trip_or_contract(self, obj):
        if obj.trip:
            return format_html(
                '<a href="/admin/operations/trip/{}/change/" class="font-weight-bold">Trip #{}</a>',
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

    @admin.display(description='Expense Type', ordering='expense_type')
    def expense_type_badge(self, obj):
        type_styles = {
            'toll': ('badge-primary', 'fas fa-road', 'Toll'),
            'permit': ('badge-info', 'fas fa-id-badge', 'Permit'),
            'parking': ('badge-secondary', 'fas fa-parking', 'Parking'),
            'epass': ('badge-info', 'fas fa-ticket-alt', 'E-Pass'),
            'border_tax': ('badge-dark', 'fas fa-passport', 'Border Tax'),
            'driver_food': ('badge-warning', 'fas fa-utensils', 'Driver Food'),
            'hotel': ('badge-warning', 'fas fa-hotel', 'Hotel Room'),
            'water': ('badge-info', 'fas fa-tint', 'Water Bottles'),
            'snacks': ('badge-warning', 'fas fa-cookie-bite', 'Snacks'),
            'repair': ('badge-danger', 'fas fa-wrench', 'Emergency Repair'),
            'other': ('badge-secondary', 'fas fa-ellipsis-h', 'Other'),
        }
        badge_cls, icon, label = type_styles.get(obj.expense_type, ('badge-secondary', 'fas fa-receipt', obj.get_expense_type_display()))
        return format_html('<span class="badge {}"><i class="{} mr-1"></i>{}</span>', badge_cls, icon, label)

    @admin.display(description='Amount', ordering='amount')
    def amount_display(self, obj):
        return format_html(
            '<strong class="text-white" style="font-size: 13px;">{}</strong>',
            f'₹{obj.amount:,.2f}',
        )

    @admin.display(description='Paid By', ordering='paid_by')
    def paid_by_badge(self, obj):
        badges = {
            'company': ('badge-primary', 'Company'),
            'driver': ('badge-warning', 'Driver'),
            'customer': ('badge-info', 'Customer'),
        }
        badge_cls, label = badges.get(obj.paid_by, ('badge-secondary', obj.get_paid_by_display()))
        return format_html('<span class="badge {}">{}</span>', badge_cls, label)

    @admin.display(description='Billable to Client', ordering='billable_to_customer')
    def billable_badge(self, obj):
        if obj.billable_to_customer:
            return mark_safe('<span class="badge badge-success"><i class="fas fa-check mr-1"></i>Billable</span>')
        return mark_safe('<span class="badge badge-secondary">Non-Billable</span>')

    @admin.display(description='Receipt')
    def receipt_link(self, obj):
        if obj.receipt:
            return format_html(
                '<a href="{}" target="_blank" class="btn btn-xs btn-outline-info">'
                '<i class="fas fa-receipt mr-1"></i>View</a>',
                obj.receipt.url,
            )
        return '—'


@admin.register(DriverAdvance)
class DriverAdvanceAdmin(admin.ModelAdmin):
    inlines = [DriverAdvanceAllocationInline]
    list_display = (
        'driver_badge',
        'date',
        'amount_display',
        'allocated_display',
        'remaining_badge',
        'trip_or_contract',
        'notes',
    )
    list_filter = ('date', 'driver', UnallocatedAdvanceFilter)
    search_fields = (
        'driver__name',
        'trip__trip_id',
        'contract_trip__shift__route__name',
        'notes',
    )
    autocomplete_fields = ['driver', 'trip']
    date_hierarchy = 'date'

    @admin.display(description='Driver', ordering='driver')
    def driver_badge(self, obj):
        if obj.driver:
            return format_html(
                '<a href="/admin/core/driver/{}/change/" class="font-weight-bold">👤 {}</a>',
                obj.driver.pk,
                obj.driver.name,
            )
        return '—'

    @admin.display(description='Total Advance', ordering='amount')
    def amount_display(self, obj):
        return format_html(
            '<strong class="text-white" style="font-size: 13px;">{}</strong>',
            f'₹{obj.amount:,.2f}',
        )

    @admin.display(description='Allocated to Trips')
    def allocated_display(self, obj):
        return f'₹{obj.allocated_amount:,.2f}'

    @admin.display(description='Remaining Balance')
    def remaining_badge(self, obj):
        rem = obj.remaining_amount
        if rem == 0:
            return mark_safe('<span class="badge badge-success">✓ Fully Settled</span>')
        if rem == obj.amount:
            return format_html(
                '<span class="badge badge-danger">🔴 {} (Unallocated)</span>',
                f'₹{rem:,.2f}',
            )
        return format_html(
            '<span class="badge badge-warning">🟡 {} (Partial)</span>',
            f'₹{rem:,.2f}',
        )

    @admin.display(description='Linked Trip')
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
        return mark_safe('<span class="text-muted">—</span>')


@admin.register(DriverSettlement)
class DriverSettlementAdmin(admin.ModelAdmin):
    list_display = (
        'driver_badge',
        'trip_or_contract',
        'total_days',
        'batta_display',
        'adv_adj_display',
        'expenses_display',
        'cash_collected_display',
        'fines_deduction_display',
        'balance_badge',
        'settled_badge',
    )
    list_filter = ('settled_on', 'driver', SettlementStatusFilter)
    search_fields = (
        'driver__name',
        'trip__trip_id',
        'contract_trip__shift__route__name',
    )
    autocomplete_fields = ['driver', 'trip']
    actions = [mark_settled_today]

    @admin.display(description='Driver', ordering='driver')
    def driver_badge(self, obj):
        if obj.driver:
            return format_html(
                '<a href="/admin/core/driver/{}/change/" class="font-weight-bold">👤 {}</a>',
                obj.driver.pk,
                obj.driver.name,
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
        return '—'

    @admin.display(description='Driver Batta', ordering='batta')
    def batta_display(self, obj):
        return f'₹{obj.batta:,.2f}'

    @admin.display(description='Adv Adjusted')
    def adv_adj_display(self, obj):
        return f'₹{obj.advance_adjusted:,.2f}'

    @admin.display(description='Driver Expenses')
    def expenses_display(self, obj):
        return f'₹{obj.driver_expenses:,.2f}'

    @admin.display(description='Cash Collected')
    def cash_collected_display(self, obj):
        return f'₹{obj.cash_collected:,.2f}'

    @admin.display(description='Traffic Fines')
    def fines_deduction_display(self, obj):
        if obj.traffic_fines_deduction > 0:
            return format_html(
                '<span class="text-danger font-weight-bold">{}</span>',
                f'₹{obj.traffic_fines_deduction:,.2f}',
            )
        return '₹0'

    @admin.display(description='Final Balance')
    def balance_badge(self, obj):
        bal = obj.balance
        if bal > 0:
            return format_html(
                '<span class="badge badge-success font-weight-bold" style="font-size: 13px;">'
                '+{} (Company Pays)</span>',
                f'₹{bal:,.2f}',
            )
        if bal < 0:
            return format_html(
                '<span class="badge badge-danger font-weight-bold" style="font-size: 13px;">'
                '-{} (Driver Owes)</span>',
                f'₹{abs(bal):,.2f}',
            )
        return mark_safe('<span class="badge badge-secondary">₹0.00 (Balanced)</span>')

    @admin.display(description='Settlement')
    def settled_badge(self, obj):
        if obj.settled_on:
            return format_html(
                '<span class="badge badge-success"><i class="fas fa-check-circle mr-1"></i>{}</span>',
                obj.settled_on,
            )
        return mark_safe('<span class="badge badge-warning"><i class="fas fa-clock mr-1"></i>Pending</span>')


@admin.register(SupplierTripCost)
class SupplierTripCostAdmin(admin.ModelAdmin):
    list_display = (
        'date',
        'trip_or_contract',
        'supplier_badge',
        'vehicle_badge',
        'amount_display',
        'description',
    )
    list_filter = ('date', 'supplier')
    search_fields = (
        'trip__trip_id',
        'trip__vehicle__registration_number',
        'supplier__name',
    )
    autocomplete_fields = ['trip', 'vehicle', 'supplier']
    date_hierarchy = 'date'

    @admin.display(description='Trip / Shift')
    def trip_or_contract(self, obj):
        if obj.trip:
            return format_html(
                '<a href="/admin/operations/trip/{}/change/" class="font-weight-bold">Trip #{}</a>',
                obj.trip.pk,
                obj.trip.trip_id,
            )
        if obj.contract_trip:
            return format_html(
                '<a href="/admin/fleet_contracts/contracttriplog/{}/change/">Shift: {}</a>',
                obj.contract_trip.pk,
                obj.contract_trip,
            )
        return '—'

    @admin.display(description='Outsourced Supplier', ordering='supplier')
    def supplier_badge(self, obj):
        if obj.supplier:
            return format_html(
                '<a href="/admin/core/supplier/{}/change/" class="font-weight-bold">'
                '<span class="badge badge-secondary"><i class="fas fa-truck-loading mr-1"></i>{}</span></a>',
                obj.supplier.pk,
                obj.supplier.name,
            )
        return '—'

    @admin.display(description='Vehicle', ordering='vehicle')
    def vehicle_badge(self, obj):
        if obj.vehicle:
            return format_html(
                '<a href="/admin/core/vehicle/{}/change/">🚌 {}</a>',
                obj.vehicle.pk,
                obj.vehicle.registration_number,
            )
        return '—'

    @admin.display(description='Amount', ordering='amount')
    def amount_display(self, obj):
        return format_html(
            '<strong class="text-white" style="font-size: 13px;">{}</strong>',
            f'₹{obj.amount:,.2f}',
        )


@admin.register(DriverSalaryProfile)
class DriverSalaryProfileAdmin(admin.ModelAdmin):
    list_display = ('driver_link', 'basic_salary_display', 'allowances_display', 'epf_info', 'esi_info')
    search_fields = ('driver__name', 'driver__phone', 'epf_number', 'esi_number')
    autocomplete_fields = ('driver',)

    @admin.display(description='Driver', ordering='driver__name')
    def driver_link(self, obj):
        return format_html(
            '<a href="/admin/core/driver/{}/change/"><strong>👤 {}</strong></a>',
            obj.driver.pk, obj.driver.name
        )

    @admin.display(description='Basic Monthly Salary')
    def basic_salary_display(self, obj):
        return f"₹{obj.basic_salary:,.2f}"

    @admin.display(description='Monthly Allowances')
    def allowances_display(self, obj):
        return f"₹{obj.allowances:,.2f}"

    @admin.display(description='EPF Settings')
    def epf_info(self, obj):
        if obj.epf_number:
            return format_html('<span class="badge badge-info">EPF: {} ({}%)</span>', obj.epf_number, obj.epf_deduction_rate)
        return mark_safe('<span class="text-muted">Not enrolled</span>')

    @admin.display(description='ESI Settings')
    def esi_info(self, obj):
        if obj.esi_number:
            return format_html('<span class="badge badge-success">ESI: {} ({}%)</span>', obj.esi_number, obj.esi_deduction_rate)
        return mark_safe('<span class="text-muted">Not enrolled</span>')


@admin.register(DriverPayslip)
class DriverPayslipAdmin(admin.ModelAdmin):
    list_display = (
        'driver_link', 'period_display', 'days_present_badge',
        'gross_display', 'deductions_display', 'net_payable_badge', 'actions_display'
    )
    list_filter = ('year', 'month')
    search_fields = ('driver__name', 'driver__phone')
    autocomplete_fields = ('driver',)

    @admin.display(description='Driver', ordering='driver__name')
    def driver_link(self, obj):
        return format_html(
            '<a href="/admin/core/driver/{}/change/"><strong>👤 {}</strong></a>',
            obj.driver.pk, obj.driver.name
        )

    @admin.display(description='Period', ordering='month')
    def period_display(self, obj):
        import calendar
        month_name = calendar.month_abbr[obj.month] if 1 <= obj.month <= 12 else str(obj.month)
        return f"{month_name} {obj.year}"

    @admin.display(description='Duty Days', ordering='days_present')
    def days_present_badge(self, obj):
        return format_html('<span class="badge badge-primary">{} Days</span>', obj.days_present)

    @admin.display(description='Gross Earnings')
    def gross_display(self, obj):
        return f"₹{obj.gross_earnings:,.2f}"

    @admin.display(description='Total Deductions')
    def deductions_display(self, obj):
        return format_html('<span class="text-danger">-₹{}</span>', f"{obj.total_deductions:,.2f}")

    @admin.display(description='Net Take-Home Pay')
    def net_payable_badge(self, obj):
        return format_html(
            '<strong class="text-success" style="font-size: 14px;">₹{}</strong>',
            f"{obj.net_payable:,.2f}"
        )

    @admin.display(description='Payslip Slip')
    def actions_display(self, obj):
        return format_html(
            '<a href="/finance/payslips/{}/" target="_blank" class="button" style="padding: 3px 8px; font-size: 11px;">📄 View Slip</a>',
            obj.pk
        )

