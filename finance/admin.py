from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline
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
    Account,
    JournalEntry,
    JournalItem,
    CorporateGSTInvoice,
    InvoiceLineItem,
    EWayBill,
    PettyCashAccount,
    PettyCashTransaction,
    BankStatementUpload,
    BankStatementEntry,
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

class DriverAdvanceAllocationInline(TabularInline):
    model = DriverAdvanceAllocation
    extra = 1
    autocomplete_fields = ['trip']


# ── Admins ────────────────────────────────────────────────────────────────────

@admin.register(TripExpense)
class TripExpenseAdmin(ModelAdmin):
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
    list_select_related = ('trip',)
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
            '<strong class="text-slate-900 dark:text-white" style="font-size: 13px; font-weight: 700;">{}</strong>',
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
class DriverAdvanceAdmin(ModelAdmin):
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
    list_select_related = ('driver', 'trip', 'contract_trip')
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
            '<strong class="text-slate-900 dark:text-white" style="font-size: 13px; font-weight: 700;">{}</strong>',
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
class DriverSettlementAdmin(ModelAdmin):
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
    list_select_related = ('driver', 'trip', 'contract_trip')
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
class SupplierTripCostAdmin(ModelAdmin):
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
            '<strong class="text-slate-900 dark:text-white" style="font-size: 13px; font-weight: 700;">{}</strong>',
            f'₹{obj.amount:,.2f}',
        )


@admin.register(DriverSalaryProfile)
class DriverSalaryProfileAdmin(ModelAdmin):
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
class DriverPayslipAdmin(ModelAdmin):
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


class JournalItemInline(TabularInline):
    model = JournalItem
    extra = 2
    fields = ('account', 'party', 'debit', 'credit', 'memo')


@admin.register(Account)
class AccountAdmin(ModelAdmin):
    list_display = ('code', 'name', 'account_type_badge', 'currency', 'balance_display', 'is_active')
    list_filter = ('account_type', 'is_active')
    search_fields = ('code', 'name', 'description')

    @admin.display(description='Account Type')
    def account_type_badge(self, obj):
        colors = {
            'asset': 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20',
            'liability': 'bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20',
            'equity': 'bg-purple-500/10 text-purple-600 dark:text-purple-400 border border-purple-500/20',
            'income': 'bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20',
            'expense': 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20',
        }
        badge_style = colors.get(obj.account_type, 'bg-gray-100 text-gray-800')
        return format_html(
            '<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold {}">{}</span>',
            badge_style,
            obj.get_account_type_display()
        )

    @admin.display(description='Current Balance')
    def balance_display(self, obj):
        bal = obj.current_balance
        color = "text-emerald-600 dark:text-emerald-400" if bal >= 0 else "text-rose-600 dark:text-rose-400"
        return format_html('<span class="font-mono font-bold {}">{}</span>', color, f'₹{bal:,.2f}')


@admin.register(JournalEntry)
class JournalEntryAdmin(ModelAdmin):
    list_display = ('entry_number', 'date', 'entry_type_badge', 'reference_id', 'total_debit_display', 'total_credit_display', 'balanced_badge', 'is_posted_badge')
    list_filter = ('entry_type', 'is_posted', 'date')
    search_fields = ('entry_number', 'reference_id', 'narration')
    inlines = [JournalItemInline]

    @admin.display(description='Entry Type')
    def entry_type_badge(self, obj):
        return format_html(
            '<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-sky-500/10 text-sky-600 dark:text-sky-400 border border-sky-500/20">{}</span>',
            obj.get_entry_type_display()
        )

    @admin.display(description='Total Debit (DR)')
    def total_debit_display(self, obj):
        return format_html('<span class="font-mono font-bold text-slate-800 dark:text-slate-100">{}</span>', f'₹{obj.total_debit:,.2f}')

    @admin.display(description='Total Credit (CR)')
    def total_credit_display(self, obj):
        return format_html('<span class="font-mono font-bold text-slate-800 dark:text-slate-100">{}</span>', f'₹{obj.total_credit:,.2f}')

    @admin.display(description='Balanced')
    def balanced_badge(self, obj):
        if obj.is_balanced:
            return mark_safe('<span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-bold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">✓ BALANCED</span>')
        return mark_safe('<span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-bold bg-rose-500/10 text-rose-600 dark:text-rose-400 animate-pulse">⚠ UNBALANCED</span>')

    @admin.display(description='Status')
    def is_posted_badge(self, obj):
        if obj.is_posted:
            return mark_safe('<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-indigo-500/10 text-indigo-600 dark:text-indigo-400">POSTED</span>')
        return mark_safe('<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-amber-500/10 text-amber-600 dark:text-amber-400">DRAFT</span>')


