import calendar
from datetime import date, datetime
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import models
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from core.models import Driver, Party
from fleet_contracts.models import ContractMonthlyInvoice, ContractTripLog
from operations.models import Booking, TrafficFine, Trip
from statements.models import GeneratedStatement

from .export_services import (
    calculate_driver_duty_days,
    generate_batch_payroll,
    generate_monthly_driver_payslip,
    generate_tally_expense_xml,
    generate_tally_sales_xml,
    generate_zoho_expense_csv,
    generate_zoho_sales_csv,
)
from .models import (
    DriverAdvance,
    DriverPayslip,
    DriverSalaryProfile,
    FastagTollDeduction,
    FuelRecord,
    Payment,
    TripExpense,
)


@login_required
def api_payment_context(request):
    booking_id = request.GET.get('booking_id')
    trip_id = request.GET.get('trip_id')
    contract_trip_id = request.GET.get('contract_trip_id')
    statement_id = request.GET.get('statement_id')

    data = {}

    if booking_id:
        try:
            booking = Booking.objects.get(pk=booking_id)
            data['party_id'] = booking.party_id
            amount = (booking.quoted_price or 0) - booking.advance_received
            data['balance'] = str(max(amount, 0))
        except Booking.DoesNotExist:
            pass

    elif trip_id:
        try:
            trip = Trip.objects.get(pk=trip_id)
            data['party_id'] = trip.party_id
            data['balance'] = str(trip.balance)
        except Trip.DoesNotExist:
            pass

    elif contract_trip_id:
        try:
            ct = ContractTripLog.objects.get(pk=contract_trip_id)
            data['party_id'] = ct.shift.route.contract.customer_id
        except ContractTripLog.DoesNotExist:
            pass

    elif statement_id:
        try:
            stmt = GeneratedStatement.objects.get(pk=statement_id)
            data['party_id'] = stmt.party_id

            total_received = Payment.objects.filter(statement=stmt).aggregate(
                total=models.Sum('amount')
            )['total'] or 0
            balance = stmt.closing_balance - total_received
            data['balance'] = str(max(balance, 0))
        except GeneratedStatement.DoesNotExist:
            pass

    return JsonResponse(data)


# ==============================================================================
# PHASE 3: FINANCIAL & GOVERNANCE INTEGRATION VIEWS
# ==============================================================================

