from django.urls import path
from .views import compliance_and_maintenance_dashboard, api_compliance_summary, api_send_renewal_warnings

app_name = 'maintenance'

urlpatterns = [
    path('compliance/', compliance_and_maintenance_dashboard, name='compliance_dashboard'),
    path('api/compliance-summary/', api_compliance_summary, name='api_compliance_summary'),
    path('api/send-renewal-warnings/', api_send_renewal_warnings, name='api_send_renewal_warnings'),
]
