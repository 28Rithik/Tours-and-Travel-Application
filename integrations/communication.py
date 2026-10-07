import calendar
import requests
from decimal import Decimal
from django.conf import settings
from django.utils import timezone


def send_whatsapp_message(to_phone, message_text, template_name=None):
    """
    Sends a WhatsApp message using the WhatsApp Business API.
    Uses standard text or predefined template.
    Gracefully handles dev/test environments without breaking execution.
    """
    if not to_phone:
        return {"status": "skipped", "reason": "No phone number provided"}

    # Normalize phone: ensure only digits, default +91 for India if 10 digits
    clean_phone = ''.join(filter(str.isdigit, str(to_phone)))
    if len(clean_phone) == 10:
        clean_phone = f"91{clean_phone}"

    api_token = getattr(settings, 'WHATSAPP_API_TOKEN', None)
    phone_number_id = getattr(settings, 'WHATSAPP_PHONE_NUMBER_ID', None)

    # In local/test mode without credentials, log and return simulated success
    if not api_token or not phone_number_id or api_token == 'test_token':
        try:
            print(f"[SIMULATED WHATSAPP -> {clean_phone}]:\n{message_text}\n" + "-"*40)
        except UnicodeEncodeError:
            print(f"[SIMULATED WHATSAPP -> {clean_phone}]:\n{message_text.encode('ascii', 'replace').decode('ascii')}\n" + "-"*40)
        return {
            "messaging_product": "whatsapp",
            "contacts": [{"wa_id": clean_phone}],
            "messages": [{"id": f"wamid.simulated.{timezone.now().timestamp()}"}],
            "status": "simulated_sent"
        }

    url = f"https://graph.facebook.com/v17.0/{phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": clean_phone,
        "type": "text",
        "text": {"body": message_text}
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        return response.json()
    except Exception as e:
        print(f"Failed to send WhatsApp message to {clean_phone}: {e}")
        return {"error": str(e)}


def send_email_notification(to_email, subject, body_html):
    """
    Sends transactional email. Falls back cleanly to console log in development.
    """
    if not to_email:
        return False
    try:
        from django.core.mail import send_mail
        send_mail(
            subject=subject,
            message=body_html,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@sivagayathiritravels.com'),
            recipient_list=[to_email],
            fail_silently=True,
            html_message=body_html
        )
        return True
    except Exception as e:
        print(f"[EMAIL SEND FAILED TO {to_email}]: {e}")
        return False


# ==============================================================================
# EVENT-DRIVEN OMNICHANNEL ALERT DISPATCHERS
# ==============================================================================

def dispatch_trip_assignment_alert(trip, base_url="http://127.0.0.1:8000"):
    """
    Broadcasts booking confirmation, driver details, and live passenger GPS tracking
    link to the customer upon assignment.
    """
    customer_phone = (
        trip.booking.guest_phone if trip.booking and trip.booking.guest_phone
        else (trip.party.phone if trip.party else "")
    )
    guest_name = trip.guest_name or (trip.booking.guest_name if trip.booking else "Guest")
    veh_str = trip.vehicle.registration_number if trip.vehicle else "To be announced"
    veh_type = trip.vehicle.vehicle_type.name if trip.vehicle and trip.vehicle.vehicle_type else "Vehicle"
    driver_name = trip.driver.name if trip.driver else "To be assigned"
    driver_phone = trip.driver.phone if trip.driver else "N/A"
    tracking_link = f"{base_url}{trip.tracking_url}" if trip.tracking_token else f"{base_url}/track/"

    message = (
        f"Namaste {guest_name}! 🙏\n\n"
        f"Your Sivagayathiri Travels booking *{trip.trip_id}* is confirmed.\n\n"
        f"🚖 *Vehicle:* {veh_str} ({veh_type})\n"
        f"👤 *Captain:* {driver_name} (📞 {driver_phone})\n"
        f"📍 *Pickup:* {trip.pickup_location} at {trip.start_time or 'Scheduled time'}\n"
        f"🏁 *Destination:* {trip.destination}\n\n"
        f"🛰️ *Live GPS Vehicle Tracking:* {tracking_link}\n\n"
        f"Wishing you a safe and comfortable journey with us!"
    )

    result = send_whatsapp_message(customer_phone, message)

    # Log to CRM CommunicationLog
    try:
        from crm.models import CommunicationLog
        from core.models import Client
        client = Client.objects.filter(pk=trip.party_id).first()
        if client:
            CommunicationLog.objects.create(
                client=client,
                booking=trip.booking,
                comm_type='whatsapp',
                message_content=message,
                status='sent'
            )
    except Exception:
        pass

    return result


def dispatch_emergency_sos_broadcast(incident):
    """
    Instant broadcast to fleet control room and management on Emergency SOS trigger.
    """
    control_room_phone = getattr(settings, 'FLEET_CONTROL_ROOM_PHONE', '919876543210')
    veh_reg = incident.vehicle.registration_number if incident.vehicle else "N/A"
    driver_name = incident.driver.name if incident.driver else "N/A"
    driver_phone = incident.driver.phone if incident.driver else "N/A"

    message = (
        f"🚨 *CRITICAL FLEET SOS ALERT!* 🚨\n\n"
        f"• *Incident ID:* {incident.incident_id}\n"
        f"• *Type:* {incident.get_incident_type_display()}\n"
        f"• *Severity:* {incident.get_severity_display()}\n"
        f"• *Vehicle:* {veh_reg}\n"
        f"• *Captain:* {driver_name} ({driver_phone})\n"
        f"• *Passengers:* {incident.passenger_count} ({incident.get_passengers_safety_status_display()})\n"
        f"• *Location:* {incident.location_address or 'Highway GPS coordinates'}\n"
        f"• *Issue:* {incident.description}\n\n"
        f"⚡ Please dispatch standby vehicle from Mission Control immediately."
    )
    return send_whatsapp_message(control_room_phone, message)


def dispatch_payslip_alert(payslip, base_url="http://127.0.0.1:8000"):
    """
    Sends salary disbursement summary to the driver on WhatsApp.
    """
    driver = payslip.driver
    if not driver or not driver.phone:
        return {"status": "skipped", "reason": "No driver phone"}

    month_name = calendar.month_name[payslip.month]
    message = (
        f"Vanakkam {driver.name}! 💰\n\n"
        f"Your monthly salary payslip for *{month_name} {payslip.year}* has been finalized:\n\n"
        f"• *Verified Duty Days:* {payslip.days_present} Days\n"
        f"• *Gross Earnings:* ₹{payslip.gross_earnings:,.2f}\n"
        f"• *Statutory Deductions (EPF/ESI):* ₹{(payslip.epf_deduction + payslip.esi_deduction):,.2f}\n"
        f"• *Fines / Advances:* ₹{(payslip.traffic_fines_deduction + payslip.advances_recovered):,.2f}\n"
        f"• *Net Take-Home Pay:* *₹{payslip.net_payable:,.2f}*\n\n"
        f"📄 View & print your complete salary slip: {base_url}/finance/payslips/{payslip.id}/\n\n"
        f"Thank you for your dedicated service!"
    )
    return send_whatsapp_message(driver.phone, message)


def send_trip_invoice_pdf(trip_or_id, recipient_phone=None, base_url="http://127.0.0.1:8000"):
    """
    Dispatches automated WhatsApp notification with official GST invoice details
    and PDF download link for a Trip or CorporateGSTInvoice.
    """
    from operations.whatsapp_bot import send_trip_invoice_pdf as _send_invoice
    return _send_invoice(trip_or_id, recipient_phone=recipient_phone, base_url=base_url)

