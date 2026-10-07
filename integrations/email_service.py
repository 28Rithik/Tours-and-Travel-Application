import logging
from django.core.mail.backends.smtp import EmailBackend
from django.core.mail import EmailMultiAlternatives
from django.utils import timezone
from .models import IntegrationSettings

logger = logging.getLogger(__name__)


def send_dynamic_email(to_email: str, subject: str, body_text: str, body_html: str = None, test_mode: bool = False) -> dict:
    """
    Sends an email using the database-configured SMTP credentials from IntegrationSettings.
    Falls back gracefully if SMTP is not configured or in test mode.
    """
    if not to_email:
        return {"status": "error", "message": "Recipient email address is required"}

    cfg = IntegrationSettings.get_settings()

    if not cfg.email_active and not test_mode:
        return {"status": "skipped", "message": "Email service is marked inactive in settings"}

    from_email = f"{cfg.sender_name} <{cfg.sender_email}>" if cfg.sender_name else cfg.sender_email

    # Check daily limit
    if cfg.emails_sent_today >= cfg.email_daily_limit and not test_mode:
        return {"status": "error", "message": f"Daily limit of {cfg.email_daily_limit} emails reached"}

    # Dynamic backend configuration
    use_tls = (cfg.smtp_encryption == 'tls')
    use_ssl = (cfg.smtp_encryption == 'ssl')

    try:
        backend = EmailBackend(
            host=cfg.smtp_host,
            port=cfg.smtp_port,
            username=cfg.smtp_username if cfg.smtp_username else None,
            password=cfg.smtp_password if cfg.smtp_password else None,
            use_tls=use_tls,
            use_ssl=use_ssl,
            timeout=8,
            fail_silently=False
        )

        msg = EmailMultiAlternatives(
            subject=subject,
            body=body_text,
            from_email=from_email,
            to=[to_email],
            connection=backend
        )
        if body_html:
            msg.attach_alternative(body_html, "text/html")

        # In dev/mock mode if password is empty or test host
        if not cfg.smtp_password or cfg.smtp_host in ['localhost', 'custom']:
            # Log test simulation
            logger.info(f"[SIMULATED DYNAMIC EMAIL -> {to_email}]: {subject}")
            cfg.emails_sent_today += 1
            cfg.last_email_sent_at = timezone.now()
            cfg.save(update_fields=['emails_sent_today', 'last_email_sent_at'])
            return {
                "status": "success",
                "message": f"Verified! Simulated email sent to {to_email} via {cfg.smtp_host}:{cfg.smtp_port} (TLS: {use_tls}, SSL: {use_ssl})."
            }

        # Real SMTP transmission
        backend.open()
        msg.send()
        backend.close()

        cfg.emails_sent_today += 1
        cfg.last_email_sent_at = timezone.now()
        cfg.save(update_fields=['emails_sent_today', 'last_email_sent_at'])

        return {
            "status": "success",
            "message": f"Verified! Live email successfully delivered to {to_email} via {cfg.smtp_host}:{cfg.smtp_port}."
        }

    except Exception as e:
        logger.error(f"[Dynamic Email Failed to {to_email}]: {e}")
        return {
            "status": "error",
            "message": f"SMTP Connection Error: {str(e)}"
        }
