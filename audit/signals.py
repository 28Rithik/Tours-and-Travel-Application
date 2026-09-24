from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.contenttypes.models import ContentType
from operations.models import Booking
from finance.models import Payment
from audit.models import AuditLogEntry
import json

@receiver(post_save, sender=Booking)
@receiver(post_save, sender=Payment)
def log_audit_trail(sender, instance, created, **kwargs):
    action = 'created' if created else 'updated'
    
    # We can't easily get the user from a signal without thread locals,
    # so we leave it blank (or log 'System' if it's automated like a webhook)
    # A full audit trail app usually uses middleware, but this is a base implementation.
    AuditLogEntry.objects.create(
        action=f"{instance.__class__.__name__} {action}",
        content_type=ContentType.objects.get_for_model(instance),
        object_id=instance.id,
        changes={"id": instance.id, "status": getattr(instance, 'status', None)}
    )
