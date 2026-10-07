from django.urls import path
from . import views

app_name = 'payments_gateway'

urlpatterns = [
    path('webhook/razorpay/', views.razorpay_webhook, name='razorpay_webhook'),
    path('webhook/cashfree/', views.cashfree_webhook, name='cashfree_webhook'),
    path('direct-upi/confirm/', views.api_direct_upi_confirm, name='direct_upi_confirm'),
    path('dynamic-upi/generate/', views.api_generate_dynamic_upi, name='dynamic_upi_generate'),
    path('simulate-webhook/', views.api_simulate_payment_webhook, name='simulate_payment_webhook'),
    path('studio-metrics/', views.api_payment_studio_metrics, name='payment_studio_metrics'),
]
