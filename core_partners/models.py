from django.db import models
from core.models import (
    Client as BaseClient,
    Supplier as BaseSupplier,
    RateCard as BaseRateCard,
)


class Client(BaseClient):
    class Meta:
        proxy = True
        app_label = 'core_partners'
        verbose_name = 'Client'
        verbose_name_plural = 'Clients'


class Supplier(BaseSupplier):
    class Meta:
        proxy = True
        app_label = 'core_partners'
        verbose_name = 'Supplier'
        verbose_name_plural = 'Suppliers'


class RateCard(BaseRateCard):
    class Meta:
        proxy = True
        app_label = 'core_partners'
        verbose_name = 'Rate card'
        verbose_name_plural = 'Rate cards'
