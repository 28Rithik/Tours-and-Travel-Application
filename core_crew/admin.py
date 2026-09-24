from django.contrib import admin
from core.admin import (
    DriverAdmin as BaseDriverAdmin,
    CleanerAdmin as BaseCleanerAdmin,
    LicenseClassAdmin as BaseLicenseClassAdmin,
)
from .models import Driver, Cleaner, LicenseClass


@admin.register(Driver)
class DriverAdmin(BaseDriverAdmin):
    def has_module_permission(self, request):
        return super(BaseDriverAdmin, self).has_module_permission(request)


@admin.register(Cleaner)
class CleanerAdmin(BaseCleanerAdmin):
    def has_module_permission(self, request):
        return super(BaseCleanerAdmin, self).has_module_permission(request)


@admin.register(LicenseClass)
class LicenseClassAdmin(BaseLicenseClassAdmin):
    def has_module_permission(self, request):
        return super(BaseLicenseClassAdmin, self).has_module_permission(request)
