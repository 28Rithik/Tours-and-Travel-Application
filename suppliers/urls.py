from django.urls import path
from . import views

app_name = 'suppliers'

urlpatterns = [
    # Studios & Hubs
    path('settlement-hub/', views.admin_settlement_hub_view, name='settlement-hub'),
    path('hotel-vouchers/', views.admin_hotel_vouchers_hub_view, name='hotel-vouchers-hub'),

    # Printable Documents
    path('hotel-voucher/<int:voucher_id>/print/', views.hotel_voucher_print_view, name='hotel-voucher-print'),
    path('duty-slip/<int:settlement_id>/print/', views.outsourced_duty_slip_print_view, name='duty-slip-print'),
    path('settlement/<int:settlement_id>/print/', views.outsourced_settlement_print_view, name='settlement-print'),

    # REST APIs
    path('api/settlement/calculate/', views.api_calculate_settlement, name='api-settlement-calculate'),
    path('api/settlement/<int:settlement_id>/approve/', views.api_approve_settlement, name='api-settlement-approve'),
    path('api/hotel-voucher/create/', views.api_create_hotel_voucher, name='api-hotel-voucher-create'),
    path('api/hotel-voucher/<int:voucher_id>/whatsapp/', views.api_hotel_voucher_whatsapp, name='api-hotel-voucher-whatsapp'),
]
