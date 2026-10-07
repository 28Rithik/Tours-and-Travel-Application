import os
import sys
import django
from decimal import Decimal

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
django.setup()

from payments_gateway.models import PaymentGatewayConfig

def seed_gateway_configs():
    configs = [
        {
            'provider': 'direct_upi',
            'name': 'Sivagayathiri Travels Direct Dynamic UPI',
            'is_active': True,
            'is_sandbox': False,
            'api_key': 'UPI-INTENT-KEY-LIVE',
            'api_secret': '',
            'webhook_secret': 'upi_internal_secret_key_2026',
            'upi_vpa': 'sivagayathiritravels@icici',
            'merchant_name': 'Sivagayathiri Travels',
            'mcc_code': '4121',
            'gateway_fee_percent': Decimal('0.00'),
            'gst_on_fee_percent': Decimal('0.00'),
            'auto_post_to_gl': True,
        },
        {
            'provider': 'razorpay',
            'name': 'Razorpay Corporate Gateway',
            'is_active': True,
            'is_sandbox': True,
            'api_key': 'rzp_test_sivagayathiri_fleet',
            'api_secret': 'rzp_sec_test_secret_key_99',
            'webhook_secret': 'rzp_webhook_secret_fleet_2026',
            'upi_vpa': 'sivagayathiritravels.rzp@icici',
            'merchant_name': 'Sivagayathiri Tours & Travels',
            'mcc_code': '4121',
            'gateway_fee_percent': Decimal('1.75'),
            'gst_on_fee_percent': Decimal('18.00'),
            'auto_post_to_gl': True,
        },
        {
            'provider': 'cashfree',
            'name': 'Cashfree AutoCollect Payments',
            'is_active': True,
            'is_sandbox': True,
            'api_key': 'CF_APP_TEST_771892',
            'api_secret': 'cf_sec_test_secret_8819',
            'webhook_secret': 'cf_webhook_secret_cashfree_2026',
            'upi_vpa': 'sivagayathiri.cashfree@yesbank',
            'merchant_name': 'Sivagayathiri Travels',
            'mcc_code': '4121',
            'gateway_fee_percent': Decimal('1.65'),
            'gst_on_fee_percent': Decimal('18.00'),
            'auto_post_to_gl': True,
        },
        {
            'provider': 'offline',
            'name': 'Fleet Cash Desk & Branch Collections',
            'is_active': True,
            'is_sandbox': False,
            'api_key': 'OFFLINE-DESK-KEY',
            'api_secret': '',
            'webhook_secret': '',
            'upi_vpa': 'sivagayathiritravels@icici',
            'merchant_name': 'Sivagayathiri Travels Cash Desk',
            'mcc_code': '4121',
            'gateway_fee_percent': Decimal('0.00'),
            'gst_on_fee_percent': Decimal('0.00'),
            'auto_post_to_gl': True,
        },
    ]

    for cfg_data in configs:
        obj, created = PaymentGatewayConfig.objects.get_or_create(
            provider=cfg_data['provider'],
            defaults=cfg_data
        )
        print(f"[{'NEW' if created else 'OK'}] {obj.name} ({obj.provider.upper()})")

    print(f"\nTotal Gateway Configurations: {PaymentGatewayConfig.objects.count()}")

if __name__ == '__main__':
    seed_gateway_configs()
