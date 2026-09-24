from django.urls import path
from . import views

app_name = 'analytics'

urlpatterns = [
    path('dashboard/', views.package_profitability_dashboard, name='dashboard'),
    path('fleet/', views.fleet_analytics_dashboard, name='fleet_analytics'),
    path('driver-scorecard/<int:driver_id>/', views.api_driver_scorecard_detail, name='api_driver_scorecard_detail'),
]
