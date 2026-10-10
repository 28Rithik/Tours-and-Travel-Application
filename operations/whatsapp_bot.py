import logging
import os
import re
from decimal import Decimal
from django.conf import settings
from django.utils import timezone
from django.urls import reverse

from core.models import Driver, Vehicle, Party, Client
from operations.models import Trip, EmergencyIncidentAlert, WhatsAppBotMessage, DriverHandoverSession
from integrations.communication import send_whatsapp_message

logger = logging.getLogger(__name__)


def normalize_phone_digits(phone):
    """
    Normalizes any phone string to digits only.
    Defaults to Indian 91 country code if 10 digits provided.
    """
    if not phone:
        return ""
    clean = re.sub(r'\D', '', str(phone))
    if len(clean) == 10:
        return f"91{clean}"
    if len(clean) > 10 and clean.startswith("0"):
        return f"91{clean[1:]}"
    return clean


def format_currency(val):
    try:
        return f"₹{Decimal(str(val or 0)):,.2f}"
    except Exception:
        return f"₹{val or 0}"


def generate_passenger_dispatch_sheet(trip, base_url="http://127.0.0.1:8000"):
    """
    Generates a luxury, high-conversion WhatsApp Trip Sheet for the passenger.
    Includes booking ref, vehicle brand/plate, captain name & contact,
    pickup schedule, live GPS tracking, and dynamic UPI payment.
    """
    guest = trip.guest_name or (trip.booking.guest_name if trip.booking else "Valued Guest")
    p_date = trip.start_date or (trip.booking.pickup_date if trip.booking else timezone.now().date())
    p_time = trip.start_time or (trip.booking.pickup_time if trip.booking else "Reporting Time")
    pickup_loc = trip.pickup_location or "Designated Pickup Point"
    destination = trip.destination or "Destination As Scheduled"

    veh = trip.vehicle
    veh_str = f"{veh.brand} {veh.model} ({veh.registration_number})" if veh else (
        trip.booking.vehicle_type.name if (trip.booking and trip.booking.vehicle_type) else "Premium Fleet Vehicle"
    )
    veh_type = veh.vehicle_type.name if (veh and veh.vehicle_type) else "Comfort AC"

    driver = trip.driver
    driver_name = driver.name if driver else "To Be Assigned Shortly"
    driver_phone = driver.phone if driver else "Operations Desk (+91 94431 23456)"
    driver_rating = getattr(driver, 'rating', 4.9) if driver else 4.9

    tracking_url = f"{base_url}/track/{trip.tracking_token}/" if trip.tracking_token else f"{base_url}/fleet/live/"
    
    total_val = trip.total_amount if hasattr(trip, 'total_amount') and trip.total_amount else (trip.fixed_amount or 0)
    received = trip.received_amount if hasattr(trip, 'received_amount') else 0
    balance = max(Decimal(str(total_val)) - Decimal(str(received)), Decimal('0'))

    # UPI Dynamic Payment Deep Link
    upi_vpa = getattr(settings, 'COMPANY_UPI_VPA', 'sivagayathiritravels@icici')
    upi_link = f"upi://pay?pa={upi_vpa}&pn=SivagayathiriTravels&am={balance}&cu=INR&tn=Trip_{trip.trip_id}"

    lines = [
        "✨ *SIVAGAYATHIRI TRAVELS — TRIP DISPATCH CONFIRMATION* ✨",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"Namaste *{guest}*! 🙏",
        f"Your private chauffeur-driven trip *#{trip.trip_id}* has been confirmed and scheduled.",
        "",
        "🚘 *VEHICLE & FLEET DETAILS*",
        f"• Vehicle: *{veh_str}*",
        f"• Category: {veh_type}",
        f"• Sanitzation & Safety: 100% Certified Cleaned",
        "",
        "🧑‍✈️ *YOUR ASSIGNED CAPTAIN*",
        f"• Name: *Captain {driver_name}*",
        f"• Contact: 📞 {driver_phone}",
        f"• Driver Rating: ⭐ {driver_rating} / 5.0 (Verified)",
        "",
        "📍 *JOURNEY SCHEDULE*",
        f"• Date: *{p_date}*",
        f"• Pickup Time: *{p_time}*",
        f"• Pickup Location: {pickup_loc}",
        f"• Destination: {destination}",
        "",
        "🛰️ *LIVE GPS VEHICLE TRACKING*",
        "Track your vehicle's live movement and arrival time:",
        f"👉 {tracking_url}",
        "",
        "💳 *BILLING & PAYMENT SUMMARY*",
        f"• Trip Total: {format_currency(total_val)}",
        f"• Advance Received: {format_currency(received)}",
        f"• Balance Payable: *{format_currency(balance)}*",
    ]

    if balance > 0:
        lines.extend([
            "",
            "⚡ *Instant UPI Payment Link:*",
            f"{upi_link}",
            "*(Tap link to pay securely via Google Pay, PhonePe, or Paytm)*",
        ])

    lines.extend([
        "",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "🚨 *24x7 Control Room & SOS Support:*",
        "Helpline: +91 94431 23456 | Reply *SOS* anytime for emergency assistance.",
        "Wishing you a memorable and peaceful journey!"
    ])

    return "\n".join(lines)


