from django.contrib import admin
from .models import SupplierContract, CommissionRule

# ──────────────────────────────────────────────────────────────────────────
# HIDDEN: These models now appear under "Partner Governance & Audit Logs"
# via proxy models in enterprise_governance/models.py.
# ──────────────────────────────────────────────────────────────────────────

@admin.register(SupplierContract)
class SupplierContractAdmin(admin.ModelAdmin):
    list_display = ('title', 'supplier', 'valid_from', 'valid_to', 'is_active')
    list_filter = ('is_active', 'supplier')
    search_fields = ('title', 'supplier__name')

    def has_module_permission(self, request):
        return False


@admin.register(CommissionRule)
class CommissionRuleAdmin(admin.ModelAdmin):
    list_display = ('agent_name', 'commission_percentage', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('agent_name',)

    def has_module_permission(self, request):
        return False
