"""
Dynamic NPCI UPI Intent & QR Code Generator Engine.
Generates Indian Unified Payments Interface (UPI) URI links, high-res scalable vector SVG QR codes,
Base64 PNG data-URIs, and direct mobile deep links for Google Pay, PhonePe, and Paytm.
"""

import io
import base64
import urllib.parse
from decimal import Decimal
import qrcode
import qrcode.image.svg
from .models import PaymentGatewayConfig


def get_default_upi_config():
    """Retrieve active Direct UPI configuration or fallback to defaults."""
    cfg = PaymentGatewayConfig.objects.filter(provider='direct_upi', is_active=True).first()
    if not cfg:
        cfg = PaymentGatewayConfig.objects.filter(is_active=True).first()
    return cfg


def build_upi_payment_url(vpa, merchant_name, amount, reference_id, note='', mcc='4121'):
    """
    Constructs an NPCI-compliant UPI Intent URI.
    Format: upi://pay?pa=...&pn=...&am=...&cu=INR&tr=...&tn=...&mc=...
    """
    amt_str = f"{Decimal(str(amount)):.2f}"
    params = {
        'pa': vpa.strip(),
        'pn': merchant_name.strip(),
        'am': amt_str,
        'cu': 'INR',
        'tr': str(reference_id).strip(),
        'tn': (note or f"Payment for {reference_id}").strip(),
        'mc': str(mcc).strip() if mcc else '4121',
    }
    encoded_params = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
    return f"upi://pay?{encoded_params}"


def generate_upi_qr_svg(upi_url):
    """Generates a clean, scalable vector SVG string for direct inline embedding."""
    factory = qrcode.image.svg.SvgPathImage
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=2,
        image_factory=factory
    )
    qr.add_data(upi_url)
    qr.make(fit=True)
    img = qr.make_image()
    stream = io.BytesIO()
    img.save(stream)
    return stream.getvalue().decode('utf-8')


def generate_upi_qr_base64(upi_url):
    """Generates a Base64 data-URI PNG (data:image/png;base64,...) for <img> tags and PDFs."""
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=2
    )
    qr.add_data(upi_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    encoded = base64.b64encode(buffer.getvalue()).decode('ascii')
    return f"data:image/png;base64,{encoded}"


def build_app_intent_links(upi_url):
    """
    Constructs platform-specific deep links for mobile devices:
    - Google Pay (tez://upi/pay?...)
    - PhonePe (phonepe://pay?...)
    - Paytm (paytmmp://pay?...)
    - Generic UPI (upi://pay?...)
    """
    raw_query = upi_url.replace("upi://pay?", "")
    return {
        'generic': upi_url,
        'gpay': f"tez://upi/pay?{raw_query}",
        'phonepe': f"phonepe://pay?{raw_query}",
        'paytm': f"paytmmp://pay?{raw_query}",
        'bhim': f"bhim://pay?{raw_query}",
    }


def generate_dynamic_upi_package(amount, reference_id, note='', vpa=None, merchant_name=None):
    """
    High-level convenience generator producing complete UPI bundle:
    - NPCI Intent URL
    - SVG Vector QR String
    - Base64 PNG Data-URI
    - App deep links dictionary
    """
    cfg = get_default_upi_config()
    target_vpa = vpa or (cfg.upi_vpa if cfg else 'sivagayathiritravels@icici')
    target_name = merchant_name or (cfg.merchant_name if cfg else 'Sivagayathiri Travels')
    mcc = cfg.mcc_code if cfg else '4121'

    upi_url = build_upi_payment_url(
        vpa=target_vpa,
        merchant_name=target_name,
        amount=amount,
        reference_id=reference_id,
        note=note,
        mcc=mcc
    )

    qr_svg = generate_upi_qr_svg(upi_url)
    qr_base64 = generate_upi_qr_base64(upi_url)
    deep_links = build_app_intent_links(upi_url)

    return {
        'upi_url': upi_url,
        'qr_svg': qr_svg,
        'qr_base64': qr_base64,
        'deep_links': deep_links,
        'vpa': target_vpa,
        'merchant_name': target_name,
        'amount': Decimal(str(amount)),
        'reference_id': str(reference_id),
    }
