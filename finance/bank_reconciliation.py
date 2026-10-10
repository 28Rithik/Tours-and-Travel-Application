import csv
import io
import re
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import List, Dict, Any, Optional

from django.db import transaction
from django.db.models import Q
from django.utils import timezone


def _parse_amount(val: Any) -> Decimal:
    """Safe decimal amount parser stripping currency symbols, commas, and whitespace."""
    if not val:
        return Decimal('0.00')
    if isinstance(val, (int, float, Decimal)):
        return Decimal(str(val)).quantize(Decimal('0.01'))
    s = str(val).strip().replace(',', '').replace('₹', '').replace('Rs.', '').replace('Rs', '').replace('INR', '').strip()
    # Handle brackets as negative
    if s.startswith('(') and s.endswith(')'):
        s = '-' + s[1:-1]
    # Remove any extra non-numeric characters except minus and period
    clean_s = re.sub(r'[^0-9.-]', '', s)
    try:
        return Decimal(clean_s).quantize(Decimal('0.01')) if clean_s else Decimal('0.00')
    except Exception:
        return Decimal('0.00')


def _parse_date(val: Any) -> Optional[date]:
    """Tolerant date parser supporting common Indian banking date formats."""
    if not val:
        return None
    if isinstance(val, date):
        return val
    if isinstance(val, datetime):
        return val.date()
    val_str = str(val).strip()
    formats = [
        '%d-%m-%Y', '%d/%m/%Y', '%Y-%m-%d', '%d.%m.%Y',
        '%d-%b-%Y', '%d/%b/%Y', '%d-%b-%y', '%d/%b/%y',
        '%d %b %Y', '%d %B %Y', '%Y/%m/%d'
    ]
    for fmt in formats:
        try:
            return datetime.strptime(val_str, fmt).date()
        except ValueError:
            continue
    # Attempt regex extraction if embedded in timestamp e.g. "2026-10-01 14:32:00"
    m = re.search(r'(\d{4}[-/.]\d{1,2}[-/.]\d{1,2})|(\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4})', val_str)
    if m:
        extracted = m.group(0)
        for fmt in formats:
            try:
                return datetime.strptime(extracted, fmt).date()
            except ValueError:
                continue
    return None


def extract_utr_or_ref(text: str) -> str:
    """
    Extracts 12-digit UTR, IMPS, UPI, or NEFT reference strings from bank narrations.
    Examples:
    - 'UPI/627491028374/Dr Arvind Swaminathan/SBI' -> '627491028374'
    - 'NEFT-AXIS-20261001-99882211-TRANSFER' -> '99882211'
    - 'IMPS/P2A/429182740192/PAYMENT' -> '429182740192'
    """
    if not text:
        return ""
    # Standard 12-digit UPI / IMPS RRN
    m_rrn = re.search(r'(?:UPI|IMPS|NEFT|RTGS|RRN|REF)[/:_-]?([A-Za-z0-9]{8,22})', text, re.IGNORECASE)
    if m_rrn:
        return m_rrn.group(1).strip()
    # Standalone 12-digit numeric reference
    m_num = re.search(r'\b(\d{12})\b', text)
    if m_num:
        return m_num.group(1).strip()
    # Cheque number format e.g. CHQ:123456
    m_chq = re.search(r'(?:CHQ|CHEQUE|CMS)[/:_-]?([0-9]{6,10})', text, re.IGNORECASE)
    if m_chq:
        return m_chq.group(1).strip()
    return ""


