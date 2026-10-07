from django.urls import path
from . import views

app_name = 'marketing'

urlpatterns = [
    path('campaign-studio/', views.campaign_studio_view, name='campaign-studio'),
    path('api/audience-count/', views.api_audience_count, name='api-audience-count'),
    path('api/campaign/create/', views.api_create_campaign, name='api-campaign-create'),
]
