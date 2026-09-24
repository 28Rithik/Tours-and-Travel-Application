from django.db import models
from core.models import (
    Driver as BaseDriver,
    Cleaner as BaseCleaner,
    LicenseClass as BaseLicenseClass,
)


class Driver(BaseDriver):
    class Meta:
        proxy = True
        app_label = 'core_crew'
        verbose_name = 'Driver'
        verbose_name_plural = 'Drivers'


class Cleaner(BaseCleaner):
    class Meta:
        proxy = True
        app_label = 'core_crew'
        verbose_name = 'Cleaner'
        verbose_name_plural = 'Cleaners'


class LicenseClass(BaseLicenseClass):
    class Meta:
        proxy = True
        app_label = 'core_crew'
        verbose_name = 'License class'
        verbose_name_plural = 'License classes'