class InvoiceLineItemInline(TabularInline):
    model = InvoiceLineItem
    extra = 1
    fields = ('item_description', 'sac_code', 'quantity', 'unit', 'rate', 'taxable_amount', 'cgst_amount', 'sgst_amount', 'igst_amount', 'total_amount')


@admin.register(CorporateGSTInvoice)
class CorporateGSTInvoiceAdmin(ModelAdmin):
    list_display = (
        'invoice_number',
        'recipient_legal_name',
        'invoice_date',
        'supply_type_badge',
        'taxable_value_display',
        'tax_summary_display',
        'total_invoice_value_display',
        'payment_status_badge',
        'eway_bill_badge',
        'quick_actions',
    )
    list_filter = ('invoice_type', 'supply_type', 'payment_status', 'is_reverse_charge', 'recipient_state_code')
    search_fields = ('invoice_number', 'recipient_legal_name', 'recipient_gstin', 'supplier_gstin')
    readonly_fields = ('invoice_number', 'cgst_rate', 'cgst_amount', 'sgst_rate', 'sgst_amount', 'igst_rate', 'igst_amount', 'total_tax', 'round_off', 'total_invoice_value', 'created_at', 'updated_at', 'qr_code_preview')
    inlines = [InvoiceLineItemInline]

    fieldsets = (
        ('Invoice Header & Legal Entities', {
            'fields': (
                ('invoice_number', 'invoice_date', 'due_date'),
                ('invoice_type', 'supply_type', 'is_reverse_charge'),
                ('party', 'trip', 'transport_contract'),
                ('supplier_legal_name', 'supplier_gstin', 'supplier_state_code'),
                ('recipient_legal_name', 'recipient_gstin', 'recipient_state_code'),
                ('recipient_address', 'place_of_supply'),
            )
        }),
        ('Taxation & Financial Breakdown', {
            'fields': (
                ('sac_code', 'gst_rate_percent', 'taxable_value'),
                ('cgst_rate', 'cgst_amount'),
                ('sgst_rate', 'sgst_amount'),
                ('igst_rate', 'igst_amount'),
                ('cess_amount', 'total_tax', 'round_off', 'total_invoice_value'),
            )
        }),
        ('Payment & General Ledger Posting', {
            'fields': (
                ('payment_status', 'paid_amount'),
                'gl_journal_entry',
                'qr_code_preview',
            )
        }),
    )

    @admin.display(description='Supply')
    def supply_type_badge(self, obj):
        if obj.supply_type == 'intra_state':
            return mark_safe('<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">INTRA (CGST+SGST)</span>')
        return mark_safe('<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border border-indigo-500/20">INTER (IGST)</span>')

    @admin.display(description='Taxable Val')
    def taxable_value_display(self, obj):
        return format_html('<span class="font-mono font-bold text-slate-800 dark:text-slate-100">{}</span>', f'₹{obj.taxable_value:,.2f}')

    @admin.display(description='Tax (CGST/SGST/IGST)')
    def tax_summary_display(self, obj):
        if obj.supply_type == 'intra_state':
            return format_html('<span class="text-xs font-mono text-slate-600 dark:text-slate-400">{}</span>', f'C: ₹{obj.cgst_amount:,.0f} | S: ₹{obj.sgst_amount:,.0f}')
        return format_html('<span class="text-xs font-mono text-indigo-600 dark:text-indigo-400 font-bold">{}</span>', f'IGST: ₹{obj.igst_amount:,.0f}')

    @admin.display(description='Total Invoice')
    def total_invoice_value_display(self, obj):
        return format_html('<span class="font-mono font-bold text-emerald-600 dark:text-emerald-400">{}</span>', f'₹{obj.total_invoice_value:,.2f}')

    @admin.display(description='Payment')
    def payment_status_badge(self, obj):
        colors = {
            'paid': 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20',
            'partially_paid': 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20',
            'unpaid': 'bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/20',
        }
        cls = colors.get(obj.payment_status, 'bg-slate-500/10 text-slate-600')
        return format_html('<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold border {}">{}</span>', cls, obj.get_payment_status_display().upper())

    @admin.display(description='E-Way Bill')
    def eway_bill_badge(self, obj):
        if hasattr(obj, 'eway_bill'):
            ewb = obj.eway_bill
            return format_html('<a href="/admin/finance/ewaybill/{}/change/" class="font-mono text-xs font-bold text-sky-600 dark:text-sky-400 hover:underline">EWB #{}</a>', ewb.pk, ewb.eway_bill_number[:8] + '...')
        return format_html('<a href="/admin/finance/gst-studio/?tab=workbench&inv={}" class="text-xs text-amber-600 dark:text-amber-400 hover:underline">+ Generate</a>', obj.pk)

    @admin.display(description='Actions')
    def quick_actions(self, obj):
        return format_html(
            '<div class="flex items-center gap-1.5">'
            '<a href="/finance/invoice/{}/view/" target="_blank" class="px-2 py-0.5 rounded text-xs font-medium bg-slate-100 hover:bg-slate-200 text-slate-700 dark:bg-slate-800 dark:text-slate-300">HTML</a>'
            '<a href="/finance/invoice/{}/pdf/" target="_blank" class="px-2 py-0.5 rounded text-xs font-medium bg-indigo-50 hover:bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300">📄 PDF</a>'
            '<a href="/api/finance/invoice/{}/eway-json/" download="EWB_{}.json" class="px-2 py-0.5 rounded text-xs font-medium bg-emerald-500/10 text-emerald-600 hover:bg-emerald-500/20">📥 NIC JSON</a>'
            '<button type="button" onclick="sendInvoiceWhatsApp({}, this)" class="px-2 py-0.5 rounded text-xs font-semibold bg-emerald-600 hover:bg-emerald-700 text-white flex items-center gap-1" title="Dispatch GST Invoice PDF & Payment Link via WhatsApp">💬 Send WA</button>'
            '</div>'
            '<script>'
            'if(!window._waInvHook){{window._waInvHook=true;'
            'window.sendInvoiceWhatsApp=function(id,btn){{'
            'if(!confirm("Send official GST Tax Invoice PDF & UPI link to customer via WhatsApp?")) return;'
            'const orig=btn.innerHTML; btn.innerHTML="⏳..."; btn.disabled=true;'
            'fetch(`/finance/api/invoice/${{id}}/whatsapp/`,{{method:"POST",headers:{{"X-CSRFToken":(document.cookie.match(/csrftoken=([^;]+)/)||[])[1]||"","Content-Type":"application/json"}}}})'
            '.then(r=>r.json())'
            '.then(d=>{{if(d.success){{alert("✅ "+d.message);btn.innerHTML="✅ Sent";btn.style.background="#059669";}}else{{alert("❌ "+(d.error||"Dispatch failed"));btn.innerHTML=orig;btn.disabled=false;}}}})'
            '.catch(e=>{{alert("Error: "+e);btn.innerHTML=orig;btn.disabled=false;}});'
            '}};'
            '}}'
            '</script>',
            obj.pk, obj.pk, obj.pk, obj.invoice_number.replace('/', '_'), obj.pk
        )

    @admin.display(description='Digital QR Code Stamp')
    def qr_code_preview(self, obj):
        if obj.qr_code_svg:
            return format_html('<div style="width: 140px; height: 140px; padding: 6px; background: white; border-radius: 8px;">{}</div>', mark_safe(obj.qr_code_svg))
        return mark_safe('<span class="text-slate-400 text-xs">QR Stamp will be generated on invoice finalization</span>')


