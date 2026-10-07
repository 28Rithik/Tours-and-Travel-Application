from django.core.management.base import BaseCommand
from core.models import Client
from crm.models import Inquiry, InquiryFollowUp, StaffNotification


class Command(BaseCommand):
    help = 'Cleans and removes all sample records tagged [SAMPLE].'

    def handle(self, *args, **options):
        # 1. Clean sample inquiries
        sample_inquiries = Inquiry.objects.filter(guest_name__startswith='[SAMPLE]')
        inq_count = sample_inquiries.count()
        sample_inquiries.delete()

        # 2. Clean sample clients
        sample_clients = Client.objects.filter(name__startswith='[SAMPLE]')
        client_count = sample_clients.count()
        sample_clients.delete()

        # 3. Clean sample notifications
        sample_notifs = StaffNotification.objects.filter(title__contains='Sample CRM Data')
        notif_count = sample_notifs.count()
        sample_notifs.delete()

        msg = f'Cleaned {inq_count} sample inquiries, {client_count} sample clients, and {notif_count} sample notifications.'
        self.stdout.write(self.style.SUCCESS(msg))
