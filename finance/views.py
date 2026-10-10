import calendar
from datetime import date, datetime
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
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
    generate_gstr1_b2b_csv,
    generate_itc_reconciliation_csv,
    generate_monthly_driver_payslip,
    generate_tally_expense_xml,
    generate_tally_sales_xml,
    generate_zoho_expense_csv,
    generate_zoho_sales_csv,
    reconcile_input_tax_credit,
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


# ==============================================================================
# CORPORATE GST B2B INVOICING & NIC E-WAY BILL STUDIO
# ==============================================================================

from .models import CorporateGSTInvoice, InvoiceLineItem, EWayBill
from .gst_engine import (
    INDIAN_GST_STATES,
    TRANSPORT_SAC_CODES,
    calculate_invoice_taxes,
    validate_gstin,
    generate_b2b_qr_code,
    generate_nic_eway_bill_json,
    validate_nic_eway_bill_payload,
    post_invoice_to_general_ledger,
    get_multistate_gst_audit_summary,
    get_state_name,
)
import json


@login_required
def admin_gst_studio_view(request):
    """
    Enterprise Django Unfold Corporate GST B2B Invoicing & E-Way Bill Generation Studio.
    Provides multi-state tax breakdown, NIC schema validator, live invoice generator, and audit desk.
    """
    summary = get_multistate_gst_audit_summary()
    recent_invoices = CorporateGSTInvoice.objects.select_related('party', 'trip', 'eway_bill').order_by('-id')[:30]
    active_eway_bills = EWayBill.objects.select_related('invoice').order_by('-id')[:30]
    available_trips = Trip.objects.select_related('party', 'vehicle', 'driver').order_by('-id')[:40]
    corporate_parties = Party.objects.filter(party_type__in=['corporate', 'travel_agency', 'hotel']).order_by('name')

    selected_inv_id = request.GET.get('inv')
    selected_invoice = None
    if selected_inv_id and selected_inv_id.isdigit():
        selected_invoice = CorporateGSTInvoice.objects.filter(pk=int(selected_inv_id)).first()

    context = {
        'title': 'Corporate GST B2B Invoicing & NIC E-Way Bill Studio',
        'summary': summary,
        'recent_invoices': recent_invoices,
        'active_eway_bills': active_eway_bills,
        'available_trips': available_trips,
        'corporate_parties': corporate_parties,
        'sac_codes': TRANSPORT_SAC_CODES,
        'states': INDIAN_GST_STATES,
        'selected_invoice': selected_invoice,
        'current_tab': request.GET.get('tab', 'overview'),
    }
    return render(request, 'admin/finance/gst_studio.html', context)