def generate_driver_briefing_sheet(trip, base_url="http://127.0.0.1:8000"):
    """
    Generates a WhatsApp briefing sheet dispatched to the Driver with a direct
    handover mobile link to upload start odometer photos.
    """
    driver_name = trip.driver.name if trip.driver else "Captain"
    p_date = trip.start_date or (trip.booking.pickup_date if trip.booking else timezone.now().date())
    p_time = trip.start_time or (trip.booking.pickup_time if trip.booking else "Reporting Time")
    pickup_loc = trip.pickup_location or "Designated Pickup Point"
    destination = trip.destination or "Designated Destination"
    guest = trip.guest_name or (trip.booking.guest_name if trip.booking else "Guest")
    guest_phone = trip.booking.guest_phone if (trip.booking and trip.booking.guest_phone) else "Provided on pickup"
    veh = trip.vehicle
    veh_str = f"{veh.brand} {veh.model} - {veh.registration_number}" if veh else "Assigned Vehicle"
    current_km = veh.current_km if (veh and veh.current_km) else 0

    handover_link = f"{base_url}/trip/{trip.pk}/handover/"

    lines = [
        f"Vanakkam *Captain {driver_name}*! 🫡",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"📋 *NEW TRIP DUTY ASSIGNMENT — #{trip.trip_id}*",
        "",
        f"• *Date & Time:* {p_date} @ {p_time}",
        f"• *Assigned Vehicle:* {veh_str}",
        f"• *Expected Start Odometer:* {current_km} KM",
        f"• *Guest Name:* {guest} (📞 {guest_phone})",
        f"• *Pickup:* {pickup_loc}",
        f"• *Destination:* {destination}",
        "",
        "📸 *MANDATORY DIGITAL HANDOVER:*",
        "Before departing depot/pickup, you MUST inspect vehicle and upload your start odometer photo:",
        f"👉 *Open Handover Portal:* {handover_link}",
        "",
        "💡 *Quick WhatsApp Commands:*",
        "• Reply *START* to open start duty handover.",
        "• Reply *END* when trip finishes to upload closing KM.",
        "• Reply *SOS* if you face breakdown, accident, or need help.",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "Drive safely and uphold Sivagayathiri Travels gold safety standards!"
    ]
    return "\n".join(lines)


def generate_emergency_sos_broadcast(alert, base_url="http://127.0.0.1:8000"):
    """
    Control room priority broadcast for Emergency SOS trigger.
    """
    veh_reg = alert.vehicle.registration_number if alert.vehicle else "N/A"
    driver_name = alert.driver.name if alert.driver else "N/A"
    driver_phone = alert.driver.phone if alert.driver else "N/A"
    trip_id = alert.trip.trip_id if alert.trip else "Non-Trip / En Route"
    lat, lng = alert.latitude, alert.longitude
    map_link = f"https://www.google.com/maps?q={lat},{lng}" if (lat and lng) else f"{base_url}/fleet/live/"

    lines = [
        "🚨🚨 *CRITICAL FLEET SOS EMERGENCY BROADCAST* 🚨🚨",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"• *Alert ID:* #{alert.incident_id}",
        f"• *Trip ID:* {trip_id}",
        f"• *Incident Type:* {alert.get_incident_type_display()}",
        f"• *Severity:* {alert.get_severity_display()}",
        f"• *Vehicle:* {veh_reg}",
        f"• *Captain:* {driver_name} (📞 {driver_phone})",
        f"• *Passengers:* {alert.passenger_count} ({alert.get_passengers_safety_status_display()})",
        f"• *Address/Landmark:* {alert.location_address or 'Highway Coordinates'}",
        f"• *Live Map Coordinates:* {map_link}",
        f"• *Driver Message:* {alert.description}",
        "",
        f"⚡ *Dispatch Standby Unit:* {base_url}/admin/operations/emergencyincidentalert/{alert.pk}/change/",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    ]
    return "\n".join(lines)


