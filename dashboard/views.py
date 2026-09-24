from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.utils import timezone
import datetime

from operations.models import Trip
from finance.models import FuelRecord
from maintenance.models import ComplianceDocument, DefectTicket

@login_required
def dashboard_home(request):
    now = timezone.now()
    first_day_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # 1. Active Operations
    active_trips_count = Trip.objects.filter(status='in_progress').count()
    
    # 2. Financial Health (Fuel Cost this month)
    # Note: fuel_price in FuelRecord is actually price_per_litre in the model logic
    # Total cost is fuel_quantity * fuel_price. Let's calculate it in Python if complex, or just use a raw metric
    fuel_records = FuelRecord.objects.filter(date__gte=first_day_of_month.date())
    fuel_this_month = sum([record.amount for record in fuel_records])
    
    # 3. Compliance Alerts
    fifteen_days_from_now = now.date() + datetime.timedelta(days=15)
    expiring_docs_count = ComplianceDocument.objects.filter(
        expiry_date__lte=fifteen_days_from_now
    ).count()
    
    # 4. Maintenance Alerts
    open_defects_count = DefectTicket.objects.filter(status='open').count()
    
    context = {
        'active_trips_count': active_trips_count,
        'fuel_this_month': fuel_this_month,
        'expiring_docs_count': expiring_docs_count,
        'open_defects_count': open_defects_count,
    }
    return render(request, 'dashboard/index.html', context)
