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
    generate_trip_sheet,
    trip_create,
    trip_detail,
    trip_update_status,
    api_telematics_ping,
    api_telematics_live,
    dispatch_standby_replacement,
    fleet_live_mission_control,
    api_fleet_live_feed,
    passenger_live_tracking_view,
    api_passenger_live_tracking,
    broadcast_trip_whatsapp_view,
)
from statements.views import download_statement, generate_statement
from finance.views import api_payment_context
from travelerp.views import dashboard, party_ledger, party_profitability_report, vehicle_profitability_report
from core.views import api_get_vehicle_types

urlpatterns = [
    path('', include('dashboard.urls')),
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
    path('api/payments/context/', api_payment_context, name='api_payment_context'),
    path('trips/<int:trip_id>/', trip_detail, name='trip-detail'),
    path('trips/<int:trip_id>/trip-sheet/', generate_trip_sheet, name='trip-sheet'),
    path('trips/<int:trip_id>/status/', trip_update_status, name='trip-update-status'),
    path('trips/<int:trip_id>/customer-confirmation/', customer_confirmation_preview, name='customer-confirmation-preview'),
    path('trips/<int:trip_id>/broadcast-whatsapp/', broadcast_trip_whatsapp_view, name='trip-broadcast-whatsapp'),
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
    path('incidents/<int:incident_id>/dispatch-standby/', dispatch_standby_replacement, name='dispatch-standby-replacement'),
    path('finance/', include('finance.urls')),
    path('maintenance/', include('maintenance.urls')),
    path('driver/', include('driver_portal.urls')),
    path('', RedirectView.as_view(pattern_name='dashboard', permanent=False)),
    path('packages/', include('packages.urls')),
    path('customer-portal/', include('customer_portal.urls')),
    path('payments/', include('payments_gateway.urls')),
    path('analytics/', include('analytics.urls')),
    path('crm/', include('crm.urls')),
    path('i18n/', include('django.conf.urls.i18n')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