@admin.register(EWayBill)
class EWayBillAdmin(ModelAdmin):
    list_display = (
        'eway_bill_number',
        'invoice_link',
        'vehicle_number',
        'trans_distance_km',
        'eway_bill_date',
        'valid_until',
        'status_badge',
        'actions_col',
    )
    list_filter = ('status', 'vehicle_type', 'eway_bill_date')
    search_fields = ('eway_bill_number', 'vehicle_number', 'invoice__invoice_number', 'invoice__recipient_legal_name')
    readonly_fields = ('eway_bill_number', 'eway_bill_date', 'valid_until', 'created_at', 'updated_at')

    @admin.display(description='Tax Invoice')
    def invoice_link(self, obj):
        return format_html('<a href="/admin/finance/corporategstinvoice/{}/change/" class="font-bold text-sky-600 dark:text-sky-400 hover:underline">{}</a>', obj.invoice.pk, obj.invoice.invoice_number)

    @admin.display(description='Status')
    def status_badge(self, obj):
        colors = {
            'active': 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20',
            'draft': 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20',
            'expired': 'bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/20',
            'cancelled': 'bg-slate-500/10 text-slate-600 dark:text-slate-400 border-slate-500/20',
        }
        cls = colors.get(obj.status, 'bg-slate-500/10 text-slate-600')
        return format_html('<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold border {}">{}</span>', cls, obj.get_status_display().upper())

    @admin.display(description='NIC Actions')
    def actions_col(self, obj):
        return format_html(
            '<div class="flex items-center gap-2">'
            '<a href="/api/finance/invoice/{}/eway-json/" download="EWB_{}.json" class="px-2 py-0.5 rounded text-xs font-semibold bg-emerald-600 text-white hover:bg-emerald-700">📥 Export NIC JSON</a>'
            '</div>',
            obj.invoice.pk, obj.eway_bill_number
        )


