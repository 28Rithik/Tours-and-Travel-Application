"""
Automated NHAI FASTag CSV Statement Reconciler & Toll Plaza Auditor
Sivagayathiri Tours & Travels ERP

Parses bank / NETC FASTag CSV statements (ICICI, Axis, HDFC, SBI, NETC),
matches transactions against active Vehicle rosters and Trip schedules,
and applies corridor heuristic audits to detect off-route movements and ghost kilometers.
"""

import csv
import io
import re
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from django.utils import timezone
from django.db.models import Q

from core.models import Vehicle
from operations.models import Trip
from operations.route_estimator import CORRIDOR_MATRIX, estimate_route
from finance.models import CorporateFastagAccount, FastagTollDeduction


# Highway Corridor Toll Plaza Directory for South Indian Commercial Hubs
KNOWN_TOLL_PLAZAS = {
    'kaniyur': {'corridor': 'NH-544 (Salem - Coimbatore - Cochin)', 'state': 'Tamil Nadu'},
    'vijayamangalam': {'corridor': 'NH-544 (Salem - Coimbatore)', 'state': 'Tamil Nadu'},
    'walayar': {'corridor': 'NH-544 (TN-Kerala Border)', 'state': 'Kerala'},
    'paliakkara': {'corridor': 'NH-544 (Thrissur - Cochin)', 'state': 'Kerala'},
    'thoppur': {'corridor': 'NH-44 (Dharmapuri - Salem Ghats)', 'state': 'Tamil Nadu'},
    'krishnagiri': {'corridor': 'NH-44 (Hosur - Krishnagiri)', 'state': 'Tamil Nadu'},
    'attibele': {'corridor': 'NH-44 (Bangalore - Hosur Border)', 'state': 'Karnataka'},
    'omalur': {'corridor': 'NH-44 (Salem - Dharmapuri)', 'state': 'Tamil Nadu'},
    'rasampalayam': {'corridor': 'NH-44 (Salem - Namakkal)', 'state': 'Tamil Nadu'},
    'kappalur': {'corridor': 'NH-44 (Madurai Bypass)', 'state': 'Tamil Nadu'},
    'samayanallur': {'corridor': 'NH-44 (Dindigul - Madurai)', 'state': 'Tamil Nadu'},
    'paranur': {'corridor': 'NH-32 / GST Road (Chengalpattu)', 'state': 'Tamil Nadu'},
    'athur': {'corridor': 'NH-32 / GST Road (Tindivanam)', 'state': 'Tamil Nadu'},
    'sengurichi': {'corridor': 'NH-45 (Ulundurpet - Trichy)', 'state': 'Tamil Nadu'},
    'samayapuram': {'corridor': 'NH-45 (Trichy Bypass)', 'state': 'Tamil Nadu'},
    'uthandi': {'corridor': 'ECR (Chennai - Mamallapuram)', 'state': 'Tamil Nadu'},
    'sriperumbudur': {'corridor': 'NH-48 (Chennai - Ranipet)', 'state': 'Tamil Nadu'},
    'nemili': {'corridor': 'NH-48 (Sriperumbudur)', 'state': 'Tamil Nadu'},
    'chennasamudram': {'corridor': 'NH-48 (Ranipet)', 'state': 'Tamil Nadu'},
    'pallikonda': {'corridor': 'NH-48 (Vellore)', 'state': 'Tamil Nadu'},
    'vaniyambadi': {'corridor': 'NH-48 (Vaniyambadi - Ambur)', 'state': 'Tamil Nadu'},
    'coimbatore bypass': {'corridor': 'L&T Coimbatore Bypass', 'state': 'Tamil Nadu'},
}


def normalize_vrn(vrn_str):
    """Normalizes vehicle registration numbers: 'TN 38 BX 4411' -> 'TN38BX4411'"""
    if not vrn_str:
        return ''
    return re.sub(r'[^A-Z0-9]', '', str(vrn_str).upper())