def parse_bank_statement_csv(csv_content_or_file, bank_name: str = 'generic') -> List[Dict[str, Any]]:
    """
    Parses standard bank statement CSV export from SBI, HDFC, ICICI, Axis, or Generic CSV.
    """
    if hasattr(csv_content_or_file, 'read'):
        raw = csv_content_or_file.read()
        if isinstance(raw, bytes):
            text = raw.decode('utf-8', errors='replace')
        else:
            text = str(raw)
    else:
        text = str(csv_content_or_file)

    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    if not rows:
        return []

    # Find header row
    header_idx = -1
    date_col = -1
    narration_col = -1
    ref_col = -1
    withdrawal_col = -1
    deposit_col = -1
    balance_col = -1

    keywords_date = ['date', 'txn date', 'transaction date', 'posting date']
    keywords_narr = ['narration', 'description', 'particulars', 'remarks', 'transaction remarks']
    keywords_ref = ['chq', 'ref', 'utr', 'cheque', 'reference', 'trans id', 'rrn']
    keywords_debit = ['withdrawal', 'debit', 'dr', 'withdrawal amt', 'debit amount']
    keywords_credit = ['deposit', 'credit', 'cr', 'deposit amt', 'credit amount']
    keywords_bal = ['balance', 'closing balance', 'running balance', 'bal']

    for idx, r in enumerate(rows[:20]):
        lower_row = [c.lower().strip() for c in r]
        # Check if row looks like a header
        has_date = any(any(k in cell for k in keywords_date) for cell in lower_row)
        has_narr = any(any(k in cell for k in keywords_narr) for cell in lower_row)
        has_amt = any(any(k in cell for k in keywords_debit + keywords_credit) for cell in lower_row)
        if has_date and (has_narr or has_amt):
            header_idx = idx
            for c_idx, cell in enumerate(lower_row):
                if date_col == -1 and any(k in cell for k in keywords_date):
                    date_col = c_idx
                elif narration_col == -1 and any(k in cell for k in keywords_narr):
                    narration_col = c_idx
                elif ref_col == -1 and any(k in cell for k in keywords_ref):
                    ref_col = c_idx
                elif withdrawal_col == -1 and any(k in cell for k in keywords_debit):
                    withdrawal_col = c_idx
                elif deposit_col == -1 and any(k in cell for k in keywords_credit):
                    deposit_col = c_idx
                elif balance_col == -1 and any(k in cell for k in keywords_bal):
                    balance_col = c_idx
            break

    # If no header found, fallback to positional heuristics
    if header_idx == -1:
        header_idx = 0
        date_col = 0
        narration_col = 1
        ref_col = 2
        withdrawal_col = 3
        deposit_col = 4
        balance_col = 5

    parsed_entries = []
    for r in rows[header_idx + 1:]:
        if not r or len(r) <= date_col:
            continue
        d_val = r[date_col].strip() if date_col < len(r) else ""
        txn_date = _parse_date(d_val)
        if not txn_date:
            continue

        narr = r[narration_col].strip() if narration_col != -1 and narration_col < len(r) else ""
        ref_val = r[ref_col].strip() if ref_col != -1 and ref_col < len(r) else ""
        if not ref_val:
            ref_val = extract_utr_or_ref(narr)

        dr_amt = _parse_amount(r[withdrawal_col]) if withdrawal_col != -1 and withdrawal_col < len(r) else Decimal('0.00')
        cr_amt = _parse_amount(r[deposit_col]) if deposit_col != -1 and deposit_col < len(r) else Decimal('0.00')
        bal_amt = _parse_amount(r[balance_col]) if balance_col != -1 and balance_col < len(r) else Decimal('0.00')

        if dr_amt == 0 and cr_amt == 0:
            continue

        parsed_entries.append({
            'transaction_date': txn_date,
            'value_date': txn_date,
            'narration': narr,
            'reference_or_utr': ref_val,
            'withdrawal_amount': dr_amt,
            'deposit_amount': cr_amt,
            'balance': bal_amt,
        })

    return parsed_entries


