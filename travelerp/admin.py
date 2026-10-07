from django.contrib import admin
from django.contrib.admin.views.autocomplete import AutocompleteJsonView
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from unfold.sites import UnfoldAdminSite



# ── Party-filtered Autocomplete ────────────────────────────────────────────────
# These are the field names on the Payment model that should be filtered by party.
PARTY_FILTERED_FIELDS = {
    'booking': lambda qs, party_id: qs.filter(party_id=party_id),
    'trip':    lambda qs, party_id: qs.filter(party_id=party_id),
    'statement': lambda qs, party_id: qs.filter(party_id=party_id),
    # contract_trip filters via the contract's customer
    'contract_trip': lambda qs, party_id: qs.filter(shift__route__contract__customer_id=party_id),
}


class PartyFilteredAutocompleteView(AutocompleteJsonView):
    """Extends the default admin autocomplete to accept an optional party_id
    query parameter so dependent dropdowns (Booking, Trip, etc.) only show
    records belonging to the selected party."""

    def get(self, request, *args, **kwargs):
        # DIAGNOSTIC: Print all received GET params to the server terminal
        print(f"\n[AutoComplete] GET params: {dict(request.GET)}\n", flush=True)
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        qs = super().get_queryset()
        party_id = self.request.GET.get('party_id')
        field_name = self.request.GET.get('field_name', '')
        print(f"[AutoComplete] party_id={party_id!r}, field_name={field_name!r}, qs_count={qs.count()}", flush=True)
        if party_id and field_name in PARTY_FILTERED_FIELDS:
            try:
                qs = PARTY_FILTERED_FIELDS[field_name](qs, party_id)
                print(f"[AutoComplete] Filtered to {qs.count()} records", flush=True)
            except Exception as e:
                print(f"[AutoComplete] Filter error: {e}", flush=True)
        return qs


