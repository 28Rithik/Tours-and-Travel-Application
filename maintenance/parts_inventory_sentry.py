"""
maintenance/parts_inventory_sentry.py
Spare Parts & Consumables Store Inventory Management Sentry
Automates workshop inventory tracking, minimum reorder thresholds,
and parts issuance to vehicle maintenance job cards.
"""
from decimal import Decimal
from django.utils import timezone
from .models import SparePartItem, PartStockMovement
from core.models import Vehicle


def get_inventory_dashboard_metrics():
    """
    Computes stock statistics and reorder alerts.
    """
    all_parts = SparePartItem.objects.filter(is_active=True)
    total_items = all_parts.count()
    low_stock_items = [p for p in all_parts if p.is_low_stock]
    total_valuation = sum(p.total_inventory_value for p in all_parts)
    recent_issues = PartStockMovement.objects.filter(movement_type='jobcard_issue').count()

    return {
        'total_items': total_items,
        'low_stock_count': len(low_stock_items),
        'total_valuation': total_valuation,
        'recent_issues': recent_issues,
        'low_stock_parts': low_stock_items[:5],
    }


def seed_sample_spare_parts():
    """
    Seeds initial inventory catalog with authentic Indian commercial fleet spare parts.
    """
    if SparePartItem.objects.exists():
        return

    catalog = [
        {
            'part_code': 'OIL-15W40-SHELL',
            'name': 'Shell Rimula R4 X 15W-40 Synthetic Diesel Engine Oil',
            'category': 'lubricant_fluid',
            'applicable_models': 'Innova Crysta, Tempo Traveller, 40-Seater Coaches',
            'unit': 'Liters',
            'current_stock': Decimal('140.00'),
            'minimum_reorder_level': Decimal('35.00'),
            'unit_cost': Decimal('380.00'),
            'storage_bin': 'Bay 1 - Drum Racks',
        },
        {
            'part_code': 'COOL-RADICOOL-5L',
            'name': 'Castrol Radicool Heavy Duty Premix Coolant (5L Can)',
            'category': 'lubricant_fluid',
            'applicable_models': 'All Commercial Fleet Vehicles',
            'unit': 'Cans',
            'current_stock': Decimal('28.00'),
            'minimum_reorder_level': Decimal('10.00'),
            'unit_cost': Decimal('950.00'),
            'storage_bin': 'Rack A-1, Shelf 2',
        },
        {
            'part_code': 'PAD-CRYSTA-FR',
            'name': 'Bosch Front Disc Brake Pads Set (Innova Crysta)',
            'category': 'brake_system',
            'applicable_models': 'Toyota Innova Crysta / Hycross',
            'unit': 'Sets',
            'current_stock': Decimal('14.00'),
            'minimum_reorder_level': Decimal('4.00'),
            'unit_cost': Decimal('2450.00'),
            'storage_bin': 'Rack B-3, Bin 08',
        },
        {
            'part_code': 'TYRE-205-65-R16',
            'name': 'Bridgestone Duravis R624 Heavy Duty 205/65 R16 Tubeless Tyre',
            'category': 'tires_tubes',
            'applicable_models': 'Innova Crysta Commercial Fleet',
            'unit': 'Pieces',
            'current_stock': Decimal('3.00'),  # Low Stock!
            'minimum_reorder_level': Decimal('8.00'),
            'unit_cost': Decimal('6800.00'),
            'storage_bin': 'Tire Loft - Stacking Bay 4',
        },
        {
            'part_code': 'FILT-OIL-CRYSTA',
            'name': 'Toyota Genuine Spin-On Engine Oil Filter',
            'category': 'filters_plugs',
            'applicable_models': 'Innova Crysta 2.4L Diesel',
            'unit': 'Pieces',
            'current_stock': Decimal('22.00'),
            'minimum_reorder_level': Decimal('6.00'),
            'unit_cost': Decimal('420.00'),
            'storage_bin': 'Rack A-2, Bin 14',
        },
        {
            'part_code': 'WIPER-HYBRID-26',
            'name': 'Minda Hybrid All-Weather 26" Wiper Blade Pair',
            'category': 'wipers_accessories',
            'applicable_models': 'Innova Crysta & Tempo Traveller',
            'unit': 'Sets',
            'current_stock': Decimal('8.00'),
            'minimum_reorder_level': Decimal('5.00'),
            'unit_cost': Decimal('580.00'),
            'storage_bin': 'Rack C-1, Bin 02',
        },
        {
            'part_code': 'BULB-H4-24V',
            'name': 'Philips 24V 75/70W H4 Heavy Duty Halogen Headlamp Bulb',
            'category': 'electrical_lights',
            'applicable_models': 'BharatBenz & Ashok Leyland Luxury Coaches',
            'unit': 'Pieces',
            'current_stock': Decimal('4.00'),  # Low Stock!
            'minimum_reorder_level': Decimal('10.00'),
            'unit_cost': Decimal('190.00'),
            'storage_bin': 'Rack D-2, Electrical Drawer',
        }
    ]

    created_parts = []
    for item in catalog:
        p = SparePartItem.objects.create(**item)
        created_parts.append(p)

    # Seed sample movement logs
    v = Vehicle.objects.first()
    if v and created_parts:
        PartStockMovement.objects.create(
            part=created_parts[0],
            movement_type='jobcard_issue',
            quantity=Decimal('7.50'),
            unit_rate=Decimal('380.00'),
            total_amount=Decimal('2850.00'),
            vehicle=v,
            job_card_ref='JC-202610-019',
            issued_to_mechanic='Chief Mechanic K. Subramani',
            notes='Scheduled 40,000 KM major engine oil service',
        )
        PartStockMovement.objects.create(
            part=created_parts[2],
            movement_type='jobcard_issue',
            quantity=Decimal('1.00'),
            unit_rate=Decimal('2450.00'),
            total_amount=Decimal('2450.00'),
            vehicle=v,
            job_card_ref='JC-202610-022',
            issued_to_mechanic='Brake Specialist S. Ramesh',
            notes='Front disc brake pad replacement before Nilgiris ghat duty',
        )
