from django.db import models
from finance.models import (
    Payment as BasePayment,
    VehicleLoan as BaseVehicleLoan,
    LedgerAdjustment as BaseLedgerAdjustment,
    TripProfitReport as BaseTripProfitReport,
)


class Payment(BasePayment):
    class Meta:
        proxy = True
        app_label = 'finance_treasury'
        verbose_name = 'Payment & Voucher'
        verbose_name_plural = 'Payments & Vouchers'


class VehicleLoan(BaseVehicleLoan):
    class Meta:
        proxy = True
        app_label = 'finance_treasury'
        verbose_name = 'Vehicle Bank Loan'
        verbose_name_plural = 'Vehicle Bank Loans'


class LedgerAdjustment(BaseLedgerAdjustment):
    class Meta:
        proxy = True
        app_label = 'finance_treasury'
        verbose_name = 'Party Ledger Adjustment'
        verbose_name_plural = 'Party Ledger Adjustments'


class TripProfitReport(BaseTripProfitReport):
    class Meta:
        proxy = True
        app_label = 'finance_treasury'
        verbose_name = 'Trip P&L Report'
        verbose_name_plural = 'Trip P&L Reports'