class TravelERPAdminSite(UnfoldAdminSite):
    site_header = "TravelERP Administration"
    site_title = "TravelERP Admin Portal"
    index_title = "Welcome to TravelERP Portal"

    def autocomplete_view(self, request):
        """Use our party-filtered autocomplete instead of the default one."""
        return PartyFilteredAutocompleteView.as_view(admin_site=self)(request)

    def get_app_list(self, request, app_label=None):
        app_list = super().get_app_list(request)
        
        # Systemic Enterprise Priority Order for Apps
        app_order = {
            # Section 1: Commercial Sales Pipeline, CRM & Invoicing
            'crm': 10,
            
            # Section 2: Fleet Dispatch & Live Operations
            'operations': 20,
            'statements': 25,
            'digital_services': 30,
            
            # Section 3: Holiday Packages & Group Tour Catalog
            'packages': 40,
            'package_tours': 50,
            
            # Section 4: Institutional Contracts & Employee Commute
            'fleet_contracts': 60,
            'fleet_commute': 70,
            'core_partners': 80,
            
            # Section 5: Fleet Assets, Workshop & Legal Compliance
            'core': 90,
            'maintenance': 100,
            'maintenance_compliance': 110,
            
            # Section 6: Crew, Drivers & Mobile Portal
            'core_crew': 120,
            'driver_portal': 130,
            'analytics': 140,
            
            # Section 7: Finance, Fuel, Cash Desk & Payroll
            'finance': 150,
            'finance_fleet': 160,
            'finance_payroll': 170,
            'finance_treasury': 180,
            
            # Section 8: Enterprise Governance & System Administration
            'enterprise_governance': 190,
            'auth': 200,
        }
        
        # Systemic Priority Order for Models within each App
        model_order_map = {
            'crm': {
                'Inquiry': 1,
                'Quotation': 2,
                'DmcInvoice': 3,
                'DmcTask': 4,
                'PartnerProfile': 5,
                'B2CCustomerProfile': 6,
                'SupplierProfile': 7,
                'SupplierContractedRate': 8,
                'SupplierServiceVoucher': 9,
                'SupplierPaymentRequisition': 10,
                'HotelMaster': 11,
                'MonumentEntranceMaster': 12,
                'ActivityMaster': 13,
                'GuideChargeMaster': 14,
                'FlightMaster': 15,
                'DmcDocument': 16,
                'TravelComplaint': 17,
                'CustomerPreference': 18,
                'CommunicationLog': 19,
                'CouponProxy': 20,
                'EmailCampaignProxy': 21,
                'UpsellRecommendationProxy': 22,
            },
            'operations': {
                'Booking': 1,
                'Trip': 2,
                'BulkContract': 3,
                'BulkContractDay': 4,
                'VehicleTelematicsPing': 5,
                'EmergencyIncidentAlert': 6,
                'DriverBehaviorLog': 7,
                'GeofenceZone': 8,
                'TrafficFine': 9,
            },
            'packages': {
                'Package': 1,
                'PackageSeasonalRate': 2,
                'PackageHotelAllotment': 3,
                'PackageVehicleTariff': 4,
                'PackageTemplate': 5,
                'ItineraryDay': 6,
                'TempleDarshanSlot': 7,
                'InternationalDocumentChecklist': 8,
                'PackageAddon': 9,
                'PackageB2BMargin': 10,
                'TourFeedbackLog': 11,
            },
            'package_tours': {
                'CollegeIVProxy': 1,
                'TourDepartureBatchProxy': 2,
                'BoardingPointProxy': 3,
                'PassengerManifestProxy': 4,
                'SeasonalRateProxy': 5,
                'HotelAllotmentProxy': 6,
                'PackageAddonProxy': 7,
                'B2BMarginProxy': 8,
                'TourFeedbackProxy': 9,
            },
            'fleet_contracts': {
                'TransportContract': 1,
                'ContractFleetRoster': 2,
                'CommuterManifest': 3,
                'ContractTripLog': 4,
                'NightSafetyEscortLog': 5,
                'ContractSLAPenalty': 6,
                'ContractMonthlyInvoice': 7,
            },
            'fleet_commute': {
                'CommuteRoute': 1,
                'RouteStop': 2,
                'CommuteShift': 3,
                'CommuterManifestProxy': 4,
                'DailyTripLog': 5,
                'NightSafetyEscort': 6,
            },
            'digital_services': {
                'CustomerAccountProxy': 1,
                'PaymentLinkProxy': 2,
                'InstallmentPlanProxy': 3,
                'PaymentWebhookEventProxy': 4,
                'CustomerDocumentProxy': 5,
            },
            'core_partners': {
                'Client': 1,
                'Supplier': 2,
                'RateCard': 3,
            },
            'core': {
                'Vehicle': 1,
                'VehicleType': 2,
            },
            'maintenance': {
                'PreTripInspectionChecklist': 1,
                'DefectTicket': 2,
                'ServiceReminder': 3,
                'ServiceRecord': 4,
                'VehicleAsset': 5,
                'PartInventory': 6,
            },
            'maintenance_compliance': {
                'ComplianceDocument': 1,
                'InsuranceClaim': 2,
            },
            'core_crew': {
                'Driver': 1,
                'Cleaner': 2,
                'LicenseClass': 3,
            },
            'driver_portal': {
                'DriverPortalAccount': 1,
            },
            'finance': {
                'DriverAdvance': 1,
                'DriverSettlement': 2,
                'TripExpense': 3,
                'SupplierTripCost': 4,
                'DriverSalaryProfile': 5,
                'DriverPayslip': 6,
            },
            'finance_fleet': {
                'FuelRecord': 1,
                'CorporatePetroAccount': 2,
                'CorporateFastagAccount': 3,
                'FastagTollDeduction': 4,
            },
            'finance_payroll': {
                'DriverSalaryProfile': 1,
                'DriverPayslip': 2,
                'EmployeePayment': 3,
            },
            'finance_treasury': {
                'Payment': 1,
                'LedgerAdjustment': 2,
                'VehicleLoan': 3,
                'TripProfitReport': 4,
            },
            'statements': {
                'GeneratedStatement': 1,
            },
            'enterprise_governance': {
                'SupplierContractProxy': 1,
                'CommissionRuleProxy': 2,
                'AuditLogEntryProxy': 3,
            },
            'analytics': {
                'DriverScorecard': 1,
                'ReportLog': 2,
            },
            'auth': {
                'User': 1,
                'Group': 2,
            },
        }

        # Sort models within each app according to model_order_map
        for app in app_list:
            app_lbl = app.get('app_label', '').lower()
            models = app.get('models', [])
            m_order = model_order_map.get(app_lbl, {})
            models.sort(key=lambda m: m_order.get(m.get('object_name'), 999))
            app['models'] = models

        def get_app_priority(app):
            label = app.get('app_label', '').lower()
            return app_order.get(label, 999)

        app_list.sort(key=get_app_priority)
        return app_list

    def index(self, request, extra_context=None):
        # Import models locally to avoid circular imports during setup
        from operations.models import Trip, Booking
        from core.models import Driver
        from finance.models import DriverAdvance
        
        # 1. Total Active Drivers
        active_drivers_count = Driver.objects.filter(status='active').count()
        
        # 2. Total Pending Bookings (assuming not 'confirmed')
        pending_bookings_count = Booking.objects.exclude(status='confirmed').count()
        
        # 3. Active Trips Today
        today = timezone.now().date()
        active_trips_count = Trip.objects.filter(
            start_date__lte=today,
            status__in=['started', 'assigned', 'driver_confirmed']
        ).count()
        
        # 4. Total Unsettled Driver Advances
        unsettled_advances = DriverAdvance.objects.all()
        # remaining_amount is a property, so we have to evaluate in python
        unsettled_count = sum(1 for adv in unsettled_advances if adv.remaining_amount > 0)
        
        extra_context = extra_context or {}
        extra_context.update({
            'active_drivers_count': active_drivers_count,
            'pending_bookings_count': pending_bookings_count,
            'active_trips_count': active_trips_count,
            'unsettled_advances_count': unsettled_count,
        })
        return super().index(request, extra_context=extra_context)

