from django.urls import path
from . import views

app_name = 'customer_portal'

urlpatterns = [
    # Public Exploration & Discovery
    path('', views.public_landing_view, name='home'),
    path('explore/', views.public_landing_view, name='explore'),
    path('packages/', views.package_list, name='package_list'),
    path('packages/<int:package_id>/', views.package_detail, name='package_detail'),
    path('fleet/', views.fleet_showcase_page, name='fleet'),
    path('fleet/<str:vehicle_id>/', views.vehicle_detail_page, name='vehicle_detail'),
    path('about/', views.about_us_page, name='about_us'),
    path('services/', views.services_overview_page, name='services_overview'),
    path('services/employee-transportation/', views.employee_transportation_page, name='employee_transportation'),
    path('services/school-college-transport/', views.institutional_transport_page, name='institutional_transport'),
    path('services/airport-transfers/', views.airport_transfers_page, name='airport_transfers'),
    path('services/wedding-event-transport/', views.wedding_event_transport_page, name='wedding_event_transport'),
    path('services/mice-corporate-offsites/', views.mice_corporate_offsites_page, name='mice_corporate_offsites'),
    path('services/industrial-factory-transit/', views.industrial_factory_transit_page, name='industrial_factory_transit'),
    path('services/luxury-camper-caravan/', views.luxury_camper_caravan_page, name='luxury_camper_caravan'),
    path('track-booking/', views.portal_booking_tracker, name='track_booking'),
    
    # Booking, Fare Estimator & Checkout Engine
    path('checkout/<int:inventory_id>/', views.checkout, name='checkout'),
    path('rental-checkout/', views.rental_checkout, name='rental_checkout'),
    path('booking/confirmed/<int:booking_id>/', views.booking_confirmed_view, name='booking_confirmed'),
    
    # REST APIs for Dynamic UI & Passwordless Authentication
    path('api/fare-estimator/', views.api_fare_estimator, name='api_fare_estimator'),
    path('api/validate-coupon/', views.api_validate_coupon, name='api_validate_coupon'),
    path('api/checkout/instant-upi-confirm/', views.api_checkout_instant_upi_confirm, name='api_checkout_instant_upi_confirm'),
    path('api/request-otp/', views.api_request_otp, name='api_request_otp'),
    path('api/verify-otp/', views.api_verify_otp, name='api_verify_otp'),
    path('api/custom-inquiry/', views.api_custom_inquiry, name='api_custom_inquiry'),
    
    # Intercity Bus CRS (Port 8005) Live Synergy APIs
    path('api/intercity/loyalty/', views.api_intercity_loyalty_balance, name='api_intercity_loyalty_balance'),
    path('api/intercity/routes/', views.api_intercity_search_trips, name='api_intercity_search_trips'),
    path('api/intercity/reserve-seats/', views.api_intercity_reserve_seats, name='api_intercity_reserve_seats'),
    
    # Authenticated Customer Dashboard & Documents
    path('portal/', views.portal_home, name='portal_home'),
    path('login/', views.portal_login, name='login'),
    path('logout/', views.portal_logout, name='logout'),
    path('bookings/', views.my_bookings, name='bookings'),
    path('my-bookings/', views.my_bookings, name='my_bookings'),
    path('bookings/<int:booking_id>/', views.portal_booking_detail, name='booking_detail'),
    path('booking/<int:booking_id>/live/', views.customer_portal_booking_live, name='booking_live'),
    path('booking/<int:booking_id>/invoice/', views.customer_portal_booking_invoice, name='booking_invoice'),
    path('documents/', views.my_documents, name='documents'),
]

