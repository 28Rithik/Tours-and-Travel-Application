import random
from decimal import Decimal
from django.utils import timezone
from finance.models import CorporateFastagAccount, FastagTollDeduction
from core.models import Vehicle

class ICICIFastagMockAPI:
    """
    Mocks the ICICI Corporate FASTag API.
    In a real scenario, this would use `requests.post()` with authentication tokens.
    """
    
    @staticmethod
    def sync_tolls_for_account(account_number):
        try:
            account = CorporateFastagAccount.objects.get(account_number=account_number)
        except CorporateFastagAccount.DoesNotExist:
            return {"status": "error", "message": "Account not found in DB."}
            
        # Mocking an API response that returns recent tolls for tags linked to this corporate account
        # We will just generate 2-3 random tolls for random active vehicles
        vehicles = list(Vehicle.objects.filter(status='active')[:5])
        if not vehicles:
            return {"status": "success", "message": "No vehicles found to sync."}
            
        deductions_created = 0
        for _ in range(random.randint(1, 3)):
            vehicle = random.choice(vehicles)
            amount = Decimal(str(random.randint(45, 150)))
            
            # Create the toll deduction (which automatically deducts from the master account balance)
            FastagTollDeduction.objects.create(
                account=account,
                date=timezone.now(),
                vehicle=vehicle,
                amount=amount,
                toll_plaza=random.choice(["L&T Krishnagiri Toll", "Attibele Toll Plaza", "NICE Road Toll", "NHAI Hosur Toll"])
            )
            deductions_created += 1
            
        return {
            "status": "success", 
            "message": f"Successfully synced {deductions_created} new tolls from ICICI Bank API.",
            "new_balance": account.balance
        }
