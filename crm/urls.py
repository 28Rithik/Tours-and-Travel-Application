from django.urls import path
from . import views

app_name = 'crm'

urlpatterns = [
    # Query Tracker 2.0 Pipeline
    path('queries/', views.inquiry_pipeline_view, name='inquiry_pipeline'),
    path('inquiries/', views.inquiry_pipeline_view, name='inquiries_alias'),
    
    # Phase 6: Visual Drag-and-Drop CRM Kanban Board & Lead Follow-Up Hub
    path('kanban/', views.crm_kanban_board_view, name='kanban_board'),
    path('api/inquiries/<int:inquiry_id>/update-stage/', views.api_inquiry_update_stage, name='api_inquiry_update_stage'),
    path('api/inquiries/<int:inquiry_id>/quick-followup/', views.api_inquiry_quick_followup, name='api_inquiry_quick_followup'),
    path('api/inquiries/<int:inquiry_id>/convert-to-booking/', views.api_inquiry_convert_to_booking, name='api_inquiry_convert_to_booking'),
    path('api/inquiries/<int:inquiry_id>/dispatch-whatsapp/', views.api_inquiry_dispatch_whatsapp, name='api_inquiry_dispatch_whatsapp'),
    path('api/kanban-data/', views.api_crm_kanban_data, name='api_crm_kanban_data'),

    # Phase 6 Power-Ups: Notification Bell
    path('api/notifications/poll/', views.api_notifications_poll, name='api_notifications_poll'),
    path('api/notifications/mark-read/', views.api_notifications_mark_read, name='api_notifications_mark_read'),

    # Phase 6 Power-Ups: Objection Management & TAT Analytics
    path('api/inquiries/<int:inquiry_id>/log-objection/', views.api_inquiry_log_objection, name='api_inquiry_log_objection'),
    path('api/tat-dashboard/', views.api_tat_dashboard, name='api_tat_dashboard'),

    # Phase 6 Power-Ups: Clone Record & Mass Ownership Transfer
    path('api/inquiries/<int:inquiry_id>/clone/', views.api_inquiry_clone, name='api_inquiry_clone'),
    path('api/inquiries/mass-reassign/', views.api_inquiry_mass_reassign, name='api_inquiry_mass_reassign'),

    # Quotation Studio & Builder
    path('quotations/new/', views.quotation_builder_view, name='quotation_create'),
    path('quotations/<int:quotation_id>/edit/', views.quotation_builder_view, name='quotation_builder'),
    path('quotations/<int:quotation_id>/preview/', views.quotation_preview_view, name='quotation_preview'),
    path('quotations/<int:quotation_id>/send/', views.quotation_send_to_client_action, name='quotation_send'),
    path('quotations/<int:quotation_id>/convert-to-booking/', views.quotation_convert_to_booking_view, name='quotation_convert'),
    path('quotations/<int:quotation_id>/revision/', views.quotation_create_revision_view, name='quotation_revision'),

    # AJAX Endpoints for Builder
    path('api/quotations/<int:quotation_id>/add-day/', views.quotation_add_day_api, name='api_quotation_add_day'),
    path('api/quotations/<int:quotation_id>/add-item/', views.quotation_add_item_api, name='api_quotation_add_item'),
    path('api/quotations/items/<int:item_id>/delete/', views.quotation_delete_item_api, name='api_quotation_delete_item'),
    path('api/master-data/lookup/', views.api_master_data_lookup, name='api_master_lookup'),

    # Phase B: Partner & B2C Management
    path('partners/', views.partner_management_view, name='partner_list'),

    # Phase B: Supplier Master & Contracted Rates
    path('suppliers/', views.supplier_management_view, name='supplier_list'),

    # Phase B: Supplier Service Vouchers & Extranet
    path('vouchers/', views.voucher_console_view, name='voucher_console'),
    path('vouchers/create/', views.voucher_create_view, name='voucher_create'),
    path('vouchers/<int:voucher_id>/', views.voucher_detail_view, name='voucher_detail'),
    path('vouchers/<int:voucher_id>/issue/', views.voucher_issue_action, name='voucher_issue'),
    path('vouchers/extranet/<str:token>/', views.supplier_extranet_voucher_view, name='supplier_extranet_voucher'),

    # Phase C: Executive DMC Business Dashboard & Task Management
    path('dashboard/', views.dmc_executive_dashboard_view, name='dashboard'),
    path('api/tasks/create/', views.task_create_api, name='api_task_create'),
    path('api/tasks/<int:task_id>/toggle/', views.task_toggle_status_api, name='api_task_toggle'),

    # Phase D: Master Documents & Marketing Vault
    path('documents/', views.dmc_documents_view, name='document_vault'),
    path('api/documents/upload/', views.dmc_document_upload_api, name='api_document_upload'),

    # Phase D: Complaint & Service Quality Management
    path('complaints/', views.complaints_console_view, name='complaint_list'),
    path('complaints/lodge/', views.complaint_lodge_view, name='complaint_lodge'),
    path('api/complaints/<int:complaint_id>/resolve/', views.complaint_resolve_api, name='api_complaint_resolve'),

    # Phase D: Accounts Payable & Supplier Payment Requisitions
    path('requisitions/', views.payment_requisition_console_view, name='requisition_list'),
    path('requisitions/create/', views.payment_requisition_create_view, name='requisition_create'),
    path('api/requisitions/<int:req_id>/update-status/', views.payment_requisition_status_api, name='api_requisition_status'),

    # Phase D: Client Pending Payments Aging Report & Balance WhatsApp Reminders
    path('reports/client-pending-payments/', views.client_pending_payments_report_view, name='client_pending_payments'),
    path('api/reports/send-payment-reminder/', views.send_client_payment_reminder_api, name='api_send_payment_reminder'),

    # Phase E: Proforma & Tax Invoicing Suite
    path('invoices/', views.dmc_invoice_console_view, name='invoice_console'),
    path('invoices/create/', views.dmc_invoice_create_view, name='invoice_create'),
    path('invoices/<int:invoice_id>/', views.dmc_invoice_detail_view, name='invoice_detail'),
    path('api/invoices/<int:invoice_id>/dispatch/', views.dmc_invoice_dispatch_api, name='api_invoice_dispatch'),
    path('api/invoices/<int:invoice_id>/record-payment/', views.api_record_invoice_payment, name='api_record_invoice_payment'),

    # Phase E: DMC Comprehensive Reports & Analytics Hub
    path('reports/', views.dmc_reports_hub_view, name='reports_hub'),

    # Phase 6: TutterflyCRM Power-Up APIs
    path('api/notifications/poll/', views.api_notifications_poll, name='api_notifications_poll'),
    path('api/notifications/mark-read/', views.api_notifications_mark_read, name='api_notifications_mark_read'),
    path('api/inquiries/<int:inquiry_id>/log-objection/', views.api_inquiry_log_objection, name='api_inquiry_log_objection'),
    path('api/inquiries/mass-reassign/', views.api_inquiry_mass_reassign, name='api_inquiry_mass_reassign'),
    path('api/inquiries/<int:inquiry_id>/clone/', views.api_inquiry_clone, name='api_inquiry_clone'),
    path('api/tat-dashboard/', views.api_tat_dashboard, name='api_tat_dashboard'),

    # Phase 6: Extended Power-Ups (Social Lead Ingestion, 360 Profile Enhancer, Tenant Admin)
    path('webhooks/social-lead/', views.api_social_lead_webhook, name='api_social_lead_webhook'),
    path('api/profile-enhancer/<int:party_id>/', views.api_profile_enhancer, name='api_profile_enhancer'),
    path('tenant-admin/logs/', views.tenant_admin_logs_view, name='tenant_admin_logs'),
    path('api/tenant-admin/logs/', views.api_tenant_admin_logs, name='api_tenant_admin_logs'),
    path('api/tenant-admin/user/update/', views.api_tenant_admin_user_update, name='api_tenant_admin_user_update'),
    path('api/sample-records/generate/', views.api_sample_records_generate, name='api_sample_records_generate'),
    path('api/sample-records/clean/', views.api_sample_records_clean, name='api_sample_records_clean'),
]
