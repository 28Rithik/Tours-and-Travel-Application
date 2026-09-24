from django.db import models

# ==========================================================================
#  Proxy Models — Suppliers
# ==========================================================================
from suppliers.models import SupplierContract as OriginalSupplierContract
from suppliers.models import CommissionRule as OriginalCommissionRule


class SupplierContractProxy(OriginalSupplierContract):
    class Meta:
        proxy = True
        app_label = 'enterprise_governance'
        verbose_name = 'Supplier Contract'
        verbose_name_plural = 'Supplier Contracts'


class CommissionRuleProxy(OriginalCommissionRule):
    class Meta:
        proxy = True
        app_label = 'enterprise_governance'
        verbose_name = 'Commission Rule'
        verbose_name_plural = 'Commission Rules'


# ==========================================================================
#  Proxy Models — Audit
# ==========================================================================
from audit.models import AuditLogEntry as OriginalAuditLogEntry


class AuditLogEntryProxy(OriginalAuditLogEntry):
    class Meta:
        proxy = True
        app_label = 'enterprise_governance'
        verbose_name = 'Audit Log Entry'
        verbose_name_plural = 'Audit Log Entries'
