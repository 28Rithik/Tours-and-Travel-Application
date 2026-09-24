from django.contrib import admin
from .models import CustomerAccount

# ──────────────────────────────────────────────────────────────────────────
# HIDDEN: This model now appears under "Digital Collections & Guest Portal"
# ──────────────────────────────────────────────────────────────────────────

@admin.register(CustomerAccount)
class CustomerAccountAdmin(admin.ModelAdmin):
    list_display = ('user', 'client_record', 'is_email_verified', 'created_at')
    list_filter = ('is_email_verified',)
    search_fields = ('user__username', 'client_record__name')

    def has_module_permission(self, request):
        return False
