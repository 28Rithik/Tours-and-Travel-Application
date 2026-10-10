"""
Zoho Arattai Business Messaging Service & Rathasārathi Bot Gateway
Sivagayathiri Travels & Tours ERP

Integrates with the Zoho Arattai Business Platform (business.arattai.in)
for Made-in-India, secure messaging automation:
1. Transactional Outbound Messages (Bookings, Chauffeur Allocation, Pickup PIN, Invoices)
2. Real-time Emergency SOS & Compliance Alerts to Management Channels
3. Inbound Conversational Webhook with Rathasārathi AI RAG Intelligence
"""

import os
import json
import logging
import requests
from typing import Dict, Any, Optional

from django.conf import settings
from django.utils import timezone
from integrations.models import IntegrationSettings, ArattaiMessageLog

logger = logging.getLogger(__name__)

ARATTAI_API_BASE = getattr(settings, 'ARATTAI_API_BASE_URL', 'https://business.arattai.in/api/v1')


class ArattaiBusinessService:
    """
    Client for Zoho Arattai Business Platform REST API & Interactive Bot Gateway.
    Gracefully handles live API and local test simulations.
    """

    @staticmethod
    def clean_phone(phone: str) -> str:
        """Normalizes Indian mobile number to 91XXXXXXXXXX."""
        digits = ''.join(filter(str.isdigit, str(phone or '')))
        if len(digits) == 10:
            return f"91{digits}"
        return digits

    @classmethod
    def send_message(
        cls,
        phone: str,
        text: str,
        message_type: str = 'transactional',
        media_url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Sends an outbound Arattai transactional or notification message.
        """
        clean_p = cls.clean_phone(phone)
        if not clean_p:
            return {"status": "error", "message": "Invalid recipient phone number"}

        integ_cfg = IntegrationSettings.get_settings()
        if not integ_cfg.arattai_active:
            return {"status": "skipped", "message": "Arattai Gateway is currently deactivated in settings"}

        bot_token = integ_cfg.arattai_bot_token or getattr(settings, 'ARATTAI_BOT_TOKEN', '')
        business_id = integ_cfg.arattai_business_id or getattr(settings, 'ARATTAI_BUSINESS_ID', '')

        # Simulation mode when no live bot credentials
        is_live = bool(bot_token and bot_token != 'test_token')

        if is_live:
            url = f"{ARATTAI_API_BASE}/messages"
            headers = {
                "Authorization": f"Bearer {bot_token}",
                "Content-Type": "application/json"
            }
            payload = {
                "business_id": business_id,
                "recipient": clean_p,
                "message": {"text": text},
            }
            if media_url:
                payload["message"]["media_url"] = media_url

            try:
                resp = requests.post(url, headers=headers, json=payload, timeout=10)
                resp_data = resp.json() if resp.status_code == 200 else {}
                ext_id = resp_data.get('message_id', f"ara_{timezone.now().timestamp()}")
                status_code = 'delivered' if resp.status_code == 200 else 'failed'
            except Exception as e:
                logger.error(f"Arattai API post error: {e}")
                ext_id = f"ara_err_{timezone.now().timestamp()}"
                status_code = 'failed'
        else:
            # Simulated local dispatch
            ext_id = f"ara_sim_{timezone.now().timestamp()}"
            status_code = 'delivered'
            try:
                print(f"[ARATTAI SIMULATOR -> {clean_p}] ({message_type}):\n{text}\n" + "=" * 50)
            except UnicodeEncodeError:
                safe_text = text.encode('ascii', 'replace').decode('ascii')
                print(f"[ARATTAI SIMULATOR -> {clean_p}] ({message_type}):\n{safe_text}\n" + "=" * 50)

        # Audit Log Entry
        log_entry = ArattaiMessageLog.objects.create(
            direction='outbound',
            message_type=message_type if message_type in dict(ArattaiMessageLog.MESSAGE_TYPES) else 'booking_confirmed',
            phone_number=clean_p,
            message_text=text,
            external_message_id=ext_id,
            status=status_code,
            payload=metadata or {},
        )

        # Increment counter
        integ_cfg.arattai_messages_sent += 1
        integ_cfg.save(update_fields=['arattai_messages_sent'])

        return {
            "status": "success",
            "message_id": ext_id,
            "log_id": log_entry.id,
            "recipient": clean_p,
            "simulated": not is_live,
        }

    # ──────────────────────────────────────────────────────────────────────────
    # PRE-BUILT TRANSACTIONAL TEMPLATES
    # ──────────────────────────────────────────────────────────────────────────

    @classmethod
    def send_booking_confirmation(cls, booking) -> Dict[str, Any]:
        """Dispatches reservation confirmation to passenger on Arattai."""
        client_phone = getattr(booking.client, 'phone', None)
        client_name = getattr(booking.client, 'name', 'Valued Guest')

        text = (
            f"🎉 *NAMASTE {client_name.upper()}!*\n\n"
            f"Your journey with *Sivagayathiri Travels & Tours* is confirmed!\n\n"
            f"📋 *Booking ID:* #{booking.booking_number or booking.id}\n"
            f"📅 *Departure:* {booking.pickup_date} at {booking.pickup_time or '08:00 AM'}\n"
            f"📍 *Pickup Location:* {booking.pickup_location}\n"
            f"🚗 *Vehicle Category:* {getattr(booking.vehicle_type, 'name', 'AC Deluxe Sedan')}\n"
            f"💰 *Advance Received:* ₹{booking.advance_paid:,.2f}\n\n"
            f"Your chauffeur details and live tracking link will be shared 2 hours before departure.\n"
            f"📞 24x7 Support: +91 94431 23456"
        )
        return cls.send_message(
            phone=client_phone,
            text=text,
            message_type='booking_confirmed',
            metadata={'booking_id': booking.id}
        )

    @classmethod
    def send_chauffeur_assigned(cls, trip) -> Dict[str, Any]:
        """Dispatches driver details, vehicle registration, and tracking link to guest."""
        guest_phone = getattr(trip.booking.client, 'phone', None) if trip.booking else None
        driver_name = trip.driver.name if trip.driver else 'Designated Chauffeur'
        driver_phone = trip.driver.phone if trip.driver else '+91 98765 43210'
        vehicle_reg = trip.vehicle.registration_number if trip.vehicle else 'Vehicle Staged'
        pin = trip.pickup_pin or '7482'

        tracking_url = f"{getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000')}/fleet/track/{trip.id}/"

        text = (
            f"🚗 *CHAUFFEUR ALLOCATED — TRIP #{trip.trip_number or trip.id}*\n\n"
            f"Your chauffeur has been dispatched for pickup:\n\n"
            f"👤 *Chauffeur:* {driver_name} (📞 {driver_phone})\n"
            f"🚘 *Vehicle:* {vehicle_reg}\n"
            f"🔐 *Guest Pickup PIN:* `{pin}`\n"
            f"*(Share this PIN only with your chauffeur upon boarding)*\n\n"
            f"🛰️ *Live GPS Tracking:* {tracking_url}\n"
            f"Have a pleasant and safe journey!"
        )
        return cls.send_message(
            phone=guest_phone,
            text=text,
            message_type='driver_assigned',
            metadata={'trip_id': trip.id}
        )

    @classmethod
    def send_trip_completed_invoice(cls, trip) -> Dict[str, Any]:
        """Sends final trip completion summary and invoice link."""
        guest_phone = getattr(trip.booking.client, 'phone', None) if trip.booking else None
        invoice_url = f"{getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000')}/finance/invoices/{trip.id}/download/"

        text = (
            f"🏁 *TRIP COMPLETED — THANK YOU!*\n\n"
            f"Your trip #{trip.trip_number or trip.id} with Sivagayathiri Travels has ended safely.\n\n"
            f"📏 *Total Distance:* {trip.actual_km or '0'} Kms\n"
            f"💵 *Final Settled Amount:* ₹{trip.total_fare:,.2f}\n"
            f"📑 *Download Tax Invoice:* {invoice_url}\n\n"
            f"We hope you had a memorable journey! We look forward to serving you again."
        )
        return cls.send_message(
            phone=guest_phone,
            text=text,
            message_type='trip_completed',
            metadata={'trip_id': trip.id}
        )

    # ──────────────────────────────────────────────────────────────────────────
    # INBOUND ARATTAI WEBHOOK & RATHASĀRATHI AI BOT HANDLER
    # ──────────────────────────────────────────────────────────────────────────

    @classmethod
    def handle_inbound_webhook(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processes inbound messages from Arattai users.
        Interprets commands (/status, /driver, /help) or routes natural language
        queries directly through Rathasārathi AI RAG engine!
        """
        sender_phone = cls.clean_phone(data.get('sender', data.get('from', '')))
        sender_name = data.get('sender_name', data.get('name', 'Arattai User'))
        text = (data.get('text', data.get('message', {}).get('text', ''))).strip()
        msg_id = data.get('message_id', f"in_{timezone.now().timestamp()}")

        if not text:
            return {"status": "ignored", "reason": "empty_text"}

        # Log Inbound
        inbound_log = ArattaiMessageLog.objects.create(
            direction='inbound',
            message_type='chat_query',
            phone_number=sender_phone,
            sender_name=sender_name,
            message_text=text,
            external_message_id=msg_id,
            status='received',
            payload=data,
        )

        reply_text = ""

        # Command Dispatch
        lower = text.lower()
        if lower.startswith('/status'):
            # e.g. /status 1002
            parts = text.split()
            if len(parts) > 1:
                from operations.models import Booking
                b_num = parts[1].replace('#', '')
                b = Booking.objects.filter(booking_number__icontains=b_num).first()
                if b:
                    reply_text = (
                        f"📋 *Booking #{b.booking_number} Status*\n"
                        f"• Status: *{b.get_status_display()}*\n"
                        f"• Dates: {b.pickup_date} to {b.drop_date}\n"
                        f"• Route: {b.pickup_location} -> {b.drop_location}\n"
                        f"• Payment: {b.get_payment_status_display()}"
                    )
                else:
                    reply_text = f"⚠️ No booking found matching '{b_num}'. Please check your booking ID."
            else:
                reply_text = "💡 Usage: `/status <booking_id>` (e.g. `/status 1042`)"

        elif lower.startswith('/driver'):
            parts = text.split()
            if len(parts) > 1:
                from operations.models import Trip
                t_id = parts[1].replace('#', '')
                t = Trip.objects.filter(trip_number__icontains=t_id).first()
                if t and t.driver:
                    reply_text = (
                        f"🚗 *Trip #{t.trip_number} Chauffeur Info*\n"
                        f"• Chauffeur: *{t.driver.name}* (📞 {t.driver.phone})\n"
                        f"• Vehicle: *{t.vehicle.registration_number if t.vehicle else 'Staged'}*\n"
                        f"• Status: *{t.get_status_display()}*"
                    )
                else:
                    reply_text = f"⚠️ No chauffeur currently assigned or trip '{t_id}' not found."
            else:
                reply_text = "💡 Usage: `/driver <trip_id>`"

        elif lower in ['/help', 'help', 'hi', 'hello', 'vanakkam']:
            reply_text = (
                f"👑 *Vanakkam {sender_name}! I am Rathasārathi AI on Arattai.*\n\n"
                f"I am the 24x7 intelligent assistant for *Sivagayathiri Travels & Tours*.\n\n"
                f"Commands you can use:\n"
                f"• `/status <id>` — Check booking reservation status\n"
                f"• `/driver <id>` — Get assigned chauffeur & vehicle\n\n"
                f"Or simply ask me any question! Examples:\n"
                f"👉 *'What is the cancellation policy for Ooty package?'*\n"
                f"👉 *'What are the temple dress code rules for Madurai?'*\n"
                f"👉 *'What is the driver night bata rate?'*"
            )

        else:
            # Route natural language query directly to Rathasārathi AI with RAG
            from operations.tara_copilot import ask_tara
            ai_res = ask_tara(text)
            reply_text = ai_res.get('reply', '')
            if len(reply_text) > 1200:
                # Arattai message limit formatting
                reply_text = reply_text[:1200] + "...\n\n*(Full details available on your customer portal)*"

        # Send Reply back on Arattai
        cls.send_message(
            phone=sender_phone,
            text=reply_text,
            message_type='chat_query',
            metadata={'inbound_log_id': inbound_log.id}
        )

        inbound_log.response_text = reply_text
        inbound_log.save(update_fields=['response_text'])

        return {
            "status": "success",
            "reply": reply_text,
            "inbound_log_id": inbound_log.id
        }
