import os
import sys
import django

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
django.setup()

from finance.models import Account

def seed_accounts():
    accounts_data = [
        ('1010', 'Cash on Hand', 'asset', 'Liquid cash at branches and desks'),
        ('1020', 'Operating Bank Account (Current)', 'asset', 'Primary corporate current account'),
        ('1030', 'Payment Gateway Clearing Account', 'asset', 'In-transit collections from Razorpay/Cashfree/UPI'),
        ('1100', 'Trade Accounts Receivable', 'asset', 'Outstanding balances receivable from customers/clients'),
        ('2010', 'Trade Accounts Payable', 'liability', 'Payable to outsourced fleet owners and suppliers'),
        ('2020', 'GST Output Liability', 'liability', 'Collected CGST, SGST, IGST payable to government'),
        ('3010', 'Retained Earnings & Reserves', 'equity', 'Accumulated company reserves'),
        ('4010', 'Passenger & Tour Revenue', 'income', 'Direct B2C passenger fare income'),
        ('4020', 'Corporate Contract Revenue', 'income', 'B2B monthly corporate shuttle billing income'),
        ('5010', 'Fleet Fuel Expenses', 'expense', 'Diesel and petrol expenses'),
        ('5020', 'Driver Wages & Batta', 'expense', 'Driver compensation and trip daily batta'),
        ('5030', 'Payment Gateway Processing Charges', 'expense', 'MDR transaction fees and gateway platform costs'),
        ('5040', 'Highway Toll & FASTag Charges', 'expense', 'Electronic toll collection expenses'),
        ('5050', 'Vehicle Maintenance & Repairs', 'expense', 'Fleet periodic servicing and spare parts'),
    ]
    created_count = 0
    for code, name, acct_type, desc in accounts_data:
        acct, created = Account.objects.get_or_create(
            code=code,
            defaults={'name': name, 'account_type': acct_type, 'description': desc}
        )
        if created:
            created_count += 1
        print(f"[{'NEW' if created else 'OK'}] {code} - {name} ({acct_type.upper()})")

    print(f"\nTotal Chart of Accounts: {Account.objects.count()} (Added {created_count} new)")

if __name__ == '__main__':
    seed_accounts()
