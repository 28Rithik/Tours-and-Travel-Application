from django.contrib import admin
from unfold.admin import ModelAdmin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from .models import DriverSalaryProfile, DriverPayslip, EmployeePayment


# ── Custom Filters ─────────────────────────────────────────────────────────────

class NetPayableFilter(admin.SimpleListFilter):
    title = _('Net Payable Range')
    parameter_name = 'net_payable'

    def lookups(self, request, model_admin):
        return [
            ('high', _('High (> ₹25,000)')),
            ('mid', _('Standard (₹15,000 - ₹25,000)')),
            ('low', _('Low (< ₹15,000)')),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'high':
            pks = [p.pk for p in queryset if p.net_payable > 25000]
            return queryset.filter(pk__in=pks)
        if self.value() == 'mid':
            pks = [p.pk for p in queryset if 15000 <= p.net_payable <= 25000]
            return queryset.filter(pk__in=pks)
        if self.value() == 'low':
            pks = [p.pk for p in queryset if p.net_payable < 15000]
            return queryset.filter(pk__in=pks)
        return queryset


# ── Admins ────────────────────────────────────────────────────────────────────

@admin.register(DriverSalaryProfile)
class DriverSalaryProfileAdmin(ModelAdmin):
    list_display = (
        'driver_badge',
        'basic_salary_display',
        'allowances_display',
        'gross_monthly_display',
        'epf_badge',
        'esi_badge',
    )
    search_fields = ('driver__name', 'epf_number', 'esi_number')
    autocomplete_fields = ['driver']

    @admin.display(description='Driver', ordering='driver')
    def driver_badge(self, obj):
        if obj.driver:
            return format_html(
                '<a href="/admin/core/driver/{}/change/" class="font-weight-bold">👤 {}</a>',
                obj.driver.pk,
                obj.driver.name,
            )
        return '—'

    @admin.display(description='Basic Salary', ordering='basic_salary')
    def basic_salary_display(self, obj):
        return format_html('<span class="font-mono text-xs font-semibold text-slate-800 dark:text-slate-200">{}</span>', f'₹{obj.basic_salary:,.2f}')

    @admin.display(description='Allowances', ordering='allowances')
    def allowances_display(self, obj):
        return format_html('<span class="font-mono text-xs text-slate-600 dark:text-slate-400">{}</span>', f'₹{obj.allowances:,.2f}')

    @admin.display(description='Gross Monthly Pay')
    def gross_monthly_display(self, obj):
        gross = obj.basic_salary + obj.allowances
        return format_html(
            '<span class="inline-flex items-center px-2.5 py-0.5 rounded font-mono font-bold text-xs bg-emerald-50 dark:bg-emerald-950/50 text-emerald-800 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-800">{}</span>',
            f'₹{gross:,.2f}',
        )

    @admin.display(description='EPF Account')
    def epf_badge(self, obj):
        if obj.epf_number:
            return format_html(
                '<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-sky-50 dark:bg-sky-950/50 text-sky-700 dark:text-sky-300 border border-sky-300 dark:border-sky-800">{} ({}%)</span>',
                obj.epf_number,
                obj.epf_deduction_rate,
            )
        return mark_safe('<span class="inline-flex items-center px-2 py-0.5 rounded text-xs text-slate-500 bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700">Not Enrolled</span>')

    @admin.display(description='ESI Account')
    def esi_badge(self, obj):
        if obj.esi_number:
            return format_html(
                '<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-indigo-50 dark:bg-indigo-950/50 text-indigo-700 dark:text-indigo-300 border border-indigo-300 dark:border-indigo-800">{} ({}%)</span>',
                obj.esi_number,
                obj.esi_deduction_rate,
            )
        return mark_safe('<span class="inline-flex items-center px-2 py-0.5 rounded text-xs text-slate-500 bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700">Not Enrolled</span>')


@admin.register(DriverPayslip)
class DriverPayslipAdmin(ModelAdmin):
    list_display = (
        'driver_badge',
        'period_display',
        'days_present_badge',
        'gross_earnings_display',
        'epf_deduction_display',
        'esi_deduction_display',
        'fines_recovered_display',
        'advances_recovered_display',
        'total_deductions_display',
        'net_payable_display',
    )
    list_filter = ('month', 'year', NetPayableFilter)
    search_fields = ('driver__name',)
    autocomplete_fields = ['driver']

    @admin.display(description='Driver', ordering='driver')
    def driver_badge(self, obj):
        if obj.driver:
            return format_html(
                '<a href="/admin/core/driver/{}/change/" class="font-weight-bold">👤 {}</a>',
                obj.driver.pk,
                obj.driver.name,
            )
        return '—'

    @admin.display(description='Period', ordering='year')
    def period_display(self, obj):
        import calendar
        month_name = calendar.month_name[obj.month] if 1 <= obj.month <= 12 else str(obj.month)
        return format_html(
            '<span class="badge badge-dark"><i class="fas fa-calendar-alt mr-1"></i>{} {}</span>',
            month_name,
            obj.year,
        )

    @admin.display(description='Attendance')
    def days_present_badge(self, obj):
        color = "badge-success" if obj.days_present >= 26 else "badge-warning" if obj.days_present >= 20 else "badge-danger"
        return format_html(
            '<span class="badge {}">{} / 30 days</span>',
            color,
            obj.days_present,
        )

    @admin.display(description='Gross Earnings')
    def gross_earnings_display(self, obj):
        return f'₹{obj.gross_earnings:,.2f}'

    @admin.display(description='EPF')
    def epf_deduction_display(self, obj):
        return f'₹{obj.epf_deduction:,.2f}' if obj.epf_deduction else '₹0'

    @admin.display(description='ESI')
    def esi_deduction_display(self, obj):
        return f'₹{obj.esi_deduction:,.2f}' if obj.esi_deduction else '₹0'

    @admin.display(description='Fines Recovered')
    def fines_recovered_display(self, obj):
        if obj.traffic_fines_deduction > 0:
            return format_html(
                '<span class="text-danger font-weight-bold">{}</span>',
                f'₹{obj.traffic_fines_deduction:,.2f}',
            )
        return '₹0'

    @admin.display(description='Advances Recovered')
    def advances_recovered_display(self, obj):
        if obj.advances_recovered > 0:
            return format_html(
                '<span class="text-warning font-weight-bold">{}</span>',
                f'₹{obj.advances_recovered:,.2f}',
            )
        return '₹0'

    @admin.display(description='Total Deductions')
    def total_deductions_display(self, obj):
        return format_html(
            '<span class="badge badge-warning font-weight-bold">{}</span>',
            f'₹{obj.total_deductions:,.2f}',
        )

    @admin.display(description='Net Payable')
    def net_payable_display(self, obj):
        return format_html(
            '<span class="badge badge-success font-weight-bold" style="font-size: 13px; padding: 4px 8px;">'
            '{}</span>',
            f'₹{obj.net_payable:,.2f}',
        )


@admin.register(EmployeePayment)
class EmployeePaymentAdmin(ModelAdmin):
    list_display = (
        'date',
        'recipient_badge',
        'amount_display',
        'payment_type_badge',
        'payment_mode_badge',
        'trip_or_contract',
        'notes',
    )
    list_filter = ('payment_type', 'payment_mode', 'date')
    search_fields = (
        'driver__name',
        'cleaner__name',
        'trip__trip_id',
        'contract_trip__shift__route__name',
        'notes',
    )
    autocomplete_fields = ['driver', 'cleaner', 'trip']
    date_hierarchy = 'date'

    @admin.display(description='Recipient')
    def recipient_badge(self, obj):
        if obj.driver:
            return format_html(
                '<span class="badge badge-info"><i class="fas fa-user-tie mr-1"></i>[Driver] {}</span>',
                obj.driver.name,
            )
        if obj.cleaner:
            return format_html(
                '<span class="badge badge-secondary"><i class="fas fa-broom mr-1"></i>[Cleaner] {}</span>',
                obj.cleaner.name,
            )
        return '—'

    @admin.display(description='Amount', ordering='amount')
    def amount_display(self, obj):
        return format_html(
            '<span class="inline-flex items-center px-2.5 py-0.5 rounded font-mono font-bold text-xs bg-emerald-50 dark:bg-emerald-950/50 text-emerald-800 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-800">{}</span>',
            f'₹{obj.amount:,.2f}',
        )

    @admin.display(description='Payment Type', ordering='payment_type')
    def payment_type_badge(self, obj):
        type_badges = {
            'advance': ('badge-warning', 'Trip Advance'),
            'daily_pay': ('badge-info', 'Daily Pay / Batta'),
            'settlement': ('badge-primary', 'Final Settlement'),
            'salary': ('badge-success', 'Monthly Salary'),
        }
        badge_cls, label = type_badges.get(obj.payment_type, ('badge-secondary', obj.get_payment_type_display()))
        return format_html('<span class="badge {}">{}</span>', badge_cls, label)

    @admin.display(description='Payment Mode', ordering='payment_mode')
    def payment_mode_badge(self, obj):
        mode_badges = {
            'cash': ('badge-success', 'fas fa-money-bill-wave', 'Cash'),
            'upi': ('badge-primary', 'fas fa-mobile-alt', 'UPI / GPay'),
            'bank_transfer': ('badge-info', 'fas fa-university', 'NEFT/IMPS'),
            'cheque': ('badge-secondary', 'fas fa-money-check', 'Cheque'),
            'card': ('badge-dark', 'fas fa-credit-card', 'Card'),
        }
        badge_cls, icon, label = mode_badges.get(obj.payment_mode, ('badge-secondary', 'fas fa-receipt', obj.get_payment_mode_display()))
        return format_html('<span class="badge {}"><i class="{} mr-1"></i>{}</span>', badge_cls, icon, label)

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
        return mark_safe('<span class="text-muted">—</span>')
