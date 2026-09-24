from django.core.management.base import BaseCommand
from django.utils import timezone
from marketing.models import EmailCampaign
from core.models import Client
from crm.services import send_email

class Command(BaseCommand):
    help = 'Sends active email campaigns to all subscribed customers'

    def handle(self, *args, **kwargs):
        # Get active campaigns that haven't been sent yet
        pending_campaigns = EmailCampaign.objects.filter(is_active=True, sent_at__isnull=True)
        
        if not pending_campaigns.exists():
            self.stdout.write(self.style.SUCCESS('No pending email campaigns to send.'))
            return
            
        # For simplicity, send to all clients with an email
        clients = Client.objects.exclude(email='')
        
        for campaign in pending_campaigns:
            count = 0
            for client in clients:
                send_email(client.email, campaign.subject, campaign.body_html)
                count += 1
                
            campaign.sent_at = timezone.now()
            campaign.save()
            self.stdout.write(self.style.SUCCESS(f'Successfully sent campaign "{campaign.name}" to {count} clients.'))
