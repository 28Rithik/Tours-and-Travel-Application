import datetime
import random
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth.models import User
from core.models import Client, VehicleType
from crm.models import Inquiry, InquiryFollowUp, StaffNotification

SAMPLE_LEADS_DATA = [
    {
        'guest_name': '[SAMPLE] Anandha Krishnan',
        'guest_phone': '+91 9842100111',
        'guest_email': 'anand.sample@gmail.com',
        'pickup_location': 'Coimbatore Airport',
        'destination': 'Ooty / Nilgiris, TN',
        'destination_dropdown': 'ooty',
        'journey_type': 'outstation',
        'adult_count': 4,
        'child_count': 1,
        'source': 'website',
        'priority': 'high',
        'status': 'new',
        'quoted_price': Decimal('14500.00'),
    },
    {
        'guest_name': '[SAMPLE] Priya Soundararajan',
        'guest_phone': '+91 9789100222',
        'guest_email': 'priya.sample@outlook.com',
        'pickup_location': 'Madurai Railway Station',
        'destination': 'Kodaikanal, TN',
        'destination_dropdown': 'kodaikanal',
        'journey_type': 'outstation',
        'adult_count': 2,
        'child_count': 0,
        'source': 'instagram',
        'priority': 'urgent',
        'status': 'quoted',
        'quoted_price': Decimal('18200.00'),
    },
    {
        'guest_name': '[SAMPLE] Vikramaditya Menon',
        'guest_phone': '+91 9447100333',
        'guest_email': 'vikram.menon.sample@yahoo.com',
        'pickup_location': 'Kochi Airport',
        'destination': 'Munnar Tea Hills, KL',
        'destination_dropdown': 'munnar',
        'journey_type': 'outstation',
        'adult_count': 5,
        'child_count': 2,
        'source': 'facebook',
        'priority': 'medium',
        'status': 'negotiating',
        'quoted_price': Decimal('26000.00'),
    },
    {
        'guest_name': '[SAMPLE] Suresh Babu Naidu',
        'guest_phone': '+91 9980100444',
        'guest_email': 'suresh.naidu.sample@gmail.com',
        'pickup_location': 'Bangalore City',
        'destination': 'Mysore Palace & Coorg, KA',
        'destination_dropdown': 'mysore_coorg',
        'journey_type': 'round_trip',
        'adult_count': 3,
        'child_count': 1,
        'source': 'agent_referral',
        'priority': 'medium',
        'status': 'won',
        'quoted_price': Decimal('32500.00'),
    },
    {
        'guest_name': '[SAMPLE] Rajeshwari Balaji',
        'guest_phone': '+91 9894100555',
        'guest_email': 'rajeshwari.sample@gmail.com',
        'pickup_location': 'Chennai Central',
        'destination': 'Pondicherry / Auroville',
        'destination_dropdown': 'pondicherry',
        'journey_type': 'outstation',
        'adult_count': 6,
        'child_count': 0,
        'source': 'phone',
        'priority': 'low',
        'status': 'lost',
        'lost_reason': 'price_too_high',
        'competitor_name': 'MakeMyTrip Local Cab',
        'objection_notes': 'Competitor offered 15% discount on Innova Crysta booking.',
        'win_loss_rating': 3,
        'quoted_price': Decimal('21000.00'),
    },
    {
        'guest_name': '[SAMPLE] Karthik Senthil',
        'guest_phone': '+91 9443100666',
        'guest_email': 'karthik.senthil.sample@gmail.com',
        'pickup_location': 'Tiruchirappalli Hub',
        'destination': 'Rameshwaram & Dhanushkodi, TN',
        'destination_dropdown': 'rameshwaram',
        'journey_type': 'outstation',
        'adult_count': 4,
        'child_count': 0,
        'source': 'walk_in',
        'priority': 'high',
        'status': 'in_progress',
        'quoted_price': Decimal('19800.00'),
    }
]


class Command(BaseCommand):
    help = 'Generates realistic sample CRM inquiries, follow-ups, and objections tagged [SAMPLE].'

    def handle(self, *args, **options):
        admin_user = User.objects.filter(is_staff=True).first()
        created_count = 0

        for lead in SAMPLE_LEADS_DATA:
            # Create sample client
            client, _ = Client.objects.get_or_create(
                phone=lead['guest_phone'],
                defaults={
                    'name': lead['guest_name'],
                    'email': lead['guest_email'],
                    'party_type': 'individual',
                    'address': lead['pickup_location'],
                }
            )

            today = timezone.now().date()
            inquiry, created = Inquiry.objects.get_or_create(
                guest_phone=lead['guest_phone'],
                defaults={
                    'party': client,
                    'guest_name': lead['guest_name'],
                    'guest_email': lead['guest_email'],
                    'pickup_location': lead['pickup_location'],
                    'destination': lead['destination'],
                    'destination_dropdown': lead['destination_dropdown'],
                    'pickup_date': today + datetime.timedelta(days=random.randint(1, 10)),
                    'pickup_time': datetime.time(8, 30),
                    'journey_type': lead['journey_type'],
                    'adult_count': lead['adult_count'],
                    'child_count': lead['child_count'],
                    'source': lead['source'],
                    'priority': lead['priority'],
                    'status': lead['status'],
                    'quoted_price': lead['quoted_price'],
                    'estimated_deal_value': lead['quoted_price'],
                    'assigned_to': admin_user,
                    'notes': f"{lead['guest_name']} sample inquiry generated for workflow testing.",
                    'lost_reason': lead.get('lost_reason', ''),
                    'competitor_name': lead.get('competitor_name', ''),
                    'objection_notes': lead.get('objection_notes', ''),
                    'win_loss_rating': lead.get('win_loss_rating'),
                }
            )

            if created:
                created_count += 1
                # Add sample follow-up
                InquiryFollowUp.objects.create(
                    inquiry=inquiry,
                    interaction_type='phone' if lead['source'] != 'whatsapp' else 'whatsapp',
                    notes=f"Initial discovery discussion with {inquiry.guest_name}. Tariff and vehicle availability discussed.",
                    next_action="Send revised customized itinerary PDF",
                    performed_by=admin_user,
                    is_done=True,
                )

        # Push notification
        StaffNotification.push(
            notification_type='system',
            title=f'Sample CRM Data: {created_count} Leads Generated',
            body='Generated demo leads across pipeline stages with sample follow-ups and objections.',
        )

        self.stdout.write(self.style.SUCCESS(f'Successfully generated {created_count} sample CRM records.'))
