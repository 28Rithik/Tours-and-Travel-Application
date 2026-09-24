from django.db import models
from finance.models import (
    DriverSalaryProfile as BaseDriverSalaryProfile,
    DriverPayslip as BaseDriverPayslip,
    EmployeePayment as BaseEmployeePayment,
)


class DriverSalaryProfile(BaseDriverSalaryProfile):
    class Meta:
        proxy = True
        app_label = 'finance_payroll'
        verbose_name = 'Driver Salary Profile'
        verbose_name_plural = 'Driver Salary Profiles'


class DriverPayslip(BaseDriverPayslip):
    class Meta:
        proxy = True
        app_label = 'finance_payroll'
        verbose_name = 'Driver Payslip'
        verbose_name_plural = 'Driver Payslips'


class EmployeePayment(BaseEmployeePayment):
    class Meta:
        proxy = True
        app_label = 'finance_payroll'
        verbose_name = 'Staff Payment Voucher'
        verbose_name_plural = 'Staff Payment Vouchers'
