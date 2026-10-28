"""
Core app URL configuration.

Provides routes for fleet roster management, vehicle availability, GIS raster tile proxy,
rate cards & tariffs studio, and the interactive Developer API documentation catalog.
"""

from django.urls import path
from . import views
from . import gis_views
from . import api_docs

urlpatterns = [
    # ── Fleet Management & Availability ──
    path('fleet/vehicles/', views.fleet_vehicles_roster_view, name='fleet-vehicles-roster'),
    path('fleet/categories/', views.fleet_categories_view, name='fleet-categories'),
    path('fleet/types/', views.fleet_types_view, name='fleet-types'),
    path('fleet/drivers/', views.fleet_drivers_roster_view, name='fleet-drivers-roster'),
    path('api/fleet/vehicles/<int:vehicle_id>/toggle-status/', views.api_toggle_vehicle_status_staff, name='fleet-vehicle-toggle-status'),
    path('api/vehicle-types/', views.api_get_vehicle_types, name='api_get_vehicle_types'),
    path('api/vehicles/<str:reg_no>/check-availability/', views.api_vehicle_check_availability, name='api-vehicle-check-availability'),
    path('pricing/', views.rate_cards_studio_view, name='client-pricing-studio'),

    # ── GIS Tile Engine & Edge Cache ──
    path('gis/tiles/<int:z>/<int:x>/<int:y>.png', gis_views.full_india_tile_proxy_view, name='full-india-tile-proxy'),
    path('api/gis/status/', gis_views.api_india_gis_status_view, name='api-india-gis-status'),

    # ── Developer API Catalog & OpenAPI Specification ──
    path('docs/', api_docs.api_docs_view, name='api-docs'),
    path('api/docs/', api_docs.api_docs_view, name='api-docs-alias'),
    path('api/docs/schema.json', api_docs.api_schema_json_view, name='api-schema-json'),
    path('api/docs/schema.json', api_docs.api_schema_json_view, name='api-docs-schema'),
]
