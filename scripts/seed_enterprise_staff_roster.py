import os
import sys
from pathlib import Path
from decimal import Decimal

# Ensure utf-8 output
sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

os.environ['DJANGO_SETTINGS_MODULE'] = 'travelerp.settings'
os.environ['USE_POSTGRES'] = '1'

import django
django.setup()

from django.contrib.auth.models import User, Group
from core.models import StaffProfile, Driver

STAFF_ROSTER = [
    # --------------------------------------------------------------------------
    # 1. COIMBATORE CENTRAL HQ (Main Location & Central Command Center)
    # --------------------------------------------------------------------------
    {
        'username': 'admin_rajesh',
        'first_name': 'Rajesh',
        'last_name': 'Kannan',
        'email': 'rajesh.k@sivagayathiri.in',
        'role': 'admin',
        'employee_id': 'SGT-CBE-001',
        'branch': 'Coimbatore Central HQ',
        'department': 'Executive Directorate',
        'designation': 'Managing Director & Chief Executive',
        'phone': '+91 94431 10001',
        'approval_limit_inr': Decimal('2500000.00'),
        'avatar_color': '#e11d48',
    },
    {
        'username': 'mgr_vikram',
        'first_name': 'Vikram',
        'last_name': 'Sundaram',
        'email': 'vikram.s@sivagayathiri.in',
        'role': 'manager',
        'employee_id': 'SGT-CBE-002',
        'branch': 'Coimbatore Central HQ',
        'department': 'Operations Leadership',
        'designation': 'General Manager — Operations & Fleet',
        'phone': '+91 94431 10002',
        'approval_limit_inr': Decimal('500000.00'),
        'avatar_color': '#8b5cf6',
    },
    {
        'username': 'tour_ananya',
        'first_name': 'Ananya',
        'last_name': 'Deshmukh',
        'email': 'ananya.d@sivagayathiri.in',
        'role': 'tour_designer_lead',
        'employee_id': 'SGT-CBE-003',
        'branch': 'Coimbatore Central HQ',
        'department': 'Commercial & Tour Design',
        'designation': 'Principal Tour Architect & Itinerary Lead',
        'phone': '+91 94431 10003',
        'approval_limit_inr': Decimal('100000.00'),
        'avatar_color': '#0ea5e9',
    },
    {
        'username': 'ops_suresh',
        'first_name': 'Suresh',
        'last_name': 'Balaji',
        'email': 'suresh.b@sivagayathiri.in',
        'role': 'operations',
        'employee_id': 'SGT-CBE-004',
        'branch': 'Coimbatore Central HQ',
        'department': 'Fleet & Dispatch Operations',
        'designation': 'Head of Central Fleet Dispatch',
        'phone': '+91 94431 10004',
        'approval_limit_inr': Decimal('150000.00'),
        'avatar_color': '#0284c7',
    },
    {
        'username': 'night_arvind',
        'first_name': 'Arvind',
        'last_name': 'Swaminathan',
        'email': 'arvind.s@sivagayathiri.in',
        'role': 'night_dispatcher',
        'employee_id': 'SGT-CBE-005',
        'branch': 'Coimbatore Central HQ',
        'department': 'Night Safety & Emergency SOS',
        'designation': '24/7 Night SOS Controller & Incident Lead',
        'phone': '+91 94431 10005',
        'approval_limit_inr': Decimal('75000.00'),
        'avatar_color': '#312e81',
    },
    {
        'username': 'compliance_bala',
        'first_name': 'Balasubramanian',
        'last_name': 'S',
        'email': 'bala.rto@sivagayathiri.in',
        'role': 'compliance_rto_officer',
        'employee_id': 'SGT-CBE-006',
        'branch': 'Coimbatore Central HQ',
        'department': 'Safety & Regulatory Compliance',
        'designation': 'Senior RTO Liaison & Fleet Compliance Officer',
        'phone': '+91 94431 10006',
        'approval_limit_inr': Decimal('100000.00'),
        'avatar_color': '#0369a1',
    },
    {
        'username': 'tax_srinivas',
        'first_name': 'Srinivas',
        'last_name': 'V',
        'email': 'srinivas.tax@sivagayathiri.in',
        'role': 'finance_controller',
        'employee_id': 'SGT-CBE-007',
        'branch': 'Coimbatore Central HQ',
        'department': 'Corporate Finance & Taxation',
        'designation': 'Chief Financial Controller & Tax Lead',
        'phone': '+91 94431 10007',
        'approval_limit_inr': Decimal('1000000.00'),
        'avatar_color': '#7c3aed',
    },
    {
        'username': 'cash_ramesh',
        'first_name': 'Ramesh',
        'last_name': 'Chandran',
        'email': 'ramesh.c@sivagayathiri.in',
        'role': 'treasury_petty_cashier',
        'employee_id': 'SGT-CBE-008',
        'branch': 'Coimbatore Central HQ',
        'department': 'Treasury & Depot Cash Custody',
        'designation': 'Head Office Cashier & Fastag Custodian',
        'phone': '+91 94431 10008',
        'approval_limit_inr': Decimal('50000.00'),
        'avatar_color': '#ca8a04',
    },

    # --------------------------------------------------------------------------
    # 2. TIRUPUR BRANCH (Knitwear Corridor & Corporate Commute Hub)
    # --------------------------------------------------------------------------
    {
        'username': 'mgr_senthil',
        'first_name': 'Senthil',
        'last_name': 'Kumar',
        'email': 'senthil.tpr@sivagayathiri.in',
        'role': 'manager',
        'employee_id': 'SGT-TPR-001',
        'branch': 'Tirupur Branch',
        'department': 'Regional Branch Management',
        'designation': 'Branch Manager — Tirupur Hub',
        'phone': '+91 94432 20001',
        'approval_limit_inr': Decimal('200000.00'),
        'avatar_color': '#8b5cf6',
    },
    {
        'username': 'b2b_karthik',
        'first_name': 'Karthik',
        'last_name': 'Rajan',
        'email': 'karthik.r@sivagayathiri.in',
        'role': 'b2b_corporate_lead',
        'employee_id': 'SGT-TPR-002',
        'branch': 'Tirupur Branch',
        'department': 'Corporate Mobility & B2B Contracts',
        'designation': 'Garment SEZ Commute Roster Lead',
        'phone': '+91 94432 20002',
        'approval_limit_inr': Decimal('75000.00'),
        'avatar_color': '#4f46e5',
    },
    {
        'username': 'acct_meena',
        'first_name': 'Meenakshi',
        'last_name': 'Raman',
        'email': 'meenakshi.r@sivagayathiri.in',
        'role': 'operation_account',
        'employee_id': 'SGT-TPR-003',
        'branch': 'Tirupur Branch',
        'department': 'Accounts & Trip Settlement',
        'designation': 'Senior Trip Settlement & Billing Officer',
        'phone': '+91 94432 20003',
        'approval_limit_inr': Decimal('250000.00'),
        'avatar_color': '#d97706',
    },

    # --------------------------------------------------------------------------
    # 3. ERODE BRANCH (Textile Hub & Fleet Maintenance Garage)
    # --------------------------------------------------------------------------
    {
        'username': 'mgr_manickam',
        'first_name': 'Manickam',
        'last_name': 'Chettiar',
        'email': 'manickam.erd@sivagayathiri.in',
        'role': 'manager',
        'employee_id': 'SGT-ERD-001',
        'branch': 'Erode Branch',
        'department': 'Regional Branch Management',
        'designation': 'Branch Manager — Erode Hub',
        'phone': '+91 94433 30001',
        'approval_limit_inr': Decimal('200000.00'),
        'avatar_color': '#8b5cf6',
    },
    {
        'username': 'sales_praveen',
        'first_name': 'Praveen',
        'last_name': 'Kumar',
        'email': 'praveen.k@sivagayathiri.in',
        'role': 'sales_executive',
        'employee_id': 'SGT-ERD-002',
        'branch': 'Erode Branch',
        'department': 'Commercial & Tour Sales',
        'designation': 'Kongu Belt Sales Executive',
        'phone': '+91 94433 30002',
        'approval_limit_inr': Decimal('50000.00'),
        'avatar_color': '#10b981',
    },
    {
        'username': 'workshop_karthik',
        'first_name': 'Karthik',
        'last_name': 'Raghavan',
        'email': 'karthik.mech@sivagayathiri.in',
        'role': 'workshop_manager',
        'employee_id': 'SGT-ERD-003',
        'branch': 'Erode Branch',
        'department': 'Fleet Maintenance & Workshop',
        'designation': 'Regional Garage & Maintenance Supervisor',
        'phone': '+91 94433 30003',
        'approval_limit_inr': Decimal('150000.00'),
        'avatar_color': '#ea580c',
    },

    # --------------------------------------------------------------------------
    # 4. CHENNAI BRANCH (Metro Branch & Airport Concierge)
    # --------------------------------------------------------------------------
    {
        'username': 'mgr_kothandaraman',
        'first_name': 'Kothandaraman',
        'last_name': 'R',
        'email': 'kothandaraman.maa@sivagayathiri.in',
        'role': 'manager',
        'employee_id': 'SGT-MAA-001',
        'branch': 'Chennai Branch',
        'department': 'Regional Branch Management',
        'designation': 'Regional General Manager — Chennai',
        'phone': '+91 94434 40001',
        'approval_limit_inr': Decimal('350000.00'),
        'avatar_color': '#8b5cf6',
    },
    {
        'username': 'sales_priya',
        'first_name': 'Priya',
        'last_name': 'Natarajan',
        'email': 'priya.n@sivagayathiri.in',
        'role': 'sales_executive',
        'employee_id': 'SGT-MAA-002',
        'branch': 'Chennai Branch',
        'department': 'Commercial & Corporate Proposals',
        'designation': 'Senior Enterprise Sales Executive',
        'phone': '+91 94434 40002',
        'approval_limit_inr': Decimal('75000.00'),
        'avatar_color': '#10b981',
    },
    {
        'username': 'support_divya',
        'first_name': 'Divya',
        'last_name': 'Selvam',
        'email': 'divya.s@sivagayathiri.in',
        'role': 'customer_service',
        'employee_id': 'SGT-MAA-003',
        'branch': 'Chennai Branch',
        'department': 'Guest Experience & Concierge',
        'designation': 'Airport VIP Arrival Concierge Specialist',
        'phone': '+91 94434 40003',
        'approval_limit_inr': Decimal('25000.00'),
        'avatar_color': '#06b6d4',
    },

    # --------------------------------------------------------------------------
    # 5. HOSUR BRANCH (Industrial Corridor & Karnataka Border Desk)
    # --------------------------------------------------------------------------
    {
        'username': 'mgr_venkatesh',
        'first_name': 'Venkatesh',
        'last_name': 'Murthy',
        'email': 'venkatesh.m@sivagayathiri.in',
        'role': 'manager',
        'employee_id': 'SGT-HSR-001',
        'branch': 'Hosur Branch',
        'department': 'Regional Branch Management',
        'designation': 'Branch Manager — Hosur Industrial Station',
        'phone': '+91 94435 50001',
        'approval_limit_inr': Decimal('250000.00'),
        'avatar_color': '#8b5cf6',
    },
    {
        'username': 'sales_arun',
        'first_name': 'Arun',
        'last_name': 'Kumar',
        'email': 'arun.k@sivagayathiri.in',
        'role': 'b2b_corporate_lead',
        'employee_id': 'SGT-HSR-002',
        'branch': 'Hosur Branch',
        'department': 'Corporate Mobility & SEZ Shuttles',
        'designation': 'Sipcot Shuttles & Electronic City Lead',
        'phone': '+91 94435 50002',
        'approval_limit_inr': Decimal('100000.00'),
        'avatar_color': '#4f46e5',
    },
    {
        'username': 'cash_selvaraj',
        'first_name': 'Selvaraj',
        'last_name': 'N',
        'email': 'selvaraj.n@sivagayathiri.in',
        'role': 'treasury_petty_cashier',
        'employee_id': 'SGT-HSR-003',
        'branch': 'Hosur Branch',
        'department': 'Treasury & Border Cash Desk',
        'designation': 'Border Permit & FASTag Cash Custodian',
        'phone': '+91 94435 50003',
        'approval_limit_inr': Decimal('30000.00'),
        'avatar_color': '#ca8a04',
    },

    # --------------------------------------------------------------------------
    # 6. TIRUCHIRAPPALLI (TRICHY) BRANCH (Central Transit & Temple Circuit Hub)
    # --------------------------------------------------------------------------
    {
        'username': 'mgr_ramanathan',
        'first_name': 'Ramanathan',
        'last_name': 'S',
        'email': 'ramanathan.trz@sivagayathiri.in',
        'role': 'manager',
        'employee_id': 'SGT-TRZ-001',
        'branch': 'Trichy Branch',
        'department': 'Regional Branch Management',
        'designation': 'Branch Manager — Central Tamil Nadu Hub',
        'phone': '+91 94436 60001',
        'approval_limit_inr': Decimal('200000.00'),
        'avatar_color': '#8b5cf6',
    },
    {
        'username': 'ops_arockiadass',
        'first_name': 'Arockiadass',
        'last_name': 'M',
        'email': 'arockiadass.m@sivagayathiri.in',
        'role': 'operations',
        'employee_id': 'SGT-TRZ-002',
        'branch': 'Trichy Branch',
        'department': 'Fleet & Dispatch Operations',
        'designation': 'Temple Circuit Fleet Dispatcher',
        'phone': '+91 94436 60002',
        'approval_limit_inr': Decimal('75000.00'),
        'avatar_color': '#0284c7',
    },
    {
        'username': 'driver_muthu',
        'first_name': 'Muthukumar',
        'last_name': 'S',
        'email': 'muthu.drv@sivagayathiri.in',
        'role': 'driver',
        'employee_id': 'SGT-TRZ-003',
        'branch': 'Trichy Branch',
        'department': 'Chauffeur Fleet Services',
        'designation': 'Lead Captain — Multi-Axle Volvo Coach',
        'phone': '+91 94436 60003',
        'approval_limit_inr': Decimal('10000.00'),
        'avatar_color': '#f97316',
    },
]