def process_inbound_message(sender_phone, raw_text, message_id=None, raw_payload=None, base_url="http://127.0.0.1:8000"):
    """
    Core AI & Rule-based NLP parser for WhatsApp Business Bot.
    Understands driver handover intents, passenger queries, and SOS triggers.
    Returns: (reply_text, intent, associated_trip)
    """
    clean_sender = normalize_phone_digits(sender_phone)
    text = (raw_text or "").strip()
    upper_text = text.upper()

    # Match driver by phone
    driver = Driver.objects.filter(phone__icontains=clean_sender[-10:]).first() if len(clean_sender) >= 10 else None
    
    # Match client / passenger by phone
    trip_passenger = None
    if len(clean_sender) >= 10:
        ten_digits = clean_sender[-10:]
        trip_passenger = Trip.objects.filter(
            booking__guest_phone__icontains=ten_digits
        ).order_by('-start_date').first()
        if not trip_passenger:
            trip_passenger = Trip.objects.filter(
                party__phone__icontains=ten_digits
            ).order_by('-start_date').first()

    # Active trip for driver
    active_driver_trip = None
    if driver:
        active_driver_trip = Trip.objects.filter(
            driver=driver,
            status__in=['assigned', 'started']
        ).order_by('start_date').first()
        if not active_driver_trip:
            active_driver_trip = Trip.objects.filter(
                driver=driver
            ).order_by('-start_date').first()

    relevant_trip = active_driver_trip or trip_passenger

    def match_intent(keywords):
        return any(re.search(r'\b' + re.escape(k) + r'\b', upper_text) for k in keywords)

    # =========================================================================
    # INTENT 1: EMERGENCY SOS TRIGGER
    # =========================================================================
    if match_intent(['SOS', 'EMERGENCY', 'ACCIDENT', 'HELP', 'BURST', 'BREAKDOWN']):
        intent = 'sos_trigger'
        # Auto-create EmergencyIncidentAlert
        veh = None
        drv = driver
        if relevant_trip:
            veh = relevant_trip.vehicle
            if not drv:
                drv = relevant_trip.driver
        if not veh and drv:
            veh = drv.default_vehicles.first() or Vehicle.objects.filter(default_driver=drv).first()
        if not veh:
            veh = Vehicle.objects.filter(status='active').first() or Vehicle.objects.first()
        if not drv:
            drv = Driver.objects.first()

        alert = EmergencyIncidentAlert.objects.create(
            incident_type='accident' if 'ACCIDENT' in upper_text else ('breakdown' if 'BREAKDOWN' in upper_text else 'other'),
            severity='critical',
            vehicle=veh,
            driver=drv,
            trip=relevant_trip,
            location_address=f"Broadcast from WhatsApp phone {sender_phone}",
            description=f"Auto SOS triggered via WhatsApp: {text}",
            passenger_count=relevant_trip.pax_count if (relevant_trip and relevant_trip.pax_count) else 1,
            passengers_safety_status='all_safe',
            status='reported'
        )

        # Dispatch alert to Control Room
        control_msg = generate_emergency_sos_broadcast(alert, base_url=base_url)
        control_phone = getattr(settings, 'FLEET_CONTROL_ROOM_PHONE', '919876543210')
        send_whatsapp_message(control_phone, control_msg)

        reply = (
            f"🚨 *EMERGENCY SOS LOGGED (#{alert.incident_id})* 🚨\n\n"
            f"Our Central 24x7 Fleet Operations Control Room has been alerted immediately.\n\n"
            f"• *Vehicle:* {veh.registration_number if veh else 'Fleet Unit'}\n"
            f"• *Status:* Critical Dispatch Mobilized\n"
            f"• *Control Room Helpline:* +91 94431 23456\n\n"
            f"Please stay calm and remain in a safe location. A dispatch officer is calling you right now."
        )

    # =========================================================================
    # INTENT 2: GST TAX INVOICE & E-WAY BILL DELIVERY
    # =========================================================================
    elif match_intent(['INVOICE', 'GST', 'TAX INVOICE', 'BILL PDF', 'MY BILL', 'EWAY', 'TAX BILL', 'RECEIPT']):
        intent = 'invoice_inquiry'
        from finance.models import CorporateGSTInvoice
        inv = None
        if len(clean_sender) >= 10:
            ten_digits = clean_sender[-10:]
            inv = CorporateGSTInvoice.objects.filter(
                party__phone__icontains=ten_digits
            ).order_by('-invoice_date', '-id').first()
            if not inv and relevant_trip:
                inv = CorporateGSTInvoice.objects.filter(trip=relevant_trip).order_by('-id').first()

        if inv:
            reply = generate_corporate_invoice_sheet(inv, base_url=base_url)
        else:
            reply = (
                f"🏛️ *Siva Gayathiri Tours & Travels — Billing Desk*\n\n"
                f"No issued Corporate GST Tax Invoice was found linked to phone *{sender_phone}*.\n\n"
                f"• Invoices are generated automatically within 24 hours of trip completion.\n"
                f"• To request a corporate GST bill or E-Way Bill copy, please email: *billing@sivagayathiritravels.com* with your Trip ID.\n"
                f"• Accounts Helpline: +91 94431 23456"
            )

    # =========================================================================
    # INTENT 3: START TRIP HANDOVER (DRIVER)
    # =========================================================================
    elif match_intent(['START', 'START TRIP', 'DUTY', 'OPENING']):
        intent = 'start_handover'
        if relevant_trip:
            handover_url = f"{base_url}/trip/{relevant_trip.pk}/handover/"
            reply = (
                f"🚖 *START DUTY HANDOVER — Trip #{relevant_trip.trip_id}*\n\n"
                f"Captain {driver.name if driver else 'Chauffeur'},\n"
                f"Vehicle: *{relevant_trip.vehicle or 'Assigned Vehicle'}*\n"
                f"Pickup: *{relevant_trip.pickup_location}* at {relevant_trip.start_time or 'Scheduled time'}\n\n"
                f"📸 *Please tap the link below to take the start odometer photo:*\n"
                f"👉 {handover_url}\n\n"
                f"Once uploaded, the trip will be marked started and passenger notified!"
            )
        else:
            reply = (
                "ℹ️ No active assigned trip found for your phone number.\n"
                "Please contact the fleet controller at +91 94431 23456."
            )

    # =========================================================================
    # INTENT 4: END TRIP HANDOVER (DRIVER)
    # =========================================================================
    elif match_intent(['END', 'END TRIP', 'CLOSE', 'COMPLETE', 'CLOSING']):
        intent = 'end_handover'
        if relevant_trip:
            handover_url = f"{base_url}/trip/{relevant_trip.pk}/handover/"
            reply = (
                f"🏁 *END DUTY HANDOVER — Trip #{relevant_trip.trip_id}*\n\n"
                f"Vehicle: *{relevant_trip.vehicle or 'Fleet Vehicle'}*\n"
                f"Start Odometer: *{relevant_trip.opening_km or 'Pending'} KM*\n\n"
                f"📸 *Please tap the link below to enter closing KM & snap the dashboard photo:*\n"
                f"👉 {handover_url}\n\n"
                f"Your total distance run will be computed instantly."
            )
        else:
            reply = (
                "ℹ️ No ongoing trip found to end.\n"
                "If you need assistance, please contact Dispatch at +91 94431 23456."
            )

    # =========================================================================
    # INTENT 5: TRIP STATUS & LIVE TRACKING
    # =========================================================================
    elif match_intent(['TRIP', 'STATUS', 'TRACK', 'WHERE', 'DRIVER']):
        intent = 'trip_status'
        if relevant_trip:
            reply = generate_passenger_dispatch_sheet(relevant_trip, base_url=base_url)
        else:
            reply = (
                "🔎 We could not locate an upcoming trip linked to your phone number.\n"
                "To book a luxury vehicle or speak with our concierge, call +91 94431 23456."
            )

    # =========================================================================
    # INTENT 6: PAYMENT & DYNAMIC UPI QR
    # =========================================================================
    elif any(k in upper_text for k in ['PAY', 'UPI', 'BILL', 'AMOUNT', 'BALANCE', 'PAYMENT']):
        intent = 'payment_upi'
        if relevant_trip:
            total_val = relevant_trip.total_amount if hasattr(relevant_trip, 'total_amount') and relevant_trip.total_amount else (relevant_trip.fixed_amount or 0)
            received = relevant_trip.received_amount if hasattr(relevant_trip, 'received_amount') else 0
            balance = max(Decimal(str(total_val)) - Decimal(str(received)), Decimal('0'))
            upi_vpa = getattr(settings, 'COMPANY_UPI_VPA', 'sivagayathiritravels@icici')
            upi_link = f"upi://pay?pa={upi_vpa}&pn=SivagayathiriTravels&am={balance}&cu=INR&tn=Trip_{relevant_trip.trip_id}"
            
            reply = (
                f"💳 *BILLING & INSTANT UPI PAYMENT — Trip #{relevant_trip.trip_id}*\n\n"
                f"• Total Bill: {format_currency(total_val)}\n"
                f"• Advance Paid: {format_currency(received)}\n"
                f"• *Balance Due: {format_currency(balance)}*\n\n"
                f"⚡ *Direct UPI Payment Link:*\n"
                f"{upi_link}\n\n"
                f"*(Click above to pay directly via GPay / PhonePe / Paytm / BHIM)*\n"
                f"Official GST tax invoice will be sent on trip completion."
            )
        else:
            reply = (
                "💳 For billing queries, please contact accounts at +91 94431 23456 or finance@sivagayathiritravels.com."
            )

    # =========================================================================
    # INTENT 7: MENU / FALLBACK CONCIERGE BOT
    # =========================================================================
    else:
        intent = 'general_query'
        sender_name = driver.name if driver else (
            relevant_trip.guest_name if relevant_trip else "Valued Traveler"
        )
        reply = (
            f"Namaste *{sender_name}*! Welcome to Sivagayathiri Travels 24x7 Assistant. 🙏\n\n"
            f"How can we assist you today? Please reply with one of the keywords below:\n\n"
            f"1️⃣ *TRIP* — Check booking status, vehicle & live GPS tracking\n"
            f"2️⃣ *START* — (Driver) Submit start duty & odometer photo\n"
            f"3️⃣ *END* — (Driver) Submit end duty & closing odometer\n"
            f"4️⃣ *INVOICE* — Fetch official GST Tax Invoice & E-Way Bill PDF\n"
            f"5️⃣ *PAY* — Instant UPI Payment & trip balance breakdown\n"
            f"6️⃣ *SOS* — Instant 24x7 control room emergency assistance\n\n"
            f"📞 Central Helpline: +91 94431 23456\n"
            f"🌐 Web: https://sivagayathiritravels.com"
        )

    # Log inbound and outbound messages
    try:
        # Inbound log
        WhatsAppBotMessage.objects.create(
            sender_phone=clean_sender,
            recipient_phone=getattr(settings, 'WHATSAPP_BUSINESS_PHONE', '+91 94431 23456'),
            message_direction='inbound',
            intent=intent,
            message_body=text,
            raw_payload=raw_payload or {},
            status='received',
            trip=relevant_trip,
            driver=driver,
            message_id=message_id or f"in_{timezone.now().timestamp()}"
        )
        # Outbound log
        WhatsAppBotMessage.objects.create(
            sender_phone=getattr(settings, 'WHATSAPP_BUSINESS_PHONE', '+91 94431 23456'),
            recipient_phone=clean_sender,
            message_direction='outbound',
            intent=intent,
            message_body=reply,
            raw_payload={},
            status='sent',
            trip=relevant_trip,
            driver=driver,
            message_id=f"out_{timezone.now().timestamp()}"
        )
    except Exception as e:
        logger.warning(f"Failed to log WhatsApp bot messages: {e}")

    return reply, intent, relevant_trip


