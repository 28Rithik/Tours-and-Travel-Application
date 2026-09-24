import json
from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from operations.models import Booking
from .models import PaymentWebhookEvent
from finance.models import Payment
from statements.services import generate_invoice_for_booking

@csrf_exempt
def razorpay_webhook(request):
    if request.method == 'POST':
        try:
            payload = json.loads(request.body)
            event_id = payload.get('id', 'unknown')
            event_type = payload.get('event', '')
            
            # Log the event (idempotent handling of webhook retries)
            evt_log, created_evt = PaymentWebhookEvent.objects.get_or_create(
                event_id=event_id,
                defaults={'event_type': event_type, 'payload': payload}
            )
            if not created_evt:
                return HttpResponse(status=200) # Duplicate delivery safely acknowledged
            
            # Process payment authorized, captured, or payment_link.paid
            if event_type in ['payment.captured', 'payment.authorized', 'payment_link.paid']:
                plink_entity = payload.get('payload', {}).get('payment_link', {}).get('entity', {})
                payment_entity = payload.get('payload', {}).get('payment', {}).get('entity', {})
                
                reference_id = (
                    plink_entity.get('reference_id') or
                    payment_entity.get('notes', {}).get('reference_id') or
                    payment_entity.get('description', '')
                )
                
                amt_raw = plink_entity.get('amount_paid') or payment_entity.get('amount') or 0
                from decimal import Decimal
                amount = Decimal(str(amt_raw)) / Decimal('100.0')
                
                if reference_id and amount > 0:
                    try:
                        booking = Booking.objects.filter(booking_number=reference_id).first()
                        if booking:
                            Payment.objects.create(
                                party=booking.party,
                                booking=booking,
                                date=booking.booking_date,
                                amount=amount,
                                payment_mode='bank_transfer',
                                payment_type='customer_receipt',
                                reference_number=payment_entity.get('id') or plink_entity.get('id') or f"RZP-{event_id}",
                                notes=f"Razorpay Auto-Captured: {event_id}"
                            )
                            if booking.status == 'pending':
                                booking.status = 'confirmed'
                                booking.save(update_fields=['status'])
                            try:
                                generate_invoice_for_booking(booking)
                            except Exception:
                                pass
                    except Exception as e:
                        print(f"Error processing webhook booking link: {e}")

            return HttpResponse(status=200)
        except json.JSONDecodeError:
            return HttpResponseBadRequest('Invalid payload')
    return HttpResponseBadRequest('Only POST accepted')
