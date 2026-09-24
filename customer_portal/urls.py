from django.urls import path
from . import views

app_name = 'customer_portal'

urlpatterns = [
    path('', views.portal_home, name='home'),
    path('login/', views.portal_login, name='login'),
    path('logout/', views.portal_logout, name='logout'),
    path('bookings/', views.my_bookings, name='bookings'),
    path('bookings/<int:booking_id>/', views.portal_booking_detail, name='booking_detail'),
    path('documents/', views.my_documents, name='documents'),
    path('packages/', views.package_list, name='package_list'),
    path('packages/<int:package_id>/', views.package_detail, name='package_detail'),
    path('checkout/<int:inventory_id>/', views.checkout, name='checkout'),
]
