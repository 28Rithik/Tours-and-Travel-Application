import datetime
import calendar
import json
from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Q, Count
from django.utils import timezone

from core.models import Driver, Vehicle, Party
from fleet_contracts.models import (
    TransportContract,
    Route,
    Shift,
    ContractTripLog,
    ContractSLAPenalty,
    ContractMonthlyInvoice,
)
from finance.models import (
    CorporateGSTInvoice,
    InvoiceLineItem,
    DriverAllowanceLedger,
    DriverAdvance,
)
from fleet_contracts.billing_engine import ContractBillingEngine


# ==============================================================================
# DOMAIN 6: TARIFF, BILLING & CONTRACT REVENUE STUDIO
# ==============================================================================

@login_required
def contract_billing_studio_view(request):
    """
    Contract Tariff, Billing & Revenue Studio.
    Provides corporate monthly billing reconciliation, SLA penalties deduction,
    GST Rule 46 invoicing, and contract revenue metrics.
    """
    now = timezone.now().date()
    year = int(request.GET.get('year', now.year))
    month = int(request.GET.get('month', now.month))
    contract_filter = request.GET.get('contract_id')
    status_filter = request.GET.get('status')

    # Query Invoices
    invoices_qs = ContractMonthlyInvoice.objects.select_related(
        'contract', 'contract__customer'
    ).order_by('-billing_month', '-id')

    if contract_filter:
        invoices_qs = invoices_qs.filter(contract_id=contract_filter)
    if status_filter:
        invoices_qs = invoices_qs.filter(status=status_filter)

    invoices = list(invoices_qs[:50])

    # High Level Financial KPIs
    all_invoices = ContractMonthlyInvoice.objects.all()
    total_revenue = all_invoices.aggregate(t=Sum('grand_total'))['t'] or Decimal('0.00')
    paid_revenue = all_invoices.filter(status='paid').aggregate(t=Sum('grand_total'))['t'] or Decimal('0.00')
    pending_revenue = all_invoices.filter(
        status__in=['generated', 'draft', 'partially_paid']
    ).aggregate(t=Sum('grand_total'))['t'] or Decimal('0.00')
    total_sla_penalties = all_invoices.aggregate(t=Sum('sla_penalty_deduction'))['t'] or Decimal('0.00')

    # Contracts Available for Invoicing
    active_contracts = TransportContract.objects.filter(status='active').select_related('customer').order_by('name')

    # Months list for dropdown
    month_choices = [
        (m, calendar.month_name[m]) for m in range(1, 13)
    ]
    year_choices = [now.year - 1, now.year, now.year + 1]

    context = {
        'invoices': invoices,
        'active_contracts': active_contracts,
        'current_year': year,
        'current_month': month,
        'current_month_name': calendar.month_name[month],
        'current_contract_id': int(contract_filter) if contract_filter else None,
        'current_status': status_filter,
        'month_choices': month_choices,
        'year_choices': year_choices,
        'total_revenue': total_revenue,
        'paid_revenue': paid_revenue,
        'pending_revenue': pending_revenue,
        'total_sla_penalties': total_sla_penalties,
    }
    return render(request, 'finance/contract_billing_studio.html', context)


@login_required
def contract_invoice_detail_view(request, invoice_id):
    """
    Renders official corporate GST tax invoice detail with line items and QR code.
    """
    invoice = get_object_or_404(
        ContractMonthlyInvoice.objects.select_related('contract', 'contract__customer'),
        pk=invoice_id
    )
    gst_invoice = CorporateGSTInvoice.objects.filter(invoice_number=invoice.invoice_number).first()
    line_items = gst_invoice.line_items.all() if gst_invoice else []

    context = {
        'invoice': invoice,
        'gst_invoice': gst_invoice,
        'line_items': line_items,
        'contract': invoice.contract,
        'customer': invoice.contract.customer,
    }
    return render(request, 'finance/contract_invoice_detail.html', context)


