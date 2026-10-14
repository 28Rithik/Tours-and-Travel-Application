"""
Clean Slate Purge: Retain ONLY Real Tour Packages Catalog
Removes:
- BoardingPoint / BoardingPointProxy (224 rows)
- CollegeIVExpedition / CollegeIVProxy (9 rows)
- TourFeedbackLog / TourFeedbackProxy (4 rows)
- PettyCashAccount & petty cash logs (7 rows)
- TourPassengerManifest / PassengerManifestProxy (595 rows)
- PackageInventory / TourDepartureBatchProxy (60 rows)
- PackageSeasonalRate (4 rows)
- PackageB2BMargin (3 rows)
- StaffProfile & non-superuser staff/driver/customer test accounts
- Test CRM masters, test finance accounts, test documents, old sessions
Keeps:
- Package (6,252 rows)
- ItineraryDay (30,508 rows)
- PackageVehicleTariff (31,221 rows)
- TempleDarshanSlot (1,589 rows)
- InternationalDocumentChecklist (6,125 rows)
- PackageTemplate (6 rows)
- VehicleType (25 core vehicle models)
- Superusers (rithik, admin)
- RBAC Groups & Permissions
"""

import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')

import django
django.setup()

from django.db import connection
from django.contrib.auth.models import User
from django.contrib.sessions.models import Session

from packages.models import (
    Package,
    ItineraryDay,
    PackageVehicleTariff,
    TempleDarshanSlot,
    InternationalDocumentChecklist,
    PackageTemplate,
    PackageInventory,
    BoardingPoint,
    CollegeIVExpedition,
    TourPassengerManifest,
    TourFeedbackLog,
    PackageSeasonalRate,
    PackageB2BMargin,
    PackageHotelAllotment,
    PackageAddon,
)
from core.models import StaffProfile, VehicleType
from finance.models import PettyCashAccount, Account
from crm.models import (
    HotelMaster,
    MonumentEntranceMaster,
    ActivityMaster,
    GuideChargeMaster,
    FlightMaster,
)
from documents.models import KnowledgeDocument, KnowledgeChunk
from payments_gateway.models import PaymentGatewayConfig

print("=" * 70)
print("🧹 EXECUTING COMPLETE CLEAN SLATE (KEEPING ONLY REAL TOUR PACKAGES)")
print(f"[*] Active Database: {connection.settings_dict['ENGINE']} ({connection.settings_dict['NAME']})")
print("=" * 70)

# 1. Clean Package Operational & Test Models
print("\n[*] Deleting package operational records...")
count_bp = BoardingPoint.objects.all().delete()[0]
print(f"  ✓ Deleted BoardingPoint (BoardingPointProxy): {count_bp} rows")

count_manifest = TourPassengerManifest.objects.all().delete()[0]
print(f"  ✓ Deleted TourPassengerManifest (PassengerManifestProxy): {count_manifest} rows")

count_iv = CollegeIVExpedition.objects.all().delete()[0]
print(f"  ✓ Deleted CollegeIVExpedition (CollegeIVProxy): {count_iv} rows")

count_fb = TourFeedbackLog.objects.all().delete()[0]
print(f"  ✓ Deleted TourFeedbackLog (TourFeedbackProxy): {count_fb} rows")

count_inv = PackageInventory.objects.all().delete()[0]
print(f"  ✓ Deleted PackageInventory (TourDepartureBatchProxy): {count_inv} rows")

count_sr = PackageSeasonalRate.objects.all().delete()[0]
print(f"  ✓ Deleted PackageSeasonalRate: {count_sr} rows")

count_b2b = PackageB2BMargin.objects.all().delete()[0]
print(f"  ✓ Deleted PackageB2BMargin: {count_b2b} rows")

PackageHotelAllotment.objects.all().delete()
PackageAddon.objects.all().delete()

# 2. Clean Finance Petty Cash & Test Accounts
print("\n[*] Deleting test finance records...")
count_cash = PettyCashAccount.objects.all().delete()[0]
print(f"  ✓ Deleted PettyCashAccount: {count_cash} rows")

count_acct = Account.objects.all().delete()[0]
print(f"  ✓ Deleted test Finance Accounts: {count_acct} rows")

# 3. Clean Staff & Non-Superuser Test Accounts
print("\n[*] Cleaning staff and test user accounts...")
count_staff = StaffProfile.objects.all().delete()[0]
print(f"  ✓ Deleted StaffProfile: {count_staff} rows")

# Keep only primary superusers 'rithik' and 'admin'
deleted_users = User.objects.exclude(username__in=['rithik', 'admin']).delete()[0]
print(f"  ✓ Deleted test/dummy Users: {deleted_users} rows (Preserved: 'rithik', 'admin')")

# Clear sessions
Session.objects.all().delete()
print(f"  ✓ Cleared all old browser sessions")

# 4. Clean Test CRM & Document Masters
print("\n[*] Cleaning test CRM and Document data...")
HotelMaster.objects.all().delete()
MonumentEntranceMaster.objects.all().delete()
ActivityMaster.objects.all().delete()
GuideChargeMaster.objects.all().delete()
FlightMaster.objects.all().delete()
KnowledgeDocument.objects.all().delete()
KnowledgeChunk.objects.all().delete()
PaymentGatewayConfig.objects.all().delete()
print("  ✓ Cleared test CRM and Document masters")

# 5. Verify Preserved Catalog
print("\n" + "=" * 70)
print("📊 VERIFICATION AUDIT — PRESERVED REAL TOUR PACKAGES")
print("=" * 70)
print(f"  • Real Tour Packages: {Package.objects.count():,} rows")
print(f"  • Day-by-Day Itineraries: {ItineraryDay.objects.count():,} rows")
print(f"  • Vehicle-Wise Tariffs: {PackageVehicleTariff.objects.count():,} rows")
print(f"  • Temple Darshan Slots: {TempleDarshanSlot.objects.count():,} rows")
print(f"  • International Document Rules: {InternationalDocumentChecklist.objects.count():,} rows")
print(f"  • Package Templates: {PackageTemplate.objects.count():,} rows")
print(f"  • Core Vehicle Types: {VehicleType.objects.count():,} rows")
print(f"  • Superusers: {list(User.objects.values_list('username', flat=True))}")

# Check that deleted tables are strictly 0
zeros = [
    ('BoardingPoint', BoardingPoint.objects.count()),
    ('CollegeIVExpedition', CollegeIVExpedition.objects.count()),
    ('TourFeedbackLog', TourFeedbackLog.objects.count()),
    ('TourPassengerManifest', TourPassengerManifest.objects.count()),
    ('PackageInventory', PackageInventory.objects.count()),
    ('PettyCashAccount', PettyCashAccount.objects.count()),
    ('StaffProfile', StaffProfile.objects.count()),
]

all_zero = True
for name, val in zeros:
    status = "0 (CLEAN ✅)" if val == 0 else f"{val} (FAILED ❌)"
    print(f"  • {name}: {status}")
    if val != 0: all_zero = False

print("\n" + "=" * 70)
if all_zero and Package.objects.count() == 6252:
    print("🏆 CLEAN SLATE PURGE COMPLETED SUCCESSFULLY WITH ZERO ERRORS!")
else:
    print("⚠️ Clean slate audit incomplete.")
print("=" * 70)