# ==============================================================================
# Phase 5: Petty Cash Float Register & Cash Wallet Studio Admin Registration
# ==============================================================================

class PettyCashTransactionInline(TabularInline):
    model = PettyCashTransaction
    extra = 0
    fields = ('voucher_number', 'date', 'transaction_type', 'category', 'amount', 'recipient_or_vendor', 'status')
    readonly_fields = ('voucher_number', 'date')
    ordering = ['-date', '-created_at']


@admin.register(PettyCashAccount)
class PettyCashAccountAdmin(ModelAdmin):
    list_display = (
        'account_name',
        'account_type_badge',
        'holder_display',
        'current_balance_badge',
        'allocated_limit',
        'warning_threshold',
        'studio_link',
    )
    list_filter = ('account_type', 'is_active')
    search_fields = ('account_name', 'holder_driver__name', 'holder_user__username')
    inlines = [PettyCashTransactionInline]

    @admin.display(description='Type')
    def account_type_badge(self, obj):
        colors = {
            'branch': 'bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20',
            'driver': 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20',
            'tour_manager': 'bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/20',
            'dispatcher': 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20',
        }
        cls = colors.get(obj.account_type, 'bg-slate-500/10 text-slate-600')
        return format_html('<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold border {}">{}</span>', cls, obj.get_account_type_display())

    @admin.display(description='Custodian / Holder')
    def holder_display(self, obj):
        if obj.holder_driver:
            return format_html('<span>🧑‍✈️ {}</span>', obj.holder_driver.name)
        elif obj.holder_user:
            return format_html('<span>👤 {}</span>', obj.holder_user.username)
        return mark_safe('<span class="text-slate-400">Office Float</span>')

    @admin.display(description='Cash Balance')
    def current_balance_badge(self, obj):
        bal_str = f"{obj.current_balance:,.2f}"
        if obj.is_low_balance:
            return format_html('<span style="color: #ef4444; font-weight: 800; background: rgba(239,68,68,0.1); padding: 3px 8px; border-radius: 6px;">⚠️ ₹{} (Low)</span>', bal_str)
        return format_html('<span style="color: #10b981; font-weight: 800; background: rgba(16,185,129,0.1); padding: 3px 8px; border-radius: 6px;">₹{}</span>', bal_str)

    @admin.display(description='Studio')
    def studio_link(self, obj):
        return format_html('<a href="/admin/finance/petty-cash-studio/?account_id={}" style="background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%); color: white; padding: 4px 10px; border-radius: 6px; font-weight: 700; text-decoration: none; font-size: 11px;">💵 Open Studio</a>', obj.pk)


