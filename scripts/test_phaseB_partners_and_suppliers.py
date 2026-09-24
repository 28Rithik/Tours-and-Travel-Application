import os
import sys
import datetime
from decimal import Decimal
import django

# Setup environment
sys.stdout.reconfigure(encoding='utf-8')
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
django.setup()

from django.utils import timezone
from django.contrib.auth.models import User
from django.test import Client as HttpClient
from core.models import Party, Client, Supplier, VehicleType
from crm.models import (
    PartnerProfile, PartyContactPerson, B2CCustomerProfile,
    SupplierProfile, SupplierContractedRate, SupplierServiceVoucher,
    Quotation, CommunicationLog
)

def run_tests():
    print("=" * 80)
    print("🚀 PHASE B VALIDATION: MULTI-ENTITY PARTNERS, SUPPLIERS & SERVICE VOUCHERS")
    print("=" * 80)

    # Setup User
    user, _ = User.objects.get_or_create(username='crm_phase_b_admin', defaults={'email': 'admin@travelerp.com', 'is_staff': True})
    user.set_password('AdminPass123!')
    user.save()

    # --------------------------------------------------------------------------
    # TEST 1: FTO & Corporate Management
    # --------------------------------------------------------------------------
    print("\n[TEST 1] FTO (Foreign Tour Operator) & Corporate Partner Management...")
    party_fto, _ = Party.objects.get_or_create(
        name="Kuoni Inbound Global Travel AG",
        defaults={
            'party_type': 'travel_agency',
            'phone': "+41 44 321 0000",
            'email': "inbound@kuonitravel.com",
            'gstin': "33AAACK1234F1Z9"
        }
    )

    partner_profile, _ = PartnerProfile.objects.get_or_create(
        party=party_fto,
        defaults={
            'category': 'diamond',
            'trade_name': "Kuoni Inbound Europe",
            'iata_number': "IATA-88776655",
            'credit_limit': Decimal('500000.00'),
            'pan_number': "AAACK1234F",
            'bank_beneficiary_name': "Kuoni Global Accounts",
            'bank_name': "UBS Switzerland",
            'bank_account_number': "CH930000000012345678",
            'swift_bic': "UBSWCHZH"
        }
    )

    # Add Multiple Contact Directory
    contact_ops, _ = PartyContactPerson.objects.get_or_create(
        party=party_fto,
        name="Hans Zimmer",
        defaults={
            'designation': "VP South Asia Contracting",
            'contact_type': 'operations',
            'phone': "+41 44 321 0011",
            'email': "hans.zimmer@kuoni.com",
            'is_primary': True
        }
    )

    contact_emergency, _ = PartyContactPerson.objects.get_or_create(
        party=party_fto,
        name="Elena Rossi",
        defaults={
            'designation': "24x7 Inbound Duty Manager",
            'contact_type': 'emergency',
            'phone': "+41 79 123 4567",
            'email': "emergency@kuoni.com",
            'is_primary': False
        }
    )

    assert partner_profile.category == 'diamond'
    assert partner_profile.credit_limit == Decimal('500000.00')
    assert party_fto.contact_persons.count() >= 2
    print(f"  ✓ Diamond FTO Profile established: {partner_profile}")
    print(f"  ✓ Authorized Credit Limit: ₹{partner_profile.credit_limit:,.2f}")
    print(f"  ✓ Primary Operations Contact: {contact_ops.name} ({contact_ops.designation})")
    print(f"  ✓ 24x7 Emergency Contact: {contact_emergency.name} ({contact_emergency.phone})")

    # --------------------------------------------------------------------------
    # TEST 2: Direct Retail B2C Customer Profiles
    # --------------------------------------------------------------------------
    print("\n[TEST 2] Direct Retail B2C Customer Management...")
    party_b2c, _ = Party.objects.get_or_create(
        name="Dr. Vikramaditya Sengupta",
        defaults={
            'party_type': 'individual',
            'phone': "9840011223",
            'email': "vikram.sengupta@aiims.edu"
        }
    )

    b2c_profile, _ = B2CCustomerProfile.objects.get_or_create(
        party=party_b2c,
        defaults={
            'full_name': "Dr. Vikramaditya Sengupta",
            'alternate_phone': "9444099887",
            'nationality': "Indian",
            'passport_number': "M8899001",
            'is_vip': True,
            'city': "Chennai",
            'state': "Tamil Nadu",
            'pincode': "600010",
            'instagram_handle': "@dr_vikram_travels",
            'linkedin_url': "https://linkedin.com/in/drvikramaditya",
            'refund_bank_name': "State Bank of India",
            'refund_account_no': "30012345678",
            'refund_ifsc': "SBIN0001234"
        }
    )

    assert b2c_profile.is_vip is True
    assert b2c_profile.passport_number == "M8899001"
    print(f"  ✓ B2C Traveler Profile verified: {b2c_profile}")
    print(f"  ✓ VIP Traveler Flag: {b2c_profile.is_vip} | Social: {b2c_profile.instagram_handle}")

    # --------------------------------------------------------------------------
    # TEST 3: Multi-Category Supplier Management
    # --------------------------------------------------------------------------
    print("\n[TEST 3] Multi-Category Supplier Profiles (Hotels, Transporters, Activities)...")
    
    # Supplier 1: Hotelier
    party_hotelier, _ = Party.objects.get_or_create(
        name="Savoy - IHCL SeleQtions",
        defaults={
            'party_type': 'supplier',
            'phone': "0423 2225500",
            'email': "savoy.ooty@ihcltata.com",
            'gstin': "33AAACI1234H1Z1"
        }
    )
    supplier_hotel, _ = SupplierProfile.objects.get_or_create(
        party=party_hotelier,
        defaults={
            'supplier_type': 'hotelier',
            'trade_name': "Savoy Heritage Hotel Ooty",
            'destination_city': "Ooty",
            'is_preferred': True,
            'bank_beneficiary_name': "The Indian Hotels Company Ltd",
            'bank_name': "HDFC Bank",
            'bank_account_number': "00600000001234",
            'bank_ifsc': "HDFC0000060"
        }
    )

    # Supplier 2: Transporter
    party_transporter, _ = Party.objects.get_or_create(
        name="Nilgiris Mountain Roads Transport",
        defaults={
            'party_type': 'supplier',
            'phone': "9443311223",
            'email': "fleet@nilgiristrans.com"
        }
    )
    supplier_transport, _ = SupplierProfile.objects.get_or_create(
        party=party_transporter,
        defaults={
            'supplier_type': 'transporter',
            'destination_city': "Ooty",
            'is_preferred': True
        }
    )

    assert supplier_hotel.supplier_type == 'hotelier'
    assert supplier_hotel.is_preferred is True
    assert supplier_transport.supplier_type == 'transporter'
    print(f"  ✓ Preferred Hotelier Master registered: {supplier_hotel}")
    print(f"  ✓ Transporter Master registered: {supplier_transport}")

    # --------------------------------------------------------------------------
    # TEST 4: Contracted Seasonal Rates & Margin Savings
    # --------------------------------------------------------------------------
    print("\n[TEST 4] Negotiated Supplier Contracted Rates & Seasonality...")
    
    # Rate 1: Peak Season (Summer)
    rate_peak, _ = SupplierContractedRate.objects.get_or_create(
        supplier=supplier_hotel,
        seasonality='peak',
        service_name="Heritage Grand Valley Room",
        defaults={
            'service_category': 'hotel_room',
            'room_type': "Heritage Grand Room",
            'meal_plan': 'CP',
            'rack_rate': Decimal('12000.00'),
            'contracted_buy_rate': Decimal('8500.00'),
            'is_active': True
        }
    )

    # Rate 2: Regular Season
    rate_reg, _ = SupplierContractedRate.objects.get_or_create(
        supplier=supplier_hotel,
        seasonality='regular',
        service_name="Heritage Grand Valley Room",
        defaults={
            'service_category': 'hotel_room',
            'room_type': "Heritage Grand Room",
            'meal_plan': 'CP',
            'rack_rate': Decimal('8000.00'),
            'contracted_buy_rate': Decimal('5600.00'),
            'is_active': True
        }
    )

    expected_peak_savings = round(((Decimal('12000') - Decimal('8500')) / Decimal('12000')) * Decimal('100.0'), 1)
    assert rate_peak.savings_percent == expected_peak_savings
    print(f"  ✓ Peak Rate: Rack ₹{rate_peak.rack_rate:,.0f} -> DMC Buy ₹{rate_peak.contracted_buy_rate:,.0f} ({rate_peak.savings_percent}% savings)")
    print(f"  ✓ Regular Rate: Rack ₹{rate_reg.rack_rate:,.0f} -> DMC Buy ₹{rate_reg.contracted_buy_rate:,.0f} ({rate_reg.savings_percent}% savings)")

    # --------------------------------------------------------------------------
    # TEST 5: Service Voucher & Purchase Order (LPO) Generation
    # --------------------------------------------------------------------------
    print("\n[TEST 5] Supplier Service Voucher & Purchase Order Generation...")
    
    # Check existing or create Quotation
    quote = Quotation.objects.first()
    
    voucher = SupplierServiceVoucher.objects.create(
        supplier=supplier_hotel,
        voucher_type='hotel_reservation',
        quotation=quote,
        guest_name="Dr. Vikramaditya Sengupta & Family",
        guest_phone="9840011223",
        pax_count=4,
        service_date_start=datetime.date.today() + datetime.timedelta(days=15),
        service_date_end=datetime.date.today() + datetime.timedelta(days=17),
        duration_nights=2,
        hotel_room_type="Heritage Grand Room",
        hotel_meal_plan="CP",
        room_count=2,
        contracted_unit_cost=Decimal('8500.00'),
        total_payable_to_supplier=Decimal('34000.00'), # 2 rooms x 2 nights x 8500
        special_instructions="Honeymoon arrangement, upper floor valley view rooms requested",
        created_by=user,
        status='draft'
    )

    assert voucher.voucher_number.startswith("VCH-")
    assert len(voucher.confirmation_token) > 20
    assert voucher.duration_nights == 2
    assert voucher.total_payable_to_supplier == Decimal('34000.00')
    print(f"  ✓ Generated Voucher: {voucher.voucher_number} (Status: {voucher.status})")
    print(f"  ✓ Unique Confirmation Token: {voucher.confirmation_token[:12]}...")
    print(f"  ✓ Total Settlement Payable: ₹{voucher.total_payable_to_supplier:,.2f}")

    # --------------------------------------------------------------------------
    # TEST 6: Automated Supplier Dispatch Signal & Extranet Confirmation
    # --------------------------------------------------------------------------
    print("\n[TEST 6] Automated Supplier WhatsApp Dispatch & Extranet Confirmation...")
    
    # Transition to 'issued'
    voucher.status = 'issued'
    voucher.issued_at = timezone.now()
    voucher.save()

    # Verify communication logged in CommunicationLog
    comm = CommunicationLog.objects.filter(client=party_hotelier, message_content__icontains=voucher.voucher_number).first()
    assert comm is not None, "Automated WhatsApp dispatch log must be created on voucher issue."
    print(f"  ✓ Automated dispatch logged to {party_hotelier.name}")

    # Simulate Supplier opening Extranet Portal & submitting confirmation code
    http = HttpClient()
    extranet_url = f"/crm/vouchers/extranet/{voucher.confirmation_token}/"
    resp = http.get(extranet_url)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    assert b"Supplier Extranet" in resp.content
    print(f"  ✓ GET {extranet_url} -> 200 OK (Supplier Extranet loaded)")

    # POST confirmation
    post_resp = http.post(extranet_url, {
        'action': 'confirm',
        'confirmation_reference': 'SAVOY-CONF-98441',
        'supplier_notes': 'Heritage Valley View Rooms 104 and 105 confirmed.'
    })
    assert post_resp.status_code == 302, f"Expected redirect after post, got {post_resp.status_code}"

    voucher.refresh_from_db()
    assert voucher.status == 'confirmed', f"Expected status 'confirmed', got {voucher.status}"
    assert voucher.confirmation_reference == 'SAVOY-CONF-98441'
    assert voucher.confirmed_at is not None
    print(f"  ✓ Supplier 1-Click Confirmed: Status='{voucher.status}', Ref='{voucher.confirmation_reference}'")
    print(f"  ✓ Supplier Notes: '{voucher.supplier_notes}'")

    # --------------------------------------------------------------------------
    # TEST 7: HTTP Views Validation
    # --------------------------------------------------------------------------
    print("\n[TEST 7] HTTP Endpoints Validation...")
    http.force_login(user)

    # 1. Partner Management Console
    resp = http.get('/crm/partners/')
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    assert b"FTOs, B2B Agents" in resp.content
    print("  ✓ GET /crm/partners/ -> 200 OK (Partners Console rendered)")

    # 2. B2C Travelers Console
    resp = http.get('/crm/partners/?tab=b2c')
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    assert b"Direct Retail B2C Travelers" in resp.content
    print("  ✓ GET /crm/partners/?tab=b2c -> 200 OK (B2C Travelers Console rendered)")

    # 3. Supplier Management & Contracted Rates
    resp = http.get('/crm/suppliers/')
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    assert b"Supplier Master" in resp.content or b"Contracted" in resp.content
    print("  ✓ GET /crm/suppliers/ -> 200 OK (Suppliers & Rates Console rendered)")

    # 4. Service Voucher Console
    resp = http.get('/crm/vouchers/')
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    assert b"Service Vouchers" in resp.content
    print("  ✓ GET /crm/vouchers/ -> 200 OK (Voucher Console rendered)")

    # 5. Service Voucher Detail / Document Presentation
    resp = http.get(f'/crm/vouchers/{voucher.id}/')
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    assert b"Official Supplier Service Order" in resp.content or b"Sivagayathiri Travels" in resp.content
    print(f"  ✓ GET /crm/vouchers/{voucher.id}/ -> 200 OK (Official Voucher Sheet rendered)")

    print("\n" + "=" * 80)
    print("🎉 ALL PHASE B VERIFICATION TESTS PASSED SUCCESSFULLY!")
    print("=" * 80)

if __name__ == '__main__':
    run_tests()
