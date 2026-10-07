import urllib.parse
from decimal import Decimal
from django.utils import timezone
from django.db import transaction
from operations.models import Trip, TripHotel
from .models import HotelConfirmationVoucher, HotelVoucherGuest


def generate_voucher_number():
    """Generates unique sequential hotel voucher number like HCV-2026-00001."""
    year = timezone.now().year
    prefix = f"HCV-{year}-"
    last = HotelConfirmationVoucher.objects.filter(
        voucher_number__startswith=prefix
    ).order_by('-id').first()

    if last and last.voucher_number:
        try:
            last_seq = int(last.voucher_number.split('-')[-1])
            new_seq = last_seq + 1
        except (ValueError, IndexError):
            new_seq = 1
    else:
        new_seq = 1

    return f"{prefix}{new_seq:05d}"


@transaction.atomic
def create_hotel_voucher(
    trip: Trip,
    trip_hotel: TripHotel = None,
    hotel_name: str = '',
    hotel_city: str = 'Coimbatore',
    hotel_address: str = '',
    hotel_phone: str = '',
    hotel_email: str = '',
    reservation_contact: str = '',
    check_in_date = None,
    check_out_date = None,
    lead_guest_name: str = '',
    lead_guest_phone: str = '',
    total_adults: int = 2,
    total_children: int = 0,
    total_rooms: int = 1,
    room_category: str = 'deluxe',
    meal_plan: str = 'MAP',
    agreed_tariff: Decimal = Decimal('0.00'),
    advance_paid: Decimal = Decimal('0.00'),
    billing_instruction: str = 'bill_to_company',
    special_requests: str = '',
    inclusions_notes: str = ''
):
    """
    Creates a new Hotel Confirmation Voucher linked to a trip and optional trip hotel.
    Populates default guest manifest.
    """
    # Auto-resolve dates from trip or trip_hotel
    cin = check_in_date
    if isinstance(cin, str) and cin:
        from datetime import datetime
        cin = datetime.strptime(cin[:10], '%Y-%m-%d').date()
    elif not cin and trip_hotel and trip_hotel.check_in_date:
        cin = trip_hotel.check_in_date
    elif not cin:
        cin = trip.start_date

    cout = check_out_date
    if isinstance(cout, str) and cout:
        from datetime import datetime
        cout = datetime.strptime(cout[:10], '%Y-%m-%d').date()
    elif not cout and trip_hotel and trip_hotel.check_out_date:
        cout = trip_hotel.check_out_date
    elif not cout:
        cout = trip.end_date

    nights = max(1, (cout - cin).days) if (cin and cout) else 1

    h_name = hotel_name or (trip_hotel.hotel_name if trip_hotel else 'Partner Resort & Hotel')
    r_cat = room_category or (trip_hotel.hotel_room_type if trip_hotel and trip_hotel.hotel_room_type else 'deluxe')

    # Resolve lead guest details
    g_name = lead_guest_name
    g_phone = lead_guest_phone
    if not g_name and trip.booking:
        g_name = trip.booking.guest_name or (trip.booking.party.name if trip.booking.party else '')
        g_phone = trip.booking.guest_phone or (trip.booking.party.phone if trip.booking.party else '')
    if not g_name:
        g_name = "Guest Group"
    if not g_phone:
        g_phone = "+91 98422 12345"

    sp_req = special_requests or (trip_hotel.notes if trip_hotel else '')
    if "driver" not in sp_req.lower():
        sp_req = (sp_req + " | Driver accommodation and food requested.").strip(" | ")

    voucher = HotelConfirmationVoucher(
        voucher_number=generate_voucher_number(),
        trip=trip,
        trip_hotel=trip_hotel,
        hotel_name=h_name,
        hotel_city=hotel_city,
        hotel_address=hotel_address,
        hotel_phone=hotel_phone,
        hotel_email=hotel_email,
        reservation_contact=reservation_contact,
        check_in_date=cin,
        check_out_date=cout,
        total_nights=nights,
        lead_guest_name=g_name,
        lead_guest_phone=g_phone,
        total_adults=total_adults,
        total_children=total_children,
        total_rooms=total_rooms,
        room_category=r_cat,
        meal_plan=meal_plan,
        inclusions_notes=inclusions_notes or "Welcome Drink on Arrival, Complimentary Wi-Fi, Breakfast & Dinner.",
        special_requests=sp_req,
        billing_instruction=billing_instruction,
        agreed_hotel_tariff=Decimal(str(agreed_tariff or 0)),
        advance_paid_to_hotel=Decimal(str(advance_paid or 0)),
        status='issued'
    )
    voucher.recalculate_balance()
    voucher.save()

    # Create primary guest record in guest list
    HotelVoucherGuest.objects.create(
        voucher=voucher,
        room_label="Room 101",
        guest_name=g_name,
        age=35,
        gender="M",
        id_proof_type="aadhaar"
    )

    # If trip_hotel status was pending, update it
    if trip_hotel:
        trip_hotel.confirmation_status = 'confirmed'
        trip_hotel.save(update_fields=['confirmation_status'])

    return voucher


