from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Coupon, EmailCampaign, UpsellRecommendation, PromotionCampaign


@admin.register(PromotionCampaign)
class PromotionCampaignAdmin(ModelAdmin):
    list_display = ('name', 'channel', 'target_audience', 'coupon', 'target_count', 'status', 'created_at')
    list_filter = ('status', 'channel', 'target_audience', 'created_at')
    search_fields = ('name', 'headline', 'message_body')
    readonly_fields = ('created_at',)


@admin.register(Coupon)
class CouponAdmin(ModelAdmin):
    list_display = ('code', 'discount_percent', 'flat_discount', 'applicable_package', 'used_count', 'is_active')
    list_filter = ('is_active', 'applicable_package')
    search_fields = ('code',)


@admin.register(EmailCampaign)
class EmailCampaignAdmin(ModelAdmin):
    list_display = ('name', 'subject', 'sent_at', 'is_active')
    list_filter = ('is_active', 'sent_at')
    search_fields = ('name', 'subject')


@admin.register(UpsellRecommendation)
class UpsellRecommendationAdmin(ModelAdmin):
    list_display = ('title', 'package', 'price')
    list_filter = ('package',)
    search_fields = ('title', 'package__name')
