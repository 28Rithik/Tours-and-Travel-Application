from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission, User


class Command(BaseCommand):
    help = "Sets up standard RBAC groups (Fleet_Managers, Booking_Managers, Finance_Team) with model permissions and demo staff accounts."

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Setting up RBAC User Groups and Permissions..."))

        # 1. Define Groups and their permission patterns (app_label, codenames or wildcards)
        group_specs = {
            'Fleet_Managers': {
                'desc': 'Fleet Operations, Vehicle Assets, GPS Radar, Inspections & RTO Compliance',
                'perm_filters': [
                    ('core', ['view_vehicle', 'add_vehicle', 'change_vehicle', 'view_driver', 'add_driver', 'change_driver', 'view_vehicletype', 'view_cleaner', 'change_cleaner']),
                    ('operations', ['view_trip', 'change_trip', 'view_booking']),
                    ('maintenance', ['view_compliancerecord', 'add_compliancerecord', 'change_compliancerecord', 'view_vehicledamageinspection', 'add_vehicledamageinspection', 'change_vehicledamageinspection', 'view_vehicledamagemarker', 'add_vehicledamagemarker']),
                    ('fleet_commute', None),  # all permissions in fleet_commute
                ]
            },
            'Booking_Managers': {
                'desc': 'Trip Dispatch, Booking Intake, CRM Pipelines, Quotes & Customer Care',
                'perm_filters': [
                    ('operations', ['add_booking', 'change_booking', 'delete_booking', 'view_booking', 'add_trip', 'change_trip', 'view_trip']),
                    ('core', ['add_party', 'change_party', 'view_party', 'view_vehicle', 'view_driver']),
                    ('crm', ['add_inquiry', 'change_inquiry', 'view_inquiry', 'add_quotation', 'change_quotation', 'view_quotation', 'add_customercomplaint', 'change_customercomplaint', 'view_customercomplaint', 'add_documentvaultitem', 'change_documentvaultitem', 'view_documentvaultitem', 'add_servicevoucher', 'change_servicevoucher', 'view_servicevoucher']),
                    ('packages', None),  # all package permissions
                    ('suppliers', ['view_hotelconfirmationvoucher', 'add_hotelconfirmationvoucher', 'change_hotelconfirmationvoucher']),
                    ('marketing', ['view_promotioncampaign', 'add_promotioncampaign', 'change_promotioncampaign']),
                ]
            },
            'Finance_Team': {
                'desc': 'Audit, B2B Ledger, GST Billing, Petty Cash, Tally/Zoho Export & Vendor Payables',
                'perm_filters': [
                    ('finance', ['add_tripexpense', 'change_tripexpense', 'view_tripexpense', 'add_payment', 'change_payment', 'view_payment', 'add_ledgeradjustment', 'change_ledgeradjustment', 'view_ledgeradjustment', 'add_corporategstinvoice', 'change_corporategstinvoice', 'view_corporategstinvoice', 'add_ewaybill', 'change_ewaybill', 'view_ewaybill', 'add_pettycashaccount', 'change_pettycashaccount', 'view_pettycashaccount', 'add_pettycashtransaction', 'change_pettycashtransaction', 'view_pettycashtransaction']),
                    ('suppliers', ['add_suppliertripcost', 'change_suppliertripcost', 'view_suppliertripcost', 'add_outsourcedtripsettlement', 'change_outsourcedtripsettlement', 'view_outsourcedtripsettlement']),
                    ('core', ['view_party', 'change_party', 'view_vehicle', 'view_driver']),
                    ('operations', ['view_trip', 'view_booking']),
                ]
            }
        }

        # 2. Create Groups and attach Permissions
        created_groups = {}
        for group_name, spec in group_specs.items():
            group, created = Group.objects.get_or_create(name=group_name)
            action = "Created" if created else "Found existing"
            self.stdout.write(f"  - {action} Group: {group_name} ({spec['desc']})")

            # Collect matching permissions
            assigned_perms = []
            for app_label, codenames in spec['perm_filters']:
                if codenames is None:
                    # All permissions for app
                    perms = Permission.objects.filter(content_type__app_label=app_label)
                else:
                    perms = Permission.objects.filter(content_type__app_label=app_label, codename__in=codenames)
                assigned_perms.extend(perms)

            group.permissions.set(assigned_perms)
            self.stdout.write(f"    Assigned {len(assigned_perms)} model permissions to {group_name}")
            created_groups[group_name] = group

        # 3. Create Demo Staff Users for Each Role
        demo_users = [
            {
                'username': 'fleet_mgr',
                'email': 'fleet@sivagayathiri.in',
                'password': 'fleet123',
                'first_name': 'Karthik',
                'last_name': 'FleetOps',
                'group': 'Fleet_Managers',
            },
            {
                'username': 'booking_mgr',
                'email': 'dispatch@sivagayathiri.in',
                'password': 'booking123',
                'first_name': 'Ananya',
                'last_name': 'Dispatch',
                'group': 'Booking_Managers',
            },
            {
                'username': 'finance_user',
                'email': 'accounts@sivagayathiri.in',
                'password': 'finance123',
                'first_name': 'Ramesh',
                'last_name': 'Accounts',
                'group': 'Finance_Team',
            },
        ]

        self.stdout.write("\nConfiguring Demo Staff Test Accounts...")
        for uinfo in demo_users:
            user, created = User.objects.get_or_create(
                username=uinfo['username'],
                defaults={
                    'email': uinfo['email'],
                    'first_name': uinfo['first_name'],
                    'last_name': uinfo['last_name'],
                    'is_staff': True,
                    'is_active': True,
                }
            )
            user.set_password(uinfo['password'])
            user.is_staff = True
            user.first_name = uinfo['first_name']
            user.last_name = uinfo['last_name']
            user.email = uinfo['email']
            user.save()

            # Add to respective group
            target_group = created_groups[uinfo['group']]
            user.groups.set([target_group])

            action = "Created" if created else "Updated"
            self.stdout.write(
                self.style.SUCCESS(
                    f"  [OK] {action} Staff Account: '{uinfo['username']}' | Role: {uinfo['group']} | Password: '{uinfo['password']}'"
                )
            )

        self.stdout.write(self.style.SUCCESS("\n[SUCCESS] RBAC Roles, Permissions, and Test Staff Users successfully configured."))
