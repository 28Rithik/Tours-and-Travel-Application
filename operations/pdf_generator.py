import io
import os
import math
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, Union, Dict, Any

from django.utils import timezone
import qrcode
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether, HRFlowable
)
from reportlab.pdfgen.canvas import Canvas

from core.models import Vehicle, Driver, Client as PartyClient
from operations.models import Trip, Booking

# ==============================================================================
# CORPORATE BRANDING CONSTANTS
# ==============================================================================
COMPANY_NAME = "SIVAGAYATHIRI TOURS AND TRAVELS"
COMPANY_SUBTITLE = "Enterprise Mobility • Tour Expeditions • Luxury Chauffeur Fleet"
COMPANY_ADDRESS = "123 Main Road, Gandhipuram, Coimbatore, Tamil Nadu - 641012"
COMPANY_CONTACT = "Phone: +91 98765 43210 | +91 422 2490000 | Email: dispatch@sivagayathiritravels.com"
COMPANY_GSTIN = "33AABCS1234F1Z8"
COMPANY_PAN = "AABCS1234F"
COMPANY_STATE = "Tamil Nadu (Code: 33)"

# Color Palette
PRIMARY_COLOR = colors.HexColor('#0f172a')   # Deep Slate Navy
ACCENT_COLOR = colors.HexColor('#0284c7')    # Sky Blue
SUCCESS_COLOR = colors.HexColor('#16a34a')   # Green
BORDER_COLOR = colors.HexColor('#cbd5e1')    # Light Gray
BG_LIGHT = colors.HexColor('#f8fafc')        # Very Light Blue/Gray
BG_HEADER = colors.HexColor('#f1f5f9')       # Muted Slate Header