@admin.register(PettyCashTransaction)
class PettyCashTransactionAdmin(ModelAdmin):
    list_display = (
        'voucher_number',
        'date',
        'account_link',
        'type_badge',
        'category_badge',
        'amount_display',
        'recipient_or_vendor',
        'status_badge',
        'trip_link',
    )
    list_filter = ('transaction_type', 'category', 'status', 'date')
    search_fields = ('voucher_number', 'recipient_or_vendor', 'notes', 'account__account_name')
    readonly_fields = ('voucher_number', 'balance_after', 'created_at', 'updated_at')

    @admin.display(description='Account')
    def account_link(self, obj):
        return format_html('<a href="/admin/finance/pettycashaccount/{}/change/" style="font-weight: 700; color: #818cf8;">{}</a>', obj.account.pk, obj.account.account_name)

    @admin.display(description='Type')
    def type_badge(self, obj):
        if obj.transaction_type in ['top_up', 'settlement_refund', 'adjustment']:
            return mark_safe('<span style="background: rgba(16,185,129,0.15); color: #34d399; padding: 2px 8px; border-radius: 4px; font-weight: 700; font-size: 11px;">INFLOW (+)</span>')
        return mark_safe('<span style="background: rgba(239,68,68,0.15); color: #f87171; padding: 2px 8px; border-radius: 4px; font-weight: 700; font-size: 11px;">OUTFLOW (-)</span>')

    @admin.display(description='Category')
    def category_badge(self, obj):
        return format_html('<span style="font-size: 12px; font-weight: 600;">{}</span>', obj.get_category_display())

    @admin.display(description='Amount')
    def amount_display(self, obj):
        sign = "+" if obj.transaction_type in ['top_up', 'settlement_refund', 'adjustment'] else "-"
        color = "#10b981" if sign == "+" else "#ef4444"
        amt_str = f"{obj.amount:,.2f}"
        return format_html('<span style="color: {}; font-weight: 800; font-size: 13px;">{}₹{}</span>', color, sign, amt_str)

    @admin.display(description='Status')
    def status_badge(self, obj):
        colors = {
            'approved': ('#047857', '#d1fae5', '✅ Approved'),
            'submitted': ('#b45309', '#fef3c7', '⏳ Review Pending'),
            'rejected': ('#b91c1c', '#fee2e2', '❌ Rejected'),
            'draft': ('#4b5563', '#f3f4f6', 'Draft'),
        }
        fg, bg, label = colors.get(obj.status, ('#4b5563', '#f3f4f6', obj.status))
        return format_html('<span style="background: {}; color: {}; padding: 2px 8px; border-radius: 4px; font-weight: 700; font-size: 11px;">{}</span>', bg, fg, label)

    @admin.display(description='Trip')
    def trip_link(self, obj):
        if obj.trip:
            return format_html('<a href="/admin/operations/trip/{}/change/" style="color: #38bdf8; font-weight: 600;">#{}</a>', obj.trip.pk, obj.trip.trip_id)
        return mark_safe('<span style="color: #94a3b8;">-</span>')


# ==============================================================================
# Phase 5: Automated Bank Statement CSV Reconciler Admin Registration
# ==============================================================================

class BankStatementEntryInline(TabularInline):
    model = BankStatementEntry
    extra = 0
    fields = ('transaction_date', 'reference_or_utr', 'deposit_amount', 'matched_booking', 'match_confidence', 'status')
    readonly_fields = ('transaction_date', 'reference_or_utr', 'deposit_amount')
    ordering = ['-deposit_amount']


