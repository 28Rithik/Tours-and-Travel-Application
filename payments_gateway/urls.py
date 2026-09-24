from django.urls import path
from . import views

app_name = 'payments_gateway'

urlpatterns = [
    path('webhook/razorpay/', views.razorpay_webhook, name='razorpay_webhook'),
]
