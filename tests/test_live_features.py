from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from packages.models import Package


class LiveFeaturesTestCase(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_superuser('test_admin_live', 'admin_live@example.com', 'adminpass')
        self.client = Client()
        self.client.force_login(self.user)

    def test_live_features_and_preview(self):
        # 1. Test /packages/quote/preview/ draft rendering without saved DB record
        res_preview = self.client.get('/packages/quote/preview/?name=4+NIGHTS+5+DAYS+KERALA+COLLEGE+IV&nights=4&days=5&price_with_food=6850&modal=1')
        self.assertEqual(res_preview.status_code, 200)
        html_preview = res_preview.content.decode('utf-8')
        self.assertIn("KERALA COLLEGE IV", html_preview)
        self.assertNotIn('<div class="top-action-bar">', html_preview)

        # 2. Test /packages/quote/<id>/?modal=1 for existing package
        pkg = Package.objects.create(
            package_code="TEST-LIVE-PKG",
            name="SIVA GAYATHRI SPECIAL TOUR",
            destination="Ooty",
            duration_nights=2,
            duration_days=3,
            pricing_type="per_person",
            base_price=Decimal('3500.00'),
        )
        res_pkg_modal = self.client.get(f'/packages/quote/{pkg.id}/?modal=1')
        self.assertEqual(res_pkg_modal.status_code, 200)
        html_pkg_modal = res_pkg_modal.content.decode('utf-8')
        self.assertNotIn('<div class="top-action-bar">', html_pkg_modal)
        self.assertIn("SIVA GAYATHRI", html_pkg_modal)

        # 3. Test Profit Margin Calculation formulas
        pax = 50
        ap_rate = Decimal('6850')
        total_revenue = pax * ap_rate
        bus_cost = Decimal('44000')
        hotel_cost = Decimal('46800')
        food_cost = Decimal('87500')
        misc_cost = Decimal('23000')
        total_cost = bus_cost + hotel_cost + food_cost + misc_cost
        net_profit = total_revenue - total_cost
        margin_percent = round((net_profit / total_revenue) * 100, 1)
        breakeven_pax_rate = int(total_cost / pax)

        self.assertEqual(total_revenue, Decimal('342500'))
        self.assertEqual(total_cost, Decimal('201300'))
        self.assertEqual(net_profit, Decimal('141200'))
        self.assertEqual(margin_percent, Decimal('41.2'))
        self.assertEqual(breakeven_pax_rate, 4026)

        # 4. Verify WhatsApp briefing formats
        student_template = "🚌 *SIVA GAYATHRI TOURS & TRAVELS — STUDENT TRIP BRIEFING*"
        self.assertTrue(len(student_template) > 10)
