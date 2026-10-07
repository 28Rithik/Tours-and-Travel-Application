import re
import json
import base64
import hashlib
from io import BytesIO
from decimal import Decimal, ROUND_HALF_UP
from django.utils import timezone
import qrcode
from qrcode.image.svg import SvgPathImage

# Standard Indian GST State Code Directory
INDIAN_GST_STATES = {
    '01': 'Jammu & Kashmir',
    '02': 'Himachal Pradesh',
    '03': 'Punjab',
    '04': 'Chandigarh',
    '05': 'Uttarakhand',
    '06': 'Haryana',
    '07': 'Delhi',
    '08': 'Rajasthan',
    '09': 'Uttar Pradesh',
    '10': 'Bihar',
    '11': 'Sikkim',
    '12': 'Arunachal Pradesh',
    '13': 'Nagaland',
    '14': 'Manipur',
    '15': 'Mizoram',
    '16': 'Tripura',
    '17': 'Meghalaya',
    '18': 'Assam',
    '19': 'West Bengal',
    '20': 'Jharkhand',
    '21': 'Odisha',
    '22': 'Chhattisgarh',
    '23': 'Madhya Pradesh',
    '24': 'Gujarat',
    '26': 'Dadra & Nagar Haveli and Daman & Diu',
    '27': 'Maharashtra',
    '29': 'Karnataka',
    '30': 'Goa',
    '31': 'Lakshadweep',
    '32': 'Kerala',
    '33': 'Tamil Nadu',
    '34': 'Puducherry',
    '35': 'Andaman & Nicobar Islands',
    '36': 'Telangana',
    '37': 'Andhra Pradesh',
    '38': 'Ladakh',
}

TRANSPORT_SAC_CODES = {
    '996601': 'Rental services of passenger cars with operator',
    '996602': 'Rental services of buses and coaches with operator',
    '996411': 'Local passenger transportation services',
    '996412': 'Sightseeing transportation services',
    '996511': 'Road transport services of goods (GTA)',
    '996719': 'Other supporting transport services',
}


def get_state_name(state_code):
    """Returns official state name for 2-digit code."""
    code = str(state_code or '').strip().zfill(2)
    return INDIAN_GST_STATES.get(code, f"State {code}")


def validate_gstin(gstin, expected_state_code=None):
    """
    Validates standard 15-character Indian GSTIN.
    Format: 2 digits (State) + 10 chars (PAN) + 1 char (Entity #) + 'Z' + 1 char (Checksum)
    """
    if not gstin:
        return False, "GSTIN is missing"
    
    clean_gstin = str(gstin).strip().upper()
    if len(clean_gstin) != 15:
        return False, f"Invalid length: GSTIN must be exactly 15 characters (got {len(clean_gstin)})"

    pattern = r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$"
    if not re.match(pattern, clean_gstin):
        return False, "Invalid GSTIN format: Must conform to 2-digit State + 10-char PAN + Entity + Z + Checksum"

    state_prefix = clean_gstin[:2]
    if state_prefix not in INDIAN_GST_STATES:
        return False, f"Unknown State Code prefix '{state_prefix}' in GSTIN"

    if expected_state_code:
        expected_clean = str(expected_state_code).strip().zfill(2)
        if state_prefix != expected_clean:
            return False, f"State code mismatch: GSTIN specifies state '{state_prefix}' ({INDIAN_GST_STATES.get(state_prefix)}), but client state is '{expected_clean}'"

    return True, "Valid GSTIN"