def parse_date_smart(date_str):
    """Robust parser for varying bank statement datetime formats."""
    if not date_str:
        return None
    date_str = str(date_str).strip()
    formats = [
        '%d-%m-%Y %H:%M:%S',
        '%d/%m/%Y %H:%M:%S',
        '%Y-%m-%d %H:%M:%S',
        '%d-%m-%Y %H:%M',
        '%d/%m/%Y %H:%M',
        '%Y-%m-%d %H:%M',
        '%d-%b-%Y %H:%M:%S',
        '%d-%b-%Y %H:%M',
        '%d-%m-%Y',
        '%d/%m/%Y',
        '%Y-%m-%d',
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return None


def clean_decimal(val):
    if not val:
        return Decimal('0.00')
    cleaned = re.sub(r'[^0-9.]', '', str(val))
    try:
        return Decimal(cleaned)
    except (InvalidOperation, ValueError):
        return Decimal('0.00')


def get_default_fastag_account():
    """Returns or creates the default Corporate FASTag Master Account."""
    account = CorporateFastagAccount.objects.filter(is_active=True).first()
    if not account:
        account = CorporateFastagAccount.objects.create(
            account_name="ICICI Corporate Fleet FASTag Wallet",
            account_number="FASTAG-ICICI-CORP-9921",
            balance=Decimal('85000.00'),
            is_active=True
        )
    return account


def reconcile_fastag_statement(statement_text_or_file):
    """
    Parses FASTag CSV content and reconciles against:
    1. Fleet Vehicle Roster
    2. Active/Historical Operations Trips
    3. Corridor Route Matrix Heuristics
    4. Duplicate Deduction Detection
    """
    if hasattr(statement_text_or_file, 'read'):
        content = statement_text_or_file.read()
        if isinstance(content, bytes):
            content = content.decode('utf-8-sig', errors='replace')
    else:
        content = str(statement_text_or_file)

    reader = csv.reader(io.StringIO(content.strip()))
    rows = list(reader)
    if not rows:
        return {'status': 'error', 'message': 'Empty statement or invalid CSV.'}

    # Locate header row
    header_idx = -1
    col_map = {}
    for i, r in enumerate(rows[:10]):
        row_lower = [c.strip().lower() for c in r]
        # Look for essential column markers
        has_vrn = any('vehicle' in c or 'vrn' in c or 'tag' in c for c in row_lower)
        has_amt = any('amount' in c or 'debit' in c or 'fee' in c for c in row_lower)
        if has_vrn and has_amt:
            header_idx = i
            for c_idx, c_val in enumerate(row_lower):
                if any(k in c_val for k in ['date', 'time', 'processed']):
                    col_map['date'] = c_idx
                elif any(k in c_val for k in ['vehicle', 'vrn', 'tag']):
                    col_map['vrn'] = c_idx
                elif any(k in c_val for k in ['plaza', 'location', 'toll', 'particulars']):
                    col_map['plaza'] = c_idx
                elif any(k in c_val for k in ['amount', 'debit', 'fee']):
                    col_map['amount'] = c_idx
                elif any(k in c_val for k in ['ref', 'txn id', 'transaction id', 'urn']):
                    col_map['ref'] = c_idx
            break

    if header_idx == -1 or 'vrn' not in col_map or 'amount' not in col_map:
        # Fallback to positional mapping if standard headers weren't named
        col_map = {'date': 0, 'vrn': 1, 'plaza': 2, 'amount': 3, 'ref': 4}
        data_rows = rows
    else:
        data_rows = rows[header_idx + 1:]

    # Pre-index vehicles for O(1) matching
    vehicles = Vehicle.objects.select_related('vehicle_type').all()
    v_dict = {}
    for v in vehicles:
        norm = normalize_vrn(v.registration_number)
        v_dict[norm] = v

    parsed_entries = []
    total_amount = Decimal('0.00')
    matched_amount = Decimal('0.00')
    matched_count = 0
    off_route_count = 0
    unassigned_count = 0
    duplicate_count = 0
    unknown_vehicle_count = 0

    for idx, r in enumerate(data_rows):
        if not r or len(r) <= max(col_map.get('vrn', 1), col_map.get('amount', 3)):
            continue

        raw_date = r[col_map['date']].strip() if 'date' in col_map and col_map['date'] < len(r) else ''
        raw_vrn = r[col_map['vrn']].strip() if 'vrn' in col_map and col_map['vrn'] < len(r) else ''
        raw_plaza = r[col_map['plaza']].strip() if 'plaza' in col_map and col_map['plaza'] < len(r) else 'Highway Toll Plaza'
        raw_amt = r[col_map['amount']].strip() if 'amount' in col_map and col_map['amount'] < len(r) else '0'
        raw_ref = r[col_map['ref']].strip() if 'ref' in col_map and col_map['ref'] < len(r) else f"FASTAG-TXN-{idx+1001}"

        parsed_dt = parse_date_smart(raw_date) or datetime.now()
        txn_date_only = parsed_dt.date()
        amount = clean_decimal(raw_amt)
        norm_v = normalize_vrn(raw_vrn)

        if not norm_v or amount <= 0:
            continue

        total_amount += amount

        vehicle = v_dict.get(norm_v)
        matched_trip = None
        audit_status = 'MATCHED'
        audit_badge = 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300'
        audit_notes = 'Toll matched to operational schedule'
        corridor_info = None

        if not vehicle:
            audit_status = 'UNKNOWN_VEHICLE'
            audit_badge = 'bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-300'
            audit_notes = f'VRN {raw_vrn} not found in Sivagayathiri Fleet Roster'
            unknown_vehicle_count += 1
        else:
            # Check duplicate in FastagTollDeduction
            is_dup = FastagTollDeduction.objects.filter(
                vehicle=vehicle,
                amount=amount,
                date__date=txn_date_only,
                toll_plaza__icontains=raw_plaza[:8]
            ).exists()

            if is_dup:
                audit_status = 'DUPLICATE'
                audit_badge = 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400'
                audit_notes = 'Duplicate: Toll deduction already committed in ERP'
                duplicate_count += 1
            else:
                # Search Trip on duty for this vehicle on txn_date
                trip = Trip.objects.filter(
                    vehicle=vehicle,
                    start_date__lte=txn_date_only
                ).filter(
                    Q(end_date__gte=txn_date_only) | Q(end_date__isnull=True)
                ).first()

                if not trip:
                    # Try looking +/- 1 day buffer for overnight trips
                    from datetime import timedelta
                    trip = Trip.objects.filter(
                        vehicle=vehicle,
                        start_date__gte=txn_date_only - timedelta(days=1),
                        start_date__lte=txn_date_only + timedelta(days=1)
                    ).first()

                if trip:
                    matched_trip = trip
                    # Corridor route audit
                    origin = ''
                    destination = ''
                    if trip.booking:
                        origin = trip.booking.pickup_location or ''
                        destination = trip.booking.destination or ''
                    elif trip.package:
                        origin = 'Coimbatore'
                        destination = trip.package.title or ''

                    # Check plaza match against corridor heuristics
                    plaza_lower = raw_plaza.lower()
                    plaza_match = False
                    for p_key, p_val in KNOWN_TOLL_PLAZAS.items():
                        if p_key in plaza_lower:
                            corridor_info = p_val['corridor']
                            # If corridor known, verify if route matches
                            if any(c in origin.lower() or c in destination.lower() for c in ['chennai', 'salem', 'bangalore', 'cochin', 'ooty', 'munnar', 'madurai', 'trichy']):
                                plaza_match = True
                            break

                    # If route destination was local (e.g. Ooty/Munnar) but toll is in Bangalore/Attibele, flag off-route!
                    is_off_route = False
                    if 'ooty' in destination.lower() and ('attibele' in plaza_lower or 'paranur' in plaza_lower):
                        is_off_route = True
                    elif 'munnar' in destination.lower() and ('sriperumbudur' in plaza_lower or 'krishnagiri' in plaza_lower):
                        is_off_route = True

                    if is_off_route:
                        audit_status = 'OFF_ROUTE_ALERT'
                        audit_badge = 'bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300'
                        audit_notes = f'Route Deviation: Trip is {origin} → {destination}, but toll logged at {raw_plaza}'
                        off_route_count += 1
                    else:
                        audit_status = 'MATCHED'
                        audit_badge = 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300'
                        audit_notes = f'Matched Trip #{trip.trip_id or trip.id} ({origin or "Depot"} → {destination or "Highway"})'
                        matched_count += 1
                        matched_amount += amount
                else:
                    audit_status = 'UNASSIGNED_TRIP'
                    audit_badge = 'bg-red-100 text-red-800 dark:bg-red-950/60 dark:text-red-300'
                    audit_notes = f'Ghost KM Alert: Vehicle {vehicle.registration_number} on highway with no scheduled trip'
                    unassigned_count += 1

        parsed_entries.append({
            'row_id': idx + 1,
            'date': parsed_dt.strftime('%d-%m-%Y %H:%M'),
            'date_raw': parsed_dt.isoformat(),
            'vrn': vehicle.registration_number if vehicle else raw_vrn,
            'vehicle_id': vehicle.id if vehicle else None,
            'vehicle_category': str(vehicle.vehicle_category) if vehicle and vehicle.vehicle_category else 'Commercial',
            'toll_plaza': raw_plaza,
            'corridor_info': corridor_info or 'National Highway Corridor',
            'amount': float(amount),
            'ref_number': raw_ref,
            'trip_id': matched_trip.id if matched_trip else None,
            'trip_code': matched_trip.trip_id if matched_trip and matched_trip.trip_id else (f"TRP-{matched_trip.id}" if matched_trip else '—'),
            'audit_status': audit_status,
            'audit_badge': audit_badge,
            'audit_notes': audit_notes,
            'can_commit': (audit_status in ['MATCHED', 'OFF_ROUTE_ALERT', 'UNASSIGNED_TRIP']),
        })

    master_account = get_default_fastag_account()

    return {
        'status': 'success',
        'account_id': master_account.id,
        'account_name': master_account.account_name,
        'account_balance': float(master_account.balance),
        'total_records': len(parsed_entries),
        'total_amount': float(total_amount),
        'matched_count': matched_count,
        'matched_amount': float(matched_amount),
        'off_route_count': off_route_count,
        'unassigned_count': unassigned_count,
        'duplicate_count': duplicate_count,
        'unknown_vehicle_count': unknown_vehicle_count,
        'entries': parsed_entries,
    }


def generate_sample_nhai_statement_csv():
    """
    Generates a realistic NHAI / NETC FASTag statement CSV with actual Sivagayathiri fleet vehicles.
    """
    vehicles = Vehicle.objects.filter(status__in=['available', 'assigned', 'on_trip'])[:4]
    v_list = [v.registration_number for v in vehicles]
    while len(v_list) < 4:
        v_list.append(f"TN 38 BX {1000 + len(v_list)}")

    today_str = date.today().strftime('%d-%m-%Y')

    csv_data = [
        ["Transaction Date", "Vehicle Number", "Toll Plaza Name", "Amount (INR)", "Reference ID"],
        [f"{today_str} 06:14:22", v_list[0], "Vijayamangalam Toll Plaza (NH-544)", "130.00", "NETC202610230001827"],
        [f"{today_str} 07:45:10", v_list[0], "Kaniyur Toll Plaza (NH-544 Coimbatore)", "110.00", "NETC202610230001828"],
        [f"{today_str} 08:30:45", v_list[1] if len(v_list) > 1 else v_list[0], "Thoppur Toll Plaza (NH-44 Salem Ghats)", "145.00", "NETC202610230002104"],
        [f"{today_str} 10:15:00", v_list[2] if len(v_list) > 2 else v_list[0], "Attibele Toll Plaza (NH-44 Hosur-Bangalore)", "125.00", "NETC202610230003419"],
        [f"{today_str} 11:22:18", v_list[3] if len(v_list) > 3 else v_list[0], "Paranur Toll Plaza (GST Road Chengalpattu)", "95.00", "NETC202610230004501"],
        [f"{today_str} 14:05:50", "TN 99 ZZ 9999", "Walayar Toll Plaza (NH-544 Border)", "85.00", "NETC202610230005882"],
    ]

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerows(csv_data)
    return output.getvalue()
