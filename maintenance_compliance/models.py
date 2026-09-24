from django.db import models
from maintenance.models import (
    ComplianceDocument as BaseComplianceDocument,
    InsuranceClaim as BaseInsuranceClaim,
)


class ComplianceDocument(BaseComplianceDocument):
    class Meta:
        proxy = True
        app_label = 'maintenance_compliance'
        verbose_name = 'Compliance Document'
        verbose_name_plural = 'Compliance Documents'


class InsuranceClaim(BaseInsuranceClaim):
    class Meta:
        proxy = True
        app_label = 'maintenance_compliance'
        verbose_name = 'Insurance Claim'
        verbose_name_plural = 'Insurance Claims'
