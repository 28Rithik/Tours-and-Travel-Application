from django.urls import path
from . import views

app_name = 'integrations'

urlpatterns = [
    # Image 1: Main Integrations Hub
    path('', views.integrations_hub_view, name='hub'),
    path('hub/', views.integrations_hub_view, name='hub_alias'),

    # Image 2: Email (SES / SMTP) Studio & Test Verification
    path('email/', views.email_service_studio_view, name='email_studio'),
    path('email/test/', views.api_test_email, name='email_test_direct'),
    path('api/email/test/', views.api_test_email, name='api_test_email'),

    # Meta Lead Ads (Facebook & Instagram Webhook Ingestion)
    path('meta/webhook/', views.api_meta_lead_webhook, name='meta_webhook_direct'),
    path('api/meta/webhook/', views.api_meta_lead_webhook, name='api_meta_lead_webhook'),
    path('meta/simulate/', views.api_meta_lead_simulate, name='meta_simulate_direct'),
    path('api/meta/simulate/', views.api_meta_lead_simulate, name='api_meta_lead_simulate'),

    # Google Sheets 5-Minute Auto-Import
    path('google-sheets/sync/', views.api_google_sheet_sync, name='google_sheets_sync_direct'),
    path('api/google-sheets/sync/', views.api_google_sheet_sync, name='api_google_sheet_sync'),

    # Left Sidebar Feature 1: Agent Dashboard
    path('agent-dashboard/', views.agent_dashboard_view, name='agent_dashboard'),

    # Left Sidebar Feature 2: Manager Approvals Module
    path('approvals/', views.manager_approvals_view, name='manager_approvals'),
    path('approvals/<int:approval_id>/action/', views.api_action_approval, name='api_action_approval'),

    # Zoho Arattai Business Webhook
    path('arattai/webhook/', views.arattai_inbound_webhook_view, name='arattai_webhook'),
    path('api/arattai/webhook/', views.arattai_inbound_webhook_view, name='api_arattai_webhook'),
]
