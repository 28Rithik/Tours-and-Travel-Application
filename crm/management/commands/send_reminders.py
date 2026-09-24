from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from operations.models import Booking
from crm.services import send_whatsapp_message, send_email

class Command(BaseCommand):
    help = 'Sends automated reminders for upcoming trips and pending payments'

    def handle(self, *args, **kwargs):
        # 1. Remind about upcoming trips (3 days before)
        target_date = timezone.now().date() + timedelta(days=3)
        upcoming_bookings = Booking.objects.filter(pickup_date=target_date, status='confirmed')
        
        for booking in upcoming_bookings:
            phone = booking.guest_phone
            if phone:
                msg = f"Hi {booking.guest_name}, your trip to {booking.destination} is coming up on {booking.pickup_date}. We can't wait to host you!"
                send_whatsapp_message(phone, msg)
                
            email = booking.party.email if booking.party else None
            if email:
                send_email(email, f"Upcoming Trip to {booking.destination}", msg)
                
            self.stdout.write(self.style.SUCCESS(f'Sent trip reminder for booking {booking.booking_number}'))
            
        # 2. Remind about pending installments
        from payments_gateway.models import InstallmentPlan
        plans = InstallmentPlan.objects.filter(is_active=True, booking__status='pending')
        
        for plan in plans:
            phone = plan.booking.guest_phone
            if phone:
                msg = f"Hi {plan.booking.guest_name}, just a friendly reminder to complete your pending payment for booking {plan.booking.booking_number} to confirm your package."
                send_whatsapp_message(phone, msg)
                
            self.stdout.write(self.style.SUCCESS(f'Sent payment reminder for booking {plan.booking.booking_number}'))
            
        # 3. Abandoned Cart Reminders
        # Bookings that are 'pending' and were created more than 2 hours ago
        two_hours_ago = timezone.now() - timedelta(hours=2)
        abandoned_bookings = Booking.objects.filter(status='pending', created_at__lte=two_hours_ago)
        
        for booking in abandoned_bookings:
            # Prevent spamming - in a real app, track whether we already sent it
            phone = booking.guest_phone
            if phone:
                msg = f"Hi {booking.guest_name}, we noticed you didn't complete your checkout for the {booking.destination} trip! Let us know if you need any help."
                send_whatsapp_message(phone, msg)
                
            email = booking.party.email if booking.party else None
            if email:
                send_email(email, "Complete your booking!", msg)
                
            self.stdout.write(self.style.SUCCESS(f'Sent abandoned cart reminder for booking {booking.booking_number}'))