def seed_staff():
    print("=" * 80)
    print("SEEDING ENTERPRISE STAFF ROSTER (6 OPERATIONAL HUBS)")
    print("Main Location: Coimbatore Central HQ")
    print("Branches: Tirupur, Erode, Chennai, Hosur, Trichy")
    print("=" * 80)

    created_count = 0
    updated_count = 0

    for item in STAFF_ROSTER:
        # 1. Create or get user
        user, u_created = User.objects.get_or_create(
            username=item['username'],
            defaults={
                'first_name': item['first_name'],
                'last_name': item['last_name'],
                'email': item['email'],
                'is_staff': True,
                'is_superuser': (item['role'] == 'admin'),
            }
        )
        if u_created or not user.has_usable_password():
            user.set_password('SivaStaff@2026')
            user.save()

        # Link to Driver object if driver role
        linked_driver = None
        if item['role'] == 'driver':
            linked_driver = Driver.objects.filter(status='active').first()

        # 2. Create or update StaffProfile
        profile, p_created = StaffProfile.objects.update_or_create(
            user=user,
            defaults={
                'role': item['role'],
                'employee_id': item['employee_id'],
                'branch': item['branch'],
                'department': item['department'],
                'designation': item['designation'],
                'phone': item['phone'],
                'approval_limit_inr': item['approval_limit_inr'],
                'avatar_color': item['avatar_color'],
                'is_on_duty': True,
                'linked_driver': linked_driver,
            }
        )

        status_str = "CREATED" if p_created else "UPDATED"
        print(f"[{status_str}] {item['employee_id']}: {item['first_name']} {item['last_name']} -> {item['role']} @ {item['branch']}")
        if p_created:
            created_count += 1
        else:
            updated_count += 1

    print("\n" + "=" * 80)
    print(f"COMPLETED: {created_count} profiles created, {updated_count} profiles updated.")
    print(f"Total Staff Profiles in Database: {StaffProfile.objects.count()}")
    print("=" * 80)

if __name__ == '__main__':
    seed_staff()