# ==============================================================================
# TWO-PASS NUMBERED CANVAS (Page X of Y)
# ==============================================================================
class PDFNumberedCanvas(Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_footer(num_pages)
            super().showPage()
        super().save()

    def draw_footer(self, total_pages: int):
        self.saveState()
        self.setStrokeColor(BORDER_COLOR)
        self.setLineWidth(0.6)
        self.line(12 * mm, 12 * mm, 198 * mm, 12 * mm)

        self.setFont('Helvetica', 8)
        self.setFillColor(colors.HexColor('#64748b'))
        self.drawString(
            12 * mm, 8 * mm,
            f"Generated via TravelERP • {COMPANY_NAME} • Computer Generated Document"
        )
        page_str = f"Page {self._pageNumber} of {total_pages}"
        self.drawRightString(198 * mm, 8 * mm, page_str)
        self.restoreState()


# ==============================================================================
# UTILITY HELPERS
# ==============================================================================
def make_qr_image(data_str: str, size_mm: float = 24.0) -> Image:
    """Generates a high-contrast QR code flowable Image."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=1,
    )
    qr.add_data(data_str)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return Image(buf, width=size_mm * mm, height=size_mm * mm)


def amount_in_words_inr(amount: Union[Decimal, float, int]) -> str:
    """Converts a monetary value into Indian Lakhs/Crores English words."""
    try:
        val = int(round(float(amount)))
    except (ValueError, TypeError):
        return "Rupees Zero Only"

    if val == 0:
        return "Rupees Zero Only"

    units = [
        "", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine",
        "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen",
        "Seventeen", "Eighteen", "Nineteen"
    ]
    tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]

    def two_digits(n):
        if n < 20:
            return units[n]
        return tens[n // 10] + (" " + units[n % 10] if n % 10 else "")

    def three_digits(n):
        h = n // 100
        rem = n % 100
        res = ""
        if h > 0:
            res += units[h] + " Hundred"
            if rem > 0:
                res += " "
        if rem > 0:
            res += two_digits(rem)
        return res

    crores = val // 10000000
    rem = val % 10000000
    lakhs = rem // 100000
    rem = rem % 100000
    thousands = rem // 1000
    rem = rem % 1000

    parts = []
    if crores > 0:
        parts.append(two_digits(crores) + " Crore")
    if lakhs > 0:
        parts.append(two_digits(lakhs) + " Lakh")
    if thousands > 0:
        parts.append(two_digits(thousands) + " Thousand")
    if rem > 0:
        parts.append(three_digits(rem))

    return "Rupees " + " ".join(parts).strip() + " Only"


def _format_date(val: Any, fmt: str = '%d/%m/%Y', default: str = 'N/A') -> str:
    """Safely formats any date, datetime, or date-string into the requested format."""
    if not val:
        return default
    if hasattr(val, 'strftime'):
        try:
            return val.strftime(fmt)
        except Exception:
            pass
    val_str = str(val).strip()
    if not val_str:
        return default
    try:
        from datetime import datetime
        for ifmt in ('%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y', '%Y/%m/%d'):
            try:
                return datetime.strptime(val_str, ifmt).strftime(fmt)
            except ValueError:
                pass
    except Exception:
        pass
    return val_str


def _format_time(val: Any, default: str = '08:00 AM') -> str:
    """Safely formats any time, datetime, or time-string into 'HH:MM AM/PM'."""
    if not val:
        return default
    if hasattr(val, 'strftime'):
        try:
            return val.strftime('%I:%M %p')
        except Exception:
            pass
    val_str = str(val).strip()
    if not val_str:
        return default
    try:
        from datetime import datetime
        for ifmt in ('%H:%M:%S', '%H:%M', '%I:%M %p', '%I:%M%p'):
            try:
                return datetime.strptime(val_str, ifmt).strftime('%I:%M %p')
            except ValueError:
                pass
    except Exception:
        pass
    return val_str


def _build_styles() -> Dict[str, ParagraphStyle]:
    """Generates custom typography styles for ReportLab documents."""
    base = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=base['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=18,
        textColor=PRIMARY_COLOR,
        spaceAfter=2,
    )
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=base['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor('#64748b'),
    )
    section_h2 = ParagraphStyle(
        'SectionH2',
        parent=base['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=13,
        textColor=PRIMARY_COLOR,
        spaceBefore=8,
        spaceAfter=4,
    )
    cell_bold = ParagraphStyle(
        'CellBold',
        parent=base['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=PRIMARY_COLOR,
    )
    cell_regular = ParagraphStyle(
        'CellRegular',
        parent=base['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#334155'),
    )
    cell_small = ParagraphStyle(
        'CellSmall',
        parent=base['Normal'],
        fontName='Helvetica',
        fontSize=7.5,
        leading=9.5,
        textColor=colors.HexColor('#64748b'),
    )
    return {
        'title': title_style,
        'subtitle': subtitle_style,
        'h2': section_h2,
        'cell_bold': cell_bold,
        'cell_reg': cell_regular,
        'cell_small': cell_small,
    }


# ==============================================================================
# 1. OFFICIAL DRIVER TRIP SHEET PDF
# ==============================================================================
def render_trip_sheet_pdf(trip: Trip) -> bytes:
    """
    Renders an official Driver Trip Sheet PDF complete with verification QR code,
    duty timetable, vehicle specs, odometer log table, and signature blocks.
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=14 * mm,
        bottomMargin=16 * mm
    )
    styles = _build_styles()
    story = []

    # A. Corporate Header & QR Code
    qr_url = f"https://sivagayathiritravels.com/trips/{trip.id}/status/"
    qr_flowable = make_qr_image(qr_url, size_mm=22.0)

    header_left = [
        Paragraph(COMPANY_NAME, styles['title']),
        Paragraph(COMPANY_SUBTITLE, styles['subtitle']),
        Paragraph(f"{COMPANY_ADDRESS} • {COMPANY_CONTACT}", styles['subtitle']),
        Paragraph(f"<b>GSTIN:</b> {COMPANY_GSTIN} | <b>PAN:</b> {COMPANY_PAN}", styles['subtitle']),
    ]
    header_right = [
        Paragraph("<b>OFFICIAL DRIVER TRIP SHEET</b>", ParagraphStyle('RHead', parent=styles['cell_bold'], fontSize=11, leading=13, alignment=2, textColor=ACCENT_COLOR)),
        Paragraph(f"<b>Trip Ref:</b> #{trip.trip_id or f'TR-{trip.id}'}", ParagraphStyle('RRef', parent=styles['cell_bold'], fontSize=9, leading=11, alignment=2)),
        Paragraph(f"<b>Date:</b> {_format_date(trip.start_date, '%d/%m/%Y', default=_format_date(timezone.localdate(), '%d/%m/%Y'))}", ParagraphStyle('RDate', parent=styles['cell_small'], alignment=2)),
    ]

    header_table = Table(
        [[header_left, header_right, qr_flowable]],
        colWidths=[110 * mm, 50 * mm, 26 * mm]
    )
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(header_table)
    story.append(HRFlowable(width="100%", thickness=1.5, color=PRIMARY_COLOR, spaceAfter=8, spaceBefore=4))

    # B. Passenger & Journey Meta Table
    b = trip.booking
    guest_name = trip.guest_name or (b.guest_name if b else "Valued Guest")
    guest_phone = (b.guest_phone if b else "") or "N/A"
    client_name = trip.party.name if trip.party else "Direct Private Client"
    route_display = f"{b.pickup_location if b else 'Origin'} ➡️ {b.destination if b else 'Destination'}"
    raw_time = (b.reporting_time if (b and b.reporting_time) else (b.pickup_time if (b and b.pickup_time) else None))
    reporting_time = _format_time(raw_time, default='08:00 AM')

    journey_meta = [
        [
            Paragraph("<b>Guest / Passenger:</b>", styles['cell_bold']),
            Paragraph(f"{guest_name} (📞 {guest_phone})", styles['cell_reg']),
            Paragraph("<b>Corporate Client:</b>", styles['cell_bold']),
            Paragraph(client_name, styles['cell_reg']),
        ],
        [
            Paragraph("<b>Scheduled Route:</b>", styles['cell_bold']),
            Paragraph(route_display, styles['cell_reg']),
            Paragraph("<b>Journey Type:</b>", styles['cell_bold']),
            Paragraph(f"{b.get_journey_type_display() if b else 'Outstation'} ({trip.days_count or 1} Days)", styles['cell_reg']),
        ],
        [
            Paragraph("<b>Reporting Schedule:</b>", styles['cell_bold']),
            Paragraph(f"{_format_date(trip.start_date, '%d %b %Y', default='Scheduled')} @ {reporting_time}", styles['cell_reg']),
            Paragraph("<b>Passenger Count:</b>", styles['cell_bold']),
            Paragraph(f"{trip.pax_count or (b.pax_count if b else 1)} Pax", styles['cell_reg']),
        ]
    ]
    t_journey = Table(journey_meta, colWidths=[38 * mm, 55 * mm, 38 * mm, 55 * mm])
    t_journey.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), BG_LIGHT),
        ('BOX', (0, 0), (-1, -1), 0.8, BORDER_COLOR),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(t_journey)
    story.append(Spacer(1, 6 * mm))

    # C. Assigned Vehicle & Chauffeur Specification Block
    v = trip.vehicle
    v_plate = v.registration_number if v else "UNASSIGNED"
    v_desc = f"{v.brand} {v.model} ({v.vehicle_type.name if v.vehicle_type else 'Fleet'})" if v else "Pending Allocation"
    
    d = trip.driver
    d_name = d.name if d else "UNASSIGNED"
    d_phone = d.phone if d else "N/A"
    d_badge = f"Badge: {d.badge_number}" if (d and d.badge_number) else "Verified Chauffeur"

    crew_data = [
        [
            Paragraph("<b>Assigned Vehicle Plate</b>", styles['cell_bold']),
            Paragraph(f"<font color='{ACCENT_COLOR.hexval()}'><b>{v_plate}</b></font> • {v_desc}", styles['cell_reg']),
            Paragraph("<b>Duty Chauffeur / Captain</b>", styles['cell_bold']),
            Paragraph(f"<b>{d_name}</b> (📞 {d_phone}) • {d_badge}", styles['cell_reg']),
        ]
    ]
    t_crew = Table(crew_data, colWidths=[42 * mm, 51 * mm, 42 * mm, 51 * mm])
    t_crew.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#e0f2fe')),
        ('BOX', (0, 0), (-1, -1), 1.0, ACCENT_COLOR),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#bae6fd')),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(t_crew)
    story.append(Spacer(1, 6 * mm))

    # D. Odometer & Duty Meter Recording Table
    story.append(Paragraph("<b>DUTY TIMINGS &amp; ODOMETER LOG (TO BE RECORDED ON TRIP)</b>", styles['h2']))
    odo_table_data = [
        [
            Paragraph("<b>Duty Milestone</b>", styles['cell_bold']),
            Paragraph("<b>Date (DD/MM)</b>", styles['cell_bold']),
            Paragraph("<b>Time (HH:MM)</b>", styles['cell_bold']),
            Paragraph("<b>Odometer Reading (KM)</b>", styles['cell_bold']),
            Paragraph("<b>Location / Garage</b>", styles['cell_bold']),
        ],
        [
            Paragraph("Garage Out / Starting", styles['cell_reg']),
            Paragraph(_format_date(trip.start_date, '%d/%m/%Y', default=""), styles['cell_reg']),
            Paragraph("", styles['cell_reg']),
            Paragraph(str(trip.opening_km) if trip.opening_km else "___________ KM", styles['cell_reg']),
            Paragraph(b.pickup_location if b else "Garage Depot", styles['cell_reg']),
        ],
        [
            Paragraph("Customer Pickup Point", styles['cell_reg']),
            Paragraph("", styles['cell_reg']),
            Paragraph("", styles['cell_reg']),
            Paragraph("___________ KM", styles['cell_reg']),
            Paragraph("", styles['cell_reg']),
        ],
        [
            Paragraph("Customer Drop Point", styles['cell_reg']),
            Paragraph("", styles['cell_reg']),
            Paragraph("", styles['cell_reg']),
            Paragraph("___________ KM", styles['cell_reg']),
            Paragraph("", styles['cell_reg']),
        ],
        [
            Paragraph("Garage In / Closing", styles['cell_reg']),
            Paragraph(_format_date(trip.end_date, '%d/%m/%Y', default=""), styles['cell_reg']),
            Paragraph("", styles['cell_reg']),
            Paragraph(str(trip.closing_km) if trip.closing_km else "___________ KM", styles['cell_reg']),
            Paragraph("Depot Close", styles['cell_reg']),
        ],
        [
            Paragraph("<b>TOTALS</b>", styles['cell_bold']),
            Paragraph(f"<b>{trip.days_count or 1} Day(s)</b>", styles['cell_bold']),
            Paragraph("<b>Total Hours: _____</b>", styles['cell_bold']),
            Paragraph(f"<b>Total Run: {(trip.closing_km - trip.opening_km) if (trip.closing_km and trip.opening_km) else '______'} KM</b>", styles['cell_bold']),
            Paragraph("AC [  ]   Non-AC [  ]", styles['cell_bold']),
        ]
    ]
    t_odo = Table(odo_table_data, colWidths=[46 * mm, 30 * mm, 30 * mm, 40 * mm, 40 * mm])
    t_odo.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), BG_HEADER),
        ('BOX', (0, 0), (-1, -1), 0.8, BORDER_COLOR),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('TOPPADDING', (0, 0), (-1, -1), 4.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4.5),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#f1f5f9')),
    ]))
    story.append(t_odo)
    story.append(Spacer(1, 6 * mm))

    # E. En-Route Expenses & Toll Log Table
    story.append(Paragraph("<b>EN-ROUTE EXPENSES &amp; TOLL RECORD</b>", styles['h2']))
    exp_data = [
        [
            Paragraph("<b>FASTag Toll Amount</b>", styles['cell_bold']),
            Paragraph("<b>Parking Charges</b>", styles['cell_bold']),
            Paragraph("<b>State Entry Tax / Permit</b>", styles['cell_bold']),
            Paragraph("<b>Driver Bata / Food</b>", styles['cell_bold']),
            Paragraph("<b>Total Out-of-Pocket</b>", styles['cell_bold']),
        ],
        [
            Paragraph("₹ _____________", styles['cell_reg']),
            Paragraph("₹ _____________", styles['cell_reg']),
            Paragraph("₹ _____________", styles['cell_reg']),
            Paragraph(f"₹ {trip.driver_bata:,.2f}" if trip.driver_bata else "₹ _____________", styles['cell_reg']),
            Paragraph("₹ _____________", styles['cell_bold']),
        ]
    ]
    t_exp = Table(exp_data, colWidths=[37 * mm, 37 * mm, 40 * mm, 36 * mm, 36 * mm])
    t_exp.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), BG_HEADER),
        ('BOX', (0, 0), (-1, -1), 0.8, BORDER_COLOR),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(t_exp)
    story.append(Spacer(1, 6 * mm))

    # F. Chauffeur Code of Conduct & Passenger Safety Box
    safety_text = (
        "<b>SAFETY MANDATE:</b> Maximum highway speed 80 km/h (40 km/h in Ghats/Hills). "
        "Strict zero alcohol/smoking policy. All passengers must wear seatbelts. "
        "In case of emergency or breakdown, call 24x7 Control Room: +91 98765 43210 immediately."
    )
    t_safety = Table([[Paragraph(safety_text, styles['cell_small'])]], colWidths=[186 * mm])
    t_safety.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#fef3c7')),
        ('BOX', (0, 0), (-1, -1), 0.8, colors.HexColor('#f59e0b')),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(t_safety)
    story.append(Spacer(1, 8 * mm))

    # G. Signatures & Guest Feedback Verification
    guest_cell = [
        Paragraph("<b>Guest Feedback &amp; Signature</b>", styles['cell_small'])
    ]
    if getattr(trip, 'customer_signature_data', None):
        try:
            import base64
            sig_raw = str(trip.customer_signature_data)
            if ',' in sig_raw:
                sig_raw = sig_raw.split(',', 1)[1]
            sig_bytes = base64.b64decode(sig_raw)
            sig_flowable = Image(io.BytesIO(sig_bytes), width=42 * mm, height=15 * mm)
            guest_cell.append(sig_flowable)
        except Exception:
            guest_cell.append(Paragraph("<br/><i>[Digitally Signed by Passenger]</i>", styles['cell_small']))
    else:
        guest_cell.append(Paragraph("<br/><br/>Signature: ______________________", styles['cell_small']))

    stars_count = trip.guest_rating if getattr(trip, 'guest_rating', None) else None
    if stars_count:
        star_display = f"Rating: {'★' * stars_count}{'☆' * (5 - stars_count)} ({stars_count}/5)"
    else:
        star_display = "Rating: [ ★ ★ ★ ★ ★ ]"
    guest_cell.append(Paragraph(star_display, styles['cell_small']))

    sig_data = [
        [
            guest_cell,
            Paragraph("<b>Chauffeur / Captain Signature</b><br/><br/><br/>I confirm accurate odometer readings.<br/>Signature: ______________________", styles['cell_small']),
            Paragraph("<b>Authorized Fleet Dispatcher</b><br/><br/><br/>Verified for Sivagayathiri Travels<br/>Seal &amp; Sign: ___________________", styles['cell_small']),
        ]
    ]
    t_sig = Table(sig_data, colWidths=[62 * mm, 62 * mm, 62 * mm])
    t_sig.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.8, BORDER_COLOR),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('BACKGROUND', (0, 0), (-1, -1), BG_LIGHT),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(KeepTogether(t_sig))

    doc.build(story, canvasmaker=PDFNumberedCanvas)
    buf.seek(0)
    return buf.getvalue()