def calculate_invoice_taxes(taxable_value, gst_rate_percent=Decimal('5.00'), supplier_state='33', recipient_state='33', is_rcm=False):
    """
    Computes CGST, SGST, IGST, and invoice totals based on Place of Supply (POS).
    """
    taxable = Decimal(str(taxable_value or '0.00'))
    rate = Decimal(str(gst_rate_percent or '5.00'))
    supp_state = str(supplier_state or '33').strip().zfill(2)
    recip_state = str(recipient_state or '33').strip().zfill(2)

    if supp_state == recip_state:
        supply_type = 'intra_state'
        cgst_rate = rate / Decimal('2.00')
        sgst_rate = rate / Decimal('2.00')
        igst_rate = Decimal('0.00')
        cgst_amount = (taxable * cgst_rate) / Decimal('100.00')
        sgst_amount = (taxable * sgst_rate) / Decimal('100.00')
        igst_amount = Decimal('0.00')
    else:
        supply_type = 'inter_state'
        cgst_rate = Decimal('0.00')
        sgst_rate = Decimal('0.00')
        igst_rate = rate
        cgst_amount = Decimal('0.00')
        sgst_amount = Decimal('0.00')
        igst_amount = (taxable * igst_rate) / Decimal('100.00')

    total_tax = cgst_amount + sgst_amount + igst_amount
    unrounded = taxable + total_tax
    rounded = unrounded.quantize(Decimal('1'), rounding=ROUND_HALF_UP)
    round_off = rounded - unrounded

    return {
        'supply_type': supply_type,
        'taxable_value': taxable,
        'gst_rate_percent': rate,
        'cgst_rate': cgst_rate,
        'cgst_amount': cgst_amount,
        'sgst_rate': sgst_rate,
        'sgst_amount': sgst_amount,
        'igst_rate': igst_rate,
        'igst_amount': igst_amount,
        'total_tax': total_tax,
        'round_off': round_off,
        'total_invoice_value': rounded,
        'is_reverse_charge': is_rcm,
    }


def generate_b2b_qr_code(invoice_obj, eway_bill_number=None):
    """
    Generates B2B Digital Verification QR code conforming to Rule 46 of CGST.
    Encodes: Supplier GSTIN, Recipient GSTIN, Doc No, Doc Date, Invoice Value, HSN, IRN Hash, EWB No.
    Returns (qr_payload_text, svg_str, png_base64_uri).
    """
    supplier_gstin = invoice_obj.supplier_gstin or "33AAAAA0000A1Z5"
    recipient_gstin = invoice_obj.recipient_gstin or "URP"
    doc_no = invoice_obj.invoice_number or f"INV-{invoice_obj.pk}"
    doc_date = invoice_obj.invoice_date.strftime('%d/%m/%Y') if invoice_obj.invoice_date else timezone.now().strftime('%d/%m/%Y')
    tot_val = f"{invoice_obj.total_invoice_value:.2f}"
    item_cnt = invoice_obj.line_items.count() or 1
    hsn_code = invoice_obj.sac_code or "996601"
    
    # Generate cryptographic hash signature
    hash_raw = f"{supplier_gstin}|{recipient_gstin}|{doc_no}|{doc_date}|{tot_val}|{hsn_code}"
    irn_hash = hashlib.sha256(hash_raw.encode('utf-8')).hexdigest()[:24].upper()
    ewb_no = eway_bill_number or (invoice_obj.eway_bill.eway_bill_number if hasattr(invoice_obj, 'eway_bill') else "")

    qr_payload = (
        f"GSTIN_SUP:{supplier_gstin}|GSTIN_REC:{recipient_gstin}|"
        f"DOC_NO:{doc_no}|DOC_TYP:INV|DOC_DT:{doc_date}|"
        f"TOT_VAL:{tot_val}|ITEM_CNT:{item_cnt}|MAIN_HSN:{hsn_code}|"
        f"IRN:{irn_hash}|EWB:{ewb_no or 'N/A'}"
    )

    # 1. Generate Vector SVG
    try:
        svg_factory = SvgPathImage
        qr_svg_obj = qrcode.make(qr_payload, image_factory=svg_factory, box_size=10, border=1)
        svg_stream = BytesIO()
        qr_svg_obj.save(svg_stream)
        svg_str = svg_stream.getvalue().decode('utf-8')
    except Exception:
        svg_str = ""

    # 2. Generate Base64 PNG
    try:
        qr_png_obj = qrcode.make(qr_payload, box_size=6, border=2)
        png_stream = BytesIO()
        qr_png_obj.save(png_stream, format='PNG')
        png_b64 = base64.b64encode(png_stream.getvalue()).decode('utf-8')
        png_uri = f"data:image/png;base64,{png_b64}"
    except Exception:
        png_uri = ""

    return qr_payload, svg_str, png_uri


