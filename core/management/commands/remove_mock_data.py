from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q

from core.models import Driver, Party, RateCard, Vehicle
from finance.models import (
    DriverAdvance,
    DriverAdvanceAllocation,
    DriverSettlement,
    FuelRecord,
    LedgerAdjustment,
    Payment,
    SupplierTripCost,
    TripExpense,
)
from operations.models import Booking, Trip, TripJourney
from statements.models import GeneratedStatement


class Command(BaseCommand):
    help = 'Remove only seeded DEMO data and preserve the company record.'

    @transaction.atomic
    def handle(self, *args, **options):
        demo_trips = Trip.objects.filter(trip_id__startswith='TR-DEMO-')
        demo_bookings = Booking.objects.filter(booking_number__startswith='BK-DEMO-')
        demo_vehicles = Vehicle.objects.filter(registration_number__startswith='TN-DEMO-')
        demo_drivers = Driver.objects.filter(Q(license_number__startswith='DEMO-LIC-') | Q(phone__startswith='92000'))
        demo_parties = Party.objects.filter(Q(email__endswith='@demo.example') | Q(address__contains='Supplier Road')).exclude(name='Sivagayathiri Tours and Travels')

        trip_ids = list(demo_trips.values_list('id', flat=True))
        booking_ids = list(demo_bookings.values_list('id', flat=True))
        vehicle_ids = list(demo_vehicles.values_list('id', flat=True))
        driver_ids = list(demo_drivers.values_list('id', flat=True))
        party_ids = list(demo_parties.values_list('id', flat=True))

        GeneratedStatement.objects.filter(Q(party_id__in=party_ids) | Q(party__email__endswith='@demo.example')).delete()
        DriverAdvanceAllocation.objects.filter(Q(advance__driver_id__in=driver_ids) | Q(trip_id__in=trip_ids)).delete()
        DriverSettlement.objects.filter(Q(driver_id__in=driver_ids) | Q(trip_id__in=trip_ids)).delete()
        DriverAdvance.objects.filter(driver_id__in=driver_ids).delete()
        SupplierTripCost.objects.filter(Q(trip_id__in=trip_ids) | Q(supplier_id__in=party_ids) | Q(vehicle_id__in=vehicle_ids)).delete()
        Payment.objects.filter(Q(trip_id__in=trip_ids) | Q(party_id__in=party_ids)).delete()
        TripExpense.objects.filter(trip_id__in=trip_ids).delete()
        FuelRecord.objects.filter(Q(trip_id__in=trip_ids) | Q(vehicle_id__in=vehicle_ids)).delete()
        LedgerAdjustment.objects.filter(party_id__in=party_ids).delete()
        TripJourney.objects.filter(trip_id__in=trip_ids).delete()
        Trip.objects.filter(id__in=trip_ids).delete()
        Booking.objects.filter(id__in=booking_ids).delete()
        RateCard.objects.filter(Q(party_id__in=party_ids) | Q(vehicle_id__in=vehicle_ids)).delete()
        Driver.objects.filter(id__in=driver_ids).delete()
        Vehicle.objects.filter(id__in=vehicle_ids).delete()
        Party.objects.filter(id__in=party_ids).delete()

        self.stdout.write(self.style.SUCCESS('Seeded DEMO data removed.'))
        self.stdout.write('Sivagayathiri Tours and Travels was preserved.')
