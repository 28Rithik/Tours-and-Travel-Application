from django.utils import timezone
from operations.models import Booking
from suppliers.models import CommissionRule
from finance.models import LedgerAdjustment
from core.models import Supplier

def calculate_agent_commission(booking: Booking, agent_name: str):
    """
    Calculates agent commission based on active rules.
    """
    try:
        rule = CommissionRule.objects.get(agent_name=agent_name, is_active=True)
        commission_amount = float(booking.quoted_price or 0) * (float(rule.commission_percentage) / 100)
        
        # Write to Payable ledger via LedgerAdjustment
        supplier, _ = Supplier.objects.get_or_create(name=agent_name, defaults={'party_type': 'supplier'})
        
        LedgerAdjustment.objects.create(
            party=supplier,
            date=timezone.now().date(),
            amount=commission_amount,
            description=f"Commission for booking {booking.booking_number}",
            adjustment_type='increase_payable',
            is_approved=True
        )
        
        return commission_amount
    except CommissionRule.DoesNotExist:
        return 0
