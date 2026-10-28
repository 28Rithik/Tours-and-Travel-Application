"""
Operations app URL configuration.

Contains routes for booking dispatch, trip lifecycle cockpit, GPS telematics radar,
driver handover, WhatsApp bot integrations, and operational sentry studios.
"""

from django.urls import path
from . import views

urlpatterns = [
    # ── WhatsApp Bot & Handover Studio ──
    path('operations/whatsapp-bot/', views.admin_whatsapp_bot_studio_view, name='operations-whatsapp-bot'),
    path('admin/operations/whatsapp-bot/', views.admin_whatsapp_bot_studio_view, name='admin-whatsapp-bot-studio'),
    path('admin/whatsapp-bot/', views.admin_whatsapp_bot_studio_view, name='admin-whatsapp-bot-studio-alias'),
    path('trip/<int:trip_id>/handover/', views.driver_handover_view, name='driver-handover-view'),
    path('trips/<int:trip_id>/handover/', views.driver_handover_view, name='driver-handover-view-alias'),
    path('trip/<int:trip_id>/handover/sos/', views.driver_handover_sos_view, name='driver-handover-sos'),

    # ── Tour Lifecycle Cockpit & Milestone APIs ──
    path('trip/<int:trip_id>/lifecycle/', views.trip_lifecycle_portal_view, name='trip-lifecycle-portal'),
    path('driver/trip/<int:trip_id>/lifecycle/', views.trip_lifecycle_portal_view, name='driver-trip-lifecycle-portal'),
    path('admin/operations/trip/<int:trip_id>/lifecycle/', views.trip_lifecycle_portal_view, name='admin-trip-lifecycle-portal'),
    path('api/trip/<int:trip_id>/milestone/advance/', views.api_trip_milestone_advance, name='api-trip-milestone-advance'),
    path('api/trip/<int:trip_id>/milestones/', views.api_trip_milestones_status, name='api-trip-milestones-status'),
    path('api/trip/<int:trip_id>/expense/add/', views.api_trip_quick_expense, name='api-trip-quick-expense'),
    path('api/trip/<int:trip_id>/signature/', views.api_trip_customer_signature, name='api-trip-customer-signature'),
    path('api/trips/<int:trip_id>/signature/', views.api_trip_customer_signature, name='api-trips-customer-signature'),
    path('api/trip/<int:trip_id>/verify-boarding/', views.api_trip_verify_boarding, name='api-trip-verify-boarding'),
    path('api/trip/<int:trip_id>/passengers/', views.api_trip_passengers_list, name='api-trip-passengers-list'),
    path('api/whatsapp/webhook/', views.whatsapp_webhook_view, name='api-whatsapp-webhook'),
    path('api/whatsapp/simulate/', views.api_whatsapp_simulator, name='api-whatsapp-simulate'),
    path('api/whatsapp/trip/<int:trip_id>/dispatch/', views.api_dispatch_whatsapp_trip_sheet, name='api-whatsapp-trip-dispatch'),
    path('api/whatsapp/handover/<int:session_id>/audit/', views.api_handover_session_audit, name='api-handover-session-audit'),

    # ── Multi-Day Tour Itinerary Day-by-Day Builder & Guest Portal ──
    path('operations/itinerary-builder/', views.admin_trip_itinerary_builder_view, name='operations-itinerary-builder-hub'),
    path('operations/trip/<int:trip_id>/itinerary-builder/', views.admin_trip_itinerary_builder_view, name='operations-trip-itinerary-builder'),
    path('admin/operations/itinerary-builder/', views.admin_trip_itinerary_builder_view, name='admin-operations-itinerary-builder-hub'),
    path('admin/operations/trip/<int:trip_id>/itinerary-builder/', views.admin_trip_itinerary_builder_view, name='admin-trip-itinerary-builder'),
    path('admin/trip/<int:trip_id>/itinerary-builder/', views.admin_trip_itinerary_builder_view, name='admin-trip-itinerary-builder-alias'),
    path('tour/itinerary/<str:token>/', views.guest_tour_itinerary_view, name='guest-tour-itinerary'),
    path('trip/<int:trip_id>/itinerary/', views.guest_tour_itinerary_view, name='trip-itinerary-portal'),
    path('api/trip/<int:trip_id>/itinerary/save/', views.api_trip_itinerary_save, name='api-trip-itinerary-save'),
    path('api/trip/<int:trip_id>/itinerary/import-package/', views.api_trip_itinerary_import_package, name='api-trip-itinerary-import-package'),
    path('api/trip/<int:trip_id>/itinerary/', views.api_trip_itinerary_get, name='api-trip-itinerary-get'),

    # ── Rathasārathi AI Operations Copilot ──
    path('operations/rathasarathi-ai/', views.admin_rathasarathi_copilot_studio_view, name='operations-rathasarathi-ai'),
    path('admin/operations/rathasarathi-ai/', views.admin_rathasarathi_copilot_studio_view, name='admin-rathasarathi-copilot-studio'),
    path('admin/rathasarathi-ai/', views.admin_rathasarathi_copilot_studio_view, name='admin-rathasarathi-copilot-studio-alias'),
    path('api/rathasarathi/chat/', views.api_rathasarathi_chat, name='api-rathasarathi-chat'),
    path('api/rathasarathi/quick-stats/', views.api_rathasarathi_quick_stats, name='api-rathasarathi-quick-stats'),
    path('api/rathasarathi/set-key/', views.api_rathasarathi_set_key, name='api-rathasarathi-set-key'),

    # ── GPS Telematics, Radar & Live Feed ──
    path('admin/operations/fleet-radar/', views.admin_fleet_radar_view, name='admin-fleet-radar'),
    path('admin/fleet-radar/', views.admin_fleet_radar_view, name='admin-fleet-radar-alias'),
    path('operations/fleet-radar/', views.fleet_live_mission_control, name='operations-fleet-radar'),
    path('fleet/live/', views.fleet_live_mission_control, name='fleet-live'),
    path('api/fleet/live-feed/', views.api_fleet_live_feed, name='api-fleet-live-feed'),
    path('api/fleet/simulate-tick/', views.api_fleet_telematics_tick, name='api-fleet-simulate-tick'),
    path('api/telematics/ping/', views.api_telematics_ping, name='api_telematics_ping'),
    path('api/telematics/live/<int:vehicle_id>/', views.api_telematics_live, name='api_telematics_live'),
    path('api/fleet/transfer/request/', views.api_request_depot_transfer, name='api-fleet-transfer-request'),
    path('api/fleet/transfer/<int:transfer_id>/receive/', views.api_receive_depot_transfer, name='api-fleet-transfer-receive'),
    path('api/fleet/transfer/history/', views.api_depot_transfer_history, name='api-fleet-transfer-history'),
    path('track/<str:token>/', views.passenger_live_tracking_view, name='passenger-live-tracking'),
    path('api/track/<str:token>/live/', views.api_passenger_live_tracking, name='api-passenger-live-tracking'),
    path('incidents/<int:incident_id>/dispatch-standby/', views.dispatch_standby_replacement, name='dispatch-standby-replacement'),
    path('api/incidents/<str:incident_id>/acknowledge/', views.api_acknowledge_incident, name='api-acknowledge-incident'),
    path('api/fleet/geofence-alarms/', views.api_active_geofence_alarms, name='api-active-geofence-alarms'),
    path('api/vehicle/<int:vehicle_id>/quick-telemetry/', views.api_vehicle_quick_telemetry, name='api-vehicle-quick-telemetry'),

    # ── State Border Permits & E-Pass Sentry ──
    path('operations/border-permits/', views.border_permit_studio_view, name='operations-border-permits'),
    path('admin/operations/border-permits/', views.border_permit_studio_view, name='admin-operations-border-permits'),
    path('api/operations/border-permits/check/<int:trip_id>/', views.api_border_permit_check, name='api-operations-border-permits-check'),
    path('api/operations/border-permits/pay/', views.api_border_permit_record_payment, name='api-operations-border-permits-pay'),
    path('api/operations/border-permits/seed/', views.api_border_permit_seed, name='api-operations-border-permits-seed'),
    path('api/operations/epass/issue/', views.api_epass_issue, name='api-operations-epass-issue'),
    path('api/operations/epass/verify/<int:epass_id>/', views.api_epass_verify, name='api-operations-epass-verify'),

    # ── Chauffeur Fatigue & Mandatory Duty Rest Sentry ──
    path('operations/driver-fatigue-sentry/', views.driver_fatigue_sentry_view, name='operations-driver-fatigue-sentry'),
    path('admin/operations/driver-fatigue-sentry/', views.driver_fatigue_sentry_view, name='admin-operations-driver-fatigue-sentry'),
    path('api/operations/driver-fatigue/audit/<int:driver_id>/', views.api_driver_fatigue_audit, name='api-operations-driver-fatigue-audit'),
    path('api/operations/driver-fatigue/override/', views.api_driver_fatigue_override, name='api-operations-driver-fatigue-override'),
    path('api/operations/driver-fatigue/seed/', views.api_driver_fatigue_seed, name='api-operations-driver-fatigue-seed'),

    # ── Highway Breakdown & Emergency SOS Relief Dispatch ──
    path('operations/breakdown-sos/', views.breakdown_sos_studio_view, name='operations-breakdown-sos'),
    path('admin/operations/breakdown-sos/', views.breakdown_sos_studio_view, name='admin-operations-breakdown-sos'),
    path('api/operations/breakdown-sos/log/', views.api_log_sos_incident, name='api-operations-breakdown-sos-log'),
    path('api/operations/breakdown-sos/dispatch/', views.api_dispatch_sos_replacement, name='api-operations-breakdown-sos-dispatch'),

    # ── Flight & Train PNR Group Arrival Manifest ──
    path('operations/pnr-arrivals/', views.pnr_arrivals_studio_view, name='operations-pnr-arrivals'),
    path('admin/operations/pnr-arrivals/', views.pnr_arrivals_studio_view, name='admin-operations-pnr-arrivals'),
    path('api/operations/pnr-arrivals/status/', views.api_update_arrival_status, name='api-operations-pnr-arrivals-status'),

    # ── Trip Cash Advance & Envelope Studio ──
    path('operations/cash-envelopes/', views.trip_cash_envelope_studio_view, name='operations-cash-envelopes'),
    path('admin/operations/cash-envelopes/', views.trip_cash_envelope_studio_view, name='admin-operations-cash-envelopes'),
    path('api/operations/cash-advance/issue/', views.api_cash_advance_issue, name='api-operations-cash-advance-issue'),
    path('api/operations/cash-advance/expense-log/', views.api_cash_advance_expense_log, name='api-operations-cash-advance-expense-log'),
    path('api/operations/cash-advance/reconcile/', views.api_cash_advance_reconcile, name='api-operations-cash-advance-reconcile'),
    path('api/operations/cash-advance/seed/', views.api_cash_advance_seed, name='api-operations-cash-advance-seed'),

    # ── Statutory Compliance Sentry (FC, AITP, AIS-140) ──
    path('operations/statutory-compliance/', views.statutory_compliance_studio_view, name='operations-statutory-compliance'),
    path('admin/operations/statutory-compliance/', views.statutory_compliance_studio_view, name='admin-operations-statutory-compliance'),
    path('api/operations/statutory-compliance/renew/', views.api_compliance_renew_document, name='api-operations-compliance-renew'),
    path('api/operations/statutory-compliance/seed/', views.api_compliance_seed, name='api-operations-compliance-seed'),

    # ── Parivahan RTO Traffic E-Challan Sentry ──
    path('operations/echallan-sentry/', views.echallan_sentry_studio_view, name='operations-echallan-sentry'),
    path('admin/operations/echallan-sentry/', views.echallan_sentry_studio_view, name='admin-operations-echallan-sentry'),
    path('api/operations/echallan/liability/', views.api_echallan_assign_responsibility, name='api-operations-echallan-liability'),
    path('api/operations/echallan/pay/', views.api_echallan_mark_paid, name='api-operations-echallan-pay'),
    path('api/operations/echallan/seed/', views.api_echallan_seed, name='api-operations-echallan-seed'),

    # ── Empty-Leg Return Deadhead Trip Marketplace ──
    path('operations/empty-legs/', views.empty_leg_studio_view, name='operations-empty-legs'),
    path('admin/operations/empty-legs/', views.empty_leg_studio_view, name='admin-operations-empty-legs'),
    path('api/operations/empty-legs/publish/', views.api_empty_leg_publish, name='api-operations-empty-legs-publish'),
    path('api/operations/empty-legs/book/', views.api_empty_leg_book, name='api-operations-empty-legs-book'),
    path('api/operations/empty-legs/seed/', views.api_empty_leg_seed, name='api-operations-empty-legs-seed'),

    # ── Driver Allowance (Bata) Engine ──
    path('api/trip/<int:trip_id>/bata/calculate/', views.api_trip_calculate_bata, name='api-trip-calculate-bata'),

    # ── Database Health Dashboard & Audit ──
    path('operations/database-health/', views.admin_database_health_dashboard_view, name='operations-database-health'),
    path('admin/operations/database-health/', views.admin_database_health_dashboard_view, name='admin-database-health-dashboard'),
    path('admin/database-health/', views.admin_database_health_dashboard_view, name='admin-database-health-alias'),
    path('api/database-health/audit/', views.api_database_health_audit, name='api-database-health-audit'),
    path('api/database-health/snapshot/', views.api_database_snapshot_export, name='api-database-snapshot-export'),
    path('api/database-health/maintenance/', views.api_run_scheduler_maintenance, name='api-database-scheduler-maintenance'),

    # ── Booking Dispatch & Operations Console ──
    path('dispatch/', views.booking_list, name='dispatch-console'),
    path('bookings/', views.booking_list, name='booking-list'),
    path('bookings/create/', views.booking_create, name='booking-create'),
    path('bookings/<int:booking_id>/edit/', views.booking_edit, name='booking-edit'),
    path('bookings/<int:booking_id>/', views.booking_detail, name='booking-detail'),
    path('bookings/<int:booking_id>/pdf/voucher/', views.booking_voucher_pdf_view, name='booking-voucher-pdf'),
    path('bookings/<int:booking_id>/trip/create/', views.trip_create, name='trip-create'),
    path('api/bookings/<int:booking_id>/', views.api_get_booking, name='api_get_booking'),
    path('api/packages/<int:package_id>/inventory/', views.api_package_inventory, name='api_package_inventory'),
    path('api/package-inventory/<int:inventory_id>/', views.api_inventory_detail, name='api_inventory_detail'),
    path('api/bulk-contracts/<int:contract_id>/', views.api_bulk_contract_context, name='api_bulk_contract_context'),
    path('api/trips/<int:trip_id>/', views.api_get_trip, name='api_get_trip'),

    # ── Trip Execution & Documents ──
    path('trips/<int:trip_id>/', views.trip_detail, name='trip-detail'),
    path('trips/<int:trip_id>/trip-sheet/', views.generate_trip_sheet, name='trip-sheet'),
    path('trips/<int:trip_id>/pdf/trip-sheet/', views.trip_sheet_pdf_view, name='trip-sheet-pdf'),
    path('trips/<int:trip_id>/pdf/invoice/', views.trip_invoice_pdf_view, name='trip-invoice-pdf'),
    path('customer/trip/<int:trip_id>/invoice/', views.customer_trip_invoice_view, name='customer-trip-invoice'),
    path('trips/<int:trip_id>/status/', views.trip_update_status, name='trip-update-status'),
    path('trips/<int:trip_id>/customer-confirmation/', views.customer_confirmation_preview, name='customer-confirmation-preview'),
    path('trips/<int:trip_id>/quick-assign/', views.trip_quick_assign_view, name='trip-quick-assign'),
    path('api/trips/<int:trip_id>/dispatch-recommendations/', views.api_smart_dispatch_recommendations, name='api-trip-dispatch-recommendations'),
    path('trips/<int:trip_id>/broadcast-whatsapp/', views.broadcast_trip_whatsapp_view, name='trip-broadcast-whatsapp'),
    path('trips/<int:trip_id>/broadcast-driver-whatsapp/', views.broadcast_driver_whatsapp_view, name='trip-broadcast-driver-whatsapp'),

    # ── GIS Routing, Telemetry Pipeline & Streams ──
    path('api/routing/route/', views.api_osrm_route_view, name='api_osrm_route'),
    path('api/spatial/nearest-vehicles/', views.api_spatial_nearest_vehicles_view, name='api_spatial_nearest_vehicles'),
    path('gis/metrics/', views.api_gis_prometheus_metrics_view, name='gis_prometheus_metrics'),
    path('gis/health/', views.api_gis_health_view, name='gis_health'),
    path('gis/control-center/', views.gis_control_center_dashboard_view, name='gis_control_center'),
    path('api/routing/optimize/', views.api_route_optimizer_view, name='api_route_optimizer'),
    path('api/telemetry/pipeline-ingest/', views.api_telemetry_pipeline_ingest_view, name='api_telemetry_pipeline_ingest'),
    path('api/telemetry/stream-publish/', views.api_telemetry_stream_publish_view, name='api_telemetry_stream_publish'),
    path('api/telemetry/stream-consume/', views.api_telemetry_stream_consume_view, name='api_telemetry_stream_consume'),
    path('api/operations/route-estimate/', views.api_route_estimate, name='api-operations-route-estimate'),
    path('api/operations/global-search/', views.api_global_search, name='api-operations-global-search'),
]

