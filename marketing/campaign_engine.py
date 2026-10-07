import urllib.parse
from datetime import timedelta
from django.utils import timezone
from core.models import Party, Client
from operations.models import Booking
from crm.models import Inquiry
from .models import PromotionCampaign, Coupon


CAMPAIGN_TEMPLATES = {
    'diwali': {
        'headline': "🪔 Diwali Festival Special Outstation & Package Travel",
        'body': (
            "Vanakkam {name}! 🪔 Celebrate this Diwali with family & friends stress-free! "
            "Book our sanitized Innova Crysta, Force Urbania, or Luxury Bus for your hometown trip or holiday. "
            "Use Coupon Code *{coupon_code}* to get an instant discount on your booking! "
            "Book online at https://sivagayathiri.in or call our 24x7 desk at 98422 12345."
        )
    },
    'pongal': {
        'headline': "🌾 Iniya Pongal Thirunaal Tour Packages Special",
        'body': (
            "Iniya Pongal Nalvazhthukkal {name}! 🌾 Plan your 4-day festive holiday to Ooty, Kodaikanal, "
            "or Munnar with Sivagayathiri Travels. Deluxe hotels, breakfast + dinner, and private transport included. "
            "Apply Promo Code *{coupon_code}* for exclusive savings! "
            "Direct link: https://sivagayathiri.in/packages/"
        )
    },
    'sabarimala': {
        'headline': "🕉️ Sabarimala Mandala & Makaravilakku Pilgrimage Van / Bus Booking",
        'body': (
            "Swamiye Saranam Ayyappa! 🙏 Planning your Sabarimala Yatra from Coimbatore/Tirupur? "
            "Book our 12/17/26 Seater Tempo Travellers & 35-Seater Air Suspended Coaches with experienced ghat-road drivers. "
            "Exclusive Pilgrimage Offer Code: *{coupon_code}*. Call 98422 12345 today."
        )
    },
    'summer': {
        'headline': "☀️ Beat the Heat - Nilgiris & Kerala Summer Escapes",
        'body': (
            "Hello {name}! ☀️ Plan your summer family vacation to the cool hills of Ooty, Coonoor, "
            "Wayanad & Valparai. Enjoy customized itineraries, top-rated resorts, and hassle-free travel. "
            "Use voucher *{coupon_code}* for your family booking! Call Sivagayathiri Travels: 98422 12345."
        )
    }
}


def get_audience_recipients(audience_type: str):
    """
    Returns list of recipients (dicts with name and phone) based on chosen target cohort.
    """
    recipients = []
    seen_phones = set()

    if audience_type == 'corporate_clients':
        parties = Party.objects.filter(party_type='corporate', is_active=True).exclude(phone='')
        for p in parties[:200]:
            clean_phone = p.phone.strip()
            if clean_phone and clean_phone not in seen_phones:
                seen_phones.add(clean_phone)
                recipients.append({'name': p.name, 'phone': clean_phone, 'type': 'Corporate'})

    elif audience_type == 'cold_inquiries':
        ninety_days_ago = timezone.now() - timedelta(days=90)
        inquiries = Inquiry.objects.filter(
            created_at__gte=ninety_days_ago,
            status__in=['new', 'contacted', 'quote_sent', 'lost']
        ).exclude(phone='')
        for inq in inquiries[:200]:
            clean_phone = inq.phone.strip()
            if clean_phone and clean_phone not in seen_phones:
                seen_phones.add(clean_phone)
                recipients.append({'name': inq.customer_name, 'phone': clean_phone, 'type': 'CRM Lead'})

    else:  # all_tourists / default
        # Pull past holiday tour customers from bookings
        bookings = Booking.objects.select_related('party').filter(
            journey_type__in=['outstation', 'round_trip']
        ).order_by('-id')[:250]

        for b in bookings:
            p_name = b.guest_name or (b.party.name if b.party else 'Customer')
            p_phone = (b.guest_phone or (b.party.phone if b.party else '')).strip()
            if p_phone and p_phone not in seen_phones:
                seen_phones.add(p_phone)
                recipients.append({'name': p_name, 'phone': p_phone, 'type': 'Tourist'})

        # If few bookings, fill with active individual parties
        if len(recipients) < 10:
            for p in Party.objects.filter(party_type__in=['individual', 'travel_agency'], is_active=True)[:50]:
                if p.phone and p.phone.strip() not in seen_phones:
                    seen_phones.add(p.phone.strip())
                    recipients.append({'name': p.name, 'phone': p.phone.strip(), 'type': 'Customer'})

    return recipients


def generate_campaign_dispatches(campaign: PromotionCampaign):
    """
    Generates personalized broadcast list with WhatsApp deep links.
    """
    recipients = get_audience_recipients(campaign.target_audience)
    coupon_code = campaign.coupon.code if campaign.coupon else 'HOLIDAY2026'

    dispatches = []
    for r in recipients:
        msg = campaign.message_body.replace('{name}', r['name']).replace('{coupon_code}', coupon_code)
        phone = r['phone'].replace(' ', '').replace('-', '').replace('+', '')
        if phone and not phone.startswith('91') and len(phone) == 10:
            phone = f"91{phone}"

        encoded = urllib.parse.quote(msg)
        wa_link = f"https://wa.me/{phone}?text={encoded}" if phone else f"https://wa.me/?text={encoded}"

        dispatches.append({
            'name': r['name'],
            'phone': r['phone'],
            'type': r['type'],
            'message': msg,
            'whatsapp_link': wa_link
        })

    # Update counts on campaign
    campaign.target_count = len(dispatches)
    campaign.save(update_fields=['target_count'])

    return dispatches
