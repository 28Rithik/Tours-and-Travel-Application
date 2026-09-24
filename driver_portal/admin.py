from django.contrib import admin
from .models import DriverPortalAccount


@admin.register(DriverPortalAccount)
class DriverPortalAccountAdmin(admin.ModelAdmin):
    list_display = ('driver', 'phone_number', 'quick_pin', 'is_active', 'last_login_at', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('driver__name', 'driver__phone', 'user__username')
    autocomplete_fields = ['driver', 'user']

    @admin.display(description="Phone Number")
    def phone_number(self, obj):
        return obj.driver.phone if obj.driver else "-"
