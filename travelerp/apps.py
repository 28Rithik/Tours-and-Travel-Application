from django.contrib.admin.apps import AdminConfig

class TravelERPAdminConfig(AdminConfig):
    default_site = 'travelerp.admin.TravelERPAdminSite'
