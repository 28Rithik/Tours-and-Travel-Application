from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission, User
from decimal import Decimal
from core.models import StaffProfile, Driver


class Command(BaseCommand):
    help = "Sets up enterprise RBAC groups, permissions, and realistic Indian staff profiles across all departments."

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Setting up Enterprise RBAC Groups, Permissions & Staff Profiles..."))

        # 1. Group Specifications and Permission Filters
        group_specs = {
            'Super_Admins': {
                'desc': 'System Directors & Super Administrators (Full Root Access)',
                'perm_filters': [
                    ('core', None),
                    ('operations', None),
                    ('crm', None),
                    ('finance', None),
                    ('maintenance', None),
                    ('packages', None),
                    ('suppliers', None),
                    ('marketing', None),
                    ('analytics', None),
                ]
            },
            'General_Managers': {
                'desc': 'General & Branch Managers (Cross-Department Approvals & Governance)',
                'perm_filters': [
                    ('core', ['view_vehicle', 'view_driver', 'view_party', 'change_party']),
                    ('operations', ['view_trip', 'change_trip', 'view_booking', 'change_booking']),
                    ('crm', ['view_inquiry', 'change_inquiry', 'view_quotation', 'change_quotation', 'view_customercomplaint', 'change_customercomplaint', 'view_documentvaultitem']),
                    ('finance', ['view_tripexpense', 'change_tripexpense', 'view_payment', 'change_payment', 'view_corporategstinvoice', 'view_ledgeradjustment', 'change_ledgeradjustment']),
                    ('maintenance', ['view_compliancerecord', 'view_vehicledamageinspection']),
                    ('packages', ['view_customtourpackage', 'change_customtourpackage']),
                    ('suppliers', ['view_hotelconfirmationvoucher', 'view_suppliertripcost']),
                    ('analytics', None),
                ]
            },
            'Sales_Executives': {
                'desc': 'Senior Sales Executives & Tour Designers (Bespoke Quotations, Itineraries & CRM)',
                'perm_filters': [
                    ('operations', ['add_booking', 'change_booking', 'view_booking', 'view_trip']),
                    ('core', ['add_party', 'change_party', 'view_party', 'view_vehicle', 'view_vehicletype']),
                    ('crm', ['add_inquiry', 'change_inquiry', 'view_inquiry', 'add_quotation', 'change_quotation', 'view_quotation', 'view_documentvaultitem', 'add_documentvaultitem', 'view_customercomplaint', 'add_customercomplaint']),
                    ('packages', None),
                    ('suppliers', ['view_hotelconfirmationvoucher', 'add_hotelconfirmationvoucher', 'change_hotelconfirmationvoucher']),
                    ('marketing', ['view_promotioncampaign']),
                ]
            },
            'Corporate_Sales': {
                'desc': 'Corporate B2B Account Representatives (Bulk Contracts & Institutional Clients)',
                'perm_filters': [
                    ('operations', ['add_booking', 'change_booking', 'view_booking', 'view_trip']),
                    ('core', ['add_party', 'change_party', 'view_party', 'view_vehicle', 'view_vehicletype']),
                    ('crm', ['add_inquiry', 'change_inquiry', 'view_inquiry', 'add_quotation', 'change_quotation', 'view_quotation']),
                    ('packages', ['view_customtourpackage', 'view_packagetourbatch']),
                ]
            },
            'Operations_Dispatch': {
                'desc': 'Fleet & Dispatch Operations (Real-Time Radar, Vehicle Allocation, Driver Handover)',
                'perm_filters': [
                    ('core', ['view_vehicle', 'add_vehicle', 'change_vehicle', 'view_driver', 'add_driver', 'change_driver', 'view_vehicletype', 'view_cleaner']),
                    ('operations', ['view_trip', 'add_trip', 'change_trip', 'view_booking']),
                    ('maintenance', ['view_compliancerecord', 'add_compliancerecord', 'change_compliancerecord', 'view_vehicledamageinspection', 'add_vehicledamageinspection', 'change_vehicledamageinspection', 'view_vehicledamagemarker', 'add_vehicledamagemarker']),
                    ('fleet_commute', None),
                ]
            },
            'Accounts_Finance': {
                'desc': 'Operations Accounts & Billing (GST Tax Invoices, Driver Settlements, TDS 194C, B2B Ledgers)',
                'perm_filters': [
                    ('finance', ['add_tripexpense', 'change_tripexpense', 'view_tripexpense', 'add_payment', 'change_payment', 'view_payment', 'add_ledgeradjustment', 'change_ledgeradjustment', 'view_ledgeradjustment', 'add_corporategstinvoice', 'change_corporategstinvoice', 'view_corporategstinvoice', 'add_ewaybill', 'change_ewaybill', 'view_ewaybill', 'add_pettycashaccount', 'change_pettycashaccount', 'view_pettycashaccount', 'add_pettycashtransaction', 'change_pettycashtransaction', 'view_pettycashtransaction']),
                    ('suppliers', ['add_suppliertripcost', 'change_suppliertripcost', 'view_suppliertripcost', 'add_outsourcedtripsettlement', 'change_outsourcedtripsettlement', 'view_outsourcedtripsettlement']),
                    ('core', ['view_party', 'change_party', 'view_vehicle', 'view_driver']),
                    ('operations', ['view_trip', 'view_booking']),
                ]
            },
            'Chauffeur_Drivers': {
                'desc': 'Field Chauffeurs & Senior Drivers (Mobile Handover, Waypoints & SOS)',
                'perm_filters': [
                    ('operations', ['view_trip', 'change_trip']),
                    ('core', ['view_vehicle', 'view_driver']),
                ]
            },
            'Guest_Support': {
                'desc': 'Guest Experience & Trip Concierge Specialists (Passenger Care & Communications)',
                'perm_filters': [
                    ('operations', ['view_trip', 'view_booking']),
                    ('crm', ['view_customercomplaint', 'add_customercomplaint', 'change_customercomplaint', 'view_inquiry']),
                    ('core', ['view_party', 'view_driver', 'view_vehicle']),
                ]
            },
            # Legacy groups for backwards compatibility with earlier Phase 2-5 test suites
            'Fleet_Managers': {
                'desc': 'Legacy Alias: Fleet Operations',
                'perm_filters': [
                    ('core', ['view_vehicle', 'add_vehicle', 'change_vehicle', 'view_driver', 'add_driver', 'change_driver', 'view_vehicletype']),
                    ('operations', ['view_trip', 'change_trip', 'view_booking']),
                    ('maintenance', None),
                ]
            },
            'Booking_Managers': {
                'desc': 'Legacy Alias: Booking & Dispatch Managers',
                'perm_filters': [
                    ('operations', ['add_booking', 'change_booking', 'view_booking', 'add_trip', 'change_trip', 'view_trip']),
                    ('crm', None),
                    ('packages', None),
                ]
            },
            'Finance_Team': {
                'desc': 'Legacy Alias: Finance Team',
                'perm_filters': [
                    ('finance', None),
                    ('suppliers', None),
                ]
            }
        }

        # 2. Create Groups & Bind Permissions
        created_groups = {}
        for group_name, spec in group_specs.items():
            group, created = Group.objects.get_or_create(name=group_name)
            assigned_perms = []
            for app_label, codenames in spec['perm_filters']:
                if codenames is None:
                    perms = Permission.objects.filter(content_type__app_label=app_label)
                else:
                    perms = Permission.objects.filter(content_type__app_label=app_label, codename__in=codenames)
                assigned_perms.extend(perms)
            group.permissions.set(assigned_perms)
            created_groups[group_name] = group
            self.stdout.write(f"  [OK] Group '{group_name}' configured with {len(assigned_perms)} permissions.")

        # 3. Enterprise Staff Users Definition
        first_driver = Driver.objects.first()

        staff_roster = [
            {
                'username': 'admin_rajesh',
                'email': 'rajesh.kannan@sivagayathiri.in',
                'password': 'admin123',
                'first_name': 'Rajesh',
                'last_name': 'Kannan',
                'is_staff': True,
                'is_superuser': True,
                'groups': ['Super_Admins', 'General_Managers', 'Fleet_Managers', 'Booking_Managers', 'Finance_Team'],
                'profile': {
                    'role': 'admin',
                    'employee_id': 'SGT-EXEC-001',
                    'branch': 'Chennai Central HQ',
                    'department': 'Executive Management',
                    'designation': 'Managing Director & System Director',
                    'phone': '+91 94431 11001',
                    'emergency_contact': '+91 94431 99001',
                    'approval_limit_inr': Decimal('2500000.00'),
                    'monthly_sales_target_inr': Decimal('0.00'),
                    'avatar_color': '#e11d48',
                }
            },
            {
                'username': 'mgr_vikram',
                'email': 'vikram.sundaram@sivagayathiri.in',
                'password': 'manager123',
                'first_name': 'Vikram',
                'last_name': 'Sundaram',
                'is_staff': True,
                'is_superuser': False,
                'groups': ['General_Managers', 'Operations_Dispatch', 'Accounts_Finance', 'Fleet_Managers', 'Booking_Managers', 'Finance_Team'],
                'profile': {
                    'role': 'manager',
                    'employee_id': 'SGT-MGR-002',
                    'branch': 'Coimbatore Hub',
                    'department': 'Regional Operations',
                    'designation': 'General Manager (South India Operations)',
                    'phone': '+91 94431 22002',
                    'emergency_contact': '+91 94431 99002',
                    'approval_limit_inr': Decimal('500000.00'),
                    'monthly_sales_target_inr': Decimal('0.00'),
                    'avatar_color': '#8b5cf6',
                }
            },
            {
                'username': 'sales_priya',
                'email': 'priya.natarajan@sivagayathiri.in',
                'password': 'sales123',
                'first_name': 'Priya',
                'last_name': 'Natarajan',
                'is_staff': True,
                'is_superuser': False,
                'groups': ['Sales_Executives', 'Booking_Managers'],
                'profile': {
                    'role': 'sales_executive',
                    'employee_id': 'SGT-SLS-003',
                    'branch': 'Chennai Central HQ',
                    'department': 'Commercial & Tour Planning',
                    'designation': 'Senior Sales Executive & Tour Designer',
                    'phone': '+91 98425 33003',
                    'emergency_contact': '+91 98425 99003',
                    'approval_limit_inr': Decimal('50000.00'),
                    'monthly_sales_target_inr': Decimal('1500000.00'),
                    'avatar_color': '#10b981',
                }
            },
            {
                'username': 'sales_arun',
                'email': 'arun.kumar@sivagayathiri.in',
                'password': 'sales123',
                'first_name': 'Arun',
                'last_name': 'Kumar',
                'is_staff': True,
                'is_superuser': False,
                'groups': ['Corporate_Sales', 'Booking_Managers'],
                'profile': {
                    'role': 'sales',
                    'employee_id': 'SGT-SLS-004',
                    'branch': 'Bengaluru Station',
                    'department': 'Corporate Client Solutions',
                    'designation': 'Corporate Accounts Executive',
                    'phone': '+91 98425 44004',
                    'emergency_contact': '+91 98425 99004',
                    'approval_limit_inr': Decimal('30000.00'),
                    'monthly_sales_target_inr': Decimal('1200000.00'),
                    'avatar_color': '#059669',
                }
            },
            {
                'username': 'ops_suresh',
                'email': 'suresh.balaji@sivagayathiri.in',
                'password': 'ops123',
                'first_name': 'Suresh',
                'last_name': 'Balaji',
                'is_staff': True,
                'is_superuser': False,
                'groups': ['Operations_Dispatch', 'Fleet_Managers'],
                'profile': {
                    'role': 'operations',
                    'employee_id': 'SGT-OPS-005',
                    'branch': 'Coimbatore Hub',
                    'department': 'Fleet & Dispatch Operations',
                    'designation': 'Head of Fleet Operations & Dispatch',
                    'phone': '+91 94431 55005',
                    'emergency_contact': '+91 94431 99005',
                    'approval_limit_inr': Decimal('100000.00'),
                    'monthly_sales_target_inr': Decimal('0.00'),
                    'avatar_color': '#0284c7',
                }
            },
            {
                'username': 'acct_meena',
                'email': 'meenakshi.raman@sivagayathiri.in',
                'password': 'accounts123',
                'first_name': 'Meenakshi',
                'last_name': 'Raman',
                'is_staff': True,
                'is_superuser': False,
                'groups': ['Accounts_Finance', 'Finance_Team'],
                'profile': {
                    'role': 'operation_account',
                    'employee_id': 'SGT-FIN-006',
                    'branch': 'Chennai Central HQ',
                    'department': 'Accounts, Tax & Settlements',
                    'designation': 'Lead Accountant & GST Compliance Officer',
                    'phone': '+91 94431 66006',
                    'emergency_contact': '+91 94431 99006',
                    'approval_limit_inr': Decimal('250000.00'),
                    'monthly_sales_target_inr': Decimal('0.00'),
                    'avatar_color': '#d97706',
                }
            },
            {
                'username': 'driver_muthu',
                'email': 'muthukumar.s@sivagayathiri.in',
                'password': 'driver123',
                'first_name': 'Muthukumar',
                'last_name': 'S',
                'is_staff': True,
                'is_superuser': False,
                'groups': ['Chauffeur_Drivers'],
                'profile': {
                    'role': 'driver',
                    'employee_id': 'SGT-DRV-007',
                    'branch': 'Madurai Depo',
                    'department': 'Field Operations',
                    'designation': 'Master Chauffeur (Volvo Multi-Axle & Urbania)',
                    'phone': '+91 98425 77007',
                    'emergency_contact': '+91 98425 99007',
                    'approval_limit_inr': Decimal('5000.00'),
                    'monthly_sales_target_inr': Decimal('0.00'),
                    'avatar_color': '#f97316',
                    'linked_driver': first_driver,
                }
            },
            {
                'username': 'support_divya',
                'email': 'divya.selvam@sivagayathiri.in',
                'password': 'support123',
                'first_name': 'Divya',
                'last_name': 'Selvam',
                'is_staff': True,
                'is_superuser': False,
                'groups': ['Guest_Support', 'Booking_Managers'],
                'profile': {
                    'role': 'customer_service',
                    'employee_id': 'SGT-SUP-008',
                    'branch': 'Chennai Central HQ',
                    'department': 'Guest Experience & Concierge',
                    'designation': 'Passenger Care & Quality Specialist',
                    'phone': '+91 98425 88008',
                    'emergency_contact': '+91 98425 99008',
                    'approval_limit_inr': Decimal('10000.00'),
                    'monthly_sales_target_inr': Decimal('0.00'),
                    'avatar_color': '#06b6d4',
                }
            },
        ]

        # 4. Provision or Update Users & StaffProfiles
        self.stdout.write("\nProvisioning Enterprise Staff Profiles...")
        for entry in staff_roster:
            u, created = User.objects.get_or_create(
                username=entry['username'],
                defaults={
                    'email': entry['email'],
                    'first_name': entry['first_name'],
                    'last_name': entry['last_name'],
                    'is_staff': entry['is_staff'],
                    'is_superuser': entry['is_superuser'],
                    'is_active': True,
                }
            )
            u.set_password(entry['password'])
            u.first_name = entry['first_name']
            u.last_name = entry['last_name']
            u.email = entry['email']
            u.is_staff = entry['is_staff']
            u.is_superuser = entry['is_superuser']
            u.is_active = True
            u.save()

            # Assign groups
            target_groups = [created_groups[g] for g in entry['groups'] if g in created_groups]
            u.groups.set(target_groups)

            # Profile creation/update
            prof_data = entry['profile']
            sp, _ = StaffProfile.objects.get_or_create(user=u, defaults={'employee_id': prof_data['employee_id']})
            sp.role = prof_data['role']
            sp.employee_id = prof_data['employee_id']
            sp.branch = prof_data['branch']
            sp.department = prof_data['department']
            sp.designation = prof_data['designation']
            sp.phone = prof_data['phone']
            sp.emergency_contact = prof_data['emergency_contact']
            sp.approval_limit_inr = prof_data['approval_limit_inr']
            sp.monthly_sales_target_inr = prof_data['monthly_sales_target_inr']
            sp.avatar_color = prof_data['avatar_color']
            if 'linked_driver' in prof_data and prof_data['linked_driver']:
                sp.linked_driver = prof_data['linked_driver']
            sp.is_on_duty = True
            sp.save()

            status_str = "Created" if created else "Updated"
            self.stdout.write(f"  [+] {status_str}: {sp.employee_id} | {u.get_full_name()} ({sp.get_role_display()}) | User: {u.username}")

        # Also update legacy demo users (fleet_mgr, booking_mgr, finance_user) so tests remain fully compatible
        legacy_updates = [
            ('fleet_mgr', 'Fleet_Managers', 'operations', 'SGT-LEG-01', 'Fleet Manager Test'),
            ('booking_mgr', 'Booking_Managers', 'sales_executive', 'SGT-LEG-02', 'Booking Manager Test'),
            ('finance_user', 'Finance_Team', 'operation_account', 'SGT-LEG-03', 'Finance User Test'),
        ]
        for uname, gname, rname, empid, desig in legacy_updates:
            leg_user = User.objects.filter(username=uname).first()
            if leg_user:
                leg_grp = Group.objects.filter(name=gname).first()
                if leg_grp:
                    leg_user.groups.add(leg_grp)
                sp, _ = StaffProfile.objects.get_or_create(user=leg_user, defaults={'employee_id': empid})
                sp.role = rname
                sp.designation = desig
                sp.save()

        self.stdout.write(self.style.SUCCESS("\n[SUCCESS] All 8 Enterprise Roles, Groups & Staff Profiles are fully provisioned!"))
