from django.urls import path
from . import views

app_name = 'driver_portal'

urlpatterns = [
    # ── Driver Dashboard & Auth ──
    path('', views.driver_dashboard, name='dashboard'),
    path('portal/', views.driver_dashboard, name='portal'),
    path('login/', views.driver_login, name='login'),
    path('logout/', views.driver_logout, name='logout'),

    # ── Route Navigation & Pickup Cockpit (Domain 2) ──
    path('commute/<int:trip_log_id>/navigation/', views.driver_commute_navigation, name='commute_navigation'),
    path('api/commute/<int:trip_log_id>/start/', views.api_start_commute_trip, name='api_start_commute_trip'),
    path('api/commute/<int:trip_log_id>/complete/', views.api_complete_commute_trip, name='api_complete_commute_trip'),

    # ── Attendance & Duty Hours APIs ──
    path('api/clock-in/', views.api_driver_clock_in, name='api_clock_in'),
    path('api/clock-out/', views.api_driver_clock_out, name='api_clock_out'),

    # ── Route Delay Sentry & Passenger Actions ──
    path('api/report-delay/', views.api_driver_report_delay, name='api_report_delay'),
    path('api/board-commuter/', views.api_driver_board_commuter, name='api_board_commuter'),
    path('api/absent-commuter/', views.api_driver_absent_commuter, name='api_absent_commuter'),

    # ── Outstation Tour Trip & Milestones ──
    path('trip/<int:trip_id>/', views.driver_trip_detail, name='trip_detail'),
    path('trip/<int:trip_id>/start/', views.driver_trip_start, name='trip_start'),
    path('trip/<int:trip_id>/end/', views.driver_trip_end, name='trip_end'),

    # ── Pre-Trip Inspection, Fuel & SOS ──
    path('inspection/', views.driver_inspection, name='inspection'),
    path('fuel/', views.driver_fuel_log, name='fuel_log'),
    path('sos/', views.driver_sos_trigger, name='sos'),

    # ── PWA Assets ──
    path('manifest.json', views.pwa_manifest, name='manifest'),
    path('sw.js', views.pwa_service_worker, name='sw'),
]