def generate_hotel_whatsapp_link(voucher: HotelConfirmationVoucher):
    """
    Constructs an executive WhatsApp dispatch message and click-to-chat URL
    for the hotel reservations desk.
    """
    meal_dict = {
        'EP': 'EP (Room Only - No Meals)',
        'CP': 'CP (Continental - Breakfast Included)',
        'MAP': 'MAP (Breakfast + Dinner Included)',
        'AP': 'AP (All Meals - Breakfast, Lunch & Dinner Included)',
    }
    meal_text = meal_dict.get(voucher.meal_plan, voucher.meal_plan)

    cin_t = voucher.check_in_time.strftime('%I:%M %p') if hasattr(voucher.check_in_time, 'strftime') else str(voucher.check_in_time)
    cout_t = voucher.check_out_time.strftime('%I:%M %p') if hasattr(voucher.check_out_time, 'strftime') else str(voucher.check_out_time)

    msg = (
        f"🏨 *HOTEL RESERVATION CONFIRMATION VOUCHER*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 *Voucher Ref:* {voucher.voucher_number}\n"
        f"🏢 *Hotel / Resort:* {voucher.hotel_name} ({voucher.hotel_city})\n"
        f"👤 *Lead Guest:* {voucher.lead_guest_name} ({voucher.lead_guest_phone})\n"
        f"👥 *Total Guests:* {voucher.total_adults} Adults, {voucher.total_children} Children\n"
        f"📅 *Check-In:* {voucher.check_in_date.strftime('%d-%b-%Y')} ({cin_t})\n"
        f"📅 *Check-Out:* {voucher.check_out_date.strftime('%d-%b-%Y')} ({cout_t})\n"
        f"🌙 *Duration:* {voucher.total_nights} Night(s)\n"
        f"🛏️ *Rooms:* {voucher.total_rooms} x {voucher.get_room_category_display()}\n"
        f"🍽️ *Meal Plan:* {meal_text}\n"
        f"💳 *Billing Terms:* {voucher.get_billing_instruction_display()}\n"
    )

    if voucher.special_requests:
        msg += f"⚠️ *Special Instructions:* {voucher.special_requests}\n"

    msg += (
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"✨ *Issued By:* Sivagayathiri Tours and Travels, Coimbatore\n"
        f"📞 *24x7 Operations Desk:* +91 98422 12345 / ops@sivagayathiri.in\n"
        f"Kindly acknowledge and reply with your CRS Reservation Reference."
    )

    # Clean phone
    phone = (voucher.hotel_phone or '').strip().replace(' ', '').replace('-', '').replace('+', '')
    if phone and not phone.startswith('91') and len(phone) == 10:
        phone = f"91{phone}"

    encoded = urllib.parse.quote(msg)
    wa_url = f"https://wa.me/{phone}?text={encoded}" if phone else f"https://wa.me/?text={encoded}"

    return {
        'message_text': msg,
        'whatsapp_url': wa_url,
        'voucher_number': voucher.voucher_number
    }
