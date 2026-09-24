from django.db import models
from finance.models import (
    FuelRecord as BaseFuelRecord,
    CorporatePetroAccount as BaseCorporatePetroAccount,
    PetroRecharge as BasePetroRecharge,
    CorporateFastagAccount as BaseCorporateFastagAccount,
    FastagRecharge as BaseFastagRecharge,
    FastagTollDeduction as BaseFastagTollDeduction,
)


class FuelRecord(BaseFuelRecord):
    class Meta:
        proxy = True
        app_label = 'finance_fleet'
        verbose_name = 'Fuel Record'
        verbose_name_plural = 'Fuel Records'


class CorporatePetroAccount(BaseCorporatePetroAccount):
    class Meta:
        proxy = True
        app_label = 'finance_fleet'
        verbose_name = 'Corporate Petro Account'
        verbose_name_plural = 'Corporate Petro Accounts'


class PetroRecharge(BasePetroRecharge):
    class Meta:
        proxy = True
        app_label = 'finance_fleet'
        verbose_name = 'Petro Card Recharge'
        verbose_name_plural = 'Petro Card Recharges'


class CorporateFastagAccount(BaseCorporateFastagAccount):
    class Meta:
        proxy = True
        app_label = 'finance_fleet'
        verbose_name = 'Corporate FASTag Account'
        verbose_name_plural = 'Corporate FASTag Accounts'


class FastagRecharge(BaseFastagRecharge):
    class Meta:
        proxy = True
        app_label = 'finance_fleet'
        verbose_name = 'FASTag Recharge'
        verbose_name_plural = 'FASTag Recharges'


class FastagTollDeduction(BaseFastagTollDeduction):
    class Meta:
        proxy = True
        app_label = 'finance_fleet'
        verbose_name = 'FASTag Toll Deduction'
        verbose_name_plural = 'FASTag Toll Deductions'