def dispatch_passenger_alert_whatsapp(trip, base_url="http://127.0.0.1:8000"):
    """
    1-Click Automated Passenger Dispatcher.
    Constructs luxury trip sheet, sends via WhatsApp Business API,
    logs to WhatsAppBotMessage, and increments trip.whatsapp_broadcast_count.
    """
    customer_phone = (
        trip.booking.guest_phone if (trip.booking and trip.booking.guest_phone)
        else (trip.party.phone if trip.party else "")
    )
    if not customer_phone:
        return {"status": "skipped", "reason": "No passenger phone found"}

    message = generate_passenger_dispatch_sheet(trip, base_url=base_url)
    clean_phone = normalize_phone_digits(customer_phone)

    result = send_whatsapp_message(clean_phone, message)

    # Record message log
    try:
        WhatsAppBotMessage.objects.create(
            sender_phone=getattr(settings, 'WHATSAPP_BUSINESS_PHONE', '+91 94431 23456'),
            recipient_phone=clean_phone,
            message_direction='outbound',
            intent='dispatch_alert',
            message_body=message,
            raw_payload=result if isinstance(result, dict) else {},
            status='sent' if ('messages' in result or result.get('status') == 'simulated_sent') else 'failed',
            trip=trip,
            driver=trip.driver,
            message_id=result.get('messages', [{}])[0].get('id', f"out_{timezone.now().timestamp()}") if isinstance(result, dict) else ""
        )
        trip.whatsapp_broadcast_count = (trip.whatsapp_broadcast_count or 0) + 1
        trip.save(update_fields=['whatsapp_broadcast_count'])
    except Exception as e:
        logger.warning(f"Error recording passenger alert WhatsApp log: {e}")

    return result