def auto_match_statement_entries(entries_qs) -> int:
    """
    Multi-strategy matching algorithm comparing un-reconciled bank statement rows
    against open Bookings, Invoices, Trips, and Customer accounts.
    """
    from operations.models import Booking, Trip
    from finance.models import CorporateGSTInvoice, Payment
    from core.models import Party

    matched_count = 0

    for entry in entries_qs.filter(status='unmatched', deposit_amount__gt=0):
        amt = entry.deposit_amount
        narr = entry.narration or ""
        utr = (entry.reference_or_utr or "").strip()
        t_date = entry.transaction_date

        matched_booking = None
        matched_invoice = None
        matched_party = None
        confidence = 0
        reason = ""

        # Strategy 1: Exact UTR match against existing Payment
        if utr:
            existing_pay = Payment.objects.filter(reference_number__iexact=utr).first()
            if existing_pay:
                confidence = 100
                matched_party = existing_pay.party
                matched_booking = existing_pay.booking
                reason = f"Exact UTR match ({utr}) on logged Payment #{existing_pay.pk}"

        # Strategy 2: Exact Booking Number in Narration e.g. "BK-2026-0042" or "BK-0042"
        if confidence == 0:
            m_bk = re.search(r'\b(BK-[A-Za-z0-9-]+)\b', narr, re.IGNORECASE)
            if m_bk:
                bk_no = m_bk.group(1).upper()
                bk = Booking.objects.filter(booking_number__iexact=bk_no).first()
                if bk:
                    matched_booking = bk
                    matched_party = bk.party
                    confidence = 100
                    reason = f"Exact Booking Number ({bk_no}) found in bank narration"

        # Strategy 3: Exact Invoice Number in Narration e.g. "INV-2026-0001"
        if confidence == 0:
            m_inv = re.search(r'\b(INV-[A-Za-z0-9-]+)\b', narr, re.IGNORECASE)
            if m_inv:
                inv_no = m_inv.group(1).upper()
                inv = CorporateGSTInvoice.objects.filter(invoice_number__iexact=inv_no).first()
                if inv:
                    matched_invoice = inv
                    matched_party = inv.party
                    confidence = 100
                    reason = f"Exact Invoice Number ({inv_no}) found in bank narration"

        # Strategy 4: Exact Trip ID in Narration e.g. "TR-2026-001"
        if confidence == 0:
            m_tr = re.search(r'\b(TR-[A-Za-z0-9-]+)\b', narr, re.IGNORECASE)
            if m_tr:
                tr_id = m_tr.group(1).upper()
                tr = Trip.objects.filter(trip_id__iexact=tr_id).select_related('booking', 'party').first()
                if tr:
                    matched_booking = tr.booking
                    matched_party = tr.party
                    confidence = 95
                    reason = f"Exact Trip ID ({tr_id}) in narration"

        # Strategy 5: 10-digit Phone Number in Narration
        if confidence == 0:
            phones = re.findall(r'\b([6-9]\d{9})\b', narr)
            for phone in phones:
                bk = Booking.objects.filter(guest_phone=phone).order_by('-id').first()
                if bk:
                    matched_booking = bk
                    matched_party = bk.party
                    confidence = 90
                    reason = f"Guest mobile number ({phone}) identified in UPI remark"
                    break

        # Strategy 6: High Confidence Amount + Customer / Guest Name matching
        if confidence == 0:
            # Check open bookings where quoted_price matches exactly
            open_bks = Booking.objects.filter(
                quoted_price=amt
            ).order_by('-id')[:20]

            for bk in open_bks:
                # Check if guest name or party name appears in narration
                g_name = (bk.guest_name or "").lower().strip()
                p_name = (bk.party.name if bk.party else "").lower().strip()
                
                # Check first name or primary keyword
                name_words = [w for w in (g_name + " " + p_name).split() if len(w) >= 4]
                if any(w in narr.lower() for w in name_words):
                    matched_booking = bk
                    matched_party = bk.party
                    confidence = 90
                    reason = f"Amount ₹{amt:,.2f} + Customer name '{g_name or p_name}' matched"
                    break

        # Strategy 7: Proximity Match (Amount matches booking balance within +/- 4 days)
        if confidence == 0 and t_date:
            min_date = t_date - timedelta(days=4)
            max_date = t_date + timedelta(days=4)
            prox_bk = Booking.objects.filter(
                quoted_price=amt,
                pickup_date__gte=min_date,
                pickup_date__lte=max_date
            ).order_by('-id').first()
            if prox_bk:
                matched_booking = prox_bk
                matched_party = prox_bk.party
                confidence = 75
                reason = f"Amount ₹{amt:,.2f} matches Booking #{prox_bk.booking_number} within 4-day pickup window"

        if confidence >= 75:
            entry.matched_booking = matched_booking
            entry.matched_invoice = matched_invoice
            entry.matched_party = matched_party
            entry.match_confidence = confidence
            entry.match_reason = reason
            entry.status = 'matched'
            entry.save(update_fields=['matched_booking', 'matched_invoice', 'matched_party', 'match_confidence', 'match_reason', 'status'])
            matched_count += 1

    return matched_count


