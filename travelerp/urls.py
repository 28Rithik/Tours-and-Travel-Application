"""
URL configuration for travelerp project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static
from operations.views import (
    api_get_booking,
    api_package_inventory,
    api_inventory_detail,
    api_get_trip,
    api_bulk_contract_context,
    booking_create,
    booking_detail,
    booking_list,
    customer_confirmation_preview,
    customer_trip_invoice_view,
    generate_trip_sheet,
    trip_create,
    trip_detail,
    trip_update_status,
    api_telematics_ping,
    api_telematics_live,
    dispatch_standby_replacement,
    fleet_live_mission_control,
    api_fleet_live_feed,
    admin_fleet_radar_view,
    api_fleet_telematics_tick,
    passenger_live_tracking_view,
    api_passenger_live_tracking,
    broadcast_trip_whatsapp_view,
    broadcast_driver_whatsapp_view,
    trip_quick_assign_view,
    driver_handover_view,
    driver_handover_sos_view,
    whatsapp_webhook_view,
    admin_whatsapp_bot_studio_view,
    api_whatsapp_simulator,
    api_handover_session_audit,
    api_dispatch_whatsapp_trip_sheet,
    api_osrm_route_view,
    api_spatial_nearest_vehicles_view,
    api_gis_prometheus_metrics_view,
    api_gis_health_view,
    gis_control_center_dashboard_view,
    api_route_optimizer_view,
    api_telemetry_pipeline_ingest_view,
    api_telemetry_stream_publish_view,
    api_telemetry_stream_consume_view,
    api_tara_chat,
    api_tara_quick_stats,
    api_tara_set_key,
    admin_tara_copilot_studio_view,
    trip_lifecycle_portal_view,
    api_trip_milestone_advance,
    api_trip_milestones_status,
    api_trip_quick_expense,
    admin_trip_itinerary_builder_view,
    api_trip_itinerary_save,
    api_trip_itinerary_import_package,
    api_trip_itinerary_get,
    guest_tour_itinerary_view,
)
from statements.views import download_statement, generate_statement
from maintenance.views import damage_marker_studio_view
from finance.views import (
    api_payment_context,
    admin_gst_studio_view,
    api_generate_corporate_invoice_eway,
    api_export_nic_eway_json,
    corporate_invoice_print_view,
    api_dispatch_corporate_invoice_whatsapp,
    admin_petty_cash_studio_view,
    driver_mobile_wallet_view,
)
from driver_portal.views import pwa_manifest, pwa_service_worker
from travelerp.views import dashboard, party_ledger, party_profitability_report, vehicle_profitability_report
from core.views import api_get_vehicle_types, api_vehicle_check_availability
from payments_gateway.views import (
    admin_payment_studio_view,
    api_generate_dynamic_upi,
    api_direct_upi_confirm,
    api_simulate_payment_webhook,
    api_payment_studio_metrics,
)
from crm.views import crm_kanban_board_view
from customer_portal.views import public_landing_view
from integrations import views as integrations_views

urlpatterns = [
    path('', public_landing_view, name='public-landing'),
    # WhatsApp Business Bot & Driver Handover Studio
    path('admin/operations/whatsapp-bot/', admin_whatsapp_bot_studio_view, name='admin-whatsapp-bot-studio'),
    path('admin/whatsapp-bot/', admin_whatsapp_bot_studio_view, name='admin-whatsapp-bot-studio-alias'),
    path('trip/<int:trip_id>/handover/', driver_handover_view, name='driver-handover-view'),
    path('trips/<int:trip_id>/handover/', driver_handover_view, name='driver-handover-view-alias'),
    path('trip/<int:trip_id>/handover/sos/', driver_handover_sos_view, name='driver-handover-sos'),
    # Phase 3: 7-Milestone Tour Lifecycle Cockpit & APIs
    path('trip/<int:trip_id>/lifecycle/', trip_lifecycle_portal_view, name='trip-lifecycle-portal'),
    path('driver/trip/<int:trip_id>/lifecycle/', trip_lifecycle_portal_view, name='driver-trip-lifecycle-portal'),
    path('admin/operations/trip/<int:trip_id>/lifecycle/', trip_lifecycle_portal_view, name='admin-trip-lifecycle-portal'),
    path('api/trip/<int:trip_id>/milestone/advance/', api_trip_milestone_advance, name='api-trip-milestone-advance'),
    path('api/trip/<int:trip_id>/milestones/', api_trip_milestones_status, name='api-trip-milestones-status'),
    path('api/trip/<int:trip_id>/expense/add/', api_trip_quick_expense, name='api-trip-quick-expense'),
    path('api/whatsapp/webhook/', whatsapp_webhook_view, name='api-whatsapp-webhook'),
    path('api/whatsapp/simulate/', api_whatsapp_simulator, name='api-whatsapp-simulate'),
    path('api/whatsapp/trip/<int:trip_id>/dispatch/', api_dispatch_whatsapp_trip_sheet, name='api-whatsapp-trip-dispatch'),
    path('api/whatsapp/handover/<int:session_id>/audit/', api_handover_session_audit, name='api-handover-session-audit'),
    # Phase 4: Multi-Day Tour Itinerary Day-by-Day Builder & Live Guest Experience Portal
    path('admin/operations/trip/<int:trip_id>/itinerary-builder/', admin_trip_itinerary_builder_view, name='admin-trip-itinerary-builder'),
    path('admin/trip/<int:trip_id>/itinerary-builder/', admin_trip_itinerary_builder_view, name='admin-trip-itinerary-builder-alias'),
    path('tour/itinerary/<str:token>/', guest_tour_itinerary_view, name='guest-tour-itinerary'),
    path('trip/<int:trip_id>/itinerary/', guest_tour_itinerary_view, name='trip-itinerary-portal'),
    path('api/trip/<int:trip_id>/itinerary/save/', api_trip_itinerary_save, name='api-trip-itinerary-save'),
    path('api/trip/<int:trip_id>/itinerary/import-package/', api_trip_itinerary_import_package, name='api-trip-itinerary-import-package'),
    path('api/trip/<int:trip_id>/itinerary/', api_trip_itinerary_get, name='api-trip-itinerary-get'),
    # TARA AI Operations Copilot (Powered by Groq / LLM) Studio
    path('admin/operations/tara-ai/', admin_tara_copilot_studio_view, name='admin-tara-copilot-studio'),
    path('admin/tara-ai/', admin_tara_copilot_studio_view, name='admin-tara-copilot-studio-alias'),
    # 2D Interactive Vehicle Damage Marker & Inspection Studio
    path('admin/maintenance/damage-marker/', damage_marker_studio_view, name='admin-damage-marker-studio'),
    # Unfold Admin Telematics GPS Radar Map
    path('admin/operations/fleet-radar/', admin_fleet_radar_view, name='admin-fleet-radar'),
    path('admin/fleet-radar/', admin_fleet_radar_view, name='admin-fleet-radar-alias'),
    path('api/fleet/simulate-tick/', api_fleet_telematics_tick, name='api-fleet-telematics-tick'),
    # Unfold Admin Dynamic UPI & Payment Gateway Studio
    path('admin/finance/payment-studio/', admin_payment_studio_view, name='admin-payment-studio'),
    path('admin/payments/studio/', admin_payment_studio_view, name='admin-payments-studio-alias'),
    path('api/payments/dynamic-upi/generate/', api_generate_dynamic_upi, name='api-dynamic-upi-generate'),
    path('api/payments/direct-upi/confirm/', api_direct_upi_confirm, name='api-direct-upi-confirm'),
    path('api/payments/simulate-webhook/', api_simulate_payment_webhook, name='api-simulate-payment-webhook'),
    path('api/payments/studio-metrics/', api_payment_studio_metrics, name='api-payment-studio-metrics'),
    # Corporate GST B2B Invoicing & NIC E-Way Bill Studio
    path('admin/finance/gst-studio/', admin_gst_studio_view, name='admin-gst-studio'),
    path('admin/gst-studio/', admin_gst_studio_view, name='admin-gst-studio-alias'),
    path('api/finance/generate-invoice-ewaybill/', api_generate_corporate_invoice_eway, name='api-finance-generate-invoice-ewaybill'),
    path('api/finance/invoice/<int:invoice_id>/eway-json/', api_export_nic_eway_json, name='api-finance-export-eway-json'),
    path('api/finance/invoice/<int:invoice_id>/whatsapp/', api_dispatch_corporate_invoice_whatsapp, name='api-finance-invoice-whatsapp-direct'),
    path('finance/invoice/<int:invoice_id>/view/', corporate_invoice_print_view, name='finance-corporate-invoice-view'),
    # Phase 5: Petty Cash Float Register & Driver/Tour Manager Cash Wallet Studio
    path('admin/finance/petty-cash-studio/', admin_petty_cash_studio_view, name='admin-petty-cash-studio'),
    path('admin/petty-cash/', admin_petty_cash_studio_view, name='admin-petty-cash-alias'),
    path('driver/wallet/', driver_mobile_wallet_view, name='driver-mobile-wallet'),
    path('driver/trip/<int:trip_id>/petty-cash/', driver_mobile_wallet_view, name='driver-trip-petty-cash'),
    # Phase 6: Visual Drag-and-Drop CRM Kanban Board & Lead Follow-Up Hub
    path('admin/crm/kanban/', crm_kanban_board_view, name='admin-crm-kanban'),
    path('admin/kanban/', crm_kanban_board_view, name='admin-crm-kanban-alias'),
    # Omnichannel Integrations Hub, Meta Webhook, Email SES/SMTP Studio, Agent Dashboard & Approvals
    path('admin/integrations/', include('integrations.urls')),
    path('api/integrations/meta/webhook/', integrations_views.api_meta_lead_webhook, name='api_meta_lead_webhook_root'),
    path('api/integrations/meta/simulate/', integrations_views.api_meta_lead_simulate, name='api_meta_lead_simulate_root'),
    path('api/integrations/google-sheets/sync/', integrations_views.api_google_sheet_sync, name='api_google_sheet_sync_root'),
    path('api/integrations/email/test/', integrations_views.api_test_email, name='api_test_email_root'),
    # Progressive Web App (PWA) root manifest and service worker
    path('manifest.json', pwa_manifest, name='pwa-manifest'),
    path('sw.js', pwa_service_worker, name='pwa-sw'),
    # Fleet Profitability & Cost-Per-KM (CPK) Optimization Radar Studio
    path('', include('finance_fleet.urls')),
    # Aliases and redirects for Package Tours Friendly URLs
    path('admin/package_tours/tourbusdeparturebatch/', RedirectView.as_view(url='/admin/package_tours/tourdeparturebatchproxy/', permanent=False)),
    path('admin/package_tours/tourbusdeparturebatch/<path:subpath>', RedirectView.as_view(url='/admin/package_tours/tourdeparturebatchproxy/%(subpath)s', permanent=False)),
    path('admin/package_tours/passengermanifest/', RedirectView.as_view(url='/admin/package_tours/passengermanifestproxy/', permanent=False)),
    path('admin/package_tours/passengermanifest/<path:subpath>', RedirectView.as_view(url='/admin/package_tours/passengermanifestproxy/%(subpath)s', permanent=False)),
    path('admin/package_tours/boardingpoint/', RedirectView.as_view(url='/admin/package_tours/boardingpointproxy/', permanent=False)),
    path('admin/package_tours/boardingpoint/<path:subpath>', RedirectView.as_view(url='/admin/package_tours/boardingpointproxy/%(subpath)s', permanent=False)),
    path('admin/package_tours/collegeiv/', RedirectView.as_view(url='/admin/package_tours/collegeivproxy/', permanent=False)),
    path('admin/package_tours/collegeiv/<path:subpath>', RedirectView.as_view(url='/admin/package_tours/collegeivproxy/%(subpath)s', permanent=False)),
    path('admin/', admin.site.urls),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('dashboard/', dashboard, name='dashboard'),
    path('dispatch/', booking_list, name='dispatch-console'),
    path('bookings/', booking_list, name='booking-list'),
    path('bookings/create/', booking_create, name='booking-create'),
    path('bookings/<int:booking_id>/', booking_detail, name='booking-detail'),
    path('bookings/<int:booking_id>/trip/create/', trip_create, name='trip-create'),
    path('api/bookings/<int:booking_id>/', api_get_booking, name='api_get_booking'),
    path('api/packages/<int:package_id>/inventory/', api_package_inventory, name='api_package_inventory'),
    path('api/package-inventory/<int:inventory_id>/', api_inventory_detail, name='api_inventory_detail'),
    path('api/bulk-contracts/<int:contract_id>/', api_bulk_contract_context, name='api_bulk_contract_context'),
    path('api/trips/<int:trip_id>/', api_get_trip, name='api_get_trip'),
    path('api/vehicle-types/', api_get_vehicle_types, name='api_get_vehicle_types'),
    path('api/vehicles/<str:reg_no>/check-availability/', api_vehicle_check_availability, name='api-vehicle-check-availability'),
    path('api/vehicles/<str:reg_no>/check-availability/', api_vehicle_check_availability, name='api_vehicle_check_availability'),
    path('api/payments/context/', api_payment_context, name='api_payment_context'),
    path('trips/<int:trip_id>/', trip_detail, name='trip-detail'),
    path('trips/<int:trip_id>/trip-sheet/', generate_trip_sheet, name='trip-sheet'),
    path('customer/trip/<int:trip_id>/invoice/', customer_trip_invoice_view, name='customer-trip-invoice'),
    path('trips/<int:trip_id>/status/', trip_update_status, name='trip-update-status'),
    path('trips/<int:trip_id>/customer-confirmation/', customer_confirmation_preview, name='customer-confirmation-preview'),
    path('trips/<int:trip_id>/quick-assign/', trip_quick_assign_view, name='trip-quick-assign'),
    path('trips/<int:trip_id>/broadcast-whatsapp/', broadcast_trip_whatsapp_view, name='trip-broadcast-whatsapp'),
    path('trips/<int:trip_id>/broadcast-driver-whatsapp/', broadcast_driver_whatsapp_view, name='trip-broadcast-driver-whatsapp'),
    path('parties/<int:party_id>/ledger/', party_ledger, name='party-ledger'),
    path('statements/generate/', generate_statement, name='generate-statement'),
    path('statements/<int:statement_id>/download/', download_statement, name='download-statement'),
    path('reports/vehicle-profitability/', vehicle_profitability_report, name='vehicle-profitability'),
    path('reports/party-profitability/', party_profitability_report, name='party-profitability'),
    path('api/telematics/ping/', api_telematics_ping, name='api_telematics_ping'),
    path('api/telematics/live/<int:vehicle_id>/', api_telematics_live, name='api_telematics_live'),
    path('fleet/live/', fleet_live_mission_control, name='fleet-live'),
    path('api/fleet/live-feed/', api_fleet_live_feed, name='api-fleet-live-feed'),
    path('track/<str:token>/', passenger_live_tracking_view, name='passenger-live-tracking'),
    path('api/track/<str:token>/live/', api_passenger_live_tracking, name='api-passenger-live-tracking'),
    path('api/routing/route/', api_osrm_route_view, name='api_osrm_route'),
    path('api/spatial/nearest-vehicles/', api_spatial_nearest_vehicles_view, name='api_spatial_nearest_vehicles'),
    path('gis/metrics/', api_gis_prometheus_metrics_view, name='gis_prometheus_metrics'),
    path('gis/health/', api_gis_health_view, name='gis_health'),
    path('gis/control-center/', gis_control_center_dashboard_view, name='gis_control_center'),
    path('api/routing/optimize/', api_route_optimizer_view, name='api_route_optimizer'),
    path('api/telemetry/pipeline-ingest/', api_telemetry_pipeline_ingest_view, name='api_telemetry_pipeline_ingest'),
    path('api/telemetry/stream-publish/', api_telemetry_stream_publish_view, name='api_telemetry_stream_publish'),
    path('api/telemetry/stream-consume/', api_telemetry_stream_consume_view, name='api_telemetry_stream_consume'),
    # TARA AI Operations Copilot (Powered by Groq / LLM) API
    path('api/tara/chat/', api_tara_chat, name='api-tara-chat'),
    path('api/tara/quick-stats/', api_tara_quick_stats, name='api-tara-quick-stats'),
    path('api/tara/set-key/', api_tara_set_key, name='api-tara-set-key'),
    path('incidents/<int:incident_id>/dispatch-standby/', dispatch_standby_replacement, name='dispatch-standby-replacement'),
    path('htmx/', include('operations.htmx_urls')),
    path('packages/htmx/', include('packages.htmx_urls')),
    path('finance/', include('finance.urls')),
    path('maintenance/', include('maintenance.urls')),
    path('driver/', include('driver_portal.urls')),
    path('commute/', include('fleet_commute.urls')),
    path('packages/', include('packages.urls')),
    path('customer-portal/', include('customer_portal.urls')),
    path('payments/', include('payments_gateway.urls')),
    path('analytics/', include('analytics.urls')),
    path('crm/', include('crm.urls')),
    path('suppliers/', include('suppliers.urls')),
    path('marketing/', include('marketing.urls')),
    path('i18n/', include('django.conf.urls.i18n')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
