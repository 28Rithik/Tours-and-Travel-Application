from django.contrib.admin.apps import AdminConfig


class TravelERPAdminConfig(AdminConfig):
    default_site = 'travelerp.admin.TravelERPAdminSite'

    def ready(self):
        super().ready()
        from django.contrib import admin
        from django.contrib.auth.models import User, Group
        from django.contrib.auth.admin import UserAdmin as BaseUserAdmin, GroupAdmin as BaseGroupAdmin
        from unfold.admin import ModelAdmin

        class UnfoldUserAdmin(BaseUserAdmin, ModelAdmin):
            pass

        class UnfoldGroupAdmin(BaseGroupAdmin, ModelAdmin):
            pass

        try:
            admin.site.unregister(User)
        except admin.sites.NotRegistered:
            pass
        try:
            admin.site.unregister(Group)
        except admin.sites.NotRegistered:
            pass

        admin.site.register(User, UnfoldUserAdmin)
        admin.site.register(Group, UnfoldGroupAdmin)
