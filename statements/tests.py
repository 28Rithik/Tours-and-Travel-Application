from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.contrib.auth import get_user_model

from core.models import Party
from finance.models import Payment
from operations.models import Booking
from .renderers import render_excel, render_pdf
from .services import build_statement_rows
from finance.services import calculate_party_ledger
from .models import GeneratedStatement


class StatementTests(TestCase):
	def setUp(self):
		self.user = get_user_model().objects.create_user(username='tester', password='test-password-123')

	def test_payment_is_a_separate_row_and_exports_are_generated(self):
		party = Party.objects.create(name='Statement Party', party_type='corporate')
		Booking.objects.create(
			booking_number='BK-0003', party=party, guest_name='Guest', pickup_location='A',
			destination='B', pickup_date=date(2026, 4, 1), pickup_time='09:00',
			journey_type='local', vehicle_type='Sedan',
		)
		Payment.objects.create(
			party=party, date=date(2026, 4, 2), amount=Decimal('500'),
			payment_type='supplier_payment', payment_mode='cash',
		)
		ledger = calculate_party_ledger(party, date(2026, 4, 1), date(2026, 4, 30))
		rows = build_statement_rows(party, date(2026, 4, 1), date(2026, 4, 30))
		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0]['row_type'], 'payment')
		self.assertTrue(render_pdf(party, date(2026, 4, 1), date(2026, 4, 30), rows, ledger).startswith(b'%PDF'))
		self.assertTrue(render_excel(party, date(2026, 4, 1), date(2026, 4, 30), rows, ledger).startswith(b'PK'))

	def test_authenticated_statement_generation_persists_and_downloads(self):
		party = Party.objects.create(name='Mock Party', party_type='corporate')
		self.client.force_login(self.user)
		response = self.client.post('/statements/generate/', {
			'statement_type': 'party', 'party': party.pk, 'from_date': '2026-04-01', 'to_date': '2026-04-30', 'file_format': 'pdf',
		})
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response['Content-Type'], 'application/pdf')
		statement = GeneratedStatement.objects.get(party=party)
		download = self.client.get(f'/statements/{statement.pk}/download/')
		self.assertEqual(download.status_code, 200)
		self.assertTrue(download.content.startswith(b'%PDF'))