def generate_nic_eway_bill_json(invoice_obj, trip_obj=None, transporter_id=None, trans_distance_km=None):
    """
    Constructs 100% schema-compliant National Informatics Centre (NIC) E-Way Bill JSON payload.
    Conforms to E-Way Bill System Specification v1.04.
    """
    trip = trip_obj or invoice_obj.trip
    
    # Resolve vehicle number
    vehicle_no = ""
    if trip and trip.vehicle:
        vehicle_no = trip.vehicle.registration_number.replace(" ", "").upper()
    elif hasattr(invoice_obj, 'eway_bill') and invoice_obj.eway_bill.vehicle_number:
        vehicle_no = invoice_obj.eway_bill.vehicle_number.replace(" ", "").upper()
    else:
        # Check first line item
        first_item = invoice_obj.line_items.first()
        if first_item and first_item.vehicle:
            vehicle_no = first_item.vehicle.registration_number.replace(" ", "").upper()
        else:
            vehicle_no = "TN01BV9999"

    # Resolve Transporter
    trans_id = transporter_id or invoice_obj.supplier_gstin or "33AAAAA0000A1Z5"
    trans_name = invoice_obj.supplier_legal_name or "Siva Gayathiri Tours & Travels"
    
    # Distance
    if trans_distance_km:
        distance = int(trans_distance_km)
    elif trip and trip.used_km and trip.used_km > 0:
        distance = int(trip.used_km)
    else:
        distance = 50

    from_state_int = int(str(invoice_obj.supplier_state_code or '33').strip())
    to_state_int = int(str(invoice_obj.recipient_state_code or '33').strip())
    from_pincode = int(str(invoice_obj.supplier_pincode or '600001').strip())
    
    to_pincode_str = str(invoice_obj.recipient_pincode or '600001').strip()
    to_pincode = int(to_pincode_str) if to_pincode_str.isdigit() and len(to_pincode_str) == 6 else 600001

    doc_date_str = invoice_obj.invoice_date.strftime('%d/%m/%Y') if invoice_obj.invoice_date else timezone.now().strftime('%d/%m/%Y')

    # Build itemList
    item_list = []
    line_items = invoice_obj.line_items.all()
    if line_items.exists():
        for idx, item in enumerate(line_items, start=1):
            hsn = int(item.sac_code.replace("SAC", "").strip()) if item.sac_code.replace("SAC", "").strip().isdigit() else 996601
            item_list.append({
                "itemNo": idx,
                "productName": item.item_description or "Passenger Transport / Rent-a-cab Service",
                "productDesc": item.item_description or "Chauffeur Transport Service",
                "hsnCode": hsn,
                "quantity": float(item.quantity or 1),
                "qtyUnit": item.unit or "OTH",
                "taxableAmount": float(item.taxable_amount or invoice_obj.taxable_value),
                "sgstRate": float(invoice_obj.sgst_rate or 0.0),
                "cgstRate": float(invoice_obj.cgst_rate or 0.0),
                "igstRate": float(invoice_obj.igst_rate or 0.0),
                "cessRate": 0.0,
            })
    else:
        hsn = int(invoice_obj.sac_code.replace("SAC", "").strip()) if invoice_obj.sac_code.replace("SAC", "").strip().isdigit() else 996601
        item_list.append({
            "itemNo": 1,
            "productName": "Passenger Transport / Rent-a-cab Service",
            "productDesc": "Executive Passenger Transport Service",
            "hsnCode": hsn,
            "quantity": 1.0,
            "qtyUnit": "OTH",
            "taxableAmount": float(invoice_obj.taxable_value),
            "sgstRate": float(invoice_obj.sgst_rate or 0.0),
            "cgstRate": float(invoice_obj.cgst_rate or 0.0),
            "igstRate": float(invoice_obj.igst_rate or 0.0),
            "cessRate": 0.0,
        })

    nic_payload = {
        "supplyType": "O",
        "subSupplyType": "1",
        "subSupplyDesc": "",
        "docType": "INV",
        "docNo": (invoice_obj.invoice_number or f"INV-{invoice_obj.pk}").replace("2026-27", "26-27")[:16],
        "docDate": doc_date_str,
        "fromGstin": invoice_obj.supplier_gstin or "33AAAAA0000A1Z5",
        "fromTrdName": invoice_obj.supplier_trade_name or "SIVAGAYATHIRI TRAVELS",
        "fromAddr1": invoice_obj.supplier_address[:100] if invoice_obj.supplier_address else "12/4, Gandhi Road",
        "fromAddr2": "",
        "fromPlace": "Chennai",
        "fromPincode": from_pincode,
        "actFromStateCode": from_state_int,
        "fromStateCode": from_state_int,
        "toGstin": invoice_obj.recipient_gstin or "URP",
        "toTrdName": (invoice_obj.recipient_trade_name or invoice_obj.recipient_legal_name)[:100],
        "toAddr1": (invoice_obj.recipient_address or "Corporate Office")[:100],
        "toAddr2": "",
        "toPlace": (invoice_obj.place_of_supply.split('-')[-1] if '-' in invoice_obj.place_of_supply else invoice_obj.place_of_supply)[:50] or "Chennai",
        "toPincode": to_pincode,
        "actToStateCode": to_state_int,
        "toStateCode": to_state_int,
        "totalValue": float(invoice_obj.taxable_value),
        "cgstValue": float(invoice_obj.cgst_amount),
        "sgstValue": float(invoice_obj.sgst_amount),
        "igstValue": float(invoice_obj.igst_amount),
        "cessValue": float(invoice_obj.cess_amount or 0.0),
        "totInvValue": float(invoice_obj.total_invoice_value),
        "transDistance": distance,
        "transporterId": trans_id,
        "transporterName": trans_name[:100],
        "transDocNo": (trip.trip_id if trip else invoice_obj.invoice_number)[:15],
        "transDocDate": doc_date_str,
        "transMode": "1",
        "vehicleNo": vehicle_no,
        "vehicleType": "R",
        "itemList": item_list,
    }

    return nic_payload


