from django.db import models
from packages.models import (
    CollegeIVExpedition as BaseCollegeIVExpedition,
    PackageInventory as BasePackageInventory,
    BoardingPoint as BaseBoardingPoint,
    TourPassengerManifest as BaseTourPassengerManifest,
    PackageHotelAllotment as BasePackageHotelAllotment,
    TourFeedbackLog as BaseTourFeedbackLog,
    PackageSeasonalRate as BasePackageSeasonalRate,
    PackageAddon as BasePackageAddon,
    PackageB2BMargin as BasePackageB2BMargin,
)


class CollegeIVProxy(BaseCollegeIVExpedition):
    class Meta:
        proxy = True
        app_label = 'package_tours'
        verbose_name = 'College Tour'
        verbose_name_plural = 'College Tours'


class TourDepartureBatchProxy(BasePackageInventory):
    class Meta:
        proxy = True
        app_label = 'package_tours'
        verbose_name = 'Tour Departure'
        verbose_name_plural = 'Tour Departures'


class BoardingPointProxy(BaseBoardingPoint):
    class Meta:
        proxy = True
        app_label = 'package_tours'
        verbose_name = 'Boarding Point'
        verbose_name_plural = 'Boarding Points'


class PassengerManifestProxy(BaseTourPassengerManifest):
    class Meta:
        proxy = True
        app_label = 'package_tours'
        verbose_name = 'Passenger List'
        verbose_name_plural = 'Passenger Lists'


class HotelAllotmentProxy(BasePackageHotelAllotment):
    class Meta:
        proxy = True
        app_label = 'package_tours'
        verbose_name = 'Hotel Allotment'
        verbose_name_plural = 'Hotel Allotments'


class TourFeedbackProxy(BaseTourFeedbackLog):
    class Meta:
        proxy = True
        app_label = 'package_tours'
        verbose_name = 'Tour Feedback'
        verbose_name_plural = 'Tour Reviews'


class SeasonalRateProxy(BasePackageSeasonalRate):
    class Meta:
        proxy = True
        app_label = 'package_tours'
        verbose_name = 'Seasonal Rate'
        verbose_name_plural = 'Seasonal Rates'


class PackageAddonProxy(BasePackageAddon):
    class Meta:
        proxy = True
        app_label = 'package_tours'
        verbose_name = 'Tour Add-On'
        verbose_name_plural = 'Tour Add-Ons'


class B2BMarginProxy(BasePackageB2BMargin):
    class Meta:
        proxy = True
        app_label = 'package_tours'
        verbose_name = 'B2B Agent Margin'
        verbose_name_plural = 'B2B Agent Margins'
