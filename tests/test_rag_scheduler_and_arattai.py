"""
Automated Test Suite for Rathasārathi RAG Knowledge Engine,
Background Scheduler & Zoho Arattai Gateway Integration
Sivagayathiri Travels & Tours ERP
"""

import json
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.urls import reverse

from operations.rag_engine import RAGKnowledgeEngine
from operations.tara_copilot import ask_tara
from operations.scheduler_engine import TravelERPScheduler
from integrations.models import IntegrationSettings, ArattaiMessageLog
from integrations.arattai_service import ArattaiBusinessService

User = get_user_model()


class RathasarathiRAGAndSchedulerTestCase(TestCase):
    def setUp(self):
        # Create staff user
        self.admin = User.objects.create_superuser(
            username='rag_admin',
            email='rag_admin@travelerp.com',
            password='Password@123'
        )
        self.client = Client()
        self.client.force_login(self.admin)

        # Enable Arattai in IntegrationSettings
        cfg = IntegrationSettings.get_settings()
        cfg.arattai_active = True
        cfg.save()

        # Seed RAG Knowledge Base in test DB
        call_command('seed_rag_knowledge_base')

    def test_01_rag_engine_index_and_search(self):
        """Validates that all knowledge docs index and yield grounded semantic matches."""
        results = RAGKnowledgeEngine.search("cancellation refund policy", top_k=3)
        self.assertTrue(len(results) > 0)
        top = results[0]
        self.assertIn("cancellation", top['document_title'].lower())
        self.assertGreater(top['score'], 0.1)

    def test_02_ask_tara_rag_grounded_response(self):
        """Validates that Rathasārathi AI returns grounded knowledge for policies."""
        res = ask_tara("What is the driver night bata rate and cancellation policy?")
        self.assertEqual(res['status'], 'success')
        self.assertIn("Customer Booking, Cancellation, Night Bata", res['reply'])
        self.assertTrue(len(res.get('kpi_cards', [])) >= 2)

    def test_03_travelerp_scheduler_runs_cleanly(self):
        """Validates that TravelERPScheduler executes database backup and compliance audit."""
        res = TravelERPScheduler.run_all_scheduled_tasks()
        self.assertEqual(res['status'], 'completed')
        self.assertIn(res['backup_job']['status'], ['success', 'completed'])
        self.assertEqual(res['compliance_watchdog']['status'], 'success')
        self.assertIsInstance(res['compliance_watchdog']['total_vehicle_alerts'], int)

    def test_04_scheduler_management_command(self):
        """Validates manage.py run_travelerp_scheduler --once."""
        call_command('run_travelerp_scheduler', once=True)

    def test_05_arattai_outbound_messaging_and_audit(self):
        """Validates outbound transactional message logging in ArattaiMessageLog."""
        res = ArattaiBusinessService.send_message(
            phone="9876543210",
            text="Your journey is confirmed with Sivagayathiri Travels!",
            message_type="booking_confirmed"
        )
        self.assertEqual(res['status'], 'success')
        self.assertEqual(res['recipient'], '919876543210')

        log = ArattaiMessageLog.objects.get(id=res['log_id'])
        self.assertEqual(log.direction, 'outbound')
        self.assertEqual(log.phone_number, '919876543210')

    def test_06_arattai_inbound_webhook_help_command(self):
        """Validates that inbound /help command receives helpful interactive prompt."""
        payload = {
            'sender': '919844112233',
            'sender_name': 'Meena Tour Leader',
            'text': '/help'
        }
        resp = self.client.post(
            '/api/integrations/arattai/webhook/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['status'], 'success')
        self.assertIn('Rathasārathi AI', data['reply'])

    def test_07_arattai_inbound_webhook_rag_inquiry(self):
        """Validates that inbound customer inquiry gets answered via Rathasārathi RAG."""
        payload = {
            'sender': '919844112233',
            'sender_name': 'Meena Tour Leader',
            'text': 'What are the temple dress code rules for Madurai Meenakshi?'
        }
        resp = self.client.post(
            '/api/integrations/arattai/webhook/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['status'], 'success')
        self.assertIn('Temple Dress Codes', data['reply'])

    def test_08_database_maintenance_api_endpoint(self):
        """Validates the /api/database-health/maintenance/ endpoint."""
        resp = self.client.get('/api/database-health/maintenance/')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['status'], 'completed')
        self.assertIn('backup_job', data)
        self.assertIn('compliance_watchdog', data)
