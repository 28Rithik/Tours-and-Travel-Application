import os
import sys
import django

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.abspath('.'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
django.setup()

from fleet_contracts.models import TransportContract

def seed_specs():
    print("Populating category_specifications for all Transport Contracts...")
    contracts = TransportContract.objects.all()
    count = 0

    corporate_portals = [
        "https://telematics.sivagayathiritravels.com/live/tcs-siruseri",
        "https://telematics.sivagayathiritravels.com/live/infosys-mcity",
        "https://telematics.sivagayathiritravels.com/live/cts-sholinganallur",
        "https://telematics.sivagayathiritravels.com/live/wipro-elcot",
        "https://telematics.sivagayathiritravels.com/live/amazon-perungudi",
        "https://telematics.sivagayathiritravels.com/live/accenture-tecci",
    ]

    school_attendants = [
        ("Kavitha M.", "+91 98401 23456"),
        ("Saraswathi R.", "+91 98402 34567"),
        ("Shanthi K.", "+91 98403 45678"),
        ("Meena Kumari V.", "+91 98404 56789"),
        ("Jayanthi S.", "+91 98405 67890"),
    ]

    factory_corridors = [
        "Sriperumbudur - Oragadam Industrial Corridor Fastag (SIPCOT Zone)",
        "Maraimalai Nagar - Singaperumal Koil Industrial Belt Fastag",
        "Ennore Port - Manali Petrochemical Expressway Toll Pass",
        "Irungattukottai SIPCOT Automotive Corridor Fastag",
    ]

    hospital_desks = [
        "Apollo Main Greams Road Casualty Desk: 044-28290200",
        "MIOT International Manapakkam Trauma Transport: 044-42002288",
        "SIMS Hospital Vadapalani Emergency Transit: 044-43577777",
        "Gleneagles Global Health City Perumbakkam Desk: 044-44777000",
    ]

    govt_officers = [
        ("Thiru. S. Ramanathan, Deputy Protocol Officer", "TN-POL-SEC-2026/088"),
        ("Tmt. R. Revathi, Under Secretary (Transport Desk)", "TN-SEC-GAD-2026/142"),
        ("Thiru. K. Chandrasekar, Senior Transport Officer", "TN-PSU-TIDEL-2026/019"),
        ("Thiru. V. Natarajan, Protocol Liaison Officer", "TN-GOV-VIP-2026/054"),
    ]

    for i, c in enumerate(contracts):
        cat = c.contract_category
        specs = {}

        if cat == 'corporate':
            specs = {
                'night_escort_mandatory': True,
                'escort_timing_window': '20:00 - 06:00',
                'safe_drop_confirmation': 'otp_sms' if i % 2 == 0 else 'security_call',
                'max_in_transit_minutes': 55 if i % 3 == 0 else 60,
                'pickup_grace_minutes': 10,
                'gps_telematics_portal': corporate_portals[i % len(corporate_portals)],
                'roster_cutoff_hours': 4,
                'panic_button_installed': True,
            }
        elif cat == 'school':
            attendant = school_attendants[i % len(school_attendants)]
            specs = {
                'speed_governor_certified': True,
                'speed_limit_kmh': 40,
                'female_attendant_name': attendant[0],
                'female_attendant_phone': attendant[1],
                'child_safety_grills_verified': True,
                'parent_alerts_enabled': True,
                'vacation_excluded_months': 'May (Summer Vacation 0-Fee)',
                'yellow_board_rto_verified': True,
                'first_aid_fire_extinguisher': True,
            }
        elif cat == 'factory':
            specs = {
                'shift_a_timing': '06:00 AM - 02:00 PM',
                'shift_b_timing': '02:00 PM - 10:00 PM',
                'shift_c_timing': '10:00 PM - 06:00 AM',
                'gate_siren_buffer_minutes': 15,
                'assembly_downtime_penalty_rate': 5000 if i % 2 == 0 else 7500,
                'highway_toll_allocation': factory_corridors[i % len(factory_corridors)],
                'min_bus_seating_capacity': 54 if i % 2 == 0 else 40,
                'worker_union_safety_charter': True,
            }
        elif cat == 'hospital':
            specs = {
                'emergency_recall_minutes': 25 if i % 2 == 0 else 30,
                'cabin_sanitization_protocol': 'Daily post-shift fumigation with hospital-grade disinfectant and HEPA air filter check',
                'ac_reliability_sla': True,
                'doctor_priority_dispatch': True,
                'hospital_emergency_desk': hospital_desks[i % len(hospital_desks)],
                'dual_crew_driver_rotation': True,
            }
        elif cat == 'government':
            officer = govt_officers[i % len(govt_officers)]
            specs = {
                'police_verification_verified': True,
                'uniform_protocol_mandatory': True,
                'govt_movement_order_ref': officer[1],
                'km_billing_clause': 'office_to_office' if i % 2 == 0 else 'garage_to_garage',
                'psu_tds_credit_terms': '60 Days Credit with Form 16A TDS Certificate',
                'protocol_officer_name': officer[0],
            }
        else:
            specs = {
                'general_terms': 'Standard commercial bulk transport parameters apply.',
            }

        c.category_specifications = specs
        c.save(update_fields=['category_specifications'])
        count += 1

    print(f"✅ Successfully populated category_specifications for {count} Transport Contracts.")

if __name__ == '__main__':
    seed_specs()