@login_required
def api_generate_corporate_invoice_eway(request):
    """
    API endpoint: 1-Click Generation of Corporate GST B2B Invoice, NIC E-Way Bill, QR Stamping,
    and automatic balanced Double-Entry posting to General Ledger.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed. Use POST.'}, status=405)

    try:
        if request.content_type == 'application/json':
            payload = json.loads(request.body.decode('utf-8'))
        else:
            payload = request.POST.dict()

        trip_id = payload.get('trip_id')
        party_id = payload.get('party_id')
        taxable_value = Decimal(str(payload.get('taxable_value') or '0.00'))
        gst_rate = Decimal(str(payload.get('gst_rate_percent') or '5.00'))
        sac_code = str(payload.get('sac_code') or '996601').strip()
        is_rcm = str(payload.get('is_reverse_charge', '')).lower() in ['true', '1', 'on', 'yes']
        recip_state = str(payload.get('recipient_state_code') or '').strip().zfill(2)
        vehicle_no = str(payload.get('vehicle_number') or '').strip().replace(" ", "").upper()
        distance_km = int(payload.get('trans_distance_km') or 50)
        auto_eway = str(payload.get('auto_generate_eway', 'true')).lower() in ['true', '1', 'on', 'yes']

        trip = None
        if trip_id and str(trip_id).isdigit():
            trip = Trip.objects.filter(pk=int(trip_id)).select_related('party', 'vehicle', 'driver').first()

        party = None
        if party_id and str(party_id).isdigit():
            party = Party.objects.filter(pk=int(party_id)).first()
        elif trip and trip.party:
            party = trip.party

        if not party:
            return JsonResponse({'success': False, 'error': 'Please select a valid Corporate Client / Party.'}, status=400)

        # Fallback values from trip or defaults
        if taxable_value <= 0:
            if trip:
                taxable_value = trip.fixed_amount if trip.billing_model == 'fixed' and trip.fixed_amount > 0 else (trip.total_amount or Decimal('5000.00'))
            else:
                taxable_value = Decimal('5000.00')

        if not vehicle_no and trip and trip.vehicle:
            vehicle_no = trip.vehicle.registration_number.replace(" ", "").upper()
        if not vehicle_no:
            vehicle_no = "TN01BV9999"

        if not recip_state:
            recip_state = (party.state_code or "33").strip().zfill(2)

        # 1. Create CorporateGSTInvoice
        invoice = CorporateGSTInvoice(
            party=party,
            trip=trip,
            invoice_type='regular_b2b',
            supplier_legal_name="Siva Gayathiri Tours & Travels",
            supplier_trade_name="Sivagayathiri Travels",
            supplier_gstin="33AAAAA0000A1Z5",
            supplier_state_code="33",
            supplier_address="12/4, Gandhi Road, Chennai, Tamil Nadu - 600001",
            supplier_pincode="600001",
            recipient_legal_name=party.name,
            recipient_trade_name=party.name,
            recipient_gstin=party.gstin or "",
            recipient_state_code=recip_state,
            recipient_address=party.address or f"Corporate Office, {get_state_name(recip_state)}",
            recipient_pincode="600001",
            place_of_supply=f"{recip_state}-{get_state_name(recip_state)}",
            is_reverse_charge=is_rcm,
            sac_code=sac_code,
            taxable_value=taxable_value,
            gst_rate_percent=gst_rate,
        )
        invoice.save()

        # 2. Create Line Item
        item_desc = f"Chauffeur-Driven Passenger Transport ({sac_code})"
        if trip:
            item_desc = f"Trip #{trip.trip_id}: {trip.pickup_location} ➔ {trip.destination} ({vehicle_no})"

        InvoiceLineItem.objects.create(
            invoice=invoice,
            item_description=item_desc,
            sac_code=sac_code,
            vehicle=trip.vehicle if trip else None,
            trip=trip,
            quantity=Decimal('1.00'),
            unit="TRIP",
            rate=taxable_value,
            taxable_amount=taxable_value,
            cgst_amount=invoice.cgst_amount,
            sgst_amount=invoice.sgst_amount,
            igst_amount=invoice.igst_amount,
            total_amount=invoice.total_invoice_value,
        )

        # 3. Generate B2B Verification QR Code
        qr_payload, svg_str, png_uri = generate_b2b_qr_code(invoice)
        invoice.qr_code_data = qr_payload
        invoice.qr_code_svg = svg_str
        invoice.save(update_fields=['qr_code_data', 'qr_code_svg'])

        # 4. Generate Official NIC E-Way Bill if requested
        eway_bill = None
        nic_json = {}
        if auto_eway:
            nic_json = generate_nic_eway_bill_json(
                invoice_obj=invoice,
                trip_obj=trip,
                trans_distance_km=distance_km
            )
            is_valid, validation_errors = validate_nic_eway_bill_payload(nic_json)

            eway_bill = EWayBill.objects.create(
                invoice=invoice,
                supply_type="O",
                sub_supply_type="1",
                doc_type="INV",
                transporter_id=invoice.supplier_gstin,
                transporter_name=invoice.supplier_legal_name,
                trans_distance_km=distance_km,
                trans_mode="1",
                vehicle_number=vehicle_no,
                vehicle_type="R",
                nic_payload_json=nic_json,
                status='active',
                qr_code_svg=svg_str
            )

        # 5. Post to General Ledger
        gl_entry = post_invoice_to_general_ledger(invoice)

        return JsonResponse({
            'success': True,
            'invoice_id': invoice.pk,
            'invoice_number': invoice.invoice_number,
            'invoice_date': invoice.invoice_date.strftime('%d-%m-%Y'),
            'total_invoice_value': float(invoice.total_invoice_value),
            'taxable_value': float(invoice.taxable_value),
            'total_tax': float(invoice.total_tax),
            'cgst_amount': float(invoice.cgst_amount),
            'sgst_amount': float(invoice.sgst_amount),
            'igst_amount': float(invoice.igst_amount),
            'supply_type': invoice.get_supply_type_display(),
            'eway_bill_id': eway_bill.pk if eway_bill else None,
            'eway_bill_number': eway_bill.eway_bill_number if eway_bill else None,
            'gl_journal_entry': gl_entry.entry_number if gl_entry else None,
            'nic_json': nic_json,
            'qr_code_svg': svg_str,
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def api_export_nic_eway_json(request, invoice_id):
    """
    Returns official downloadable NIC E-Way Bill JSON file conforming to Schema v1.04.
    """
    invoice = get_object_or_404(CorporateGSTInvoice, pk=invoice_id)
    if hasattr(invoice, 'eway_bill') and invoice.eway_bill.nic_payload_json:
        payload = invoice.eway_bill.nic_payload_json
    else:
        payload = generate_nic_eway_bill_json(invoice)

    filename = f"NIC_EWB_{invoice.invoice_number.replace('/', '_')}.json"
    response = HttpResponse(
        json.dumps(payload, indent=2),
        content_type='application/json'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@login_required
def corporate_invoice_print_view(request, invoice_id):
    """
    Rule 46 CGST Compliant Tax Invoice & Duty Slip with Digital QR Stamping.
    """
    invoice = get_object_or_404(
        CorporateGSTInvoice.objects.select_related('party', 'trip', 'gl_journal_entry'),
        pk=invoice_id
    )
    if not invoice.qr_code_svg:
        _, svg_str, _ = generate_b2b_qr_code(invoice)
        invoice.qr_code_svg = svg_str
        invoice.save(update_fields=['qr_code_svg'])

    line_items = invoice.line_items.select_related('vehicle').all()

    # Convert total amount to words helper
    def amount_to_words(amt):
        try:
            from num2words import num2words
            return num2words(int(amt), lang='en_IN').title() + " Rupees Only"
        except Exception:
            return f"Rupees {int(amt):,} Only"

    context = {
        'invoice': invoice,
        'line_items': line_items,
        'eway_bill': getattr(invoice, 'eway_bill', None),
        'amount_words': amount_to_words(invoice.total_invoice_value),
        'company_bank': {
            'bank_name': 'ICICI Bank Ltd',
            'branch': 'T. Nagar Branch, Chennai',
            'account_name': 'Siva Gayathiri Tours & Travels',
            'account_number': '000905029988',
            'ifsc_code': 'ICIC0000009',
            'upi_id': 'sivagayathiritravels@icici',
        }
    }
    return render(request, 'finance/corporate_tax_invoice.html', context)


@login_required
def corporate_invoice_pdf_view(request, invoice_id):
    """
    Renders official downloadable/printable GST Tax Invoice PDF.
    """
    from operations.pdf_generator import render_tax_invoice_pdf
    invoice = get_object_or_404(CorporateGSTInvoice, pk=invoice_id)
    pdf_bytes = render_tax_invoice_pdf(invoice)
    filename = f"TaxInvoice-{invoice.invoice_number or invoice.id}.pdf"

    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    disposition = 'attachment' if request.GET.get('download') == '1' else 'inline'
    response['Content-Disposition'] = f'{disposition}; filename="{filename}"'
    return response


@login_required
def export_gstr1_b2b_view(request):
    """
    GSTR-1 B2B e-Invoice CSV download.
    Generates ClearTax/Zoho/Tally-compatible GSTR-1 Table 4A CSV.
    """
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')

    csv_content = generate_gstr1_b2b_csv(from_date=from_date, to_date=to_date)
    response = HttpResponse(csv_content, content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="GSTR1_B2B_{timezone.now().strftime("%Y%m%d")}.csv"'
    return response


@login_required
def export_itc_reconciliation_view(request):
    """
    ITC Reconciliation CSV download.
    Cross-references purchase-side input tax credits for GSTR-3B filing.
    """
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')

    csv_content = generate_itc_reconciliation_csv(from_date=from_date, to_date=to_date)
    response = HttpResponse(csv_content, content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="ITC_Reconciliation_{timezone.now().strftime("%Y%m%d")}.csv"'
    return response


@csrf_exempt
@login_required
def api_dispatch_corporate_invoice_whatsapp(request, invoice_id):
    """
    1-Click WhatsApp Delivery of Corporate GST Tax Invoice & E-Way Bill.
    Constructs luxury tax invoice summary, stamps live PDF print link,
    and dispatches via WhatsApp Business Engine to the recipient party.
    """
    invoice = get_object_or_404(
        CorporateGSTInvoice.objects.select_related('party', 'trip', 'eway_bill'),
        pk=invoice_id
    )

    custom_phone = None
    if request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8'))
            custom_phone = data.get('phone')
        except Exception:
            custom_phone = request.POST.get('phone')
    else:
        custom_phone = request.GET.get('phone')

    from operations.whatsapp_bot import dispatch_corporate_invoice_whatsapp

    # Build clean base URL
    base_url = request.build_absolute_uri('/')[:-1]
    result = dispatch_corporate_invoice_whatsapp(invoice, recipient_phone=custom_phone, base_url=base_url)

    is_success = result.get('status') == 'success'
    target_phone = result.get('phone', custom_phone or getattr(invoice.party, 'phone', ''))

    return JsonResponse({
        'success': is_success,
        'status': result.get('status'),
        'invoice_id': invoice.id,
        'invoice_number': invoice.invoice_number,
        'recipient_phone': target_phone,
        'message': f"Invoice {invoice.invoice_number} successfully dispatched to {target_phone} via WhatsApp!" if is_success else result.get('reason', 'Failed to dispatch WhatsApp invoice.'),
        'result': result
    })


# ==============================================================================
# Phase 5: Petty Cash Float Register & Driver/Tour Manager Cash Wallet Studio
# ==============================================================================

@login_required
def admin_petty_cash_studio_view(request):
    """
    Cashier & Dispatcher Control Studio for user-level petty cash float registers,
    cash disbursement vouchers, receipts audit, and running balances.
    """
    from .models import PettyCashAccount, PettyCashTransaction
    from core.models import Driver

    # Ensure default accounts exist
    if not PettyCashAccount.objects.exists():
        PettyCashAccount.objects.create(
            account_name="Coimbatore Main Depot Float",
            account_type="branch",
            allocated_limit=Decimal('50000.00'),
            current_balance=Decimal('25000.00'),
            warning_threshold=Decimal('5000.00'),
            notes="Central garage petty cash box for spot purchases and toll reloads"
        )
        first_driver = Driver.objects.filter(status='active').first()
        if first_driver:
            PettyCashAccount.objects.create(
                account_name=f"Driver Float - {first_driver.name}",
                account_type="driver",
                holder_driver=first_driver,
                allocated_limit=Decimal('15000.00'),
                current_balance=Decimal('8500.00'),
                warning_threshold=Decimal('2000.00'),
                notes=f"Active travel float issued to {first_driver.name}"
            )
        PettyCashAccount.objects.create(
            account_name="Emergency Breakdown & Spot Repair Float",
            account_type="dispatcher",
            allocated_limit=Decimal('20000.00'),
            current_balance=Decimal('12000.00'),
            warning_threshold=Decimal('3000.00'),
            notes="Dispatcher standby fund for highway towing and spot tyre replacement"
        )

    accounts = PettyCashAccount.objects.filter(is_active=True).select_related('holder_user', 'holder_driver')
    
    # Recalculate balances to ensure accuracy
    for acc in accounts:
        if acc.transactions.exists():
            acc.recalculate_balance()

    total_circulation = sum((acc.current_balance for acc in accounts), Decimal('0.00'))
    
    today = timezone.localtime().date()
    today_txns = PettyCashTransaction.objects.filter(date=today, status__in=['approved', 'submitted'])
    today_disbursed = sum((t.amount for t in today_txns if t.transaction_type in ['expense', 'trip_advance']), Decimal('0.00'))
    today_topups = sum((t.amount for t in today_txns if t.transaction_type in ['top_up', 'settlement_refund']), Decimal('0.00'))
    
    pending_audits = PettyCashTransaction.objects.filter(status='submitted').count()
    low_balance_accounts = [acc for acc in accounts if acc.is_low_balance]

    # Filtered transactions
    txns = PettyCashTransaction.objects.select_related('account', 'trip', 'authorized_by').order_by('-date', '-created_at')
    
    acc_filter = request.GET.get('account_id')
    cat_filter = request.GET.get('category')
    status_filter = request.GET.get('status')
    
    if acc_filter:
        txns = txns.filter(account_id=acc_filter)
    if cat_filter:
        txns = txns.filter(category=cat_filter)
    if status_filter:
        txns = txns.filter(status=status_filter)

    txns = txns[:100]

    trips = Trip.objects.filter(status__in=['booked', 'assigned', 'started']).order_by('-id')[:50]
    drivers = Driver.objects.filter(status='active').order_by('name')

    return render(request, 'finance/petty_cash_studio.html', {
        'accounts': accounts,
        'transactions': txns,
        'total_circulation': total_circulation,
        'today_disbursed': today_disbursed,
        'today_topups': today_topups,
        'pending_audits': pending_audits,
        'low_balance_count': len(low_balance_accounts),
        'low_balance_accounts': low_balance_accounts,
        'selected_account_id': acc_filter,
        'selected_category': cat_filter,
        'selected_status': status_filter,
        'categories': PettyCashTransaction.EXPENSE_CATEGORIES,
        'trips': trips,
        'drivers': drivers,
    })


@csrf_exempt
@login_required
def api_petty_cash_topup(request):
    """
    POST endpoint to top-up / replenish an active petty cash float.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)

    import json
    from .models import PettyCashAccount, PettyCashTransaction

    try:
        acc_id = None
        amount = Decimal('0.00')
        notes = ""
        ref_no = ""

        if request.content_type == 'application/json' and request.body:
            data = json.loads(request.body.decode('utf-8'))
            acc_id = data.get('account_id')
            amount = Decimal(str(data.get('amount', '0.00')))
            notes = data.get('notes', '').strip()
            ref_no = data.get('reference_number', '').strip()
        else:
            acc_id = request.POST.get('account_id')
            amount = Decimal(str(request.POST.get('amount', '0.00')))
            notes = request.POST.get('notes', '').strip()
            ref_no = request.POST.get('reference_number', '').strip()

        if not acc_id:
            return JsonResponse({'status': 'error', 'message': 'Account ID required.'}, status=400)
        if amount <= 0:
            return JsonResponse({'status': 'error', 'message': 'Top-up amount must be positive.'}, status=400)

        account = get_object_or_404(PettyCashAccount, pk=acc_id)

        txn = PettyCashTransaction.objects.create(
            account=account,
            transaction_type='top_up',
            category='top_up_receipt',
            amount=amount,
            notes=notes or f"Float replenishment authorized by {request.user.username}",
            status='approved',
            authorized_by=request.user,
            recipient_or_vendor=ref_no or "Central Cashier"
        )

        return JsonResponse({
            'status': 'success',
            'message': f'₹{amount:,.2f} added to {account.account_name}.',
            'voucher_number': txn.voucher_number,
            'new_balance': float(account.current_balance),
        })

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


