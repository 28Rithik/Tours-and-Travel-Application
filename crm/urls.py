from django.urls import path
from . import views

app_name = 'crm'

urlpatterns = [
    # Query Tracker 2.0 Pipeline
    path('queries/', views.inquiry_pipeline_view, name='inquiry_pipeline'),
    path('inquiries/', views.inquiry_pipeline_view, name='inquiries_alias'),
    
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

    # Phase E: DMC Comprehensive Reports & Analytics Hub
    path('reports/', views.dmc_reports_hub_view, name='reports_hub'),
]
