from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import AuditLogEntry

# ──────────────────────────────────────────────────────────────────────────
# HIDDEN: This model now appears under "Partner Governance & Audit Logs"
# via proxy model in enterprise_governance/models.py.
# ──────────────────────────────────────────────────────────────────────────

@admin.register(AuditLogEntry)
class AuditLogEntryAdmin(ModelAdmin):
    list_display = ('action', 'content_type', 'object_id', 'user', 'timestamp')
    list_filter = ('action', 'content_type', 'timestamp')
    search_fields = ('action', 'user__username')
    readonly_fields = ('action', 'content_type', 'object_id', 'content_object', 'user', 'changes', 'timestamp')

    def has_module_permission(self, request):
        return False

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
