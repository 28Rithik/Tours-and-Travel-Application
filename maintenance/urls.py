from django.urls import path
from .views import (
    compliance_and_maintenance_dashboard,
    api_compliance_summary,
    api_send_renewal_warnings,
    damage_marker_studio_view,
    api_damage_inspection_save,
    api_damage_inspection_detail,
    damage_inspection_print_certificate,
)

app_name = 'maintenance'

urlpatterns = [
    path('compliance/', compliance_and_maintenance_dashboard, name='compliance_dashboard'),
    path('api/compliance-summary/', api_compliance_summary, name='api_compliance_summary'),
    path('api/send-renewal-warnings/', api_send_renewal_warnings, name='api_send_renewal_warnings'),
    # 2D Interactive Vehicle Damage Marker & Inspection Studio
    path('damage-marker/', damage_marker_studio_view, name='damage_marker_studio'),
    path('damage-inspection/<int:inspection_id>/print/', damage_inspection_print_certificate, name='damage_inspection_print'),
    path('api/damage-inspection/save/', api_damage_inspection_save, name='api_damage_inspection_save'),
    path('api/damage-inspection/<int:inspection_id>/', api_damage_inspection_detail, name='api_damage_inspection_detail'),
]

