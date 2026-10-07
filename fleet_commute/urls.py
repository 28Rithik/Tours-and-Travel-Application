from django.urls import path
from .views import (
    women_safety_studio_view,
    api_simulate_ivr_call,
    api_ivr_dtmf_webhook,
    api_verify_boarding_otp,
    bulk_roster_import_view,
    sample_roster_csv_download,
    employee_mobile_web_pass_view,
    esg_scorecard_dashboard_view,
    client_portal_index_view,
    client_transparency_portal_view,
    roster_dispatcher_studio_view,
    api_execute_roster_dispatch,
    parent_live_bus_tracking_view,
    api_commute_live_bus_telematics,
    sla_penalty_studio_view,
    api_waive_sla_penalty,
    api_driver_pre_shift_safety_gate,
)

app_name = 'fleet_commute'

urlpatterns = [
    # Phase 1: Women Safety & Outbound IVR Simulator
    path('women-safety/', women_safety_studio_view, name='women_safety_studio'),
    path('api/ivr/simulate-call/', api_simulate_ivr_call, name='api_simulate_ivr_call'),
    path('api/ivr/webhook/', api_ivr_dtmf_webhook, name='api_ivr_dtmf_webhook'),

    # Phase 2: Passenger OTP Boarding
    path('api/verify-boarding-otp/', api_verify_boarding_otp, name='api_verify_boarding_otp'),

    # Phase 3: Bulk Corporate CSV Roster Importer
    path('bulk-import/', bulk_roster_import_view, name='bulk_roster_import'),
    path('bulk-import/sample-csv/', sample_roster_csv_download, name='sample_roster_csv_download'),

    # Phase 4: Employee Commute Mobile Web Pass
    path('pass/<str:pass_token>/', employee_mobile_web_pass_view, name='employee_mobile_web_pass'),

    # Phase 5: ESG Sustainability & Driver Behavior Scorecard
    path('esg-scorecard/', esg_scorecard_dashboard_view, name='esg_scorecard'),

    # Phase 6: Corporate Client Transparency & Compliance Portal
    path('client-portal/', client_portal_index_view, name='client_portal_index'),
    path('client-portal/<int:contract_id>/', client_transparency_portal_view, name='client_transparency_portal'),

    # Phase 7: Automated Batch Daily Roster Dispatcher (300+ Vehicles Scale)
    path('roster-dispatcher/', roster_dispatcher_studio_view, name='roster_dispatcher_studio'),
    path('api/roster-dispatcher/generate/', api_execute_roster_dispatch, name='api_execute_roster_dispatch'),

    # Phase 8: Parent & Employee Real-Time Live Bus Tracking Portal & Telematics API
    path('track/<str:pass_token>/', parent_live_bus_tracking_view, name='parent_live_bus_tracking'),
    path('api/track/<str:pass_token>/live/', api_commute_live_bus_telematics, name='api_commute_live_bus_telematics'),

    # Phase 9: Corporate SLA Performance & Penalty Deductions Studio
    path('sla-penalties/', sla_penalty_studio_view, name='sla_penalty_studio'),
    path('api/sla-penalties/waive/', api_waive_sla_penalty, name='api_waive_sla_penalty'),

    # Phase 10: Driver Pre-Shift "Fit-to-Drive" & Sobriety Breathalyzer Gate
    path('api/driver/pre-shift-safety/', api_driver_pre_shift_safety_gate, name='api_driver_pre_shift_safety_gate'),
]
