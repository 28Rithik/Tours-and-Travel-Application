import os
import sys
import django
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
django.setup()

from django.contrib.admin.sites import site
from django.test import RequestFactory
from django.contrib.auth.models import User
from packages.models import (
    Package,
    PackageSeasonalRate,
    PackageHotelAllotment,
    PackageAddon,
    PackageB2BMargin,
    TourFeedbackLog,
    CollegeIVExpedition,
    TourPassengerManifest,
    PackageInventory,
)
from fleet_contracts.models import (
    TransportContract,
    ContractFleetRoster,
    ContractMonthlyInvoice,
    ContractSLAPenalty,
)
from package_tours.models import (
    CollegeIVProxy,
    TourDepartureBatchProxy,
    PassengerManifestProxy,
    HotelAllotmentProxy,
    TourFeedbackProxy,
    SeasonalRateProxy,
    PackageAddonProxy,
    B2BMarginProxy,
)

def test_all_admin_forms():
    print("=" * 80)
    print("📋 DEEP VERIFICATION OF ALL ADMIN FORMS & INLINES")
    print("=" * 80)

    factory = RequestFactory()
    admin_user = User.objects.filter(is_superuser=True).first()
    request = factory.get('/admin/')
    request.user = admin_user

    models_to_test = [
        # Core Packages
        Package,
        PackageSeasonalRate,
        PackageHotelAllotment,
        PackageAddon,
        PackageB2BMargin,
        TourFeedbackLog,
        CollegeIVExpedition,
        PackageInventory,
        TourPassengerManifest,

        # Package Tours Proxies
        CollegeIVProxy,
        TourDepartureBatchProxy,
        PassengerManifestProxy,
        HotelAllotmentProxy,
        TourFeedbackProxy,
        SeasonalRateProxy,
        PackageAddonProxy,
        B2BMarginProxy,

        # Fleet Contracts
        TransportContract,
        ContractFleetRoster,
        ContractMonthlyInvoice,
        ContractSLAPenalty,
    ]

    passed = 0
    total = 0

    for model in models_to_test:
        total += 1
        model_admin = site._registry.get(model)
        if not model_admin:
            print(f"  [FAIL] {model.__name__} is NOT registered in admin.site!")
            sys.exit(1)

        try:
            # 1. Test get_form
            form_class = model_admin.get_form(request)
            form_instance = form_class()
            
            # 2. Test get_inline_instances
            inlines = model_admin.get_inline_instances(request)
            inline_names = [type(inline).__name__ for inline in inlines]

            # 3. Test fieldsets resolution
            fieldsets = model_admin.get_fieldsets(request)
            fields_in_fieldsets = []
            for fs_name, fs_dict in fieldsets:
                for f in fs_dict.get('fields', []):
                    if isinstance(f, (list, tuple)):
                        fields_in_fieldsets.extend(f)
                    else:
                        fields_in_fieldsets.append(f)

            passed += 1
            inlines_str = f" ({len(inlines)} inlines: {', '.join(inline_names)})" if inlines else ""
            print(f"  [PASS] {model.__name__} form initialized cleanly with {len(fields_in_fieldsets)} fields{inlines_str}")
        except Exception as e:
            print(f"  [FAIL] {model.__name__} form initialization error: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

    print("\n" + "=" * 80)
    print(f"🎉 ALL {passed}/{total} ADMIN FORMS INITIALIZED PERFECTLY WITH 0 ERRORS!")
    print("=" * 80)

if __name__ == '__main__':
    test_all_admin_forms()
