from django.test import TestCase
from django.core.exceptions import ValidationError
from datetime import date
from core.models import Client
from fleet_contracts.models import TransportContract

class FleetContractsHardeningTests(TestCase):
    def setUp(self):
        self.client = Client.objects.create(name='School A', phone='123')
        self.contract1 = TransportContract.objects.create(
            customer=self.client,
            name='Term 1',
            start_date=date(2025, 1, 1),
            end_date=date(2025, 6, 30),
            status='active'
        )

    def test_overlap_active_contracts(self):
        contract2 = TransportContract(
            customer=self.client,
            name='Term 2 overlapping',
            start_date=date(2025, 5, 1), # Overlaps with Term 1
            end_date=date(2025, 12, 31),
            status='active'
        )
        with self.assertRaises(ValidationError) as cm:
            contract2.clean()
        self.assertIn('An active contract', str(cm.exception))

    def test_draft_does_not_overlap(self):
        contract2 = TransportContract(
            customer=self.client,
            name='Term 2 Draft',
            start_date=date(2025, 5, 1),
            end_date=date(2025, 12, 31),
            status='draft'
        )
        contract2.clean() # Should not raise