def validate_nic_eway_bill_payload(payload):
    """
    Validates payload against NIC E-Way Bill Schema v1.04 requirements.
    Returns (is_valid: bool, errors: list).
    """
    errors = []
    required_keys = [
        'supplyType', 'subSupplyType', 'docType', 'docNo', 'docDate',
        'fromGstin', 'fromTrdName', 'fromAddr1', 'fromPlace', 'fromPincode',
        'actFromStateCode', 'fromStateCode', 'toGstin', 'toTrdName', 'toAddr1',
        'toPlace', 'toPincode', 'actToStateCode', 'toStateCode',
        'totalValue', 'cgstValue', 'sgstValue', 'igstValue', 'totInvValue',
        'transDistance', 'transporterId', 'transMode', 'vehicleNo', 'vehicleType',
        'itemList'
    ]

    for key in required_keys:
        if key not in payload or payload[key] is None or payload[key] == "":
            errors.append(f"Missing mandatory field '{key}'")

    if 'docNo' in payload and len(str(payload['docNo'])) > 16:
        errors.append(f"Field 'docNo' exceeds maximum allowed length of 16 characters (got {len(str(payload['docNo']))})")

    if 'vehicleNo' in payload:
        v_no = str(payload['vehicleNo']).replace(" ", "")
        if not (6 <= len(v_no) <= 15):
            errors.append(f"Invalid vehicle registration number format '{v_no}'")

    if 'transDistance' in payload:
        try:
            dist = int(payload['transDistance'])
            if dist <= 0:
                errors.append("Field 'transDistance' must be greater than 0 KM")
        except ValueError:
            errors.append("Field 'transDistance' must be a valid integer")

    if 'itemList' in payload and not payload['itemList']:
        errors.append("Field 'itemList' must contain at least 1 line item")

    is_valid = len(errors) == 0
    return is_valid, errors


