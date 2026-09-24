import random
from decimal import Decimal
from django.utils import timezone
from finance.models import CorporatePetroAccount, FuelRecord
from core.models import Vehicle

class PetroCardMockAPI:
    """
    Mocks a Corporate Fuel API like HPCL DriveTrack or BPCL SmartFleet.
    """
    
    @staticmethod
    def sync_fuel_transactions(account_number):
        try:
            account = CorporatePetroAccount.objects.get(account_number=account_number)
        except CorporatePetroAccount.DoesNotExist:
            return {"status": "error", "message": "Petro account not found in DB."}
            
        vehicles = list(Vehicle.objects.filter(status='active')[:5])
        if not vehicles:
            return {"status": "success", "message": "No vehicles found to sync."}
            
        records_created = 0
        for _ in range(random.randint(1, 4)):
            vehicle = random.choice(vehicles)
            quantity = Decimal(str(random.randint(20, 80)))
            price_per_litre = Decimal('98.50')
            
            # Create the fuel record (automatically deducts from master balance)
            FuelRecord.objects.create(
                vehicle=vehicle,
                date=timezone.now().date(),
                fuel_quantity=quantity,
                fuel_price=price_per_litre,
                petro_account=account,
                api_reference_number=f"TXN-{random.randint(100000, 999999)}",
                fuel_station=random.choice(["HPCL Hosur", "BPCL Electronic City", "IOCL Silk Board"])
                # Note: opening_km and closing_km are left blank as they are unknown from the API
            )
            records_created += 1
            
        return {
            "status": "success", 
            "message": f"Successfully synced {records_created} fuel transactions.",
            "new_balance": account.balance
        }
