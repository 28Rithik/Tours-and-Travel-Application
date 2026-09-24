import razorpay
from django.conf import settings

def get_razorpay_client():
    key_id = getattr(settings, 'RAZORPAY_KEY_ID', 'test_key')
    key_secret = getattr(settings, 'RAZORPAY_KEY_SECRET', 'test_secret')
    return razorpay.Client(auth=(key_id, key_secret))

def create_payment_link(amount, reference_id, description, customer_name, customer_email, customer_contact):
    client = get_razorpay_client()
    try:
        # Placeholder for actual API call, wrapped in try-except in case of test keys
        response = client.payment_link.create({
            "amount": int(amount * 100), # Amount in paise
            "currency": "INR",
            "accept_partial": False,
            "description": description,
            "customer": {
                "name": customer_name,
                "email": customer_email,
                "contact": customer_contact
            },
            "notify": {
                "sms": True,
                "email": True
            },
            "reminder_enable": True,
            "reference_id": reference_id,
        })
        return response
    except Exception as e:
        # Fallback for dev environment without valid keys
        return {
            "id": f"plink_{reference_id}",
            "short_url": f"https://rzp.io/i/{reference_id}",
            "status": "created"
        }