# ==============================================================================
# 2. GST TAX INVOICE PDF (B2B & B2C)
# ==============================================================================
def render_tax_invoice_pdf(trip_or_invoice: Any) -> bytes:
    """
    Renders an official GST Tax Invoice PDF adhering to Section 31 of CGST Act.
    Includes SAC 996412 line items, CGST/SGST/IGST breakdown, reverse charge flag,
    and Dynamic UPI QR Code for instant settlement.
    """
    from finance.models import CorporateGSTInvoice

    invoice = None
    trip = None

    if isinstance(trip_or_invoice, CorporateGSTInvoice):
        invoice = trip_or_invoice
        trip = invoice.trip
    elif isinstance(trip_or_invoice, Trip):
        trip = trip_or_invoice
        invoice = getattr(trip, 'gst_invoices', None)
        if invoice is not None and hasattr(invoice, 'first'):
            invoice = invoice.first()
        elif hasattr(trip, 'corporate_invoices'):
            invoice = trip.corporate_invoices.first()
        else:
            try:
                invoice = CorporateGSTInvoice.objects.filter(trip=trip).first()
            except Exception:
                invoice = None

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=14 * mm,
        bottomMargin=16 * mm
    )
    styles = _build_styles()
    story = []

    # Financial figures resolution
    inv_num = invoice.invoice_number if invoice else f"INV-{trip.id:05d}"
    inv_date = invoice.invoice_date if invoice else (trip.end_date or timezone.localdate())
    
    # Financial calculation fallback
    if invoice:
        taxable_value = invoice.taxable_value
        cgst_amt = invoice.cgst_amount
        sgst_amt = invoice.sgst_amount
        igst_amt = invoice.igst_amount
        total_tax = invoice.total_tax
        grand_total = invoice.total_invoice_value
        is_rcm = invoice.is_reverse_charge
        pos = invoice.place_of_supply or COMPANY_STATE
    else:
        # Compute from Trip
        taxable_value = Decimal(str(trip.fixed_amount or (trip.day_rate * (trip.days_count or 1)) or 4500.00))
        gst_rate = Decimal('5.00')  # standard 5% transport rate
        cgst_amt = round(taxable_value * Decimal('0.025'), 2)
        sgst_amt = round(taxable_value * Decimal('0.025'), 2)
        igst_amt = Decimal('0.00')
        total_tax = cgst_amt + sgst_amt
        grand_total = taxable_value + total_tax
        is_rcm = False
        pos = COMPANY_STATE

    # Dynamic UPI Payment QR Code
    upi_str = f"upi://pay?pa=sivagayathiritravels@okaxis&pn=Sivagayathiri%20Travels&am={grand_total:.2f}&cu=INR&tn=Invoice%20{inv_num}"
    qr_flowable = make_qr_image(upi_str, size_mm=23.0)

    # A. Tax Invoice Header
    header_left = [
        Paragraph(COMPANY_NAME, styles['title']),
        Paragraph(f"{COMPANY_ADDRESS}", styles['subtitle']),
        Paragraph(f"<b>GSTIN:</b> {COMPANY_GSTIN} | <b>PAN:</b> {COMPANY_PAN} | <b>State:</b> {COMPANY_STATE}", styles['subtitle']),
    ]
    header_right = [
        Paragraph("<b>TAX INVOICE</b>", ParagraphStyle('InvTitle', parent=styles['cell_bold'], fontSize=13, leading=15, alignment=2, textColor=ACCENT_COLOR)),
        Paragraph(f"<b>Invoice #:</b> {inv_num}", ParagraphStyle('InvNum', parent=styles['cell_bold'], fontSize=9.5, leading=12, alignment=2)),
        Paragraph(f"<b>Invoice Date:</b> {_format_date(inv_date, '%d/%m/%Y')}", ParagraphStyle('InvD', parent=styles['cell_small'], alignment=2)),
        Paragraph(f"<b>Place of Supply:</b> {pos}", ParagraphStyle('InvPos', parent=styles['cell_small'], alignment=2)),
        Paragraph(f"<b>Reverse Charge:</b> {'YES' if is_rcm else 'NO'}", ParagraphStyle('InvRcm', parent=styles['cell_small'], alignment=2)),
    ]
    h_table = Table([[header_left, header_right, qr_flowable]], colWidths=[108 * mm, 52 * mm, 26 * mm])
    h_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(h_table)
    story.append(HRFlowable(width="100%", thickness=1.5, color=PRIMARY_COLOR, spaceAfter=8, spaceBefore=4))

    # B. Billed To / Recipient Details Table
    party = trip.party if trip else (invoice.party if invoice else None)
    client_name = party.name if party else (invoice.recipient_legal_name if invoice else "Direct Customer")
    client_gst = party.gstin if (party and hasattr(party, 'gstin') and party.gstin) else (invoice.recipient_gstin if (invoice and invoice.recipient_gstin) else "URP (Unregistered)")
    client_addr = party.address if (party and hasattr(party, 'address') and party.address) else (invoice.recipient_address if (invoice and invoice.recipient_address) else "Tamil Nadu, India")
    client_phone = party.phone if (party and party.phone) else "N/A"

    recipient_table = [
        [
            Paragraph("<b>BILLED TO (RECIPIENT):</b>", styles['cell_bold']),
            Paragraph("<b>TRANSPORT SERVICE DETAILS:</b>", styles['cell_bold']),
        ],
        [
            Paragraph(f"<b>{client_name}</b><br/>{client_addr}<br/><b>GSTIN:</b> {client_gst}<br/><b>Contact:</b> {client_phone}", styles['cell_reg']),
            Paragraph(
                f"<b>Trip Reference:</b> #{trip.trip_id if trip else 'N/A'}<br/>"
                f"<b>Route:</b> {trip.booking.pickup_location if (trip and trip.booking) else 'Coimbatore'} ➡️ {trip.booking.destination if (trip and trip.booking) else 'Destination'}<br/>"
                f"<b>Vehicle:</b> {trip.vehicle.registration_number if (trip and trip.vehicle) else 'Private AC Fleet'}<br/>"
                f"<b>Travel Dates:</b> {_format_date(trip.start_date, '%d/%m/%Y') if trip else 'N/A'} to {_format_date(trip.end_date, '%d/%m/%Y') if trip else 'N/A'}",
                styles['cell_reg']
            )
        ]
    ]
    t_rec = Table(recipient_table, colWidths=[93 * mm, 93 * mm])
    t_rec.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), BG_LIGHT),
        ('BOX', (0, 0), (-1, -1), 0.8, BORDER_COLOR),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(t_rec)
    story.append(Spacer(1, 6 * mm))

    # C. HSN/SAC Line Items Table
    line_items = [
        [
            Paragraph("<b>#</b>", styles['cell_bold']),
            Paragraph("<b>Description of Services</b>", styles['cell_bold']),
            Paragraph("<b>SAC Code</b>", styles['cell_bold']),
            Paragraph("<b>Qty / Unit</b>", styles['cell_bold']),
            Paragraph("<b>Rate (₹)</b>", styles['cell_bold']),
            Paragraph("<b>Taxable Value (₹)</b>", styles['cell_bold']),
        ]
    ]

    # Item 1: Transport Services
    v_type_str = trip.vehicle.vehicle_type.name if (trip and trip.vehicle and trip.vehicle.vehicle_type) else "Commercial Vehicle"
    desc_str = f"Passenger Transport Services - {v_type_str} Rental"
    days_cnt = trip.days_count if (trip and trip.days_count) else 1
    line_items.append([
        Paragraph("1", styles['cell_reg']),
        Paragraph(f"{desc_str}<br/><font size='7' color='#64748b'>Outstation passenger transport including vehicle &amp; fuel</font>", styles['cell_reg']),
        Paragraph("996412", styles['cell_reg']),
        Paragraph(f"{days_cnt} Days", styles['cell_reg']),
        Paragraph(f"{(taxable_value / Decimal(str(days_cnt))):,.2f}", styles['cell_reg']),
        Paragraph(f"{taxable_value:,.2f}", styles['cell_bold']),
    ])

    t_lines = Table(line_items, colWidths=[10 * mm, 80 * mm, 24 * mm, 24 * mm, 24 * mm, 24 * mm])
    t_lines.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), BG_HEADER),
        ('BOX', (0, 0), (-1, -1), 0.8, BORDER_COLOR),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
    ]))
    story.append(t_lines)
    story.append(Spacer(1, 4 * mm))

    # D. Tax Summary Computation Block
    tax_summary_data = [
        [Paragraph("Taxable Subtotal:", styles['cell_bold']), Paragraph(f"₹ {taxable_value:,.2f}", styles['cell_bold'])],
        [Paragraph("CGST @ 2.50%:", styles['cell_reg']), Paragraph(f"₹ {cgst_amt:,.2f}", styles['cell_reg'])],
        [Paragraph("SGST @ 2.50%:", styles['cell_reg']), Paragraph(f"₹ {sgst_amt:,.2f}", styles['cell_reg'])],
    ]
    if igst_amt > 0:
        tax_summary_data.append([Paragraph("IGST @ 5.00%:", styles['cell_reg']), Paragraph(f"₹ {igst_amt:,.2f}", styles['cell_reg'])])

    tax_summary_data.append([
        Paragraph("<b>GRAND TOTAL (INCL. GST):</b>", ParagraphStyle('BTotal', parent=styles['cell_bold'], fontSize=10, textColor=PRIMARY_COLOR)),
        Paragraph(f"<b>₹ {grand_total:,.2f}</b>", ParagraphStyle('BTotalVal', parent=styles['cell_bold'], fontSize=10, textColor=ACCENT_COLOR, alignment=2)),
    ])

    t_tax = Table(tax_summary_data, colWidths=[50 * mm, 36 * mm])
    t_tax.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.8, BORDER_COLOR),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e0f2fe')),
        ('TOPPADDING', (0, 0), (-1, -1), 3.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3.5),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
    ]))

    # Combine Bank Details and Tax Box side-by-side
    bank_details = [
        Paragraph("<b>BANK &amp; WIRE TRANSFER DETAILS:</b>", styles['cell_bold']),
        Paragraph("<b>Bank Name:</b> HDFC Bank Ltd.<br/><b>Account Name:</b> Sivagayathiri Tours and Travels<br/><b>A/C Number:</b> 50200012345678<br/><b>IFSC Code:</b> HDFC0001234 (Branch: Gandhipuram)<br/><b>UPI VPA:</b> sivagayathiritravels@okaxis", styles['cell_small']),
        Spacer(1, 2 * mm),
        Paragraph(f"<b>Amount in Words:</b><br/><i>{amount_in_words_inr(grand_total)}</i>", styles['cell_small']),
    ]
    t_combined = Table([[bank_details, t_tax]], colWidths=[100 * mm, 86 * mm])
    t_combined.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(t_combined)
    story.append(Spacer(1, 8 * mm))

    # E. Declaration & Signature
    decl_data = [
        [
            Paragraph(
                "<b>DECLARATION:</b> We declare that this invoice shows the actual price of the services described "
                "and that all particulars are true and correct. Subject to Coimbatore Jurisdiction.",
                styles['cell_small']
            ),
            Paragraph(
                f"For <b>{COMPANY_NAME}</b><br/><br/><br/><br/><b>Authorized Signatory</b>",
                ParagraphStyle('SigAuth', parent=styles['cell_small'], alignment=2)
            ),
        ]
    ]
    t_decl = Table(decl_data, colWidths=[116 * mm, 70 * mm])
    t_decl.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(KeepTogether(t_decl))

    doc.build(story, canvasmaker=PDFNumberedCanvas)
    buf.seek(0)
    return buf.getvalue()


