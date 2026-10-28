"""
URL configuration for travelerp project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
"""

from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.views.generic import RedirectView
from django.http import HttpResponse
from django.conf import settings
from django.conf.urls.static import static

from statements.views import download_statement, generate_statement
from maintenance.views import (
    damage_marker_studio_view,
    damage_inspection_print_certificate,
    tire_studio_view,
    workshop_mechanic_studio_view,
    parts_inventory_studio_view,
    api_issue_part_to_jobcard,
    api_receive_part_stock,
)
from finance.views import (
    api_payment_context,
    admin_gst_studio_view,
    api_generate_corporate_invoice_eway,
    api_export_nic_eway_json,
    corporate_invoice_print_view,
    corporate_invoice_pdf_view,
    api_dispatch_corporate_invoice_whatsapp,
    admin_petty_cash_studio_view,
    driver_mobile_wallet_view,
    admin_bank_reconciliation_studio_view,
    api_bank_reconciliation_upload,
    api_bank_reconciliation_reconcile_entry,
    api_bank_reconciliation_batch,
    export_bank_reconciliation_report_view,
    admin_driver_settlement_studio_view,
    api_trip_settlement_context,
    api_execute_driver_settlement,
    driver_settlement_voucher_view,
    api_driver_settlement_acknowledge,
    fuel_receipt_ocr_studio_view,
    api_fuel_receipt_ocr,
    api_fuel_receipt_approve,
    fastag_reconciliation_studio_view,
    api_fastag_parse_statement,
    api_fastag_reconcile_approve,
    tds_194c_ledger_view,
)
from driver_portal.views import pwa_manifest, pwa_service_worker
from travelerp.views import (
    dashboard,
    party_ledger,
    party_profitability_report,
    vehicle_profitability_report,
    switch_persona_view,
    staff_roles_matrix_view,
    health_check,
    robots_txt,
    sitemap_xml,
)
from payments_gateway.views import (
    admin_payment_studio_view,
    api_generate_dynamic_upi,
    api_direct_upi_confirm,
    api_simulate_payment_webhook,
    api_payment_studio_metrics,
)
from crm.views import (
    crm_kanban_board_view,
    public_digital_proposal_view,
    api_proposal_upi_confirm,
    public_proposal_brochure_pdf_view,
    feedback_reviews_hub_view,
    guest_trip_feedback_view,
    api_submit_guest_feedback,
    api_generate_feedback_link,
    api_feedback_seed,
    api_google_review_clicked,
    followup_cadence_studio_view,
)
from suppliers.views import (
    vendor_bill_audit_studio_view,
    api_vendor_bill_audit_calculate,
    api_vendor_bill_audit_approve,
    api_vendor_bill_seed,
)
from customer_portal.views import public_landing_view
from integrations import views as integrations_views
from fleet_commute import views as fleet_commute_views

