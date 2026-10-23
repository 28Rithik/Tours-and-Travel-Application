"""
Sivagayathiri Travels & Tours ERP — Highway Fuel Slip OCR & Fraud Sentry Engine.
Parses receipt text or uploaded scans from Indian Oil, Bharat Petroleum, HPCL, Shell, and Nayara bunks.
Extracts fuel volume, rate per liter, total amount, slip number, and performs fraud verification.
"""

from decimal import Decimal
import re
from datetime import datetime
from django.utils import timezone


# Tamil Nadu Commercial Corridor Benchmark (Diesel rate per liter)
TAMIL_NADU_DIESEL_BENCHMARK = Decimal('94.20')
ALLOWED_RATE_VARIATION_PERCENT = Decimal('8.0')  # ±8% tolerance for interstate border stations


def parse_fuel_receipt_text(raw_text, vehicle=None):
    """
    Extracts structured fuel receipt metrics from scanned OCR text.
    Returns:
      {
        'status': 'success',
        'station_name': str,
        'bunk_brand': str,
        'fuel_type': str,
        'liters': float,
        'rate_per_liter': float,
        'total_amount': float,
        'slip_number': str,
        'date': str (YYYY-MM-DD),
        'time': str (HH:MM),
        'vehicle_number': str,
        'fraud_check': {
          'is_flagged': bool,
          'warnings': list[str],
          'status': 'verified' | 'suspicious' | 'flagged'
        }
      }
    """
    if not raw_text:
        return {'status': 'error', 'message': 'Empty receipt text provided.'}

    text = raw_text.strip()
    upper_text = text.upper()

    # 1. Detect Bunk Brand & Station Name
    bunk_brand = 'Other Fuel Station'
    station_name = 'Highway Fuel Station'

    if 'INDIAN OIL' in upper_text or 'IOCL' in upper_text:
        bunk_brand = 'Indian Oil Corporation'
    elif 'BHARAT PETROLEUM' in upper_text or 'BPCL' in upper_text or 'SPEED' in upper_text:
        bunk_brand = 'Bharat Petroleum'
    elif 'HINDUSTAN PETROLEUM' in upper_text or 'HPCL' in upper_text or 'POWER' in upper_text:
        bunk_brand = 'Hindustan Petroleum'
    elif 'SHELL' in upper_text:
        bunk_brand = 'Shell India'
    elif 'NAYARA' in upper_text or 'ESSAR' in upper_text:
        bunk_brand = 'Nayara Energy'
    elif 'RELIANCE' in upper_text or 'JIO-BP' in upper_text:
        bunk_brand = 'Jio-bp Reliance'

    # Try extracting full station trade name from first 3 lines
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    for line in lines[:4]:
        if any(b in line.upper() for b in ['IOCL', 'INDIAN OIL', 'BPCL', 'HPCL', 'FUELS', 'PETROL', 'BUNK', 'AGENCIES', 'ENTERPRISES', 'HIGHWAY RO']):
            station_name = line[:80].strip()
            break
    if station_name == 'Highway Fuel Station' and bunk_brand != 'Other Fuel Station':
        station_name = f"{bunk_brand} - Highway RO"

    # 2. Extract Fuel Type
    fuel_type = 'Diesel'
    if 'PETROL' in upper_text or 'MOTOR SPIRIT' in upper_text or 'MS ' in upper_text:
        fuel_type = 'Petrol'

    # 3. Extract Liters / Volume
    liters = None
    # Pattern: 45.20 L, 55.40 LTR, VOL: 45.20, VOLUME: 45.20
    vol_matches = re.findall(r'(?:VOL(?:UME)?|QTY|QUANTITY)?\s*[:=]?\s*(\d{1,4}\.\d{1,3})\s*(?:L|LTR|LIT|LITRE)?\b', upper_text)
    if vol_matches:
        for vm in vol_matches:
            val = float(vm)
            if 5.0 <= val <= 600.0:  # reasonable commercial fuel quantity
                liters = val
                break

    # 4. Extract Rate / Price per Liter
    rate = None
    rate_matches = re.findall(r'(?:RATE|PRICE|RS\/L|INR\/L|DSR|DSRATE)\D*(\d{2,3}\.\d{2})', upper_text)
    if rate_matches:
        for rm in rate_matches:
            val = float(rm)
            if 80.0 <= val <= 130.0:  # reasonable rate per liter
                rate = val
                break

    # 5. Extract Total Amount (₹)
    total_amount = None
    amt_matches = re.findall(r'(?:TOTAL|AMOUNT|NET\s*AMT|NET\s*AMOUNT|BILL\s*AMT)\D*(?:RS\.?|INR)?\s*(\d{2,6}\.\d{2})', upper_text)
    if amt_matches:
        for am in amt_matches:
            val = float(am)
            if val >= 200.0:
                total_amount = val
                break

    # Reconcile Math if one metric was missed
    if liters and rate and not total_amount:
        total_amount = round(liters * rate, 2)
    elif total_amount and rate and not liters:
        liters = round(total_amount / rate, 2)
    elif total_amount and liters and not rate:
        rate = round(total_amount / liters, 2)

    # 6. Extract Date & Time
    date_str = timezone.localdate().strftime('%Y-%m-%d')
    time_str = '12:00'
    date_match = re.search(r'\b(\d{2})[/-](\d{2})[/-](\d{4})\b', text)
    if date_match:
        d, m, y = date_match.groups()
        date_str = f"{y}-{m}-{d}"
    else:
        date_match2 = re.search(r'\b(\d{4})[/-](\d{2})[/-](\d{2})\b', text)
        if date_match2:
            date_str = date_match2.group(0).replace('/', '-')

    time_match = re.search(r'\b(\d{2}:\d{2}(?::\d{2})?)\b', text)
    if time_match:
        time_str = time_match.group(1)[:5]

    # 7. Extract Vehicle Registration if printed on slip
    veh_match = re.search(r'\b(TN\s*\d{2}\s*[A-Z]{1,3}\s*\d{3,4})\b', upper_text)
    veh_number = veh_match.group(1).replace(' ', '') if veh_match else ''

    # 8. Extract Slip / Invoice Number
    slip_match = re.search(r'(?:INV|BILL|SLIP|RECEIPT|TXN|NO)\D*(\d{4,10})\b', upper_text)
    slip_number = slip_match.group(1) if slip_match else f"RO-{int(timezone.now().timestamp()) % 1000000}"

    # =========================================================================
    # FRAUD & REPUTATION VERIFICATION SENTRY
    # =========================================================================
    warnings = []
    is_flagged = False

    # Check 1: Price per liter check against TN corridor benchmark
    if rate:
        rate_dec = Decimal(str(rate))
        diff = abs(rate_dec - TAMIL_NADU_DIESEL_BENCHMARK)
        pct_diff = (diff / TAMIL_NADU_DIESEL_BENCHMARK) * Decimal('100.0')
        if pct_diff > ALLOWED_RATE_VARIATION_PERCENT:
            is_flagged = True
            warnings.append(
                f"Rate anomaly: ₹{rate:.2f}/L deviates by {pct_diff:.1f}% from the Tamil Nadu benchmark (₹{TAMIL_NADU_DIESEL_BENCHMARK}/L)."
            )

    # Check 2: Volume vs Vehicle Fuel Tank Capacity
    if vehicle and liters:
        tank_cap = float(vehicle.fuel_tank_capacity or 55.0)
        # Allow up to 10% overflow for expansion tank/pipe fill
        max_allowed_liters = tank_cap * 1.10
        if liters > max_allowed_liters:
            is_flagged = True
            warnings.append(
                f"Tank capacity overflow: {liters:.1f} L exceeds vehicle '{vehicle.registration_number}' tank capacity ({tank_cap:.0f} L)."
            )

    # Check 3: Check for duplicate fuel slips in past 48h
    if total_amount:
        from finance.models import FuelRecord
        cutoff = timezone.now().date() - timezone.timedelta(days=2)
        duplicate_exists = FuelRecord.objects.filter(
            date__gte=cutoff,
            fuel_quantity__exact=Decimal(str(liters or 0)),
            fuel_price__exact=Decimal(str(rate or 0))
        ).exists()
        if duplicate_exists:
            is_flagged = True
            warnings.append("Duplicate detection: An identical fuel entry with matching liters and price was recorded within 48 hours.")

    verification_status = 'flagged' if is_flagged else ('verified' if (liters and total_amount) else 'suspicious')

    return {
        'status': 'success',
        'station_name': station_name,
        'bunk_brand': bunk_brand,
        'fuel_type': fuel_type,
        'liters': liters or 45.0,
        'rate_per_liter': rate or float(TAMIL_NADU_DIESEL_BENCHMARK),
        'total_amount': total_amount or round(45.0 * float(TAMIL_NADU_DIESEL_BENCHMARK), 2),
        'slip_number': slip_number,
        'date': date_str,
        'time': time_str,
        'vehicle_number': veh_number or (vehicle.registration_number if vehicle else ''),
        'fraud_check': {
            'is_flagged': is_flagged,
            'warnings': warnings,
            'status': verification_status,
            'benchmark_rate': float(TAMIL_NADU_DIESEL_BENCHMARK),
        }
    }