@login_required
def accounting_export_dashboard(request):
    """
    Central hub for Tally Prime, Zoho Books financial data exports, and
    automated duty-attendance driver payroll generation.
    """
    now = timezone.now()
    default_year = now.year
    default_month = now.month
    _, last_day = calendar.monthrange(default_year, default_month)
    default_from_date = date(default_year, default_month, 1).strftime('%Y-%m-%d')
    default_to_date = date(default_year, default_month, last_day).strftime('%Y-%m-%d')

    from_date_str = request.GET.get('from_date', default_from_date)
    to_date_str = request.GET.get('to_date', default_to_date)
    
    try:
        from_date = datetime.strptime(from_date_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        from_date = date(default_year, default_month, 1)
        from_date_str = from_date.strftime('%Y-%m-%d')

    try:
        to_date = datetime.strptime(to_date_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        to_date = date(default_year, default_month, last_day)
        to_date_str = to_date.strftime('%Y-%m-%d')

    selected_year = int(request.GET.get('year', default_year))
    selected_month = int(request.GET.get('month', default_month))

    # --- 1. Sales Invoices Query ---
    trips_qs = Trip.objects.filter(
        status__in=['completed', 'billed', 'settled'],
        start_date__gte=from_date,
        start_date__lte=to_date,
    ).select_related('party', 'vehicle', 'driver').order_by('-start_date')

    contract_invoices_qs = ContractMonthlyInvoice.objects.filter(
        billing_month__gte=from_date,
        billing_month__lte=to_date,
    ).exclude(status='draft').select_related('contract__customer').order_by('-billing_month')

    trips_revenue = sum((trip.total_amount for trip in trips_qs), Decimal('0.00'))
    contract_revenue = contract_invoices_qs.aggregate(total=models.Sum('grand_total'))['total'] or Decimal('0.00')
    total_sales_revenue = trips_revenue + contract_revenue
    total_sales_count = trips_qs.count() + contract_invoices_qs.count()

    # --- 2. Expense & Fuel Vouchers Query ---
    fuel_qs = FuelRecord.objects.filter(
        date__gte=from_date,
        date__lte=to_date,
    ).select_related('vehicle', 'petro_account').order_by('-date')
    fuel_total = sum((f.amount for f in fuel_qs), Decimal('0.00'))

    expenses_qs = TripExpense.objects.filter(
        date__gte=from_date,
        date__lte=to_date,
        paid_by__in=['company', 'driver'],
    ).select_related('trip', 'contract_trip').order_by('-date')
    expenses_total = expenses_qs.aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')

    fastag_qs = FastagTollDeduction.objects.filter(
        date__date__gte=from_date,
        date__date__lte=to_date,
    ).select_related('account', 'vehicle').order_by('-date')
    fastag_total = fastag_qs.aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')

    total_expense_amount = fuel_total + expenses_total + fastag_total
    total_expense_count = fuel_qs.count() + expenses_qs.count() + fastag_qs.count()

    # --- 3. Driver Payroll & Attendance ---
    active_drivers = Driver.objects.filter(status='active').order_by('name')
    payslips = DriverPayslip.objects.filter(
        month=selected_month,
        year=selected_year,
    ).select_related('driver').order_by('driver__name')

    payroll_total_net = sum((p.net_payable for p in payslips), Decimal('0.00'))
    payroll_total_gross = sum((p.gross_earnings for p in payslips), Decimal('0.00'))
    payroll_total_deductions = sum((p.total_deductions for p in payslips), Decimal('0.00'))

    # Month selection helper list
    months_list = [
        (1, 'January'), (2, 'February'), (3, 'March'), (4, 'April'),
        (5, 'May'), (6, 'June'), (7, 'July'), (8, 'August'),
        (9, 'September'), (10, 'October'), (11, 'November'), (12, 'December')
    ]
    years_list = [default_year - 1, default_year, default_year + 1]

    context = {
        'from_date': from_date_str,
        'to_date': to_date_str,
        'selected_month': selected_month,
        'selected_year': selected_year,
        'months_list': months_list,
        'years_list': years_list,
        
        # Sales KPIs
        'total_sales_count': total_sales_count,
        'total_sales_revenue': total_sales_revenue,
        'trips_count': trips_qs.count(),
        'trips_revenue': trips_revenue,
        'contract_invoices_count': contract_invoices_qs.count(),
        'contract_revenue': contract_revenue,
        'recent_trips': trips_qs[:10],
        'recent_contract_invoices': contract_invoices_qs[:10],

        # Expense KPIs
        'total_expense_count': total_expense_count,
        'total_expense_amount': total_expense_amount,
        'fuel_count': fuel_qs.count(),
        'fuel_total': fuel_total,
        'expenses_count': expenses_qs.count(),
        'expenses_total': expenses_total,
        'fastag_count': fastag_qs.count(),
        'fastag_total': fastag_total,
        'recent_fuel': fuel_qs[:10],
        'recent_expenses': expenses_qs[:10],
        'recent_fastag': fastag_qs[:10],

        # Payroll KPIs
        'active_drivers_count': active_drivers.count(),
        'payslips_count': payslips.count(),
        'payroll_total_gross': payroll_total_gross,
        'payroll_total_deductions': payroll_total_deductions,
        'payroll_total_net': payroll_total_net,
        'payslips': payslips,
    }
    return render(request, 'finance/accounting_dashboard.html', context)


@login_required
def export_tally_sales_view(request):
    """Downloads standard Tally Prime Sales XML for the selected date range."""
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    party_id = request.GET.get('party_id')

    xml_content = generate_tally_sales_xml(from_date, to_date, party_id)
    filename = f"tally_sales_{from_date or 'all'}_to_{to_date or 'all'}.xml"

    response = HttpResponse(xml_content, content_type='application/xml; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@login_required
def export_tally_expenses_view(request):
    """Downloads standard Tally Prime Expenses & Fuel XML for the selected date range."""
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')

    xml_content = generate_tally_expense_xml(from_date, to_date)
    filename = f"tally_expenses_{from_date or 'all'}_to_{to_date or 'all'}.xml"

    response = HttpResponse(xml_content, content_type='application/xml; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@login_required
def export_zoho_sales_view(request):
    """Downloads Zoho Books compatible CSV for customer invoices."""
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    party_id = request.GET.get('party_id')

    csv_content = generate_zoho_sales_csv(from_date, to_date, party_id)
    filename = f"zoho_sales_{from_date or 'all'}_to_{to_date or 'all'}.csv"

    response = HttpResponse(csv_content, content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@login_required
def export_zoho_expenses_view(request):
    """Downloads Zoho Books compatible CSV for operational fleet expenses."""
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')

    csv_content = generate_zoho_expense_csv(from_date, to_date)
    filename = f"zoho_expenses_{from_date or 'all'}_to_{to_date or 'all'}.csv"

    response = HttpResponse(csv_content, content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@login_required
def run_batch_payroll_view(request):
    """Trigger 1-click batch payroll run for all active drivers."""
    if request.method != 'POST':
        return redirect('accounting-export')

    month = int(request.POST.get('month', timezone.now().month))
    year = int(request.POST.get('year', timezone.now().year))

    res = generate_batch_payroll(month, year)

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'status': 'success',
            'month': month,
            'year': year,
            'payslips_count': res['payslips_count'],
            'total_net_payable': str(res['total_net_payable']),
            'total_duty_days': res['total_duty_days'],
        })

    messages.success(
        request,
        f"Batch payroll for {calendar.month_name[month]} {year} executed successfully! "
        f"{res['payslips_count']} driver payslips generated (Total Net: ₹{res['total_net_payable']:,.2f}, Total Duty Days: {res['total_duty_days']})."
    )
    return redirect(f"{redirect('accounting-export').url}?month={month}&year={year}")


@login_required
def driver_payslip_detail_view(request, payslip_id):
    """Renders a printable driver payslip."""
    payslip = get_object_or_404(DriverPayslip.objects.select_related('driver'), pk=payslip_id)
    driver = payslip.driver

    # Detailed attendance info
    attendance = calculate_driver_duty_days(driver, payslip.month, payslip.year)

    # Itemized deductions
    _, last_day = calendar.monthrange(payslip.year, payslip.month)
    start_of_month = date(payslip.year, payslip.month, 1)
    end_of_month = date(payslip.year, payslip.month, last_day)

    fines = TrafficFine.objects.filter(
        driver=driver,
        financial_responsibility='driver',
        paid_by__in=['company', 'unpaid'],
        date_of_offence__date__gte=start_of_month,
        date_of_offence__date__lte=end_of_month,
    )
    advances = DriverAdvance.objects.filter(
        driver=driver,
        date__gte=start_of_month,
        date__lte=end_of_month,
    )

    context = {
        'payslip': payslip,
        'driver': driver,
        'profile': getattr(driver, 'salary_profile', None),
        'attendance': attendance,
        'fines': fines,
        'advances': advances,
        'month_name': calendar.month_name[payslip.month],
    }
    return render(request, 'finance/payslip_detail.html', context)