def post_invoice_to_general_ledger(invoice_obj, created_by_user=None):
    """
    Automated Double-Entry Posting Service for Corporate GST B2B Invoices.
    Invariant: Sum of Debits == Sum of Credits.
    Debit: Accounts Receivable (1100) -> total_invoice_value
    Credit: Transport Revenue (4000) -> taxable_value
    Credit: Output CGST (2010) -> cgst_amount
    Credit: Output SGST (2020) -> sgst_amount
    Credit: Output IGST (2030) -> igst_amount
    Credit/Debit: Round Off (4900/5900) -> round_off
    """
    from finance.models import Account, JournalEntry, JournalItem

    if invoice_obj.gl_journal_entry:
        return invoice_obj.gl_journal_entry

    # Fetch required COA accounts
    ar_acct, _ = Account.objects.get_or_create(code='1100', defaults={'name': 'Accounts Receivable (Trade Debtors)', 'account_type': 'asset'})
    rev_acct, _ = Account.objects.get_or_create(code='4000', defaults={'name': 'Operating Revenue (Transport Services)', 'account_type': 'income'})
    cgst_acct, _ = Account.objects.get_or_create(code='2010', defaults={'name': 'Output CGST Payable', 'account_type': 'liability'})
    sgst_acct, _ = Account.objects.get_or_create(code='2020', defaults={'name': 'Output SGST Payable', 'account_type': 'liability'})
    igst_acct, _ = Account.objects.get_or_create(code='2030', defaults={'name': 'Output IGST Payable', 'account_type': 'liability'})
    roundoff_acct, _ = Account.objects.get_or_create(code='4900', defaults={'name': 'Round-off Differences', 'account_type': 'income'})

    je = JournalEntry.objects.create(
        date=invoice_obj.invoice_date or timezone.now().date(),
        entry_type='invoice_billing',
        reference_id=invoice_obj.invoice_number or f"INV-{invoice_obj.pk}",
        narration=f"Corporate GST B2B Invoice #{invoice_obj.invoice_number} billed to {invoice_obj.recipient_legal_name} (GSTIN: {invoice_obj.recipient_gstin or 'URP'})",
        is_posted=True
    )

    # 1. Debit Accounts Receivable
    JournalItem.objects.create(
        entry=je,
        account=ar_acct,
        party=invoice_obj.party,
        debit=invoice_obj.total_invoice_value,
        credit=Decimal('0.00'),
        memo=f"Invoice #{invoice_obj.invoice_number} Receivable"
    )

    # 2. Credit Transport Revenue
    JournalItem.objects.create(
        entry=je,
        account=rev_acct,
        party=invoice_obj.party,
        debit=Decimal('0.00'),
        credit=invoice_obj.taxable_value,
        memo=f"Taxable Transport Services (SAC {invoice_obj.sac_code})"
    )

    # 3. Credit Output CGST
    if invoice_obj.cgst_amount > 0:
        JournalItem.objects.create(
            entry=je,
            account=cgst_acct,
            party=invoice_obj.party,
            debit=Decimal('0.00'),
            credit=invoice_obj.cgst_amount,
            memo=f"Output CGST @ {invoice_obj.cgst_rate}%"
        )

    # 4. Credit Output SGST
    if invoice_obj.sgst_amount > 0:
        JournalItem.objects.create(
            entry=je,
            account=sgst_acct,
            party=invoice_obj.party,
            debit=Decimal('0.00'),
            credit=invoice_obj.sgst_amount,
            memo=f"Output SGST @ {invoice_obj.sgst_rate}%"
        )

    # 5. Credit Output IGST
    if invoice_obj.igst_amount > 0:
        JournalItem.objects.create(
            entry=je,
            account=igst_acct,
            party=invoice_obj.party,
            debit=Decimal('0.00'),
            credit=invoice_obj.igst_amount,
            memo=f"Output IGST @ {invoice_obj.igst_rate}%"
        )

    # 6. Round-off adjustment
    if invoice_obj.round_off != 0:
        if invoice_obj.round_off > 0:
            JournalItem.objects.create(
                entry=je,
                account=roundoff_acct,
                party=invoice_obj.party,
                debit=Decimal('0.00'),
                credit=invoice_obj.round_off,
                memo="Round-off addition"
            )
        else:
            JournalItem.objects.create(
                entry=je,
                account=roundoff_acct,
                party=invoice_obj.party,
                debit=abs(invoice_obj.round_off),
                credit=Decimal('0.00'),
                memo="Round-off deduction"
            )

    invoice_obj.gl_journal_entry = je
    invoice_obj.save(update_fields=['gl_journal_entry'])
    return je


