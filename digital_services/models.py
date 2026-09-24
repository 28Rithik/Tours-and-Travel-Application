from django.db import models

# ==========================================================================
#  Proxy Models — Payments Gateway
# ==========================================================================
from payments_gateway.models import InstallmentPlan as OriginalInstallmentPlan
from payments_gateway.models import PaymentLink as OriginalPaymentLink
from payments_gateway.models import PaymentWebhookEvent as OriginalPaymentWebhookEvent


class InstallmentPlanProxy(OriginalInstallmentPlan):
    class Meta:
        proxy = True
        app_label = 'digital_services'
        verbose_name = 'Installment Plan'
        verbose_name_plural = 'Installment Plans'


class PaymentLinkProxy(OriginalPaymentLink):
    class Meta:
        proxy = True
        app_label = 'digital_services'
        verbose_name = 'Payment Link'
        verbose_name_plural = 'Payment Links'


class PaymentWebhookEventProxy(OriginalPaymentWebhookEvent):
    class Meta:
        proxy = True
        app_label = 'digital_services'
        verbose_name = 'Payment Webhook Event'
        verbose_name_plural = 'Payment Webhook Events'


# ==========================================================================
#  Proxy Models — Customer Portal
# ==========================================================================
from customer_portal.models import CustomerAccount as OriginalCustomerAccount


class CustomerAccountProxy(OriginalCustomerAccount):
    class Meta:
        proxy = True
        app_label = 'digital_services'
        verbose_name = 'Customer Account'
        verbose_name_plural = 'Customer Accounts'


# ==========================================================================
#  Proxy Models — Documents
# ==========================================================================
from documents.models import CustomerDocument as OriginalCustomerDocument


class CustomerDocumentProxy(OriginalCustomerDocument):
    class Meta:
        proxy = True
        app_label = 'digital_services'
        verbose_name = 'Customer Document'
        verbose_name_plural = 'Customer Documents'