@csrf_exempt
@login_required
def api_petty_cash_disburse(request):
    """
    POST endpoint to log an out-of-pocket cash expense voucher with receipt upload.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)

    import json
    from .models import PettyCashAccount, PettyCashTransaction

    try:
        acc_id = request.POST.get('account_id')
        amount_raw = request.POST.get('amount', '0.00')
        category = request.POST.get('category', 'toll_parking')
        vendor = request.POST.get('recipient_or_vendor', '').strip()
        notes = request.POST.get('notes', '').strip()
        trip_id = request.POST.get('trip_id')
        receipt_file = request.FILES.get('receipt_photo')

        if not acc_id and request.content_type == 'application/json' and request.body:
            data = json.loads(request.body.decode('utf-8'))
            acc_id = data.get('account_id')
            amount_raw = data.get('amount', '0.00')
            category = data.get('category', 'toll_parking')
            vendor = data.get('recipient_or_vendor', '').strip()
            notes = data.get('notes', '').strip()
            trip_id = data.get('trip_id')

        amount = Decimal(str(amount_raw or '0.00'))

        if not acc_id:
            return JsonResponse({'status': 'error', 'message': 'Account ID required.'}, status=400)
        if amount <= 0:
            return JsonResponse({'status': 'error', 'message': 'Expense amount must be positive.'}, status=400)

        account = get_object_or_404(PettyCashAccount, pk=acc_id)

        # Allow submission even if low, but flag if insufficient
        trip = Trip.objects.filter(pk=trip_id).first() if trip_id else None

        txn = PettyCashTransaction.objects.create(
            account=account,
            transaction_type='expense',
            category=category,
            amount=amount,
            recipient_or_vendor=vendor,
            notes=notes,
            trip=trip,
            receipt_photo=receipt_file,
            status='approved',
            authorized_by=request.user
        )

        return JsonResponse({
            'status': 'success',
            'message': f'Expense voucher {txn.voucher_number} of ₹{amount:,.2f} recorded.',
            'voucher_number': txn.voucher_number,
            'new_balance': float(account.current_balance),
            'category_display': txn.get_category_display(),
        })

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


@csrf_exempt
@login_required
def api_petty_cash_audit_action(request, txn_id):
    """
    1-Click Audit Approval or Rejection of Petty Cash Vouchers.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)

    import json
    from .models import PettyCashTransaction

    txn = get_object_or_404(PettyCashTransaction, pk=txn_id)

    try:
        action = 'approve'
        audit_notes = ''
        if request.body:
            try:
                data = json.loads(request.body.decode('utf-8'))
                action = data.get('action', 'approve')
                audit_notes = data.get('audit_notes', '')
            except Exception:
                pass
        if not audit_notes:
            action = request.POST.get('action', action)
            audit_notes = request.POST.get('audit_notes', audit_notes)

        if action == 'approve':
            txn.status = 'approved'
            txn.authorized_by = request.user
            txn.audit_notes = audit_notes or f"Approved by {request.user.username}"
        elif action == 'reject':
            txn.status = 'rejected'
            txn.authorized_by = request.user
            txn.audit_notes = audit_notes or f"Rejected by {request.user.username}"
        else:
            return JsonResponse({'status': 'error', 'message': f'Unknown action: {action}'}, status=400)

        txn.save(update_fields=['status', 'authorized_by', 'audit_notes', 'updated_at'])

        return JsonResponse({
            'status': 'success',
            'message': f'Voucher {txn.voucher_number} marked as {txn.get_status_display()}.',
            'new_status': txn.status,
            'account_balance': float(txn.account.current_balance),
        })

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


