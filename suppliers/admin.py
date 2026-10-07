from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline
from .models import (
    SupplierContract,
    CommissionRule,
    OutsourcedTripSettlement,
    HotelConfirmationVoucher,
    HotelVoucherGuest
)


class HotelVoucherGuestInline(TabularInline):
    model = HotelVoucherGuest
    extra = 1


@admin.register(OutsourcedTripSettlement)
class OutsourcedTripSettlementAdmin(ModelAdmin):
    list_display = (
        'settlement_number',
        'supplier',
        'vehicle',
        'settlement_date',
        'agreed_buy_rate',
        'tds_amount',
        'net_payable_amount',
        'gross_margin_earned',
        'status'
    )
    list_filter = ('status', 'tds_section', 'settlement_date')
    search_fields = ('settlement_number', 'supplier__name', 'vehicle__registration_number', 'driver_name', 'pan_number')
    date_hierarchy = 'settlement_date'
    readonly_fields = (
        'settlement_number',
        'gross_supplier_payable',
        'total_deductions',
        'tds_amount',
        'net_payable_amount',
        'gross_margin_earned',
        'created_at',
        'updated_at'
    )


@admin.register(HotelConfirmationVoucher)
class HotelConfirmationVoucherAdmin(ModelAdmin):
    list_display = (
        'voucher_number',
        'hotel_name',
        'lead_guest_name',
        'check_in_date',
        'check_out_date',
        'total_rooms',
        'meal_plan',
        'status'
    )
    list_filter = ('status', 'meal_plan', 'room_category', 'check_in_date')
    search_fields = ('voucher_number', 'hotel_name', 'lead_guest_name', 'hotel_city')
    date_hierarchy = 'check_in_date'
    inlines = [HotelVoucherGuestInline]
    readonly_fields = ('voucher_number', 'total_nights', 'balance_payable_to_hotel', 'created_at', 'updated_at')


@admin.register(SupplierContract)
class SupplierContractAdmin(ModelAdmin):
    list_display = ('title', 'supplier', 'valid_from', 'valid_to', 'is_active')
    list_filter = ('is_active', 'supplier')
    search_fields = ('title', 'supplier__name')


@admin.register(CommissionRule)
class CommissionRuleAdmin(ModelAdmin):
    list_display = ('agent_name', 'commission_percentage', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('agent_name',)
