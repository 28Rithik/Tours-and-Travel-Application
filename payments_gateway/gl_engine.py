"""
Automated Double-Entry General Ledger (GL) Posting Engine for Payment Collections.
Guarantees mathematical balance: sum(Debit) == sum(Credit), creates idempotent Journal Entries,
links transaction vouchers to Accounts Receivable & Bank/Clearing accounts,
and updates legacy Payment & Booking records for complete cross-system consistency.
"""

from decimal import Decimal
from django.utils import timezone
from django.db import transaction as db_transaction
from finance.models import Account, JournalEntry, JournalItem, Payment
from .models import GatewayTransaction, PaymentGatewayConfig


def get_or_create_core_accounts():
    """Ensures standard Chart of Accounts exist for payment processing."""
    defaults = {
        '1010': ('Cash on Hand', 'asset', 'Liquid cash at branches and desks'),
        '1020': ('Operating Bank Account (Current)', 'asset', 'Primary corporate current account'),
        '1030': ('Payment Gateway Clearing Account', 'asset', 'In-transit collections from Razorpay/Cashfree/UPI'),
        '1100': ('Trade Accounts Receivable', 'asset', 'Outstanding balances receivable from customers/clients'),
        '2010': ('Trade Accounts Payable', 'liability', 'Payable to outsourced fleet owners and suppliers'),
        '2020': ('GST Output Liability', 'liability', 'Collected CGST, SGST, IGST payable to government'),
        '5030': ('Payment Gateway Processing Charges', 'expense', 'MDR transaction fees and gateway platform costs'),
    }
    accounts = {}
    for code, (name, acct_type, desc) in defaults.items():
        acct, _ = Account.objects.get_or_create(
            code=code,
            defaults={'name': name, 'account_type': acct_type, 'description': desc}
        )
        accounts[code] = acct
    return accounts


@db_transaction.atomic
def post_gateway_transaction_to_gl(gateway_txn: GatewayTransaction):
    """
    Posts an automated balanced Double-Entry Journal Entry for a cleared transaction.
    
    Debit: Bank Account (1020) or Gateway Clearing Account (1030) [Net Amount]
    Debit: Gateway Fee Expense (5030) [MDR Fee + Tax] (if fee > 0)
    Credit: Accounts Receivable (1100) [Gross Amount]
    
    Invariant: Sum(Debits) == Sum(Credits) == Gross Amount
    """
    # 1. Idempotency Check
    if gateway_txn.journal_entry_id:
        return gateway_txn.journal_entry

    accounts = get_or_create_core_accounts()
    gross = Decimal(str(gateway_txn.gross_amount))
    fee = Decimal(str(gateway_txn.fee_amount or 0))
    tax = Decimal(str(gateway_txn.tax_amount or 0))
    total_fee = fee + tax
    net = gross - total_fee

    if gateway_txn.net_amount != net:
        gateway_txn.net_amount = net

    # 2. Select Asset Account (Bank Current A/c vs Gateway Clearing A/c)
    if gateway_txn.provider in ['direct_upi', 'offline']:
        asset_account = accounts['1020']  # Directly settles into ICICI Bank
    else:
        asset_account = accounts['1030']  # In-transit gateway clearing

    ar_account = accounts['1100']  # Accounts Receivable (Customer)
    fee_account = accounts['5030']  # Payment Gateway Fee

    # 3. Create General Ledger Journal Entry Header
    party_name = gateway_txn.party.name if gateway_txn.party else (
        gateway_txn.booking.guest_name if gateway_txn.booking else "Customer"
    )
    ref = gateway_txn.gateway_payment_id or gateway_txn.transaction_id

    entry = JournalEntry.objects.create(
        date=timezone.now().date(),
        entry_type='payment_receipt',
        reference_id=ref,
        narration=f"Auto-Reconciled {gateway_txn.get_provider_display()} collection for {party_name} [Txn: {gateway_txn.transaction_id}, Ref: {ref}]",
        is_posted=False  # Posted once line items balance
    )

    # 4. Create Line Items
    # Line 1: Debit Asset Account (Net Inflow)
    JournalItem.objects.create(
        entry=entry,
        account=asset_account,
        party=gateway_txn.party,
        debit=net,
        credit=Decimal('0.00'),
        memo=f"Net funds received via {gateway_txn.get_provider_display()}"
    )

    # Line 2: Debit Gateway Fee (if applicable)
    if total_fee > Decimal('0.00'):
        JournalItem.objects.create(
            entry=entry,
            account=fee_account,
            party=None,
            debit=total_fee,
            credit=Decimal('0.00'),
            memo=f"Gateway MDR & processing charges (Fee: ₹{fee}, GST: ₹{tax})"
        )

    # Line 3: Credit Accounts Receivable (Customer Party ledger credit)
    JournalItem.objects.create(
        entry=entry,
        account=ar_account,
        party=gateway_txn.party,
        debit=Decimal('0.00'),
        credit=gross,
        memo=f"Settlement of receivables for {party_name}"
    )

    # 5. Invariant Validation: Total Debits == Total Credits
    assert entry.is_balanced, f"Journal entry {entry.entry_number} is unbalanced! DR={entry.total_debit} vs CR={entry.total_credit}"

    entry.is_posted = True
    entry.save(update_fields=['is_posted'])

    # 6. Create / Link legacy Payment Record for full backward-compatibility
    if not gateway_txn.payment_record_id:
        # Determine party: from booking if not directly provided
        target_party = gateway_txn.party
        if not target_party and gateway_txn.booking:
            target_party = gateway_txn.booking.party

        if target_party:
            payment_mode = 'upi' if 'upi' in gateway_txn.provider else (
                'cash' if gateway_txn.provider == 'offline' else 'bank_transfer'
            )
            pay_record = Payment.objects.create(
                party=target_party,
                booking=gateway_txn.booking,
                trip=gateway_txn.trip,
                statement=gateway_txn.statement,
                date=entry.date,
                amount=gross,
                payment_type='customer_receipt',
                payment_mode=payment_mode,
                reference_number=ref,
                notes=f"{gateway_txn.get_provider_display()} Auto-Reconciled · JE #{entry.entry_number}"
            )
            gateway_txn.payment_record = pay_record

    # 7. Update Booking Status if pending
    if gateway_txn.booking and gateway_txn.booking.status == 'pending':
        gateway_txn.booking.status = 'confirmed'
        gateway_txn.booking.save(update_fields=['status'])

    # 8. Mark Transaction Captured & Link Entry
    gateway_txn.journal_entry = entry
    gateway_txn.status = 'captured'
    gateway_txn.save(update_fields=['journal_entry', 'payment_record', 'net_amount', 'status'])

    return entry