urlpatterns = [
    # Health Check (lightweight — safe for Docker/LB probes, no auth required)
    path('health/', health_check, name='health-check'),
    path('', public_landing_view, name='public-landing'),

    # Modularized Operations App & Core App Routes
    path('', include('operations.urls')),
    path('', include('core.urls')),

    # 2D Interactive Vehicle Damage Marker & Inspection Studio
    path('admin/maintenance/damage-marker/', damage_marker_studio_view, name='admin-damage-marker-studio'),

    # Unfold Admin Dynamic UPI & Payment Gateway Studio
    path('admin/finance/payment-studio/', admin_payment_studio_view, name='admin-payment-studio'),
    path('admin/payments/studio/', admin_payment_studio_view, name='admin-payments-studio-alias'),
    path('finance/payments/', admin_payment_studio_view, name='finance-payments-studio'),
    path('finance/payments-studio/', admin_payment_studio_view, name='finance-payments-studio-alias'),
    path('payments/', admin_payment_studio_view, name='payments-root-alias'),
    path('api/payments/dynamic-upi/generate/', api_generate_dynamic_upi, name='api-dynamic-upi-generate'),
    path('api/payments/direct-upi/confirm/', api_direct_upi_confirm, name='api-direct-upi-confirm'),
    path('api/payments/simulate-webhook/', api_simulate_payment_webhook, name='api-simulate-payment-webhook'),
    path('api/payments/studio-metrics/', api_payment_studio_metrics, name='api-payment-studio-metrics'),

    # Corporate GST B2B Invoicing & NIC E-Way Bill Studio
    path('finance/gst-studio/', admin_gst_studio_view, name='finance-gst-studio'),
    path('admin/finance/gst-studio/', admin_gst_studio_view, name='admin-gst-studio'),
    path('admin/gst-studio/', admin_gst_studio_view, name='admin-gst-studio-alias'),
    path('api/finance/generate-invoice-ewaybill/', api_generate_corporate_invoice_eway, name='api-finance-generate-invoice-ewaybill'),
    path('api/finance/invoice/<int:invoice_id>/eway-json/', api_export_nic_eway_json, name='api-finance-export-eway-json'),
    path('api/finance/invoice/<int:invoice_id>/whatsapp/', api_dispatch_corporate_invoice_whatsapp, name='api-finance-invoice-whatsapp-direct'),
    path('finance/invoice/<int:invoice_id>/view/', corporate_invoice_print_view, name='finance-corporate-invoice-view'),
    path('finance/invoice/<int:invoice_id>/pdf/', corporate_invoice_pdf_view, name='corporate-invoice-pdf'),

    # Petty Cash Float Register & Driver/Tour Manager Cash Wallet Studio
    path('admin/finance/petty-cash-studio/', admin_petty_cash_studio_view, name='admin-petty-cash-studio'),
    path('admin/petty-cash/', admin_petty_cash_studio_view, name='admin-petty-cash-alias'),
    path('finance/petty-cash-studio/', admin_petty_cash_studio_view, name='finance-petty-cash-studio-alias'),
    path('finance/petty-cash/', admin_petty_cash_studio_view, name='finance-petty-cash-alias'),
    path('driver/wallet/', driver_mobile_wallet_view, name='driver-mobile-wallet'),

    # Highway Fuel Receipt OCR & Bunk Verification Studio
    path('finance/fuel-receipt-ocr/', fuel_receipt_ocr_studio_view, name='fuel-receipt-ocr-studio'),
    path('admin/finance/fuel-receipt-ocr/', fuel_receipt_ocr_studio_view, name='admin-fuel-receipt-ocr'),
    path('api/finance/fuel-receipt-ocr/', api_fuel_receipt_ocr, name='api-finance-fuel-receipt-ocr'),
    path('api/finance/fuel-receipt-approve/', api_fuel_receipt_approve, name='api-finance-fuel-receipt-approve'),

    # Automated NHAI FASTag CSV Statement Reconciler & Toll Plaza Auditor
    path('finance/fastag-reconciliation/', fastag_reconciliation_studio_view, name='finance-fastag-reconciliation'),
    path('admin/finance/fastag-reconciliation/', fastag_reconciliation_studio_view, name='admin-fastag-reconciliation'),
    path('api/finance/fastag-reconciliation/parse/', api_fastag_parse_statement, name='api-finance-fastag-parse'),
    path('api/finance/fastag-reconciliation/approve/', api_fastag_reconcile_approve, name='api-finance-fastag-approve'),

    # Market Fleet Vendor Bill Auditor & Reconciliation Studio
    path('suppliers/vendor-bill-audit/', vendor_bill_audit_studio_view, name='suppliers-vendor-bill-audit'),
    path('admin/suppliers/vendor-bill-audit/', vendor_bill_audit_studio_view, name='admin-suppliers-vendor-bill-audit'),
    path('api/suppliers/vendor-bill-audit/calculate/', api_vendor_bill_audit_calculate, name='api-suppliers-vendor-bill-audit-calculate'),
    path('api/suppliers/vendor-bill-audit/approve/', api_vendor_bill_audit_approve, name='api-suppliers-vendor-bill-audit-approve'),
    path('api/suppliers/vendor-bill-audit/seed/', api_vendor_bill_seed, name='api-suppliers-vendor-bill-audit-seed'),

    # Post-Trip Customer Feedback & Google Review Conversion Engine
    path('crm/feedback-reviews/', feedback_reviews_hub_view, name='crm-feedback-reviews'),
    path('admin/crm/feedback-reviews/', feedback_reviews_hub_view, name='admin-crm-feedback-reviews'),
    path('guest/feedback/<str:token>/', guest_trip_feedback_view, name='guest-trip-feedback'),
    path('api/crm/feedback/submit/', api_submit_guest_feedback, name='api-crm-feedback-submit'),
    path('api/crm/feedback/generate-token/<int:trip_id>/', api_generate_feedback_link, name='api-crm-feedback-generate-token'),
    path('api/crm/feedback/google-clicked/<str:token>/', api_google_review_clicked, name='api-crm-feedback-google-clicked'),
    path('api/crm/feedback/seed/', api_feedback_seed, name='api-crm-feedback-seed'),

    # Spare Parts & Workshop Consumables Store Inventory Studio
    path('maintenance/parts-inventory/', parts_inventory_studio_view, name='maintenance-parts-inventory'),
    path('admin/maintenance/parts-inventory/', parts_inventory_studio_view, name='admin-maintenance-parts-inventory'),
    path('api/maintenance/parts-inventory/issue/', api_issue_part_to_jobcard, name='api-maintenance-parts-issue'),
    path('api/maintenance/parts-inventory/receive/', api_receive_part_stock, name='api-maintenance-parts-receive'),

    # Automated CRM WhatsApp Follow-up Drip Cadence Studio
    path('crm/followup-cadence/', followup_cadence_studio_view, name='crm-followup-cadence'),
    path('admin/crm/followup-cadence/', followup_cadence_studio_view, name='admin-crm-followup-cadence'),

    # Section 194C TDS Corporate Withholding Management Ledger
    path('finance/tds-194c/', tds_194c_ledger_view, name='finance-tds-194c'),
    path('admin/finance/tds-194c/', tds_194c_ledger_view, name='admin-finance-tds-194c'),

    # Automated Bank Statement CSV Reconciler & UTR Matching Studio
    path('admin/finance/bank-reconciliation/', admin_bank_reconciliation_studio_view, name='admin-bank-reconciliation-studio'),
    path('admin/bank-reconciliation/', admin_bank_reconciliation_studio_view, name='admin-bank-reconciliation-alias'),
    path('finance/bank-reconciliation/', admin_bank_reconciliation_studio_view, name='bank-reconciliation-portal'),
    path('finance/bank-reconciliation/export/', export_bank_reconciliation_report_view, name='export-bank-reconciliation'),
    path('api/finance/bank-reconciliation/upload/', api_bank_reconciliation_upload, name='api-finance-bank-reconciliation-upload'),
    path('api/finance/bank-reconciliation/reconcile/<int:entry_id>/', api_bank_reconciliation_reconcile_entry, name='api-finance-bank-reconciliation-reconcile'),
    path('api/finance/bank-reconciliation/batch/', api_bank_reconciliation_batch, name='api-finance-bank-reconciliation-batch'),

    # Automated Driver Settlement & 1-Click Payout Studio
    path('admin/finance/driver-settlement/', admin_driver_settlement_studio_view, name='admin-driver-settlement-studio'),
    path('finance/driver-settlement/', admin_driver_settlement_studio_view, name='finance-driver-settlement-root'),
    path('finance/driver-settlement-studio/', admin_driver_settlement_studio_view, name='finance-driver-settlement-studio'),
    path('finance/settlement-studio/', admin_driver_settlement_studio_view, name='finance-settlement-studio-alias'),
    path('finance/settlement/<int:settlement_id>/voucher/', driver_settlement_voucher_view, name='finance-driver-settlement-voucher-root'),
    path('api/finance/settle/<int:trip_id>/context/', api_trip_settlement_context, name='api-finance-settle-context-root'),
    path('api/finance/settle/<int:trip_id>/', api_execute_driver_settlement, name='api-finance-settle-execute-root'),
    path('api/finance/settlement/<int:settlement_id>/acknowledge/', api_driver_settlement_acknowledge, name='api-finance-settle-acknowledge-root'),

    # Visual Drag-and-Drop CRM Kanban Board & Lead Follow-Up Hub
    path('admin/crm/kanban/', crm_kanban_board_view, name='admin-crm-kanban'),
    path('admin/kanban/', crm_kanban_board_view, name='admin-crm-kanban-alias'),
    path('crm/kanban/', crm_kanban_board_view, name='crm-kanban-portal-alias'),
    path('kanban/', crm_kanban_board_view, name='kanban-root-alias'),

    # Interactive Customer Digital Proposal & Dynamic UPI Auto-Conversion
    path('quote/<str:token>/', public_digital_proposal_view, name='public-digital-proposal'),
    path('quote/<str:token>/brochure.pdf', public_proposal_brochure_pdf_view, name='public-proposal-brochure-pdf'),
    path('quote/<str:token>/confirm/', api_proposal_upi_confirm, name='api-proposal-upi-confirm'),

    # 2D Axle & Tire Health Studio + Fleet PM Engine
    path('admin/maintenance/tire-studio/', tire_studio_view, name='admin-tire-studio'),
    path('admin/tire-studio/', tire_studio_view, name='admin-tire-studio-alias'),
    path('maintenance/tire-studio/', tire_studio_view, name='maintenance-tire-studio-portal'),

    # Workshop Mechanic Studio & QR Barcode Spare Parts Checkout
    path('admin/maintenance/workshop/', workshop_mechanic_studio_view, name='admin-workshop-studio'),
    path('admin/workshop-studio/', workshop_mechanic_studio_view, name='admin-workshop-studio-alias'),
    path('maintenance/workshop/', workshop_mechanic_studio_view, name='maintenance-workshop-studio'),
    path('maintenance/workshop-studio/', workshop_mechanic_studio_view, name='maintenance-workshop-studio-alias'),

    # Omnichannel Integrations Hub, Meta Webhook, Email SES/SMTP Studio, Agent Dashboard & Approvals
    path('admin/integrations/', include('integrations.urls')),
    path('api/integrations/meta/webhook/', integrations_views.api_meta_lead_webhook, name='api_meta_lead_webhook_root'),
    path('api/integrations/meta/simulate/', integrations_views.api_meta_lead_simulate, name='api_meta_lead_simulate_root'),
    path('api/integrations/google-sheets/sync/', integrations_views.api_google_sheet_sync, name='api_google_sheet_sync_root'),
    path('api/integrations/email/test/', integrations_views.api_test_email, name='api_test_email_root'),

    # Progressive Web App (PWA) root manifest and service worker
    path('manifest.json', pwa_manifest, name='pwa-manifest'),
    path('sw.js', pwa_service_worker, name='pwa-sw'),

    # Fleet Profitability & Cost-Per-KM (CPK) Optimization Radar Studio
    path('', include('finance_fleet.urls')),

    # Aliases and redirects for Package Tours Friendly URLs
    path('admin/package_tours/tourbusdeparturebatch/', RedirectView.as_view(url='/admin/package_tours/tourdeparturebatchproxy/', permanent=False)),
    path('admin/package_tours/tourbusdeparturebatch/<path:subpath>', RedirectView.as_view(url='/admin/package_tours/tourdeparturebatchproxy/%(subpath)s', permanent=False)),
    path('admin/package_tours/passengermanifest/', RedirectView.as_view(url='/admin/package_tours/passengermanifestproxy/', permanent=False)),
    path('admin/package_tours/passengermanifest/<path:subpath>', RedirectView.as_view(url='/admin/package_tours/passengermanifestproxy/%(subpath)s', permanent=False)),
    path('admin/package_tours/boardingpoint/', RedirectView.as_view(url='/admin/package_tours/boardingpointproxy/', permanent=False)),
    path('admin/package_tours/boardingpoint/<path:subpath>', RedirectView.as_view(url='/admin/package_tours/boardingpointproxy/%(subpath)s', permanent=False)),
    path('admin/package_tours/collegeiv/', RedirectView.as_view(url='/packages/?tab=expeditions', permanent=False)),
    path('admin/package_tours/collegeivproxy/', RedirectView.as_view(url='/packages/?tab=expeditions', permanent=False)),
    path('admin/fleet_commute/corporatecontract/', RedirectView.as_view(url='/commute/contracts/?tab=contracts', permanent=False)),
    path('admin/fleet_commute/corporatecommuteroute/', RedirectView.as_view(url='/commute/contracts/?tab=routes', permanent=False)),
    path('admin/fleet_commute/corporatecommuteshift/', RedirectView.as_view(url='/commute/contracts/?tab=shifts', permanent=False)),
    path('admin/fleet_contracts/transportcontract/', RedirectView.as_view(url='/commute/contracts/?tab=contracts', permanent=False)),
    path('admin/pricing/', RedirectView.as_view(url='/pricing/', permanent=False)),

    # Arattai Inbound Webhook
    path('api/integrations/arattai/webhook/', integrations_views.arattai_inbound_webhook_view, name='api_arattai_webhook_root'),

    # Django Admin & Staff Auth
    path('admin/', admin.site.urls),
    path('staff/login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('staff/logout/', auth_views.LogoutView.as_view(next_page='/staff/login/'), name='staff_logout'),
    path('staff-login/', RedirectView.as_view(url='/staff/login/', permanent=False)),
    path('login/', RedirectView.as_view(url='/staff/login/', permanent=False)),
    path('logout/', auth_views.LogoutView.as_view(next_page='/staff/login/'), name='logout'),
    path('core/vehicles/', RedirectView.as_view(url='/fleet/vehicles/', permanent=False)),
    path('corporate/', RedirectView.as_view(url='/client/portal/', permanent=False)),

    # Corporate Commute Contracts & Shuttle Routes Studio (Staff Portal with sidebar)
    path('commute/contracts/', fleet_commute_views.contracts_studio_view, name='commute-contracts-studio'),

    path('dashboard/', dashboard, name='dashboard'),
    path('auth/switch-persona/<str:username>/', switch_persona_view, name='auth-switch-persona'),
    path('staff/roles-matrix/', staff_roles_matrix_view, name='staff-roles-matrix'),
    path('roles/', staff_roles_matrix_view, name='roles-matrix-alias'),
    path('staff/', staff_roles_matrix_view, name='staff-directory-alias'),

    # Inspection certificate print
    path('maintenance/damage-inspection/<int:inspection_id>/print/', damage_inspection_print_certificate, name='damage_inspection_print'),

    path('api/payments/context/', api_payment_context, name='api_payment_context'),
    path('parties/<int:party_id>/ledger/', party_ledger, name='party-ledger'),
    path('statements/generate/', generate_statement, name='generate-statement'),
    path('statements/<int:statement_id>/download/', download_statement, name='download-statement'),
    path('reports/vehicle-profitability/', vehicle_profitability_report, name='vehicle-profitability'),
    path('reports/party-profitability/', party_profitability_report, name='party-profitability'),

    # Operations & Packages HTMX Includes
    path('htmx/', include('operations.htmx_urls')),
    path('packages/htmx/', include('packages.htmx_urls')),

    # Other App Route Includes
    path('finance/', include('finance.urls')),
    path('maintenance/', include('maintenance.urls')),
    path('driver/', include('driver_portal.urls')),
    path('commute/', include('fleet_commute.urls')),
    path('client/login/', fleet_commute_views.client_portal_login_view, name='client_portal_root_login'),
    path('client/logout/', fleet_commute_views.client_portal_logout_view, name='client_portal_root_logout'),
    path('client/api/sso/lookup-domain/', fleet_commute_views.api_sso_domain_lookup, name='client_portal_root_sso_domain_lookup'),
    path('client/sso/<slug:brand_slug>/login/', fleet_commute_views.client_sso_initiate_view, name='client_portal_root_sso_initiate'),
    path('client/sso/<slug:brand_slug>/callback/', fleet_commute_views.client_sso_callback_view, name='client_portal_root_sso_callback'),
    path('client/brand/<slug:brand_slug>/', fleet_commute_views.client_branded_login_view, name='client_portal_root_branded_login'),
    path('client/portal/', include([
        path('', fleet_commute_views.client_portal_index_view, name='client_portal_root_index'),
        path('<int:contract_id>/', fleet_commute_views.client_transparency_portal_view, name='client_portal_root_contract'),
        path('<int:contract_id>/api/live-fleet/', fleet_commute_views.api_client_portal_live_fleet, name='client_portal_root_live_fleet'),
        path('<int:contract_id>/roster/add/', fleet_commute_views.api_client_roster_add, name='client_portal_root_roster_add'),
        path('<int:contract_id>/roster/swap-shift/', fleet_commute_views.api_client_roster_swap, name='client_portal_root_roster_swap'),
        path('<int:contract_id>/roster/import-csv/', fleet_commute_views.api_client_roster_import_csv, name='client_portal_root_roster_import_csv'),
        path('<int:contract_id>/roster/export-csv/', fleet_commute_views.client_roster_export_csv, name='client_portal_root_roster_export_csv'),
        path('<int:contract_id>/sla/dispute/', fleet_commute_views.api_client_dispute_sla_penalty, name='client_portal_root_sla_dispute'),
        path('<int:contract_id>/invoice/<int:invoice_id>/', fleet_commute_views.client_invoice_pdf_view, name='client_portal_root_invoice_pdf'),
        path('<int:contract_id>/esg/certificate/', fleet_commute_views.client_esg_certificate_view, name='client_portal_root_esg_certificate'),
        path('<int:contract_id>/api/switch-role/', fleet_commute_views.api_switch_corporate_role, name='client_portal_root_switch_role'),
        path('<int:contract_id>/api/unmask-commuter/', fleet_commute_views.api_unmask_commuter_pii, name='client_portal_root_unmask_commuter'),
    ])),
    path('client-portal/', include([
        path('', fleet_commute_views.client_portal_index_view),
        path('login/', fleet_commute_views.client_portal_login_view),
        path('logout/', fleet_commute_views.client_portal_logout_view),
        path('<int:contract_id>/', fleet_commute_views.client_transparency_portal_view),
        path('<int:contract_id>/invoice/<int:invoice_id>/', fleet_commute_views.client_invoice_pdf_view),
        path('<int:contract_id>/esg/certificate/', fleet_commute_views.client_esg_certificate_view),
        path('<int:contract_id>/api/live-fleet/', fleet_commute_views.api_client_portal_live_fleet),
        path('<int:contract_id>/roster/add/', fleet_commute_views.api_client_roster_add),
        path('<int:contract_id>/roster/swap-shift/', fleet_commute_views.api_client_roster_swap),
        path('<int:contract_id>/roster/import-csv/', fleet_commute_views.api_client_roster_import_csv),
        path('<int:contract_id>/roster/export-csv/', fleet_commute_views.client_roster_export_csv),
        path('<int:contract_id>/sla/dispute/', fleet_commute_views.api_client_dispute_sla_penalty),
        path('<int:contract_id>/api/switch-role/', fleet_commute_views.api_switch_corporate_role),
        path('<int:contract_id>/api/unmask-commuter/', fleet_commute_views.api_unmask_commuter_pii),
        path('brand/<slug:brand_slug>/', fleet_commute_views.client_branded_login_view),
        path('sso/<slug:brand_slug>/login/', fleet_commute_views.client_sso_initiate_view),
        path('sso/<slug:brand_slug>/callback/', fleet_commute_views.client_sso_callback_view),
        path('api/sso/lookup-domain/', fleet_commute_views.api_sso_domain_lookup),
    ])),
    path('packages/', include('packages.urls')),
    path('customer-portal/', include('customer_portal.urls')),
    path('customer/login/', RedirectView.as_view(url='/customer-portal/login/', permanent=False), name='customer-login-alias'),
    path('customer/', RedirectView.as_view(url='/customer-portal/', permanent=False), name='customer-home-alias'),
    path('payments/', include('payments_gateway.urls')),
    path('analytics/', include('analytics.urls')),
    path('crm/', include('crm.urls')),
    path('suppliers/', include('suppliers.urls')),
    path('marketing/', include('marketing.urls')),
    path('i18n/', include('django.conf.urls.i18n')),
    path('favicon.ico', lambda r: HttpResponse(status=204, content_type='image/x-icon')),
    path('robots.txt', robots_txt, name='robots-txt'),
    path('sitemap.xml', sitemap_xml, name='sitemap-xml'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
