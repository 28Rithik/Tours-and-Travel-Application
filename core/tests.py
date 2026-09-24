from datetime import date

from django.core.exceptions import ValidationError
from django.test import TestCase

from .models import Driver, DriverEmploymentPeriod


class WorkforceTests(TestCase):
	def test_driver_can_have_separate_historical_rehire_periods(self):
		driver = Driver.objects.create(name='Arun Kumar')
		first = DriverEmploymentPeriod.objects.create(driver=driver, joined_on=date(2023, 9, 1), left_on=date(2024, 11, 30))
		second = DriverEmploymentPeriod.objects.create(driver=driver, joined_on=date(2025, 9, 1))
		self.assertEqual(driver.employment_periods.count(), 2)
		self.assertEqual(str(first), 'Arun Kumar (2023-09-01 - 2024-11-30)')
		with self.assertRaises(ValidationError):
			DriverEmploymentPeriod.objects.create(driver=driver, joined_on=date(2026, 1, 1)).full_clean()
