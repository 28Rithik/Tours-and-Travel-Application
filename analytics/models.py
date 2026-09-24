from django.db import models
from django.utils import timezone
from core.models import Driver


class ReportLog(models.Model):
    report_name = models.CharField(max_length=255)
    generated_at = models.DateTimeField(auto_now_add=True)
    generated_by = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.report_name} ({self.generated_at.strftime('%Y-%m-%d')})"


class DriverScorecard(models.Model):
    GRADE_CHOICES = [
        ('A+', 'A+ (Elite - Star Captain)'),
        ('A', 'A (Excellent)'),
        ('B', 'B (Good / Standard)'),
        ('C', 'C (Needs Improvement)'),
        ('D', 'D (At Risk / Safety Review)'),
    ]

    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, related_name='scorecards')
    month = models.DateField(default=timezone.now, help_text="First day of the evaluation period")
    period_type = models.CharField(max_length=20, default='monthly', choices=[('monthly', 'Monthly Snapshot'), ('custom', 'Custom Period')])

    # Volume & Experience
    total_trips = models.PositiveIntegerField(default=0)
    completed_trips = models.PositiveIntegerField(default=0)
    total_kms_driven = models.PositiveIntegerField(default=0)

    # 1. Punctuality (25% Weight)
    on_time_trips = models.PositiveIntegerField(default=0)
    delayed_trips = models.PositiveIntegerField(default=0)
    punctuality_score = models.DecimalField(max_digits=5, decimal_places=2, default=100.0)

    # 2. Safety & Driving Infractions (30% Weight)
    overspeeding_count = models.PositiveIntegerField(default=0)
    harsh_braking_count = models.PositiveIntegerField(default=0)
    traffic_fines_count = models.PositiveIntegerField(default=0)
    total_fine_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    safety_score = models.DecimalField(max_digits=5, decimal_places=2, default=100.0)

    # 3. Customer Rating & Hospitality (25% Weight)
    feedback_count = models.PositiveIntegerField(default=0)
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=5.0)
    customer_rating_score = models.DecimalField(max_digits=5, decimal_places=2, default=100.0)

    # 4. Fuel Eco-Driving Efficiency (20% Weight)
    expected_fuel_litres = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    actual_fuel_litres = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    fuel_efficiency_score = models.DecimalField(max_digits=5, decimal_places=2, default=100.0)

    # Composite Outcome
    overall_composite_score = models.DecimalField(max_digits=5, decimal_places=2, default=100.0)
    grade = models.CharField(max_length=5, choices=GRADE_CHOICES, default='A')
    notes = models.TextField(blank=True)
    computed_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-month', '-overall_composite_score']
        unique_together = ('driver', 'month', 'period_type')
        verbose_name = "Driver Performance Scorecard"
        verbose_name_plural = "Driver Performance Scorecards"

    def __str__(self):
        return f"{self.driver.name} - {self.month.strftime('%b %Y')} ({self.grade} - {self.overall_composite_score}%)"

