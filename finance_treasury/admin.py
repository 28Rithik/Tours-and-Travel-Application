from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from .models import Payment, VehicleLoan, LedgerAdjustment, TripProfitReport


# ── Bulk Actions ──────────────────────────────────────────────────────────────

@admin.action(description="✅ Mark selected payments as Paid via Cash")
def mark_payments_paid(modeladmin, request, queryset):
    updated = queryset.update(payment_mode='cash')
    modeladmin.message_user(request, f"{updated} payment(s) marked as paid via Cash.")


# ── Custom Filters ─────────────────────────────────────────────────────────────

class ProfitabilityFilter(admin.SimpleListFilter):
    title = _('Trip Profitability')
    parameter_name = 'profitability'

    def lookups(self, request, model_admin):
        return [
            ('profitable', _('🟢 Profitable (> ₹0)')),
            ('loss', _('🔴 Loss Making (≤ ₹0)')),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'profitable':
            pks = [t.pk for t in queryset if t.net_profit > 0]
            return queryset.filter(pk__in=pks)
        if self.value() == 'loss':
            pks = [t.pk for t in queryset if t.net_profit <= 0]
            return queryset.filter(pk__in=pks)
        return queryset


# ── Admins ────────────────────────────────────────────────────────────────────

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        'date',
        'party_badge',
        'amount_display',
        'payment_type_badge',
        'payment_mode_badge',
        'collected_by_badge',
        'reference_number',
        'bank',
        'linked_doc',
    )
    list_filter = ('payment_type', 'payment_mode', 'collected_by', 'date')
    search_fields = (
        'party__name',
        'trip__trip_id',
        'booking__booking_number',
        'contract_trip__shift__route__name',
        'reference_number',
        'bank',
    )
    autocomplete_fields = ['party', 'booking', 'trip', 'contract_trip', 'statement']
    date_hierarchy = 'date'
    actions = [mark_payments_paid]

    class Media:
        js = ('admin/js/payment_admin.js',)

    @admin.display(description='Party', ordering='party')
    def party_badge(self, obj):
        if obj.party:
            icon = "fas fa-user" if obj.party.party_type == 'customer' else "fas fa-truck-loading"
            badge_cls = "badge-info" if obj.party.party_type == 'customer' else "badge-secondary"
            return format_html(
                '<a href="/admin/core/party/{}/change/" class="font-weight-bold">'
                '<span class="badge {}"><i class="{} mr-1"></i>{}</span></a>',
                obj.party.pk,
                badge_cls,
                icon,
                obj.party.name,
            )
        return '—'

    @admin.display(description='Amount', ordering='amount')
    def amount_display(self, obj):
        return format_html(
            '<strong class="text-white" style="font-size: 13px;">{}</strong>',
            f'₹{obj.amount:,.2f}',
        )

    @admin.display(description='Type', ordering='payment_type')
    def payment_type_badge(self, obj):
        type_badges = {
            'customer_receipt': ('badge-success', 'Customer Receipt'),
            'supplier_payment': ('badge-primary', 'Supplier Payment'),
            'advance': ('badge-warning', 'Trip Advance'),
            'adjustment': ('badge-secondary', 'Adjustment'),
            'tds_receivable': ('badge-info', 'TDS Receivable'),
        }
        badge_cls, label = type_badges.get(obj.payment_type, ('badge-secondary', obj.get_payment_type_display()))
        return format_html('<span class="badge {}">{}</span>', badge_cls, label)

    @admin.display(description='Mode', ordering='payment_mode')
    def payment_mode_badge(self, obj):
        mode_badges = {
            'cash': ('badge-success', 'fas fa-money-bill-wave', 'Cash'),
            'upi': ('badge-primary', 'fas fa-mobile-alt', 'UPI'),
            'bank_transfer': ('badge-info', 'fas fa-university', 'NEFT/RTGS'),
            'cheque': ('badge-secondary', 'fas fa-money-check', 'Cheque'),
            'card': ('badge-dark', 'fas fa-credit-card', 'Card'),
        }
        badge_cls, icon, label = mode_badges.get(obj.payment_mode, ('badge-secondary', 'fas fa-receipt', obj.get_payment_mode_display()))
        return format_html('<span class="badge {}"><i class="{} mr-1"></i>{}</span>', badge_cls, icon, label)

    @admin.display(description='Collected By', ordering='collected_by')
    def collected_by_badge(self, obj):
        if obj.collected_by == 'driver':
            return mark_safe('<span class="badge badge-warning"><i class="fas fa-user-tie mr-1"></i>Driver</span>')
        return mark_safe('<span class="badge badge-info"><i class="fas fa-building mr-1"></i>Cashier</span>')

    @admin.display(description='Linked Reference')
    def linked_doc(self, obj):
        if obj.statement:
            return format_html('<a href="/admin/statements/generatedstatement/{}/change/">Stmt #{}</a>', obj.statement.pk, obj.statement.pk)
        if obj.booking:
            return format_html('<a href="/admin/operations/booking/{}/change/">Booking #{}</a>', obj.booking.pk, obj.booking.booking_number)
        if obj.trip:
            return format_html('<a href="/admin/operations/trip/{}/change/">Trip #{}</a>', obj.trip.pk, obj.trip.trip_id)
        if obj.contract_trip:
            return format_html('<a href="/admin/fleet_contracts/contracttriplog/{}/change/">Shift #{}</a>', obj.contract_trip.pk, obj.contract_trip.pk)
        return mark_safe('<span class="text-muted">—</span>')