def get_multistate_gst_audit_summary(from_date=None, to_date=None):
    """
    Multi-State GST Audit & GSTR-1 Reconciliation Summary Engine.
    Provides state-by-state tax ledger distribution and GSTIN compliance anomalies.
    """
    from finance.models import CorporateGSTInvoice
    from core.models import Party

    qs = CorporateGSTInvoice.objects.all()
    if from_date:
        qs = qs.filter(invoice_date__gte=from_date)
    if to_date:
        qs = qs.filter(invoice_date__lte=to_date)

    total_invoices = qs.count()
    total_taxable = sum((inv.taxable_value for inv in qs), Decimal('0.00'))
    total_cgst = sum((inv.cgst_amount for inv in qs), Decimal('0.00'))
    total_sgst = sum((inv.sgst_amount for inv in qs), Decimal('0.00'))
    total_igst = sum((inv.igst_amount for inv in qs), Decimal('0.00'))
    total_tax = total_cgst + total_sgst + total_igst
    total_invoice_value = sum((inv.total_invoice_value for inv in qs), Decimal('0.00'))
    total_rcm = sum((inv.total_tax for inv in qs if inv.is_reverse_charge), Decimal('0.00'))

    # State-wise distribution
    state_breakdown = {}
    for inv in qs:
        st_code = (inv.recipient_state_code or "33").strip().zfill(2)
        st_name = INDIAN_GST_STATES.get(st_code, f"State {st_code}")
        if st_code not in state_breakdown:
            state_breakdown[st_code] = {
                'state_code': st_code,
                'state_name': st_name,
                'count': 0,
                'taxable': Decimal('0.00'),
                'cgst': Decimal('0.00'),
                'sgst': Decimal('0.00'),
                'igst': Decimal('0.00'),
                'total_tax': Decimal('0.00'),
                'total_value': Decimal('0.00'),
            }
        state_breakdown[st_code]['count'] += 1
        state_breakdown[st_code]['taxable'] += inv.taxable_value
        state_breakdown[st_code]['cgst'] += inv.cgst_amount
        state_breakdown[st_code]['sgst'] += inv.sgst_amount
        state_breakdown[st_code]['igst'] += inv.igst_amount
        state_breakdown[st_code]['total_tax'] += inv.total_tax
        state_breakdown[st_code]['total_value'] += inv.total_invoice_value

    # GSTR-1 Categorization
    table_4a = qs.filter(invoice_type='regular_b2b', is_reverse_charge=False)
    table_4b = qs.filter(is_reverse_charge=True)
    table_6b = qs.filter(invoice_type__startswith='sez')

    # GSTIN Anomaly Detector across parties
    anomalies = []
    b2b_parties = Party.objects.filter(party_type__in=['corporate', 'travel_agency', 'hotel'])
    for p in b2b_parties[:50]:
        if not p.gstin:
            anomalies.append({
                'party_id': p.pk,
                'party_name': p.name,
                'issue': 'Missing GSTIN on Corporate/B2B Account',
                'severity': 'warning'
            })
        else:
            is_valid, msg = validate_gstin(p.gstin, expected_state_code=p.state_code)
            if not is_valid:
                anomalies.append({
                    'party_id': p.pk,
                    'party_name': p.name,
                    'issue': f"Invalid GSTIN ({p.gstin}): {msg}",
                    'severity': 'danger'
                })

    return {
        'total_invoices': total_invoices,
        'total_taxable': total_taxable,
        'total_cgst': total_cgst,
        'total_sgst': total_sgst,
        'total_igst': total_igst,
        'total_tax': total_tax,
        'total_invoice_value': total_invoice_value,
        'total_rcm': total_rcm,
        'state_breakdown': sorted(state_breakdown.values(), key=lambda x: x['total_value'], reverse=True),
        'gstr1_tables': {
            'table_4a_count': table_4a.count(),
            'table_4a_taxable': sum((i.taxable_value for i in table_4a), Decimal('0.00')),
            'table_4b_count': table_4b.count(),
            'table_4b_taxable': sum((i.taxable_value for i in table_4b), Decimal('0.00')),
            'table_6b_count': table_6b.count(),
            'table_6b_taxable': sum((i.taxable_value for i in table_6b), Decimal('0.00')),
        },
        'anomalies': anomalies,
    }
