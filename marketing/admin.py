from django.contrib import admin
from .models import Coupon, EmailCampaign, UpsellRecommendation

# ──────────────────────────────────────────────────────────────────────────
# HIDDEN: These models now appear under "Sales Pipeline, CRM & Marketing"
# via proxy models in crm/models.py. Registrations are kept here only to
# preserve autocomplete and foreign-key lookups.
# ──────────────────────────────────────────────────────────────────────────

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_percent', 'flat_discount', 'applicable_package', 'used_count', 'is_active')
    list_filter = ('is_active', 'applicable_package')
    search_fields = ('code',)

    def has_module_permission(self, request):
        return False


@admin.register(EmailCampaign)
class EmailCampaignAdmin(admin.ModelAdmin):
    list_display = ('name', 'subject', 'sent_at', 'is_active')
    list_filter = ('is_active', 'sent_at')
    search_fields = ('name', 'subject')

    def has_module_permission(self, request):
        return False


@admin.register(UpsellRecommendation)
class UpsellRecommendationAdmin(admin.ModelAdmin):
    list_display = ('title', 'package', 'price')
    list_filter = ('package',)
    search_fields = ('title', 'package__name')

    def has_module_permission(self, request):
        return False
