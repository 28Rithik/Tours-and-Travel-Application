from django.urls import path
from . import htmx_views

app_name = 'htmx_operations'

urlpatterns = [
    path('booking/package-context/', htmx_views.htmx_booking_package_context, name='booking-package-context'),
    path('booking/quote-calc/', htmx_views.htmx_booking_quote_calc, name='booking-quote-calc'),
    path('party/ledger-summary/', htmx_views.htmx_party_ledger_summary, name='party-ledger-summary'),
    path('trip/vehicle-gate/', htmx_views.htmx_vehicle_compliance_gate, name='trip-vehicle-gate'),
    path('trip/driver-status/', htmx_views.htmx_driver_status_card, name='trip-driver-status'),
    path('trip/calculate-totals/', htmx_views.htmx_trip_calculate_totals, name='trip-calculate-totals'),
    path('fine/vehicle-driver/', htmx_views.htmx_fine_vehicle_driver, name='fine-vehicle-driver'),
    path('contract/rate-lookup/', htmx_views.htmx_contract_rate_lookup, name='contract-rate-lookup'),
    path('quotation/ai-calc/', htmx_views.htmx_ai_quotation_calc, name='ai-quotation-calc'),
    path('quotation/convoy/', htmx_views.htmx_convoy_quotation, name='convoy-quotation'),
]