@login_required
def driver_commute_bhatta_view(request):
    """
    Corporate Commute Chauffeur Duty Bhatta & Night Shift Allowance Ledger.
    """
    now = timezone.now().date()
    from_date_str = request.GET.get('from_date', now.replace(day=1).strftime('%Y-%m-%d'))
    to_date_str = request.GET.get('to_date', now.strftime('%Y-%m-%d'))

    try:
        from_date = datetime.datetime.strptime(from_date_str, '%Y-%m-%d').date()
    except ValueError:
        from_date = now.replace(day=1)

    try:
        to_date = datetime.datetime.strptime(to_date_str, '%Y-%m-%d').date()
    except ValueError:
        to_date = now

    driver_filter = request.GET.get('driver_id')

    # Gather drivers who have completed commute shifts
    active_drivers_qs = Driver.objects.filter(
        contracttriplog__date__gte=from_date,
        contracttriplog__date__lte=to_date
    ).distinct()

    if driver_filter:
        active_drivers_qs = active_drivers_qs.filter(id=driver_filter)

    drivers_summary = []
    total_bhatta_accrued = Decimal('0.00')
    total_night_bonuses = Decimal('0.00')
    total_net_payable = Decimal('0.00')

    for d in active_drivers_qs[:50]:
        calc = ContractBillingEngine.calculate_driver_commute_bhatta(d.id, from_date, to_date)
        drivers_summary.append(calc)
        total_bhatta_accrued += Decimal(str(calc['standard_bata']))
        total_night_bonuses += Decimal(str(calc['night_allowance'] + calc['early_morning_allowance']))
        total_net_payable += Decimal(str(calc['net_payable']))

    all_drivers = Driver.objects.filter(status__in=['available', 'active']).order_by('name')[:60]

    context = {
        'from_date': from_date.strftime('%Y-%m-%d'),
        'to_date': to_date.strftime('%Y-%m-%d'),
        'drivers_summary': drivers_summary,
        'all_drivers': all_drivers,
        'current_driver_id': int(driver_filter) if driver_filter else None,
        'total_bhatta_accrued': total_bhatta_accrued,
        'total_night_bonuses': total_night_bonuses,
        'total_net_payable': total_net_payable,
    }
    return render(request, 'finance/driver_commute_bhatta.html', context)


# ==============================================================================
# REST APIs FOR REVENUE, INVOICING & SETTLEMENTS
# ==============================================================================

@login_required
def api_billing_reconcile_preview(request):
    """
    GET API: Previews monthly commute contract billing reconciliation.
    """
    contract_id = request.GET.get('contract_id')
    if not contract_id:
        return JsonResponse({"status": "error", "message": "contract_id is required."}, status=400)

    now = timezone.now().date()
    year = int(request.GET.get('year', now.year))
    month = int(request.GET.get('month', now.month))

    try:
        res = ContractBillingEngine.reconcile_monthly_contract(int(contract_id), year, month)
        return JsonResponse({"status": "success", "data": res})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


@csrf_exempt
@login_required
def api_billing_generate_invoice(request):
    """
    POST API: Generates ContractMonthlyInvoice and CorporateGSTInvoice.
    """
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "POST method required."}, status=405)

    data = {}
    if request.content_type == 'application/json' and request.body:
        try:
            data = json.loads(request.body)
        except Exception:
            data = {}
    else:
        data = request.POST

    contract_id = data.get('contract_id')
    if not contract_id:
        return JsonResponse({"status": "error", "message": "contract_id is required."}, status=400)

    now = timezone.now().date()
    year = int(data.get('year', now.year))
    month = int(data.get('month', now.month))
    force_recreate = str(data.get('force_recreate', 'false')).lower() in ['true', '1', 'yes']

    try:
        res = ContractBillingEngine.generate_monthly_invoice(
            contract_id=int(contract_id),
            year=year,
            month=month,
            force_recreate=force_recreate
        )
        return JsonResponse(res)
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


@login_required
def api_billing_driver_bhatta(request):
    """
    GET API: Fetches duty bhatta audit breakdown for a driver.
    """
    driver_id = request.GET.get('driver_id')
    if not driver_id:
        return JsonResponse({"status": "error", "message": "driver_id is required."}, status=400)

    now = timezone.now().date()
    from_date_str = request.GET.get('from_date', now.replace(day=1).strftime('%Y-%m-%d'))
    to_date_str = request.GET.get('to_date', now.strftime('%Y-%m-%d'))

    try:
        from_date = datetime.datetime.strptime(from_date_str, '%Y-%m-%d').date()
        to_date = datetime.datetime.strptime(to_date_str, '%Y-%m-%d').date()
        calc = ContractBillingEngine.calculate_driver_commute_bhatta(int(driver_id), from_date, to_date)
        return JsonResponse({"status": "success", "data": calc})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


@csrf_exempt
@login_required
def api_billing_settle_bhatta(request):
    """
    POST API: Settles chauffeur commute bhatta into DriverAllowanceLedger.
    """
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "POST method required."}, status=405)

    data = {}
    if request.content_type == 'application/json' and request.body:
        try:
            data = json.loads(request.body)
        except Exception:
            data = {}
    else:
        data = request.POST

    driver_id = data.get('driver_id')
    if not driver_id:
        return JsonResponse({"status": "error", "message": "driver_id is required."}, status=400)

    now = timezone.now().date()
    from_date_str = data.get('from_date', now.replace(day=1).strftime('%Y-%m-%d'))
    to_date_str = data.get('to_date', now.strftime('%Y-%m-%d'))
    payment_mode = data.get('payment_mode', 'bank_transfer')
    reference = data.get('reference', '')
    notes = data.get('notes', '')

    try:
        from_date = datetime.datetime.strptime(from_date_str, '%Y-%m-%d').date()
        to_date = datetime.datetime.strptime(to_date_str, '%Y-%m-%d').date()
        res = ContractBillingEngine.settle_driver_commute_bhatta(
            driver_id=int(driver_id),
            from_date=from_date,
            to_date=to_date,
            payment_mode=payment_mode,
            reference=reference,
            notes=notes
        )
        return JsonResponse(res)
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)