# ==============================================================================
# 3. TOUR BOOKING CONFIRMATION VOUCHER PDF
# ==============================================================================
def render_booking_voucher_pdf(booking: Booking) -> bytes:
    """
    Renders an official Customer Tour Booking Confirmation Voucher PDF.
    Complete with hotel allotment, itinerary highlights, package inclusions,
    and 24/7 concierge contact info.
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=14 * mm,
        bottomMargin=16 * mm
    )
    styles = _build_styles()
    story = []

    # Verification QR Code
    qr_data = f"https://sivagayathiritravels.com/customer-portal/bookings/{booking.id}/"
    qr_flowable = make_qr_image(qr_data, size_mm=22.0)

    # A. Voucher Header
    pkg_name = booking.package.name if booking.package else "Custom Curated Holiday Expedition"
    header_left = [
        Paragraph(COMPANY_NAME, styles['title']),
        Paragraph("Holiday Packages • Fixed Departures • Pilgrimage &amp; Honeymoon Tours", styles['subtitle']),
        Paragraph(f"{COMPANY_ADDRESS} • {COMPANY_CONTACT}", styles['subtitle']),
    ]
    header_right = [
        Paragraph("<b>BOOKING VOUCHER</b>", ParagraphStyle('VTitle', parent=styles['cell_bold'], fontSize=12, leading=14, alignment=2, textColor=SUCCESS_COLOR)),
        Paragraph(f"<b>Booking Ref:</b> #{booking.booking_number}", ParagraphStyle('VRef', parent=styles['cell_bold'], fontSize=9.5, leading=11, alignment=2)),
        Paragraph(f"<b>Status:</b> CONFIRMED", ParagraphStyle('VSt', parent=styles['cell_bold'], fontSize=8.5, leading=10, alignment=2, textColor=SUCCESS_COLOR)),
        Paragraph(f"<b>Booked On:</b> {_format_date(booking.booking_date, '%d/%m/%Y')}", ParagraphStyle('VDt', parent=styles['cell_small'], alignment=2)),
    ]
    h_table = Table([[header_left, header_right, qr_flowable]], colWidths=[108 * mm, 52 * mm, 26 * mm])
    h_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(h_table)
    story.append(HRFlowable(width="100%", thickness=1.5, color=PRIMARY_COLOR, spaceAfter=8, spaceBefore=4))

    # B. Guest & Package Details Table
    drop_date_str = _format_date(booking.drop_date, '%d %b %Y', default='Flexible')
    guest_meta = [
        [
            Paragraph("<b>Primary Traveler:</b>", styles['cell_bold']),
            Paragraph(f"<b>{booking.guest_name}</b> (📞 {booking.guest_phone or 'N/A'})", styles['cell_reg']),
            Paragraph("<b>Travelers Count:</b>", styles['cell_bold']),
            Paragraph(f"<b>{booking.pax_count or 1} Guest(s)</b>", styles['cell_reg']),
        ],
        [
            Paragraph("<b>Tour Package:</b>", styles['cell_bold']),
            Paragraph(f"<b>{pkg_name}</b>", styles['cell_reg']),
            Paragraph("<b>Destination:</b>", styles['cell_bold']),
            Paragraph(booking.destination or "Scenic South India", styles['cell_reg']),
        ],
        [
            Paragraph("<b>Departure Date:</b>", styles['cell_bold']),
            Paragraph(f"{_format_date(booking.pickup_date, '%d %b %Y')} @ {_format_time(booking.pickup_time)}", styles['cell_reg']),
            Paragraph("<b>Return Date:</b>", styles['cell_bold']),
            Paragraph(drop_date_str, styles['cell_reg']),
        ],
        [
            Paragraph("<b>Pickup Address:</b>", styles['cell_bold']),
            Paragraph(booking.pickup_location, styles['cell_reg']),
            Paragraph("<b>Vehicle Category:</b>", styles['cell_bold']),
            Paragraph(str(booking.vehicle_type.name if booking.vehicle_type else 'Private AC Fleet'), styles['cell_reg']),
        ]
    ]
    t_guest = Table(guest_meta, colWidths=[38 * mm, 55 * mm, 38 * mm, 55 * mm])
    t_guest.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), BG_LIGHT),
        ('BOX', (0, 0), (-1, -1), 0.8, BORDER_COLOR),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('TOPPADDING', (0, 0), (-1, -1), 4.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4.5),
    ]))
    story.append(t_guest)
    story.append(Spacer(1, 6 * mm))

    # C. Package Inclusions & Exclusions Grid
    story.append(Paragraph("<b>TOUR INCLUSIONS &amp; EXCLUSIONS SUMMARY</b>", styles['h2']))
    inc_exc_data = [
        [
            Paragraph("<b>Included in Package</b>", styles['cell_bold']),
            Paragraph("<b>Excluded / Direct Expense</b>", styles['cell_bold']),
        ],
        [
            Paragraph(
                "• Dedicated private sanitized AC tourist vehicle<br/>"
                "• Driver daily bata, night halts &amp; highway tolls<br/>"
                "• All inter-state permits &amp; parking fees<br/>"
                "• Fuel charges for the entire scheduled itinerary<br/>"
                "• 24/7 dedicated operational tele-support",
                styles['cell_reg']
            ),
            Paragraph(
                "• Monument / temple entrance &amp; safari tickets<br/>"
                "• Personal laundry, beverages &amp; room service<br/>"
                "• Guide fees (unless explicitly booked)<br/>"
                "• Camera / drone charges at attractions<br/>"
                "• Any detours beyond scheduled itinerary",
                styles['cell_reg']
            )
        ]
    ]
    t_inc = Table(inc_exc_data, colWidths=[93 * mm, 93 * mm])
    t_inc.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), BG_HEADER),
        ('BOX', (0, 0), (-1, -1), 0.8, BORDER_COLOR),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(t_inc)
    story.append(Spacer(1, 6 * mm))

    # D. Financials / Advance Receipt Card
    quoted = booking.quoted_price or Decimal('0.00')
    advance = Decimal(str(booking.advance_received or 0))
    balance = max(Decimal('0.00'), quoted - advance)

    fin_data = [
        [
            Paragraph(f"<b>Package Price:</b> ₹ {quoted:,.2f}", styles['cell_reg']),
            Paragraph(f"<b>Advance Received:</b> <font color='{SUCCESS_COLOR.hexval()}'><b>₹ {advance:,.2f}</b></font>", styles['cell_reg']),
            Paragraph(f"<b>Balance Payable on Arrival:</b> <b>₹ {balance:,.2f}</b>", styles['cell_bold']),
        ]
    ]
    t_fin = Table(fin_data, colWidths=[62 * mm, 62 * mm, 62 * mm])
    t_fin.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#e0f2fe')),
        ('BOX', (0, 0), (-1, -1), 1.0, ACCENT_COLOR),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#bae6fd')),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ]))
    story.append(t_fin)
    story.append(Spacer(1, 6 * mm))

    # E. Important Guidelines & Support
    guideline_text = (
        "<b>TRAVELER NOTICE:</b> Please carry valid Government ID proofs (Aadhaar / Voter ID / Passport) "
        "for hotel check-ins and forest checkposts. Vehicle allocation details (Vehicle plate & Chauffeur mobile) "
        "will be dispatched via WhatsApp 12 hours prior to journey reporting time.<br/>"
        "<b>24x7 Support Helpline:</b> +91 98765 43210 | WhatsApp: +91 98765 43211"
    )
    t_guide = Table([[Paragraph(guideline_text, styles['cell_small'])]], colWidths=[186 * mm])
    t_guide.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), BG_LIGHT),
        ('BOX', (0, 0), (-1, -1), 0.8, BORDER_COLOR),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(KeepTogether(t_guide))

    doc.build(story, canvasmaker=PDFNumberedCanvas)
    buf.seek(0)
    return buf.getvalue()
