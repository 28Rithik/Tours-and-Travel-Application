from django.urls import path
from .views import (
    admin_cpk_radar_studio_view,
    api_cpk_radar_metrics,
    api_optimize_tariff,
)

urlpatterns = [
    path('admin/finance/cpk-radar/', admin_cpk_radar_studio_view, name='admin-cpk-radar'),
    path('admin/fleet/cpk-radar/', admin_cpk_radar_studio_view, name='admin-fleet-cpk-radar-alias'),
    path('api/finance/cpk-radar/metrics/', api_cpk_radar_metrics, name='api-cpk-radar-metrics'),
    path('api/finance/cpk-radar/optimize-tariff/', api_optimize_tariff, name='api-optimize-tariff'),
]
