from django.urls import path
from . import views

app_name = 'driver_portal'

urlpatterns = [
    path('', views.driver_dashboard, name='dashboard'),
    path('login/', views.driver_login, name='login'),
    path('logout/', views.driver_logout, name='logout'),
    path('inspection/', views.driver_inspection, name='inspection'),
    path('trip/<int:trip_id>/', views.driver_trip_detail, name='trip_detail'),
    path('trip/<int:trip_id>/start/', views.driver_trip_start, name='trip_start'),
    path('trip/<int:trip_id>/end/', views.driver_trip_end, name='trip_end'),
    path('fuel/', views.driver_fuel_log, name='fuel_log'),
    path('sos/', views.driver_sos_trigger, name='sos'),
]
