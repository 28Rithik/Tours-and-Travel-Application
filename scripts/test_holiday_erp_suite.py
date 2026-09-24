import os
import sys
import django
import datetime
from decimal import Decimal
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
django.setup()

from django.test import Client as TestClient
from django.contrib.auth.models import User
from packages.models import (
    Package,
    PackageSeasonalRate,
    PackageHotelAllotment,
    PackageAddon,
    PackageB2BMargin,
    TourFeedbackLog,
)

def run_tests():
    print("🧪 Running Automated Verification for Holiday Package Travel ERP Suite...\n")
    passed = 0
    total = 0

    def assert_test(cond, title):
        nonlocal passed, total
        total += 1
        if cond:
            passed += 1
            print(f"  [PASS] {title}")
        else:
            print(f"  [FAIL] {title}")
            sys.exit(1)

    # 1. Test Unit Economics
    pkg = Package.objects.filter(seasonal_rates__isnull=False).first()
    if not pkg:
        pkg = Package.objects.first()

    assert_test(pkg is not None, "Sample package found for unit economics")
    assert_test(pkg.total_direct_cost_per_pax > 0, f"Total direct cost calculated: ₹{pkg.total_direct_cost_per_pax:,.2f}")
    assert_test(pkg.gross_margin_per_pax >= 0, f"Gross margin per pax calculated: ₹{pkg.gross_margin_per_pax:,.2f}")
    assert_test(pkg.gross_margin_percentage >= 0, f"Gross margin %: {pkg.gross_margin_percentage}%")
    assert_test(pkg.projected_batch_gross_profit >= 0, f"Projected batch profit on {pkg.min_pax} pax: ₹{pkg.projected_batch_gross_profit:,.2f}")

    # 2. Test Seasonal Pricing Engine
    season = pkg.seasonal_rates.first()
    assert_test(season is not None, "Seasonal pricing tier exists")
    effective_peak = pkg.get_effective_price(travel_date=datetime.date(2025, 5, 15), with_food=True)
    base_price = pkg.price_with_food or pkg.base_price
    assert_test(effective_peak > base_price, f"Peak season price adjusted upwards: ₹{base_price:,.0f} -> ₹{effective_peak:,.0f}")

    effective_normal = pkg.get_effective_price(travel_date=datetime.date(2025, 1, 10), with_food=True)
    assert_test(effective_normal == base_price, f"Normal season returns base rate: ₹{effective_normal:,.0f}")

    # 3. Test Hotel Room Allotment
    allotment = pkg.hotel_allotments.first()
    assert_test(allotment is not None, "Hotel room allotment exists")
    assert_test(allotment.occupancy_rate > 0, f"Hotel room occupancy calculated: {allotment.occupancy_rate}% ({allotment.rooms_occupied}/{allotment.rooms_blocked} rooms)")
    assert_test(allotment.rooms_available == (allotment.rooms_blocked - allotment.rooms_occupied), f"Available rooms correct: {allotment.rooms_available}")
    assert_test(allotment.total_cost > 0, f"Total hotel allotment contract value: ₹{allotment.total_cost:,.2f}")

    # 4. Test Experience Addons
    addon = pkg.addons.first()
    assert_test(addon is not None, "Experience / Safari add-on exists")
    assert_test(addon.margin_per_unit > 0, f"Addon margin per unit: ₹{addon.margin_per_unit:,.2f}")
    assert_test(addon.margin_percentage > 0, f"Addon margin %: {addon.margin_percentage}%")

    # 5. Test B2B Sub-Agent Margins
    b2b = pkg.b2b_margins.first()
    assert_test(b2b is not None, "B2B commission rule exists")
    assert_test(b2b.net_b2b_rate_with_food < (pkg.price_with_food or pkg.base_price), f"B2B net rate discounted: ₹{b2b.net_b2b_rate_with_food:,.2f}")

    # 6. Test Feedback & NPS
    fb = pkg.feedback_logs.first()
    assert_test(fb is not None, "Customer feedback log exists")
    assert_test(fb.average_dimension_score >= 1.0, f"5D Average Quality Score: {fb.average_dimension_score} / 5.0")
    assert_test("Promoter" in fb.nps_category or "Passive" in fb.nps_category or "Detractor" in fb.nps_category, f"NPS Classification: {fb.nps_category}")

    # 7. Test Admin Endpoints & Proposal Quotation
    client = TestClient()
    admin_user = User.objects.filter(is_superuser=True).first()
    client.force_login(admin_user)

    endpoints = [
        "/admin/packages/package/",
        f"/admin/packages/package/{pkg.id}/change/",
        "/admin/packages/packageseasonalrate/",
        "/admin/packages/packagehotelallotment/",
        "/admin/packages/packageaddon/",
        "/admin/packages/packageb2bmargin/",
        "/admin/packages/tourfeedbacklog/",
        "/admin/package_tours/hotelallotmentproxy/",
        "/admin/package_tours/tourfeedbackproxy/",
        "/admin/package_tours/seasonalrateproxy/",
        "/admin/package_tours/packageaddonproxy/",
        "/admin/package_tours/b2bmarginproxy/",
        f"/packages/quote/{pkg.id}/",
        f"/packages/voucher/{pkg.id}/",
    ]

    from packages.models import CollegeIVExpedition
    exp = CollegeIVExpedition.objects.first()
    if exp:
        endpoints.append(f"/packages/manifest/{exp.id}/rooming-list/")

    for url in endpoints:
        resp = client.get(url)
        assert_test(resp.status_code == 200, f"HTTP 200 for URL: {url}")

    print(f"\n🎉 All {passed}/{total} automated tests PASSED successfully!")

if __name__ == '__main__':
    run_tests()
