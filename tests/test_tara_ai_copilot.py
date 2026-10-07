"""
Automated Integration Tests for TARA AI Operations Copilot
Sivagayathiri Travels & Tours ERP
"""

import json
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from operations.tara_copilot import ask_tara, get_active_tours_summary, get_compliance_expiry_alerts, get_financial_revenue_overview


class TaraAiCopilotTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_superuser(username='testadmin', password='testpassword', email='admin@test.com')
        self.client.login(username='testadmin', password='testpassword')

    def test_01_quick_stats_endpoint(self):
        """Verify quick stats API returns real database metrics."""
        response = self.client.get(reverse('api-tara-quick-stats'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get('status'), 'success')
        self.assertIn('active_tours', data)
        self.assertIn('compliance_alerts', data)
        self.assertIn('collection_rate', data)
        print("\n[TEST 1 PASSED] Quick Stats:", data)

    def test_02_chat_active_tours_query(self):
        """Verify natural language query for active tours."""
        payload = {"message": "How many tours are running today?"}
        response = self.client.post(
            reverse('api-tara-chat'),
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get('status'), 'success')
        self.assertIn('reply', data)
        self.assertIn('active tours', data['reply'].lower())
        self.assertTrue(len(data.get('kpi_cards', [])) >= 2)
        print("[TEST 2 PASSED] Active Tours query succeeded. Cards count:", len(data['kpi_cards']))

    def test_03_chat_compliance_query(self):
        """Verify compliance and insurance expiry query."""
        payload = {"message": "Which vehicles need insurance renewal?"}
        response = self.client.post(
            reverse('api-tara-chat'),
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get('status'), 'success')
        self.assertIn('reply', data)
        self.assertTrue(len(data.get('kpi_cards', [])) >= 2)
        print("[TEST 3 PASSED] Compliance query succeeded. Cards count:", len(data['kpi_cards']))

    def test_04_chat_revenue_query(self):
        """Verify revenue collection query."""
        payload = {"message": "What is our revenue and collection rate this month?"}
        response = self.client.post(
            reverse('api-tara-chat'),
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get('status'), 'success')
        self.assertIn('collection', data['reply'].lower())
        print("[TEST 4 PASSED] Revenue query succeeded. Collection rate identified.")

    def test_05_chat_driver_safety_query(self):
        """Verify driver safety scorecard query."""
        payload = {"message": "Show driver safety scorecard anomalies"}
        response = self.client.post(
            reverse('api-tara-chat'),
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get('status'), 'success')
        print("[TEST 5 PASSED] Driver safety query succeeded.")

    def test_06_chat_fleet_availability_query(self):
        """Verify fleet availability query."""
        payload = {"message": "Which vehicles are available for tomorrow?"}
        response = self.client.post(
            reverse('api-tara-chat'),
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get('status'), 'success')
        self.assertIn('available', data['reply'].lower())
        print("[TEST 6 PASSED] Fleet availability query succeeded.")

    def test_07_studio_page_render(self):
        """Verify full-page TARA AI studio renders with HTTP 200."""
        response = self.client.get(reverse('admin-tara-copilot-studio'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'TARA AI Operations Business Brain')
        print("[TEST 7 PASSED] TARA Studio View Rendered successfully.")

