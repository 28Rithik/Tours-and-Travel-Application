from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import CustomerAccount, CustomerOTP

# ──────────────────────────────────────────────────────────────────────────
# HIDDEN: This model now appears under "Digital Collections & Guest Portal"
# ──────────────────────────────────────────────────────────────────────────

@admin.register(CustomerAccount)
class CustomerAccountAdmin(ModelAdmin):
    list_display = ('user', 'client_record', 'is_email_verified', 'created_at')
    list_filter = ('is_email_verified',)
    search_fields = ('user__username', 'client_record__name')

    def has_module_permission(self, request):
        return False


@admin.register(CustomerOTP)
class CustomerOTPAdmin(ModelAdmin):
    list_display = ('phone', 'otp_code', 'is_verified', 'created_at', 'expires_at')
    list_filter = ('is_verified', 'created_at')
    search_fields = ('phone', 'otp_code')
    readonly_fields = ('created_at',)