def dispatch_driver_briefing_whatsapp(trip, base_url="http://127.0.0.1:8000"):
    """
    Sends trip assignment and digital handover link to Driver on WhatsApp.
    """
    driver = trip.driver
    if not driver or not driver.phone:
        return {"status": "skipped", "reason": "No driver assigned or phone missing"}

    message = generate_driver_briefing_sheet(trip, base_url=base_url)
    clean_phone = normalize_phone_digits(driver.phone)

    result = send_whatsapp_message(clean_phone, message)

    try:
        WhatsAppBotMessage.objects.create(
            sender_phone=getattr(settings, 'WHATSAPP_BUSINESS_PHONE', '+91 94431 23456'),
            recipient_phone=clean_phone,
            message_direction='outbound',
            intent='driver_briefing',
            message_body=message,
            raw_payload=result if isinstance(result, dict) else {},
            status='sent' if ('messages' in result or result.get('status') == 'simulated_sent') else 'failed',
            trip=trip,
            driver=driver,
            message_id=result.get('messages', [{}])[0].get('id', f"out_{timezone.now().timestamp()}") if isinstance(result, dict) else ""
        )
    except Exception as e:
        logger.warning(f"Error recording driver briefing WhatsApp log: {e}")

    return result


def generate_corporate_invoice_sheet(invoice, base_url="http://127.0.0.1:8000"):
    """
    Generates an official GST B2B Tax Invoice delivery message with e-Way Bill
    details, tax breakdown, and direct link to the print-ready invoice.
    """
    inv_date = invoice.invoice_date.strftime("%d-%m-%Y") if invoice.invoice_date else "Today"
    recipient = invoice.recipient_trade_name or invoice.recipient_legal_name
    gstin = invoice.recipient_gstin or "Unregistered (B2C)"
    pos = invoice.place_of_supply or "Tamil Nadu (33)"

    eway_block = ""
    if hasattr(invoice, 'eway_bill') and invoice.eway_bill:
        ewb = invoice.eway_bill
        eway_block = (
            f"\n🚚 *NIC E-Way Bill Active:*\n"
            f"• *EWB No:* `{ewb.eway_bill_number}`\n"
            f"• *Valid Upto:* {ewb.valid_until.strftime('%d-%m-%Y %H:%M') if ewb.valid_until else 'Active'}\n"
            f"• *Distance:* {getattr(ewb, 'trans_distance_km', 50)} KM\n"
        )

    # Tax breakdown text
    if invoice.supply_type == 'inter_state':
        tax_str = f"• IGST ({invoice.igst_rate}%): ₹{invoice.igst_amount:,.2f}"
    else:
        tax_str = f"• CGST ({invoice.cgst_rate}%): ₹{invoice.cgst_amount:,.2f}\n• SGST ({invoice.sgst_rate}%): ₹{invoice.sgst_amount:,.2f}"

    invoice_link = f"{base_url}/finance/invoice/{invoice.id}/view/"

    # UPI link if unpaid
    upi_block = ""
    if invoice.payment_status != 'paid':
        unpaid_val = invoice.total_invoice_value - (invoice.paid_amount or 0)
        upi_vpa = getattr(settings, 'COMPANY_UPI_VPA', 'sivagayathiritravels@icici')
        upi_link = f"upi://pay?pa={upi_vpa}&pn=SivagayathiriTravels&am={unpaid_val}&cu=INR&tn=Inv_{invoice.invoice_number}"
        upi_block = (
            f"\n💳 *Instant Payment Link (UPI / GPay / PhonePe):*\n"
            f"{upi_link}\n"
        )

    message = (
        f"🏛️ *SIVA GAYATHIRI TOURS & TRAVELS*\n"
        f"GSTIN: {invoice.supplier_gstin} | SAC: {invoice.sac_code}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📋 *OFFICIAL GST TAX INVOICE*\n"
        f"• *Invoice No:* `{invoice.invoice_number}`\n"
        f"• *Invoice Date:* {inv_date}\n"
        f"• *Billed To:* {recipient}\n"
        f"• *Client GSTIN:* {gstin}\n"
        f"• *Place of Supply:* {pos}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 *FINANCIAL BREAKDOWN:*\n"
        f"• Taxable Value: ₹{invoice.taxable_value:,.2f}\n"
        f"{tax_str}\n"
        f"• *Total Invoice Amount:* *₹{invoice.total_invoice_value:,.2f}*\n"
        f"• Payment Status: *{invoice.get_payment_status_display().upper()}*\n"
        f"{eway_block}"
        f"{upi_block}\n"
        f"📄 *View & Print Rule 46 Tax Invoice (PDF):*\n"
        f"{invoice_link}\n\n"
        f"For any invoicing or ITC queries, contact billing@sivagayathiritravels.com. 🙏"
    )
    return message