@admin.register(BankStatementUpload)
class BankStatementUploadAdmin(ModelAdmin):
    list_display = (
        'id',
        'bank_badge',
        'filename',
        'uploaded_at_display',
        'progress_badge',
        'deposits_display',
        'reconciled_display',
        'studio_link',
    )
    list_filter = ('bank_name', 'status')
    search_fields = ('filename', 'account_number')
    inlines = [BankStatementEntryInline]

    @admin.display(description='Bank')
    def bank_badge(self, obj):
        return format_html('<span style="font-weight: 700; background: rgba(99,102,241,0.15); color: #818cf8; padding: 2px 8px; border-radius: 4px;">🏦 {}</span>', obj.get_bank_name_display())

    @admin.display(description='Uploaded Date')
    def uploaded_at_display(self, obj):
        return obj.uploaded_at.strftime('%d-%b-%Y %H:%M')

    @admin.display(description='Reconciliation Progress')
    def progress_badge(self, obj):
        total = obj.total_transactions or 0
        rec = obj.reconciled_count or 0
        pct = int((rec / total) * 100) if total > 0 else 0
        color = "#10b981" if pct == 100 else ("#38bdf8" if pct > 0 else "#94a3b8")
        return format_html('<span style="color: {}; font-weight: 800;">{}/{} ({}%)</span>', color, rec, total, pct)

    @admin.display(description='Total Inflows')
    def deposits_display(self, obj):
        return format_html('<span style="font-weight: 700; color: #10b981;">₹{}</span>', f"{(obj.total_deposits or 0):,.2f}")

    @admin.display(description='Reconciled')
    def reconciled_display(self, obj):
        return format_html('<span style="font-weight: 700; color: #38bdf8;">₹{}</span>', f"{(obj.reconciled_amount or 0):,.2f}")

    @admin.display(description='Reconciliation Studio')
    def studio_link(self, obj):
        url = f"/finance/bank-reconciliation/?upload_id={obj.pk}"
        return format_html('<a href="{}" target="_blank" style="background: linear-gradient(135deg, #6366f1, #4f46e5); color: white; padding: 4px 10px; border-radius: 6px; font-weight: 700; font-size: 11px; text-decoration: none;">⚡ Open Studio</a>', url)


@admin.register(BankStatementEntry)
class BankStatementEntryAdmin(ModelAdmin):
    list_display = (
        'transaction_date',
        'bank_display',
        'reference_or_utr',
        'deposit_display',
        'matched_booking_link',
        'confidence_badge',
        'status_badge',
        'reconcile_action',
    )
    list_filter = ('status', 'upload__bank_name')
    search_fields = ('reference_or_utr', 'narration', 'matched_booking__booking_number')

    @admin.display(description='Bank')
    def bank_display(self, obj):
        return obj.upload.get_bank_name_display() if obj.upload else '-'

    @admin.display(description='Credit (+₹)')
    def deposit_display(self, obj):
        if obj.deposit_amount > 0:
            return format_html('<span style="color: #10b981; font-weight: 800;">+₹{}</span>', f"{obj.deposit_amount:,.2f}")
        return format_html('<span style="color: #ef4444; font-weight: 700;">-₹{}</span>', f"{obj.withdrawal_amount:,.2f}")

    @admin.display(description='Matched Booking')
    def matched_booking_link(self, obj):
        if obj.matched_booking:
            return format_html('<a href="/admin/operations/booking/{}/change/" style="font-weight: 700; color: #38bdf8;">{} ({})</a>', obj.matched_booking.pk, obj.matched_booking.booking_number, obj.matched_booking.guest_name)
        return mark_safe('<span style="color: #94a3b8;">Unassigned</span>')

    @admin.display(description='Confidence')
    def confidence_badge(self, obj):
        conf = obj.match_confidence
        if conf >= 90:
            color = "#10b981"
        elif conf >= 70:
            color = "#38bdf8"
        elif conf > 0:
            color = "#f59e0b"
        else:
            color = "#64748b"
        return format_html('<span style="color: {}; font-weight: 800; font-size: 12px;">{}%</span>', color, conf)

    @admin.display(description='Status')
    def status_badge(self, obj):
        colors = {
            'reconciled': ('#047857', '#d1fae5', '✅ Reconciled'),
            'matched': ('#0284c7', '#e0f2fe', '🎯 Matched'),
            'unmatched': ('#64748b', '#f1f5f9', '⏳ Unmatched'),
            'ignored': ('#9ca3af', '#f3f4f6', 'Ignored'),
        }
        fg, bg, label = colors.get(obj.status, ('#64748b', '#f1f5f9', obj.status))
        return format_html('<span style="background: {}; color: {}; padding: 2px 8px; border-radius: 4px; font-weight: 700; font-size: 11px;">{}</span>', bg, fg, label)

    @admin.display(description='Action')
    def reconcile_action(self, obj):
        if obj.status == 'reconciled':
            return mark_safe('<span style="color: #10b981; font-weight: 700; font-size: 11px;">✓ Posted</span>')
        return format_html('<a href="/finance/bank-reconciliation/?upload_id={}" target="_blank" style="color: #6366f1; font-weight: 700; font-size: 11px;">Match & Reconcile &rarr;</a>', obj.upload_id)





