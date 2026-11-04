from django.urls import path
from .views import (
    contract_billing_studio_view,
    contract_invoice_detail_view,
    driver_commute_bhatta_view,
    api_billing_reconcile_preview,
    api_billing_generate_invoice,
    api_billing_driver_bhatta,
    api_billing_settle_bhatta,
)

app_name = 'fleet_contracts'

urlpatterns = [
    # Domain 6: Tariff, Billing & Contract Revenue Studio
    path('billing/', contract_billing_studio_view, name='contract-billing-studio'),
    path('billing/invoices/<int:invoice_id>/', contract_invoice_detail_view, name='contract-invoice-detail'),
    path('billing/driver-bhatta/', driver_commute_bhatta_view, name='driver-commute-bhatta'),

    # REST APIs
    path('api/billing/reconcile-preview/', api_billing_reconcile_preview, name='api-billing-reconcile-preview'),
    path('api/billing/generate-invoice/', api_billing_generate_invoice, name='api-billing-generate-invoice'),
    path('api/billing/driver-bhatta/', api_billing_driver_bhatta, name='api-billing-driver-bhatta'),
    path('api/billing/settle-bhatta/', api_billing_settle_bhatta, name='api-billing-settle-bhatta'),
]