def dispatch_corporate_invoice_whatsapp(invoice, recipient_phone=None, base_url="http://127.0.0.1:8000"):
    """
    Delivers corporate GST tax invoice summary and PDF print link via WhatsApp.
    """
    phone = recipient_phone
    if not phone:
        if invoice.party and invoice.party.phone:
            phone = invoice.party.phone
        elif invoice.trip:
            phone = (
                invoice.trip.booking.guest_phone if (invoice.trip.booking and invoice.trip.booking.guest_phone)
                else (invoice.trip.party.phone if invoice.trip.party else "")
            )

    if not phone:
        return {"status": "skipped", "reason": "No recipient phone number found for this invoice"}

    clean_phone = normalize_phone_digits(phone)
    message = generate_corporate_invoice_sheet(invoice, base_url=base_url)

    result = send_whatsapp_message(clean_phone, message)

    try:
        WhatsAppBotMessage.objects.create(
            sender_phone=getattr(settings, 'WHATSAPP_BUSINESS_PHONE', '+91 94431 23456'),
            recipient_phone=clean_phone,
            message_direction='outbound',
            intent='invoice_delivery',
            message_body=message,
            raw_payload=result if isinstance(result, dict) else {},
            status='sent' if ('messages' in result or result.get('status') == 'simulated_sent') else 'failed',
            trip=invoice.trip,
            driver=invoice.trip.driver if invoice.trip else None,
            message_id=result.get('messages', [{}])[0].get('id', f"out_{timezone.now().timestamp()}") if isinstance(result, dict) else ""
        )
    except Exception as e:
        logger.warning(f"Error logging corporate invoice WhatsApp dispatch: {e}")

    return {
        "status": "success",
        "phone": clean_phone,
        "result": result
    }