def execute_bank_reconciliation(entry, user=None):
    """
    Executes formal reconciliation for a single BankStatementEntry:
    - Creates or links a Payment record
    - Credits customer booking/invoice balance
    - Posts double-entry general ledger entry
    - Marks entry status as 'reconciled'
    """
    if entry.status == 'reconciled' and entry.matched_payment_id:
        return entry.matched_payment

    from finance.models import Payment, Account, JournalEntry, JournalItem
    from operations.models import Booking

    # Resolve Party
    party = entry.matched_party
    if not party and entry.matched_booking:
        party = entry.matched_booking.party
    if not party and entry.matched_invoice:
        party = entry.matched_invoice.party

    if not party:
        from core.models import Party
        party = Party.objects.filter(party_type='customer').first()

    booking = entry.matched_booking
    trip = None
    if booking:
        trip = booking.trips.first()

    # Determine payment mode
    narr_upper = (entry.narration or "").upper()
    pay_mode = 'upi' if 'UPI' in narr_upper else 'bank_transfer'
    ref_num = entry.reference_or_utr or f"UTR-{entry.pk}"

    with transaction.atomic():
        payment = Payment.objects.create(
            party=party,
            booking=booking,
            trip=trip,
            date=entry.transaction_date,
            amount=entry.deposit_amount,
            payment_type='customer_receipt',
            payment_mode=pay_mode,
            reference_number=ref_num,
            bank=entry.upload.get_bank_name_display() if entry.upload else "Bank Account",
            notes=f"Auto-Reconciled from Statement #{entry.upload_id}: {entry.narration[:80]}"
        )

        # Update Booking status if pending
        if booking and booking.status == 'pending':
            booking.status = 'confirmed'
            booking.save(update_fields=['status'])

        # Update Invoice if matched
        if entry.matched_invoice:
            inv = entry.matched_invoice
            current_paid = getattr(inv, 'paid_amount', None) or getattr(inv, 'amount_paid', Decimal('0.00')) or Decimal('0.00')
            new_paid = current_paid + entry.deposit_amount
            total_val = getattr(inv, 'total_invoice_value', None) or getattr(inv, 'total_amount', Decimal('0.00')) or Decimal('0.00')
            new_status = 'paid' if new_paid >= total_val else ('partially_paid' if new_paid > 0 else 'unpaid')

            update_fields = []
            if hasattr(inv, 'paid_amount'):
                inv.paid_amount = new_paid
                update_fields.append('paid_amount')
            elif hasattr(inv, 'amount_paid'):
                inv.amount_paid = new_paid
                update_fields.append('amount_paid')

            if hasattr(inv, 'payment_status'):
                inv.payment_status = new_status
                update_fields.append('payment_status')
            elif hasattr(inv, 'status'):
                inv.status = new_status
                update_fields.append('status')

            if update_fields:
                inv.save(update_fields=update_fields)

        # Double-entry GL posting
        try:
            bank_acc = Account.objects.filter(account_type='asset', name__icontains='bank').first()
            ar_acc = Account.objects.filter(account_type='asset', name__icontains='receivable').first()
            if bank_acc and ar_acc:
                je = JournalEntry.objects.create(
                    date=entry.transaction_date,
                    reference=f"REC-JE-{entry.pk}",
                    description=f"Bank statement deposit reconciliation UTR: {ref_num}",
                    created_by=user
                )
                JournalItem.objects.create(entry=je, account=bank_acc, debit=entry.deposit_amount, credit=0)
                JournalItem.objects.create(entry=je, account=ar_acc, debit=0, credit=entry.deposit_amount)
        except Exception:
            pass

        # Update entry status
        entry.status = 'reconciled'
        entry.matched_payment = payment
        entry.reconciled_at = timezone.now()
        entry.reconciled_by = user
        entry.audit_notes = f"Reconciled as Payment #{payment.pk} ({payment.reference_number})"
        entry.save(update_fields=['status', 'matched_payment', 'reconciled_at', 'reconciled_by', 'audit_notes'])

        # Update parent statement stats
        entry.upload.update_summary_metrics()

    return payment
