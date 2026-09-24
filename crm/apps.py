from django.apps import AppConfig


class CrmConfig(AppConfig):
    name = "crm"
    verbose_name = "Sales Pipeline, CRM & Marketing"

    def ready(self):
        import crm.signals