def send_trip_invoice_pdf(trip_or_id, recipient_phone=None, base_url="http://127.0.0.1:8000"):
    """
    Automated WhatsApp delivery of Trip GST Tax Invoice & PDF download link.
    Supports either Trip instance, Trip ID/pk, or CorporateGSTInvoice.
    Dispatches:
      1. Formal GST-compliant invoice breakdown (SAC 9964/9966)
      2. Direct Rule 46 PDF invoice view & print link
      3. Dynamic UPI payment deep link for unsettled balances
      4. Detailed route, vehicle, and captain handover notes
    """
    from finance.models import CorporateGSTInvoice

    trip = None
    invoice = None

    if isinstance(trip_or_id, CorporateGSTInvoice):
        invoice = trip_or_id
        trip = invoice.trip
    elif hasattr(trip_or_id, 'trip_id'):
        trip = trip_or_id
    elif isinstance(trip_or_id, (int, str)):
        trip = Trip.objects.filter(id=trip_or_id).first() or Trip.objects.filter(trip_id=str(trip_or_id)).first()

    if not trip and not invoice:
        return {"status": "error", "reason": "Valid Trip or CorporateGSTInvoice could not be found."}

    # Locate linked corporate GST invoice if available
    if not invoice and trip:
        invoice = trip.gst_invoices.order_by('-id').first()

    # Determine recipient phone number
    phone = recipient_phone
    if not phone:
        if invoice and invoice.party and invoice.party.phone:
            phone = invoice.party.phone
        elif trip:
            if trip.booking and trip.booking.guest_phone:
                phone = trip.booking.guest_phone
            elif trip.party and trip.party.phone:
                phone = trip.party.phone

    if not phone:
        return {"status": "skipped", "reason": "No recipient phone number found for this trip invoice."}

    clean_phone = normalize_phone_digits(phone)

    # If full Corporate GST Invoice exists, route to specialized corporate template
    if invoice:
        return dispatch_corporate_invoice_whatsapp(invoice, recipient_phone=clean_phone, base_url=base_url)

    # Otherwise, generate a dedicated trip invoice dispatch sheet
    trip_id = trip.trip_id if trip else "TRIP"
    guest = trip.guest_name or (trip.booking.guest_name if (trip and trip.booking) else "Valued Guest")
    route = f"{trip.pickup_location} ➡️ {trip.destination}" if trip else "Scheduled Route"
    veh = trip.vehicle if trip else None
    veh_str = f"{veh.brand} {veh.model} ({veh.registration_number})" if veh else "Premium Fleet Vehicle"

    total_amount = Decimal(str(trip.total_amount or 0)) if trip else Decimal('0.00')
    if total_amount == Decimal('0.00') and trip and trip.booking:
        total_amount = Decimal(str(getattr(trip.booking, 'total_fare', 0) or 0))
    tax_rate = Decimal('5.00')
    taxable_val = (total_amount / (Decimal('1.00') + (tax_rate / Decimal('100.00')))).quantize(Decimal('0.01'))
    cgst_sgst = ((total_amount - taxable_val) / Decimal('2.00')).quantize(Decimal('0.01'))

    upi_vpa = getattr(settings, 'COMPANY_UPI_VPA', 'sivagayathiritravels@icici')
    upi_link = f"upi://pay?pa={upi_vpa}&pn=SivagayathiriTravels&am={total_amount}&cu=INR&tn=Trip_{trip_id}"
    portal_invoice_url = f"{base_url}/customer/trip/{trip.id}/invoice/" if trip else f"{base_url}/admin/operations/trip/"

    message = (
        f"🏛️ *SIVA GAYATHIRI TOURS & TRAVELS*\n"
        f"GSTIN: 33AAAAA0000A1Z5 | Transport SAC: 9964\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🧾 *TRIP TAX INVOICE & RECEIPT*\n"
        f"• *Trip Ref:* `{trip_id}`\n"
        f"• *Guest:* {guest}\n"
        f"• *Route:* {route}\n"
        f"• *Vehicle:* {veh_str}\n"
        f"• *Date:* {trip.start_date or timezone.now().date()}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 *FARE BREAKDOWN:*\n"
        f"• Taxable Fare: ₹{taxable_val:,.2f}\n"
        f"• CGST (2.5%): ₹{cgst_sgst:,.2f}\n"
        f"• SGST (2.5%): ₹{cgst_sgst:,.2f}\n"
        f"• *Total Amount:* *₹{total_amount:,.2f}*\n\n"
        f"📄 *Download & Print Tax Invoice (PDF):*\n"
        f"{portal_invoice_url}\n\n"
        f"💳 *Quick UPI Payment / Settlement:*\n"
        f"{upi_link}\n\n"
        f"Thank you for traveling with us! Have a wonderful day ahead. 🙏"
    )

    result = send_whatsapp_message(clean_phone, message)

    try:
        WhatsAppBotMessage.objects.create(
            sender_phone=getattr(settings, 'WHATSAPP_BUSINESS_PHONE', '+91 94431 23456'),
            recipient_phone=clean_phone,
            message_direction='outbound',
            intent='invoice_delivery',
            message_body=message,
            raw_payload=result if isinstance(result, dict) else {},
            status='sent' if ('messages' in result or result.get('status') == 'simulated_sent') else 'failed',
            trip=trip,
            driver=trip.driver if trip else None,
            message_id=result.get('messages', [{}])[0].get('id', f"out_{timezone.now().timestamp()}") if isinstance(result, dict) else ""
        )
    except Exception as e:
        logger.warning(f"Error logging trip invoice WhatsApp dispatch: {e}")

    return {
        "status": "success",
        "phone": clean_phone,
        "result": result
    }


