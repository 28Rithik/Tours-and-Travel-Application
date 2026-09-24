from django.contrib import admin
from core.admin import (
    ClientAdmin as BaseClientAdmin,
    SupplierAdmin as BaseSupplierAdmin,
    RateCardAdmin as BaseRateCardAdmin,
)
from .models import Client, Supplier, RateCard


@admin.register(Client)
class ClientAdmin(BaseClientAdmin):
    def has_module_permission(self, request):
        return super(BaseClientAdmin, self).has_module_permission(request)


@admin.register(Supplier)
class SupplierAdmin(BaseSupplierAdmin):
    def has_module_permission(self, request):
        return super(BaseSupplierAdmin, self).has_module_permission(request)


@admin.register(RateCard)
class RateCardAdmin(BaseRateCardAdmin):
    def has_module_permission(self, request):
        return super(BaseRateCardAdmin, self).has_module_permission(request)
