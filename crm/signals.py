from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from operations.models import Booking
from integrations.communication import send_whatsapp_message, send_email_notification


@receiver(post_save, sender=Booking)
def trigger_crm_automation(sender, instance, created, **kwargs):
    if not created and instance.status == 'confirmed':
        # Booking just got confirmed (e.g. from Razorpay webhook)
        phone = instance.guest_phone
        if phone:
            message = f"Hello {instance.guest_name}, your booking {instance.booking_number} to {instance.destination} is confirmed!"
            send_whatsapp_message(phone, message)
        
        email = getattr(instance.party, 'email', None)
        if email:
            send_email_notification(
                email, 
                f"Booking Confirmed: {instance.booking_number}", 
                f"<p>Thank you for booking with us. Your trip to {instance.destination} is confirmed.</p>"
            )


@receiver(post_save, sender='crm.Inquiry')
def on_inquiry_created(sender, instance, created, **kwargs):
    """
    Automated customer acknowledgment and internal SLA assignment alerts.
    """
    if created:
        phone = instance.guest_phone or (instance.party.phone if instance.party else None)
        dest = instance.destination or "your requested destination"
        msg = (
            f"Namaste {instance.guest_name}! 🙏\n\n"
            f"Thank you for contacting Sivagayathiri Travels. We have received your query *{instance.inquiry_number}* for *{dest}*.\n\n"
            f"🎯 *Priority:* {instance.get_priority_display()}\n"
            f"⏱️ *Response TAT:* Our destination expert will review your requirements and provide a customized itinerary & quotation within {instance.target_tat_hours} hours.\n\n"
            f"📞 Need immediate assistance? Call our travel desk at +91 98765 43210."
        )
        if phone:
            send_whatsapp_message(phone, msg)
            try:
                from crm.models import CommunicationLog
                CommunicationLog.objects.create(
                    client=instance.party,
                    comm_type='whatsapp',
                    message_content=msg,
                    status='sent'
                )
            except Exception:
                pass

        # Email acknowledgment to customer if email is available
        email = instance.guest_email or (instance.party.email if instance.party else None)
        if email:
            send_email_notification(
                email,
                f"Inquiry Received: {instance.inquiry_number} - Sivagayathiri Travels",
                f"<p>Dear {instance.guest_name},</p><p>We have received your travel inquiry for <b>{dest}</b>. Our team is actively reviewing your requirements and will share a customized quotation shortly.</p>"
            )


@receiver(post_save, sender='crm.Quotation')
def on_quotation_status_changed(sender, instance, created, **kwargs):
    """
    Dispatches instant WhatsApp & Email proposals when a quotation is marked as 'sent'.
    """
    if not created and instance.status == 'sent':
        phone = instance.guest_phone or (instance.party.phone if instance.party else None)
        if phone:
            base_url = getattr(settings, 'SITE_BASE_URL', 'http://127.0.0.1:8000')
            preview_url = f"{base_url}/crm/quotations/{instance.id}/preview/"
            msg = (
                f"Namaste {instance.guest_name}! 🙏\n\n"
                f"Your customized tour proposal *{instance.quotation_number}* for *{instance.destination}* "
                f"({instance.duration_nights}N/{instance.duration_days}D) is ready!\n\n"
                f"• *Travel Dates:* {instance.start_date} to {instance.end_date}\n"
                f"• *Party Size:* {instance.pax_count} Guests\n"
                f"• *Dedicated Vehicle:* {instance.vehicle_type.name if instance.vehicle_type else 'Comfort Fleet'}\n"
                f"• *Total All-Inclusive Quoted Price:* *₹{instance.total_quoted_price:,.2f}*\n\n"
                f"📄 View your interactive day-by-day itinerary, inclusions & proposal breakdown:\n{preview_url}\n\n"
                f"Please let us know if you would like any customizations!"
            )
            send_whatsapp_message(phone, msg)
            try:
                from crm.models import CommunicationLog
                CommunicationLog.objects.create(
                    client=instance.party,
                    comm_type='whatsapp',
                    message_content=msg,
                    status='sent'
                )
            except Exception:
                pass


@receiver(post_save, sender='crm.SupplierServiceVoucher')
def on_supplier_service_voucher_issued(sender, instance, created, **kwargs):
    """
    Dispatches purchase order and reservation voucher to supplier with 1-click confirmation link.
    """
    if instance.status == 'issued':
        supplier_party = instance.supplier.party
        supplier_phone = supplier_party.phone
        # Check primary contact person
        primary_contact = supplier_party.contact_persons.filter(is_primary=True).first()
        if primary_contact and primary_contact.phone:
            supplier_phone = primary_contact.phone

        base_url = getattr(settings, 'SITE_BASE_URL', 'http://127.0.0.1:8000')
        extranet_url = f"{base_url}/crm/vouchers/extranet/{instance.confirmation_token}/"

        spec_line = ""
        if instance.voucher_type == 'hotel_reservation':
            spec_line = f"🏨 {instance.room_count}x {instance.hotel_room_type} ({instance.hotel_meal_plan} Plan)"
        elif instance.voucher_type == 'transport_order':
            spec_line = f"🚗 {instance.vehicle_type_name} (Pickup: {instance.pickup_location})"
        else:
            spec_line = f"✨ {instance.activity_name or instance.get_voucher_type_display()}"

        msg = (
            f"Dear Partner ({supplier_party.name}),\n\n"
            f"Sivagayathiri Travels & Holidays has issued Official Reservation Order *{instance.voucher_number}*.\n\n"
            f"• *Lead Guest:* {instance.guest_name} ({instance.pax_count} Pax)\n"
            f"• *Dates:* {instance.service_date_start} to {instance.service_date_end} ({instance.duration_nights}N)\n"
            f"• *Service:* {spec_line}\n"
            f"• *Agreed DMC Settlement:* *₹{instance.total_payable_to_supplier:,.2f}*\n\n"
            f"⚡ *1-Click Extranet Confirmation:* Please review voucher and submit your confirmation code here:\n"
            f"{extranet_url}\n\n"
            f"Thank you for your ongoing partnership!"
        )

        if supplier_phone:
            send_whatsapp_message(supplier_phone, msg)
            try:
                from crm.models import CommunicationLog
                CommunicationLog.objects.create(
                    client=supplier_party,
                    comm_type='whatsapp',
                    message_content=msg,
                    status='sent'
                )
            except Exception:
                pass

        supplier_email = supplier_party.email or (primary_contact.email if primary_contact else None)
        if supplier_email:
            send_email_notification(
                supplier_email,
                f"Service Order & Reservation Voucher: {instance.voucher_number} - Sivagayathiri Travels",
                f"<p>Dear Partner,</p><p>Please find reservation voucher <b>{instance.voucher_number}</b> for <b>{instance.guest_name}</b>.</p><p><a href='{extranet_url}'>Click here to confirm reservation</a>.</p>"
            )


@receiver(post_save, sender='operations.EmergencyIncidentAlert')
def on_emergency_sos_reported(sender, instance, created, **kwargs):
    """
    Automated Control Room SOS Broadcast:
    Dispatches instant emergency alert to Fleet Control Room on WhatsApp & Email.
    """
    if created:
        try:
            from integrations.communication import dispatch_emergency_sos_broadcast
            dispatch_emergency_sos_broadcast(instance)
        except Exception as e:
            print(f"Failed to auto-dispatch emergency SOS signal: {e}")