@admin.register(VehicleLoan)
class VehicleLoanAdmin(admin.ModelAdmin):
    list_display = (
        'vehicle_badge',
        'financier_badge',
        'loan_account_number',
        'total_loan_display',
        'emi_display',
        'emi_due_badge',
        'interest_rate_display',
        'tenure_display',
        'is_active_badge',
    )
    list_filter = ('is_active', 'financier_name')
    search_fields = ('vehicle__registration_number', 'loan_account_number', 'financier_name')
    autocomplete_fields = ['vehicle']

    @admin.display(description='Vehicle', ordering='vehicle')
    def vehicle_badge(self, obj):
        if obj.vehicle:
            return format_html(
                '<a href="/admin/core/vehicle/{}/change/" class="font-weight-bold">🚌 {}</a>',
                obj.vehicle.pk,
                obj.vehicle.registration_number,
            )
        return '—'

    @admin.display(description='Financier / Bank', ordering='financier_name')
    def financier_badge(self, obj):
        return format_html(
            '<span class="badge badge-info"><i class="fas fa-university mr-1"></i>{}</span>',
            obj.financier_name,
        )

    @admin.display(description='Loan Sanctioned', ordering='total_loan_amount')
    def total_loan_display(self, obj):
        return format_html(
            '<strong class="text-white">{}</strong>',
            f'₹{obj.total_loan_amount:,.2f}',
        )

    @admin.display(description='Monthly EMI', ordering='emi_amount')
    def emi_display(self, obj):
        return format_html(
            '<strong class="text-warning">{}</strong>',
            f'₹{obj.emi_amount:,.2f}',
        )

    @admin.display(description='EMI Due Day')
    def emi_due_badge(self, obj):
        return format_html(
            '<span class="badge badge-dark"><i class="fas fa-calendar-day mr-1"></i>Day {} of month</span>',
            obj.emi_date_of_month,
        )

    @admin.display(description='ROI', ordering='interest_rate')
    def interest_rate_display(self, obj):
        return f'{obj.interest_rate}% p.a.'

    @admin.display(description='Tenure')
    def tenure_display(self, obj):
        return f'{obj.start_date.strftime("%b %Y")} – {obj.end_date.strftime("%b %Y")}'

    @admin.display(description='Status')
    def is_active_badge(self, obj):
        if obj.is_active:
            return mark_safe('<span class="badge badge-success">✓ Active EMI</span>')
        return mark_safe('<span class="badge badge-secondary">Closed</span>')


@admin.register(LedgerAdjustment)
class LedgerAdjustmentAdmin(admin.ModelAdmin):
    list_display = (
        'date',
        'party_badge',
        'amount_display',
        'description',
    )
    list_filter = ('date', 'party')
    search_fields = ('party__name', 'description')
    autocomplete_fields = ['party']
    date_hierarchy = 'date'

    @admin.display(description='Party', ordering='party')
    def party_badge(self, obj):
        if obj.party:
            return format_html(
                '<a href="/admin/core/party/{}/change/" class="font-weight-bold">👤 {}</a>',
                obj.party.pk,
                obj.party.name,
            )
        return '—'

    @admin.display(description='Amount', ordering='amount')
    def amount_display(self, obj):
        color = "text-success" if obj.amount >= 0 else "text-danger"
        sign = "+" if obj.amount > 0 else ""
        return format_html(
            '<strong class="{}">{}{}</strong>',
            color,
            sign,
            f'₹{obj.amount:,.2f}',
        )


@admin.register(TripProfitReport)
class TripProfitReportAdmin(admin.ModelAdmin):
    list_display = (
        'trip_id',
        'party',
        'vehicle',
        'start_date',
        'status_badge',
        'revenue_display',
        'total_supplier_cost_display',
        'total_fuel_cost_display',
        'company_paid_expenses_display',
        'driver_bata_display',
        'display_net_profit',
    )
    list_filter = ('status', 'start_date', ProfitabilityFilter)
    search_fields = ('trip_id', 'party__name')
    date_hierarchy = 'start_date'

    @admin.display(description='Status')
    def status_badge(self, obj):
        status_colors = {
            'settled': 'badge-success',
            'completed': 'badge-primary',
            'started': 'badge-warning',
            'assigned': 'badge-info',
            'cancelled': 'badge-danger',
        }
        cls = status_colors.get(obj.status, 'badge-secondary')
        return format_html('<span class="badge {}">{}</span>', cls, obj.get_status_display())

    @admin.display(description='Revenue (Billing)')
    def revenue_display(self, obj):
        return format_html('<strong>{}</strong>', f'₹{obj.total_amount:,.2f}')

    @admin.display(description='Supplier Cost')
    def total_supplier_cost_display(self, obj):
        return f'₹{obj.total_supplier_cost:,.2f}' if obj.total_supplier_cost else '₹0'

    @admin.display(description='Fuel Cost')
    def total_fuel_cost_display(self, obj):
        return f'₹{obj.total_fuel_cost:,.2f}' if obj.total_fuel_cost else '₹0'

    @admin.display(description='On-Road Expenses')
    def company_paid_expenses_display(self, obj):
        return f'₹{obj.company_paid_expenses:,.2f}' if obj.company_paid_expenses else '₹0'

    @admin.display(description='Driver Batta')
    def driver_bata_display(self, obj):
        return f'₹{obj.driver_bata:,.2f}' if obj.driver_bata else '₹0'

    @admin.display(description='Net Margin / P&L')
    def display_net_profit(self, obj):
        profit = obj.net_profit
        if profit >= 0:
            return format_html(
                '<span class="badge badge-success" style="font-size: 13px; font-weight: bold;">+{}</span>',
                f'₹{profit:,.2f}',
            )
        return format_html(
            '<span class="badge badge-danger" style="font-size: 13px; font-weight: bold;">-{}</span>',
            f'₹{abs(profit):,.2f}',
        )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