def api_petty_cash_stats(request):
    """
    GET endpoint returning summary statistics across all floats.
    """
    from .models import PettyCashAccount, PettyCashTransaction
    
    accounts = PettyCashAccount.objects.filter(is_active=True)
    total_circ = sum((a.current_balance for a in accounts), Decimal('0.00'))
    
    today = timezone.localtime().date()
    today_disbursed = PettyCashTransaction.objects.filter(
        date=today,
        transaction_type__in=['expense', 'trip_advance'],
        status__in=['approved', 'submitted']
    ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')

    pending_audits = PettyCashTransaction.objects.filter(status='submitted').count()
    low_balance_count = sum(1 for a in accounts if a.is_low_balance)

    return JsonResponse({
        'status': 'success',
        'total_circulation': float(total_circ),
        'today_disbursed': float(today_disbursed),
        'pending_audits': pending_audits,
        'low_balance_floats': low_balance_count,
        'active_accounts_count': accounts.count(),
    })


def driver_mobile_wallet_view(request, trip_id=None):
    """
    Driver & Tour Escort Mobile Cash Wallet.
    Displays running cash balance, fast spot expense logging, receipt snaps,
    and approved transaction logs directly on mobile devices.
    """
    from .models import PettyCashAccount, PettyCashTransaction
    from core.models import Driver

    trip = None
    if trip_id:
        trip = get_object_or_404(Trip.objects.select_related('driver', 'vehicle'), pk=trip_id)

    # Resolve driver account
    account = None
    if trip and trip.driver:
        account = PettyCashAccount.objects.filter(holder_driver=trip.driver, is_active=True).first()
    
    if not account:
        # Fallback to driver account linked to logged in user or first driver account
        account = PettyCashAccount.objects.filter(account_type='driver', is_active=True).first()
        if not account:
            account = PettyCashAccount.objects.filter(is_active=True).first()

    recent_txns = []
    if account:
        recent_txns = account.transactions.all().order_by('-date', '-created_at')[:20]

    return render(request, 'finance/driver_mobile_wallet.html', {
        'trip': trip,
        'account': account,
        'transactions': recent_txns,
        'categories': PettyCashTransaction.EXPENSE_CATEGORIES,
    })


# ==============================================================================
# Phase 5: Automated Bank Statement CSV Reconciler & UTR Matching Studio
# ==============================================================================

@login_required
def admin_bank_reconciliation_studio_view(request):
    """
    Dispatcher & Finance Control Studio for Automated Bank Statement Reconciliation.
    Uploads bank CSVs, matches UTR numbers & amounts against unpaid bookings/invoices,
    and 1-click executes double-entry customer receipt postings.
    """
    from .models import BankStatementUpload, BankStatementEntry
    from .bank_reconciliation import parse_bank_statement_csv, auto_match_statement_entries

    upload_id = request.GET.get('upload_id')
    selected_upload = None
    if upload_id:
        selected_upload = BankStatementUpload.objects.filter(pk=upload_id).first()
    
    if not selected_upload:
        selected_upload = BankStatementUpload.objects.order_by('-uploaded_at').first()

    uploads = BankStatementUpload.objects.all().order_by('-uploaded_at')[:15]
    
    entries = []
    if selected_upload:
        entries = selected_upload.entries.select_related('matched_booking', 'matched_invoice', 'matched_party', 'matched_payment').order_by('-deposit_amount', 'transaction_date')

    # Summary KPIs
    total_statements_count = BankStatementUpload.objects.count()
    total_deposits_all = BankStatementUpload.objects.aggregate(s=models.Sum('total_deposits'))['s'] or Decimal('0.00')
    total_reconciled_all = BankStatementUpload.objects.aggregate(s=models.Sum('reconciled_amount'))['s'] or Decimal('0.00')
    total_unmatched_entries = BankStatementEntry.objects.filter(status='unmatched', deposit_amount__gt=0).count()
    total_matched_entries = BankStatementEntry.objects.filter(status='matched').count()

    reconcile_percentage = 0
    if total_deposits_all > 0:
        reconcile_percentage = round(float(total_reconciled_all / total_deposits_all) * 100, 1)

    return render(request, 'finance/bank_reconciliation_studio.html', {
        'uploads': uploads,
        'selected_upload': selected_upload,
        'entries': entries,
        'total_statements_count': total_statements_count,
        'total_deposits_all': total_deposits_all,
        'total_reconciled_all': total_reconciled_all,
        'reconcile_percentage': reconcile_percentage,
        'total_unmatched_entries': total_unmatched_entries,
        'total_matched_entries': total_matched_entries,
    })


@login_required
@csrf_exempt
def api_bank_reconciliation_upload(request):
    """
    POST API to ingest a bank statement CSV file or raw text.
    Parses transactions, creates records, and runs auto-matching.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)

    from .models import BankStatementUpload, BankStatementEntry
    from .bank_reconciliation import parse_bank_statement_csv, auto_match_statement_entries

    bank_name = request.POST.get('bank_name', 'generic')
    account_number = request.POST.get('account_number', '')
    csv_file = request.FILES.get('statement_file')
    csv_text = request.POST.get('csv_text', '')

    filename = 'pasted_statement.csv'
    if csv_file:
        filename = csv_file.name
        content = csv_file.read()
    elif csv_text:
        content = csv_text
    else:
        return JsonResponse({'status': 'error', 'message': 'No CSV file or text provided'}, status=400)

    parsed_rows = parse_bank_statement_csv(content, bank_name=bank_name)
    if not parsed_rows:
        return JsonResponse({'status': 'error', 'message': 'Unable to parse any valid transactions from the provided CSV'}, status=400)

    upload = BankStatementUpload.objects.create(
        bank_name=bank_name,
        filename=filename,
        account_number=account_number,
        uploaded_by=request.user,
        total_transactions=len(parsed_rows),
    )

    created_entries = []
    for row in parsed_rows:
        entry = BankStatementEntry(
            upload=upload,
            transaction_date=row['transaction_date'],
            value_date=row.get('value_date') or row['transaction_date'],
            narration=row.get('narration', ''),
            reference_or_utr=row.get('reference_or_utr', ''),
            withdrawal_amount=row.get('withdrawal_amount', Decimal('0.00')),
            deposit_amount=row.get('deposit_amount', Decimal('0.00')),
            balance=row.get('balance', Decimal('0.00')),
        )
        created_entries.append(entry)

    BankStatementEntry.objects.bulk_create(created_entries)

    # Run auto-matching algorithm
    matched_count = auto_match_statement_entries(upload.entries.all())
    upload.update_summary_metrics()

    return JsonResponse({
        'status': 'success',
        'upload_id': upload.pk,
        'total_parsed': len(parsed_rows),
        'matched_count': matched_count,
        'message': f"Successfully parsed {len(parsed_rows)} transactions. {matched_count} auto-matched with ERP bookings/invoices."
    })


@login_required
@csrf_exempt
def api_bank_reconciliation_reconcile_entry(request, entry_id):
    """
    POST API to reconcile a single bank statement entry.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)

    from .models import BankStatementEntry
    from .bank_reconciliation import execute_bank_reconciliation

    entry = get_object_or_404(BankStatementEntry.objects.select_related('upload', 'matched_booking', 'matched_invoice', 'matched_party'), pk=entry_id)

    # Optional manual override from request body
    import json
    if request.body:
        try:
            data = json.loads(request.body)
            booking_id = data.get('booking_id')
            if booking_id:
                from operations.models import Booking
                bk = Booking.objects.filter(pk=booking_id).first()
                if bk:
                    entry.matched_booking = bk
                    entry.matched_party = bk.party
                    entry.match_confidence = 100
                    entry.match_reason = "Manually assigned by dispatcher"
                    entry.save()
        except Exception:
            pass

    payment = execute_bank_reconciliation(entry, user=request.user)

    return JsonResponse({
        'status': 'success',
        'entry_id': entry.pk,
        'payment_id': payment.pk,
        'payment_ref': payment.reference_number,
        'amount': float(payment.amount),
        'status_display': entry.get_status_display(),
        'message': f"Reconciled ₹{payment.amount:,.2f} as Payment #{payment.pk} ({payment.reference_number})."
    })