def dispatch_driver_briefing_whatsapp(trip, base_url="http://127.0.0.1:8000"):
    """
    Sends WhatsApp briefing sheet directly to the assigned driver with
    duty parameters, guest details, and digital vehicle handover link.
    """
    if not trip or not trip.driver or not trip.driver.phone:
        return {"status": "skipped", "reason": "No driver or driver phone assigned"}

    clean_phone = normalize_phone_digits(trip.driver.phone)
    message_text = generate_driver_briefing_sheet(trip, base_url=base_url)
    result = send_whatsapp_message(clean_phone, message_text)

    try:
        status_val = 'sent' if ('messages' in result or result.get('status') == 'simulated_sent') else 'failed'
        WhatsAppBotMessage.objects.create(
            sender_phone=getattr(settings, 'WHATSAPP_BUSINESS_PHONE', '+91 94431 23456'),
            recipient_phone=clean_phone,
            message_direction='outbound',
            intent='driver_briefing',
            message_body=message_text,
            raw_payload=result if isinstance(result, dict) else {},
            status=status_val,
            trip=trip,
            driver=trip.driver,
            message_id=result.get('messages', [{}])[0].get('id', f"out_{timezone.now().timestamp()}") if isinstance(result, dict) else ""
        )
    except Exception as e:
        logger.warning(f"Error logging driver briefing WhatsApp dispatch: {e}")

    return {
        "status": "success",
        "phone": clean_phone,
        "result": result
    }


def dispatch_passenger_alert_whatsapp(trip, base_url="http://127.0.0.1:8000"):
    """
    Sends luxury confirmation WhatsApp message to the guest/passenger with
    assigned vehicle details, captain contact, and real-time GPS tracking link.
    """
    customer_phone = (
        trip.booking.guest_phone if (trip.booking and trip.booking.guest_phone)
        else (trip.party.phone if trip.party else "")
    )
    if not customer_phone:
        return {"status": "skipped", "reason": "No passenger phone available"}

    clean_phone = normalize_phone_digits(customer_phone)
    message_text = generate_passenger_dispatch_sheet(trip, base_url=base_url)
    result = send_whatsapp_message(clean_phone, message_text)

    try:
        status_val = 'sent' if ('messages' in result or result.get('status') == 'simulated_sent') else 'failed'
        WhatsAppBotMessage.objects.create(
            sender_phone=getattr(settings, 'WHATSAPP_BUSINESS_PHONE', '+91 94431 23456'),
            recipient_phone=clean_phone,
            message_direction='outbound',
            intent='dispatch_alert',
            message_body=message_text,
            raw_payload=result if isinstance(result, dict) else {},
            status=status_val,
            trip=trip,
            driver=trip.driver if trip else None,
            message_id=result.get('messages', [{}])[0].get('id', f"out_{timezone.now().timestamp()}") if isinstance(result, dict) else ""
        )
        trip.whatsapp_broadcast_count = (trip.whatsapp_broadcast_count or 0) + 1
        trip.save(update_fields=['whatsapp_broadcast_count'])
    except Exception as e:
        logger.warning(f"Error logging passenger alert WhatsApp dispatch: {e}")

    return {
        "status": "success",
        "phone": clean_phone,
        "result": result
    }



