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
        verbose_name = 'College IV Expedition'
        verbose_name_plural = 'College IV Expeditions'


class TourDepartureBatchProxy(BasePackageInventory):
    class Meta:
        proxy = True
        app_label = 'package_tours'
        verbose_name = 'Tour Bus Departure Batch'
        verbose_name_plural = 'Tour Bus Departure Batches'


class BoardingPointProxy(BaseBoardingPoint):
    class Meta:
        proxy = True
        app_label = 'package_tours'
        verbose_name = 'Tour Boarding Point'
        verbose_name_plural = 'Boarding Points & Timetable'


class PassengerManifestProxy(BaseTourPassengerManifest):
    class Meta:
        proxy = True
        app_label = 'package_tours'
        verbose_name = 'Passenger & Rooming List'
        verbose_name_plural = 'Passenger Manifest & Rooming'


class HotelAllotmentProxy(BasePackageHotelAllotment):
    class Meta:
        proxy = True
        app_label = 'package_tours'
        verbose_name = 'Hotel Room Block Allotment'
        verbose_name_plural = 'Hotel Room Block Allotments'


class TourFeedbackProxy(BaseTourFeedbackLog):
    class Meta:
        proxy = True
        app_label = 'package_tours'
        verbose_name = 'Tour Customer Feedback'
        verbose_name_plural = 'Customer Reviews & NPS Governance'


class SeasonalRateProxy(BasePackageSeasonalRate):
    class Meta:
        proxy = True
        app_label = 'package_tours'
        verbose_name = 'Seasonal Pricing & Peak Tariff'
        verbose_name_plural = 'Seasonal Pricing & Peak Tariffs'


class PackageAddonProxy(BasePackageAddon):
    class Meta:
        proxy = True
        app_label = 'package_tours'
        verbose_name = 'Experience & Safari Add-On'
        verbose_name_plural = 'Experience & Safari Add-Ons'


class B2BMarginProxy(BasePackageB2BMargin):
    class Meta:
        proxy = True
        app_label = 'package_tours'
        verbose_name = 'B2B Reseller Tier & Margin'
        verbose_name_plural = 'B2B Reseller Tiers & Margins'