@login_required
@csrf_exempt
def api_bank_reconciliation_batch(request):
    """
    POST API to batch reconcile all confident matched entries in a statement upload.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)

    import json
    data = json.loads(request.body or '{}')
    upload_id = data.get('upload_id')
    min_confidence = int(data.get('min_confidence', 75))

    from .models import BankStatementUpload, BankStatementEntry
    from .bank_reconciliation import execute_bank_reconciliation

    upload = get_object_or_404(BankStatementUpload, pk=upload_id)
    target_entries = upload.entries.filter(
        status='matched',
        match_confidence__gte=min_confidence,
        deposit_amount__gt=0
    )

    reconciled_count = 0
    reconciled_total = Decimal('0.00')

    for entry in target_entries:
        try:
            p = execute_bank_reconciliation(entry, user=request.user)
            reconciled_count += 1
            reconciled_total += p.amount
        except Exception:
            continue

    upload.update_summary_metrics()

    return JsonResponse({
        'status': 'success',
        'reconciled_count': reconciled_count,
        'reconciled_total': float(reconciled_total),
        'message': f"Batch reconciled {reconciled_count} entries totaling ₹{reconciled_total:,.2f}."
    })


@login_required
def export_bank_reconciliation_report_view(request, upload_id=None):
    """
    Exports CSV reconciliation audit report for accountants / auditors.
    """
    import csv
    from django.http import HttpResponse
    from .models import BankStatementUpload, BankStatementEntry

    upload = None
    if upload_id:
        upload = get_object_or_404(BankStatementUpload, pk=upload_id)
        entries = upload.entries.all().order_by('-transaction_date')
        filename = f"Bank_Reconciliation_Statement_{upload.pk}_{timezone.now().strftime('%Y%m%d')}.csv"
    else:
        entries = BankStatementEntry.objects.all().order_by('-transaction_date')[:500]
        filename = f"All_Bank_Reconciliations_{timezone.now().strftime('%Y%m%d')}.csv"

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow([
        'Entry ID', 'Txn Date', 'Bank Name', 'Narration', 'UTR / Ref No',
        'Debit (₹)', 'Credit (₹)', 'Balance (₹)', 'Matched Booking',
        'Matched Customer', 'Confidence (%)', 'Match Reason', 'Status',
        'Reconciled Payment ID', 'Reconciled Date'
    ])

    for e in entries:
        writer.writerow([
            e.pk,
            e.transaction_date.strftime('%Y-%m-%d') if e.transaction_date else '',
            e.upload.get_bank_name_display() if e.upload else '',
            e.narration,
            e.reference_or_utr,
            f"{e.withdrawal_amount:.2f}",
            f"{e.deposit_amount:.2f}",
            f"{e.balance:.2f}",
            e.matched_booking.booking_number if e.matched_booking else '',
            e.matched_party.name if e.matched_party else (e.matched_booking.guest_name if e.matched_booking else ''),
            f"{e.match_confidence}%",
            e.match_reason,
            e.get_status_display(),
            e.matched_payment.reference_number if e.matched_payment else '',
            e.reconciled_at.strftime('%Y-%m-%d %H:%M') if e.reconciled_at else ''
        ])

    return response


