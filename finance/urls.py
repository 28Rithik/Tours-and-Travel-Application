from django.urls import path
from .views import (
    accounting_export_dashboard,
    export_tally_sales_view,
    export_tally_expenses_view,
    export_zoho_sales_view,
    export_zoho_expenses_view,
    run_batch_payroll_view,
    driver_payslip_detail_view,
    api_payment_context,
)

urlpatterns = [
    path('accounting/', accounting_export_dashboard, name='accounting-export'),
    path('export/tally/sales/', export_tally_sales_view, name='export-tally-sales'),
    path('export/tally/expenses/', export_tally_expenses_view, name='export-tally-expenses'),
    path('export/zoho/sales/', export_zoho_sales_view, name='export-zoho-sales'),
    path('export/zoho/expenses/', export_zoho_expenses_view, name='export-zoho-expenses'),
    path('payroll/batch-run/', run_batch_payroll_view, name='run-batch-payroll'),
    path('payslips/<int:payslip_id>/', driver_payslip_detail_view, name='driver-payslip-detail'),
    path('api/payment-context/', api_payment_context, name='finance-api-payment-context'),
]
