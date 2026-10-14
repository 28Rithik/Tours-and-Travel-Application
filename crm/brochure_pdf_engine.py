"""
Sivagayathiri TravelERP - Luxury Tour Proposal & Itinerary Brochure PDF Generator
===================================================================================
Generates high-aesthetic, multi-page branded PDF brochures for holiday proposals,
featuring:
  1. Royal Sivagayathiri letterhead with corporate branding & 24x7 control room helpline.
  2. Elegant trip hero snapshot with traveler profile & dedicated vehicle allocation.
  3. Day-by-day visual itinerary with morning/afternoon/evening schedule, hotel star
     ratings, meal plans (CP/MAP/AP), and included excursions.
  4. 3-Tier package pricing comparison table (Comfort vs. Premium Deluxe vs. Royal Luxury)
     to dramatically accelerate quotation-to-booking conversions.
  5. Transparent Inclusions vs. Exclusions matrix.
  6. Dynamic NPCI UPI QR code for instant advance token booking & bank NEFT coordinates.
  7. Terms, transparent cancellation milestones, and digital executive signature.
  8. Sub-5ms in-memory PDF caching tier.
"""

import io
import os
import time
import hashlib
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, Union, Dict, Any, List

from django.conf import settings
from django.utils import timezone
import qrcode

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether, PageBreak, HRFlowable
)
from reportlab.pdfgen.canvas import Canvas

# ==============================================================================
# CORPORATE BRANDING CONSTANTS
# ==============================================================================
COMPANY_NAME = "SIVAGAYATHIRI TOURS AND TRAVELS"
COMPANY_TAGLINE = "Bespoke Holiday Expeditions • Premium Chauffeur Fleet • Corporate DMC"
COMPANY_HQ = "123 Main Road, Gandhipuram, Coimbatore, Tamil Nadu - 641012"
COMPANY_CONTACT = "Helpline: +91 98425 33777 | +91 422 2490000 | Email: holidays@sivagayathiritravels.com"
COMPANY_GSTIN = "33AABCS1234F1Z8"
COMPANY_BANK_NAME = "Axis Bank Ltd"
COMPANY_BANK_BRANCH = "Gandhipuram Branch, Coimbatore"
COMPANY_BANK_AC_NO = "921020054321098"
COMPANY_BANK_IFSC = "UTIB0000123"
COMPANY_UPI_VPA = "sivagayathiritravels@okaxis"

# Palette
PRIMARY_TEAL = colors.HexColor('#0d5c58')     # Deep Emerald Teal
SECONDARY_NAVY = colors.HexColor('#0f172a')   # Deep Slate Navy
ACCENT_GOLD = colors.HexColor('#d97706')      # Regal Amber Gold
ACCENT_LIGHT_GOLD = colors.HexColor('#fef3c7')
BORDER_COLOR = colors.HexColor('#cbd5e1')     # Light Slate Border
BG_LIGHT = colors.HexColor('#f8fafc')         # Soft Off-White
BG_MINT = colors.HexColor('#f0fdf4')          # Soft Mint Green
TEXT_DARK = colors.HexColor('#0f172a')
TEXT_MUTED = colors.HexColor('#475569')
SUCCESS_GREEN = colors.HexColor('#059669')
DANGER_RED = colors.HexColor('#dc2626')

# In-Memory PDF Binary Cache (Sub-5ms hot-hits)
_PDF_CACHE: Dict[str, bytes] = {}
_PDF_CACHE_MAX_ENTRIES = 250


# ==============================================================================
# TWO-PASS NUMBERED CANVAS (Page X of Y with luxury top banner)
# ==============================================================================
class LuxuryBrochureCanvas(Canvas):
    """
    Two-pass ReportLab Canvas that computes total pages dynamically
    and draws running luxury headers and footers on every page.
    """
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
            self.draw_running_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_running_decorations(self, total_pages: int):
        self.saveState()
        page_num = self._pageNumber

        # Running Header on page 2 and later
        if page_num > 1:
            self.setStrokeColor(PRIMARY_TEAL)
            self.setLineWidth(1.2)
            self.line(14 * mm, 285 * mm, 196 * mm, 285 * mm)

            self.setStrokeColor(ACCENT_GOLD)
            self.setLineWidth(0.8)
            self.line(14 * mm, 284.2 * mm, 60 * mm, 284.2 * mm)

            self.setFont('Helvetica-Bold', 7.5)
            self.setFillColor(PRIMARY_TEAL)
            self.drawString(14 * mm, 287 * mm, COMPANY_NAME)

            self.setFont('Helvetica', 7.5)
            self.setFillColor(TEXT_MUTED)
            self.drawRightString(196 * mm, 287 * mm, "Luxury Holiday Proposal • Confidential")

        # Running Footer on all pages
        self.setStrokeColor(BORDER_COLOR)
        self.setLineWidth(0.6)
        self.line(14 * mm, 12 * mm, 196 * mm, 12 * mm)

        self.setFont('Helvetica', 7.5)
        self.setFillColor(TEXT_MUTED)
        self.drawString(
            14 * mm, 8.5 * mm,
            f"24x7 Guest Operations Hotline: +91 98425 33777 • GSTIN: {COMPANY_GSTIN} • Powered by Sivagayathiri TravelERP"
        )
        page_str = f"Page {page_num} of {total_pages}"
        self.drawRightString(196 * mm, 8.5 * mm, page_str)

        self.restoreState()


# ==============================================================================
# HELPER UTILITIES
# ==============================================================================
def generate_upi_qr_image(vpa: str, payee_name: str, amount: Union[Decimal, float, int], note: str, size_mm: float = 30.0) -> Image:
    """Generates a dynamic NPCI-compliant UPI QR code flowable Image."""
    amount_str = f"{float(amount):.2f}"
    import urllib.parse
    clean_vpa = vpa.strip()
    clean_name = payee_name.strip()
    clean_note = note.strip()
    upi_payload = f"upi://pay?pa={clean_vpa}&pn={urllib.parse.quote_plus(clean_name)}&am={amount_str}&cu=INR&tn={urllib.parse.quote_plus(clean_note)}"

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=1,
    )
    qr.add_data(upi_payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return Image(buf, width=size_mm * mm, height=size_mm * mm)


def get_curated_destination_itinerary(destination: str, duration_days: int) -> List[Dict[str, Any]]:
    """
    Returns rich, day-by-day destination itinerary schedules when no explicit
    QuotationDay instances are populated.
    """
    dest_lower = (destination or '').lower()
    days = max(1, duration_days)

    if 'ooty' in dest_lower or 'nilgiris' in dest_lower:
        base_days = [
            {
                'title': 'Arrival in Ooty, Pine Forest Transit & Botanical Enchantment',
                'morning': 'Private executive pickup, scenic Kallar ghat ascent with hairpin views, arrival in Ooty & smooth resort check-in.',
                'afternoon': 'Visit the Government Botanical Gardens (55-acre heritage garden) & Government Rose Garden featuring 20,000+ varieties.',
                'evening': 'Sunset at serene Ooty Lake with private boat cruise. Relaxing campfire and gourmet dinner at the resort.',
                'hotel': 'Sterling Ooty Elk Hill / Savoy IHCL SeleQtions',
                'star': '⭐⭐⭐⭐ 4-Star Scenic Hill Resort',
                'meal_plan': 'MAP Plan (Breakfast & Dinner Included)',
                'room_type': 'Deluxe Valley View Cottage',
                'overnight': 'Ooty'
            },
            {
                'title': 'Tea Plantations, Doddabetta Peak & Pykara Waterfalls',
                'morning': 'Drive to Doddabetta Peak (highest vantage in Nilgiris at 2,637m) for panoramic valley views, followed by Tea Museum tour.',
                'afternoon': 'Excursion to Pykara Waterfalls and pristine Pykara Lake with high-speed speedboat safari.',
                'evening': 'Stroll through the local Tibetan Market for homemade chocolates, eucalyptus oils, and spices. Warm bonfire night.',
                'hotel': 'Sterling Ooty Elk Hill / Savoy IHCL SeleQtions',
                'star': '⭐⭐⭐⭐ 4-Star Scenic Hill Resort',
                'meal_plan': 'MAP Plan (Breakfast & Dinner Included)',
                'room_type': 'Deluxe Valley View Cottage',
                'overnight': 'Ooty'
            },
            {
                'title': 'Coonoor Excursion, Sim’s Park & Heritage Toy Train',
                'morning': 'Board the UNESCO World Heritage Nilgiri Mountain Railway (Toy Train) to Coonoor through scenic tunnels.',
                'afternoon': 'Visit Sim’s Park botanical conservatory, Dolphin’s Nose viewpoint, and Lamb’s Rock overlooking Coimbatore plains.',
                'evening': 'Tea tasting session at Highfield Tea Factory. Return to Ooty resort for celebratory dinner.',
                'hotel': 'Sterling Ooty Elk Hill / Savoy IHCL SeleQtions',
                'star': '⭐⭐⭐⭐ 4-Star Scenic Hill Resort',
                'meal_plan': 'MAP Plan (Breakfast & Dinner Included)',
                'room_type': 'Deluxe Valley View Cottage',
                'overnight': 'Ooty'
            },
            {
                'title': 'Avalanche Lake, Emerald Dam & Pleasant Departure',
                'morning': 'Scenic drive through Emerald Lake valley to Avalanche Forest Reserve with pristine trout streams.',
                'afternoon': 'Souvenir shopping and leisurely lunch. Leisurely downhill drive via Mettupalayam.',
                'evening': 'Transfer to Coimbatore Airport / Railway Station with wonderful memories.',
                'hotel': 'Transit Departure',
                'star': 'Executive Mobility Service',
                'meal_plan': 'CP Plan (Breakfast Included)',
                'room_type': 'Day Tour / Chauffeur Standby',
                'overnight': 'Departure'
            }
        ]
    elif 'kodaikanal' in dest_lower or 'kodai' in dest_lower:
        base_days = [
            {
                'title': 'Arrival in Kodaikanal, Silver Cascade & Star Lake Walk',
                'morning': 'Chauffeur pickup, scenic ghat transit via Silver Cascade Falls, arrival at Kodaikanal hill resort & check-in.',
                'afternoon': 'Visit Bryant Park floral gardens and stroll along Coaker’s Walk mountain promenade with deep valley drop-offs.',
                'evening': 'Pedal boating in star-shaped Kodaikanal Lake and cycling around the lake perimeter. Resort dinner.',
                'hotel': 'The Carlton Kodaikanal / Sterling Kodai Lake',
                'star': '⭐⭐⭐⭐ 4-Star Lakefront Resort',
                'meal_plan': 'MAP Plan (Breakfast & Dinner Included)',
                'room_type': 'Deluxe Lake View Suite',
                'overnight': 'Kodaikanal'
            },
            {
                'title': 'Pillar Rocks, Guna Caves & Misty Pine Forests',
                'morning': 'Exploration of majestic 400-foot Pillar Rocks, Devil’s Kitchen (Guna Caves), and Moir Point.',
                'afternoon': 'Walk through the towering Korean Pine Forests and discover peaceful Green Valley View.',
                'evening': 'Visit Kurinji Andavar Temple and local artisan shops for spices and organic honey. Campfire at resort.',
                'hotel': 'The Carlton Kodaikanal / Sterling Kodai Lake',
                'star': '⭐⭐⭐⭐ 4-Star Lakefront Resort',
                'meal_plan': 'MAP Plan (Breakfast & Dinner Included)',
                'room_type': 'Deluxe Lake View Suite',
                'overnight': 'Kodaikanal'
            },
            {
                'title': 'Berijam Lake Forest Safari, Dolphin’s Nose & Farewell',
                'morning': 'Exclusive forest jeep safari to tranquil Berijam Lake sanctuary nestled deep in the shola woods.',
                'afternoon': 'Trek to Dolphin’s Nose flat rock cliff projecting over 6,600ft precipice. Traditional hill lunch.',
                'evening': 'Scenic downhill drive and transfer to Madurai / Coimbatore for onward journey.',
                'hotel': 'Transit Departure',
                'star': 'Executive Mobility Service',
                'meal_plan': 'CP Plan (Breakfast Included)',
                'room_type': 'Day Tour / Chauffeur Standby',
                'overnight': 'Departure'
            }
        ]
    elif 'munnar' in dest_lower or 'kerala' in dest_lower:
        base_days = [
            {
                'title': 'Misty Munnar Tea Hills, Valara Falls & Resort Relaxation',
                'morning': 'Chauffeur drive through lush Western Ghats, stopping at Cheeyappara and Valara Waterfalls. Arrival in Munnar.',
                'afternoon': 'Visit KDHP Tea Museum and witness live orthodox tea manufacturing with artisanal tasting.',
                'evening': 'Relaxing evening amidst cloud-kissed rolling tea carpets. Kerala spice dinner at the resort.',
                'hotel': 'Fragrant Nature Munnar / Blanket Hotel & Spa',
                'star': '⭐⭐⭐⭐ 4-Star Luxury Tea Resort',
                'meal_plan': 'MAP Plan (Breakfast & Dinner Included)',
                'room_type': 'Plantation View Premium Room',
                'overnight': 'Munnar'
            },
            {
                'title': 'Eravikulam National Park, Mattupetty Dam & Echo Point',
                'morning': 'Safari drive to Eravikulam National Park to spot the rare endangered Nilgiri Tahr and view Anamudi Peak.',
                'afternoon': 'Visit Mattupetty Dam reservoir with optional speed boating, followed by Echo Point and Kundala Lake.',
                'evening': 'Traditional Kathakali and Kalaripayattu martial arts cultural performance. Bonfire night.',
                'hotel': 'Fragrant Nature Munnar / Blanket Hotel & Spa',
                'star': '⭐⭐⭐⭐ 4-Star Luxury Tea Resort',
                'meal_plan': 'MAP Plan (Breakfast & Dinner Included)',
                'room_type': 'Plantation View Premium Room',
                'overnight': 'Munnar'
            },
            {
                'title': 'Top Station Cloud Walk & Scenic Alleppey Houseboat / Return',
                'morning': 'Sunrise drive to Top Station (boundary of Kerala-Tamil Nadu) offering breathtaking Western Ghat vistas.',
                'afternoon': 'Descent to Cochin / Alleppey for relaxing backwater cruise or Cochin airport departure.',
                'evening': 'Warm send-off by your dedicated Sivagayathiri travel executive.',
                'hotel': 'Transit Departure',
                'star': 'Executive Mobility Service',
                'meal_plan': 'CP Plan (Breakfast Included)',
                'room_type': 'Day Tour / Chauffeur Standby',
                'overnight': 'Departure'
            }
        ]
    else:
        # Universal Circuit
        base_days = [
            {
                'title': f'Departure & Scenic Journey to {destination.title()}',
                'morning': 'Sanitized luxury vehicle pickup from your residence, highway transit with curated refreshment halts.',
                'afternoon': f'Arrival in {destination.title()}, seamless VIP check-in, leisure rest after journey.',
                'evening': 'Local orientation drive, vibrant city market tour, and multi-cuisine dinner.',
                'hotel': f'Premium Star Hotel & Resort, {destination.title()}',
                'star': '⭐⭐⭐⭐ 4-Star Superior Hotel',
                'meal_plan': 'MAP Plan (Breakfast & Dinner Included)',
                'room_type': 'Executive Deluxe Room',
                'overnight': destination.title()
            },
            {
                'title': f'Full Day Heritage, Culture & Sightseeing in {destination.title()}',
                'morning': 'Lavish buffet breakfast, departure for flagship monuments, temples, and natural viewpoints.',
                'afternoon': 'Curated culinary experience followed by leisurely exploration of key tourist attractions.',
                'evening': 'Sunset spectacle, relaxing cultural activity, and dinner under the stars.',
                'hotel': f'Premium Star Hotel & Resort, {destination.title()}',
                'star': '⭐⭐⭐⭐ 4-Star Superior Hotel',
                'meal_plan': 'MAP Plan (Breakfast & Dinner Included)',
                'room_type': 'Executive Deluxe Room',
                'overnight': destination.title()
            },
            {
                'title': f'Final Excursions & Return Journey',
                'morning': 'Morning sightseeing, souvenir shopping for authentic regional handicrafts and delicacies.',
                'afternoon': 'Check-out from hotel and comfortable return drive with dedicated chauffeur.',
                'evening': 'Safe drop at home/airport with unforgettable travel memories.',
                'hotel': 'Transit Departure',
                'star': 'Executive Mobility Service',
                'meal_plan': 'CP Plan (Breakfast Included)',
                'room_type': 'Day Tour / Chauffeur Standby',
                'overnight': 'Departure'
            }
        ]

    # Adjust to requested duration
    result = []
    for i in range(days):
        if i < len(base_days):
            day_item = base_days[i].copy()
        else:
            day_item = {
                'title': f'Day {i+1}: Extended Sightseeing & Leisure in {destination.title()}',
                'morning': 'Morning breakfast, offbeat nature walks, and photography stops.',
                'afternoon': 'Leisurely lunch, optional adventure activities, and relaxation.',
                'evening': 'Resort recreation and celebratory farewell dinner.',
                'hotel': f'Premium Star Hotel & Resort, {destination.title()}',
                'star': '⭐⭐⭐⭐ 4-Star Superior Hotel',
                'meal_plan': 'MAP Plan (Breakfast & Dinner Included)',
                'room_type': 'Executive Deluxe Room',
                'overnight': destination.title()
            }
        result.append(day_item)
    return result


# ==============================================================================
# LUXURY BROCHURE GENERATOR ENGINE CLASS
# ==============================================================================
class LuxuryTourBrochurePDFEngine:
    """
    Enterprise-grade ReportLab Platypus PDF generator that turns any
    Quotation, Inquiry, or Package into a stunning multi-page brochure.
    """

    @classmethod
    def generate_brochure_pdf(
        cls,
        quotation: Any = None,
        inquiry: Any = None,
        package: Any = None,
        force_refresh: bool = False
    ) -> bytes:
        """
        Generates and returns PDF binary bytes.
        Uses in-memory cache for ultra-fast sub-5ms responses.
        """
        # 1. Compute Cache Key
        cache_key = cls._compute_cache_key(quotation, inquiry, package)
        if not force_refresh and cache_key in _PDF_CACHE:
            return _PDF_CACHE[cache_key]

        # 2. Extract Normalized Data
        data = cls._normalize_proposal_data(quotation, inquiry, package)

        # 3. Build ReportLab Platypus Story
        buf = io.BytesIO()
        doc = SimpleDocTemplate(
            buf,
            pagesize=A4,
            leftMargin=14 * mm,
            rightMargin=14 * mm,
            topMargin=16 * mm,
            bottomMargin=16 * mm,
        )

        styles = cls._build_typography_styles()
        story = []

        # Page 1: Hero & Proposal Snapshot
        cls._build_cover_header(story, styles, data)
        cls._build_trip_snapshot_card(story, styles, data)
        cls._build_welcome_narrative(story, styles, data)
        cls._build_tiered_pricing_table(story, styles, data)

        story.append(PageBreak())

        # Page 2+: Day-by-Day Visual Itinerary Flow
        cls._build_itinerary_section(story, styles, data)

        # Page End: Inclusions, UPI Advance QR, Terms & Signatures
        cls._build_inclusions_exclusions_matrix(story, styles, data)
        cls._build_booking_payment_section(story, styles, data)
        cls._build_terms_and_signature_block(story, styles, data)

        # 4. Render Document via Numbered Canvas
        doc.build(story, canvasmaker=LuxuryBrochureCanvas)
        pdf_bytes = buf.getvalue()
        buf.close()

        # 5. Store in Hot Cache
        if len(_PDF_CACHE) >= _PDF_CACHE_MAX_ENTRIES:
            # Evict oldest entry
            _PDF_CACHE.pop(next(iter(_PDF_CACHE)))
        _PDF_CACHE[cache_key] = pdf_bytes

        return pdf_bytes

    @classmethod
    def _compute_cache_key(cls, quotation: Any, inquiry: Any, package: Any) -> str:
        if quotation:
            upd = getattr(quotation, 'updated_at', None) or timezone.now()
            raw = f"quotation:{quotation.id}:{upd.isoformat()}:{getattr(quotation, 'total_quoted_price', 0)}"
        elif inquiry:
            upd = getattr(inquiry, 'created_at', None) or timezone.now()
            raw = f"inquiry:{inquiry.id}:{upd.isoformat()}:{getattr(inquiry, 'quoted_price', 0)}"
        elif package:
            upd = getattr(package, 'created_at', None) or timezone.now()
            raw = f"package:{package.id}:{upd.isoformat()}:{getattr(package, 'price_with_food', 0)}"
        else:
            raw = f"generic:{time.time()}"
        return hashlib.sha256(raw.encode('utf-8')).hexdigest()

    @classmethod
    def _normalize_proposal_data(cls, quotation: Any, inquiry: Any, package: Any) -> Dict[str, Any]:
        """Unifies Quotation, Inquiry, or Package into a standard data dictionary."""
        today = timezone.now().date()
        ref_number = "PROPOSAL-2026-001"
        guest_name = "Distinguished Traveler"
        guest_phone = "+91 98425 33777"
        guest_email = "guest@sivagayathiritravels.com"
        destination = "Ooty, Nilgiris, Tamil Nadu"
        start_date = today
        end_date = today
        pax_count = 2
        vehicle_name = "Toyota Innova Crysta 2.4 ZX (Luxury 7-Seater AC)"
        total_price = Decimal('28500.00')
        inclusions_text = ""
        exclusions_text = ""
        terms_text = ""
        itinerary_days = []
        token = "preview-token"

        if quotation:
            ref_number = quotation.quotation_number or f"QTN-{quotation.id:04d}"
            guest_name = quotation.guest_name or (quotation.party.name if quotation.party else "VIP Guest")
            guest_phone = quotation.guest_phone or (quotation.party.phone if quotation.party else "")
            guest_email = quotation.guest_email or (quotation.party.email if quotation.party else "")
            destination = quotation.destination or "Holiday Expedition"
            start_date = quotation.start_date or today
            end_date = quotation.end_date or today
            pax_count = quotation.pax_count or 2
            if quotation.vehicle_type:
                vehicle_name = str(quotation.vehicle_type)
            total_price = quotation.total_quoted_price or Decimal('25000.00')
            inclusions_text = quotation.inclusions or ""
            exclusions_text = quotation.exclusions or ""
            terms_text = quotation.terms_conditions or ""
            token = getattr(quotation, 'proposal_token', '') or getattr(quotation, 'token', 'preview-token')

            # Fetch days
            days_qs = quotation.days.all().order_by('day_number')
            if days_qs.exists():
                for d in days_qs:
                    hotel_name = d.hotel.name if d.hotel else f"Premium Star Resort, {d.overnight_destination or destination}"
                    star_name = d.hotel.get_star_category_display() if d.hotel else "⭐⭐⭐⭐ 4-Star Resort"
                    itinerary_days.append({
                        'day_number': d.day_number,
                        'title': d.title or f"Day {d.day_number}: Scenic Exploration",
                        'morning': d.description or "Morning private exploration with dedicated chauffeur.",
                        'afternoon': "Afternoon visits to key sightseeing points and relaxed dining.",
                        'evening': "Evening sunset views, local shopping, and warm resort dining.",
                        'hotel': hotel_name,
                        'star': star_name,
                        'meal_plan': f"{d.hotel_meal_plan} Plan" if d.hotel_meal_plan else "MAP Plan (Breakfast & Dinner)",
                        'room_type': getattr(d.hotel, 'room_type', 'Deluxe Valley Room') if d.hotel else 'Deluxe Valley Room',
                        'overnight': d.overnight_destination or destination
                    })

        elif inquiry:
            ref_number = inquiry.inquiry_number or f"INQ-{inquiry.id:04d}"
            guest_name = inquiry.guest_name or (inquiry.party.name if inquiry.party else "VIP Guest")
            guest_phone = inquiry.guest_phone or ""
            guest_email = inquiry.guest_email or ""
            destination = inquiry.destination or dict(inquiry.POPULAR_DESTINATIONS).get(inquiry.destination_dropdown, "Holiday Expedition")
            start_date = inquiry.pickup_date or today
            end_date = inquiry.drop_date or today
            pax_count = (inquiry.adult_count or 2) + (inquiry.child_count or 0)
            if inquiry.vehicle_type:
                vehicle_name = str(inquiry.vehicle_type)
            total_price = inquiry.quoted_price or inquiry.estimated_deal_value or Decimal('25000.00')
            token = inquiry.proposal_token or "inquiry-token"

        elif package:
            ref_number = package.package_code or f"PKG-{package.id:04d}"
            guest_name = "Valued Holiday Group"
            destination = package.destination or "South India Tour Circuit"
            pax_count = package.min_pax or 4
            if package.default_vehicle_type:
                vehicle_name = str(package.default_vehicle_type)
            else:
                vehicle_name = package.vehicle_seating_desc or "Luxury Air-Conditioned Coach"
            per_pax = package.price_with_food or package.base_price or Decimal('5700.00')
            total_price = per_pax * Decimal(str(pax_count))
            inclusions_text = package.inclusions or ""
            exclusions_text = package.exclusions or ""
            terms_text = package.terms_and_conditions or ""

        # Duration
        days_count = max(1, (end_date - start_date).days + 1) if (end_date and start_date) else 3
        nights_count = max(0, days_count - 1)

        # Synthesize itinerary if not already present
        if not itinerary_days:
            raw_itinerary = get_curated_destination_itinerary(destination, days_count)
            for idx, d in enumerate(raw_itinerary, 1):
                d['day_number'] = idx
                itinerary_days.append(d)

        # 3-Tier Prices
        deluxe_total = total_price
        standard_total = getattr(quotation, 'tier_standard_price', None) or round(total_price * Decimal('0.85'), 2)
        luxury_total = getattr(quotation, 'tier_luxury_price', None) or round(total_price * Decimal('1.38'), 2)

        standard_per_pax = round(standard_total / Decimal(str(pax_count)), 2)
        deluxe_per_pax = round(deluxe_total / Decimal(str(pax_count)), 2)
        luxury_per_pax = round(luxury_total / Decimal(str(pax_count)), 2)

        # Advance Token
        advance_token = min(Decimal('5000.00'), max(Decimal('2000.00'), round(deluxe_total * Decimal('0.20'), 2)))

        return {
            'ref_number': ref_number,
            'guest_name': guest_name,
            'guest_phone': guest_phone,
            'guest_email': guest_email,
            'destination': destination,
            'start_date': start_date,
            'end_date': end_date,
            'days_count': days_count,
            'nights_count': nights_count,
            'pax_count': pax_count,
            'vehicle_name': vehicle_name,
            'deluxe_total': deluxe_total,
            'standard_total': standard_total,
            'luxury_total': luxury_total,
            'deluxe_per_pax': deluxe_per_pax,
            'standard_per_pax': standard_per_pax,
            'luxury_per_pax': luxury_per_pax,
            'advance_token': advance_token,
            'itinerary_days': itinerary_days,
            'inclusions_text': inclusions_text,
            'exclusions_text': exclusions_text,
            'terms_text': terms_text,
            'token': token,
        }

    # ==========================================================================
    # TYPOGRAPHY STYLES BUILDER
    # ==========================================================================
    @classmethod
    def _build_typography_styles(cls) -> Dict[str, ParagraphStyle]:
        styles = getSampleStyleSheet()

        custom_styles = {
            'DocTitle': ParagraphStyle(
                'DocTitle',
                parent=styles['Normal'],
                fontName='Helvetica-Bold',
                fontSize=20,
                leading=24,
                textColor=PRIMARY_TEAL,
            ),
            'DocSubtitle': ParagraphStyle(
                'DocSubtitle',
                parent=styles['Normal'],
                fontName='Helvetica',
                fontSize=9.5,
                leading=13,
                textColor=TEXT_MUTED,
            ),
            'BadgeText': ParagraphStyle(
                'BadgeText',
                parent=styles['Normal'],
                fontName='Helvetica-Bold',
                fontSize=8,
                leading=10,
                textColor=ACCENT_GOLD,
                alignment=1,
            ),
            'HeroTourTitle': ParagraphStyle(
                'HeroTourTitle',
                parent=styles['Normal'],
                fontName='Helvetica-Bold',
                fontSize=14,
                leading=18,
                textColor=SECONDARY_NAVY,
            ),
            'SectionHeader': ParagraphStyle(
                'SectionHeader',
                parent=styles['Normal'],
                fontName='Helvetica-Bold',
                fontSize=12,
                leading=16,
                textColor=PRIMARY_TEAL,
                spaceBefore=6,
                spaceAfter=4,
            ),
            'BodyRegular': ParagraphStyle(
                'BodyRegular',
                parent=styles['Normal'],
                fontName='Helvetica',
                fontSize=8.5,
                leading=12,
                textColor=TEXT_DARK,
            ),
            'BodyMuted': ParagraphStyle(
                'BodyMuted',
                parent=styles['Normal'],
                fontName='Helvetica',
                fontSize=8,
                leading=11,
                textColor=TEXT_MUTED,
            ),
            'DayHeaderTitle': ParagraphStyle(
                'DayHeaderTitle',
                parent=styles['Normal'],
                fontName='Helvetica-Bold',
                fontSize=9.5,
                leading=13,
                textColor=colors.white,
            ),
            'ScheduleLabel': ParagraphStyle(
                'ScheduleLabel',
                parent=styles['Normal'],
                fontName='Helvetica-Bold',
                fontSize=8,
                leading=11,
                textColor=PRIMARY_TEAL,
            ),
            'TableHead': ParagraphStyle(
                'TableHead',
                parent=styles['Normal'],
                fontName='Helvetica-Bold',
                fontSize=8.5,
                leading=11,
                textColor=colors.white,
                alignment=1,
            ),
            'TableCell': ParagraphStyle(
                'TableCell',
                parent=styles['Normal'],
                fontName='Helvetica',
                fontSize=8,
                leading=11,
                textColor=TEXT_DARK,
            ),
            'TableCellBold': ParagraphStyle(
                'TableCellBold',
                parent=styles['Normal'],
                fontName='Helvetica-Bold',
                fontSize=8,
                leading=11,
                textColor=TEXT_DARK,
            ),
            'TableCellCenter': ParagraphStyle(
                'TableCellCenter',
                parent=styles['Normal'],
                fontName='Helvetica',
                fontSize=8,
                leading=11,
                textColor=TEXT_DARK,
                alignment=1,
            ),
            'CalloutTitle': ParagraphStyle(
                'CalloutTitle',
                parent=styles['Normal'],
                fontName='Helvetica-Bold',
                fontSize=10,
                leading=13,
                textColor=PRIMARY_TEAL,
            ),
            'InclusionItem': ParagraphStyle(
                'InclusionItem',
                parent=styles['Normal'],
                fontName='Helvetica',
                fontSize=7.5,
                leading=10.5,
                textColor=colors.HexColor('#065f46'),
            ),
            'ExclusionItem': ParagraphStyle(
                'ExclusionItem',
                parent=styles['Normal'],
                fontName='Helvetica',
                fontSize=7.5,
                leading=10.5,
                textColor=colors.HexColor('#991b1b'),
            ),
        }
        return custom_styles

    # ==========================================================================
    # PAGE 1: COVER HEADER
    # ==========================================================================
    @classmethod
    def _build_cover_header(cls, story: list, styles: dict, data: dict):
        # Top Header Brand Grid
        header_data = [
            [
                Paragraph(f"<b>{COMPANY_NAME}</b>", styles['DocTitle']),
                Paragraph(
                    f"<b>PROPOSAL REF:</b> {data['ref_number']}<br/>"
                    f"<b>DATE:</b> {timezone.now().strftime('%d %b %Y')}<br/>"
                    f"<b>VALIDITY:</b> 15 Days",
                    styles['BodyMuted']
                )
            ],
            [
                Paragraph(COMPANY_TAGLINE, styles['DocSubtitle']),
                Paragraph(f"<b>HQ:</b> Coimbatore, Tamil Nadu", styles['BodyMuted'])
            ]
        ]
        t = Table(header_data, colWidths=[120 * mm, 62 * mm])
        t.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
        ]))
        story.append(t)

        # Teal + Gold divider bar
        story.append(Spacer(1, 3 * mm))
        story.append(HRFlowable(width="100%", thickness=2.5, color=PRIMARY_TEAL, spaceBefore=0, spaceAfter=1))
        story.append(HRFlowable(width="100%", thickness=1, color=ACCENT_GOLD, spaceBefore=0, spaceAfter=4 * mm))

    # ==========================================================================
    # PAGE 1: TRIP SNAPSHOT CARD
    # ==========================================================================
    @classmethod
    def _build_trip_snapshot_card(cls, story: list, styles: dict, data: dict):
        dest_title = data['destination'].upper()
        days_n = f"{data['days_count']} DAYS / {data['nights_count']} NIGHTS"
        tour_headline = f"{days_n} EXCLUSIVE {dest_title} EXPEDITION"

        card_data = [
            [
                Paragraph(f"<font color='#d97706'>★ BESPOKE LUXURY HOLIDAY PROPOSAL ★</font>", styles['BadgeText']),
                ""
            ],
            [
                Paragraph(f"<b>{tour_headline}</b>", styles['HeroTourTitle']),
                ""
            ],
            [
                Paragraph(
                    f"<b>Prepared For:</b> {data['guest_name']}<br/>"
                    f"<b>Contact:</b> {data['guest_phone'] or 'Confidential'}<br/>"
                    f"<b>Email:</b> {data['guest_email'] or 'On File'}",
                    styles['BodyRegular']
                ),
                Paragraph(
                    f"<b>Duration:</b> {data['days_count']} Days & {data['nights_count']} Nights<br/>"
                    f"<b>Travel Dates:</b> {data['start_date'].strftime('%d %b %Y')} to {data['end_date'].strftime('%d %b %Y')}<br/>"
                    f"<b>Party Size:</b> {data['pax_count']} Guests (Private Tour)",
                    styles['BodyRegular']
                )
            ],
            [
                Paragraph(
                    f"<b>Dedicated Chauffeur Vehicle:</b><br/>"
                    f"<font color='#0d5c58'><b>{data['vehicle_name']}</b></font><br/>"
                    f"<font color='#64748b' size=7.5>Includes Fuel, Hill Permits, Interstate Tolls & Driver Batta</font>",
                    styles['BodyRegular']
                ),
                Paragraph(
                    f"<b>Holiday Coordinator:</b><br/>"
                    f"<b>Senior Chauffeur & Travel Specialist</b><br/>"
                    f"<font color='#64748b' size=7.5>Direct Dispatch Escalation: +91 98425 33777</font>",
                    styles['BodyRegular']
                )
            ]
        ]

        t = Table(card_data, colWidths=[91 * mm, 91 * mm])
        t.setStyle(TableStyle([
            ('SPAN', (0, 0), (1, 0)),
            ('SPAN', (0, 1), (1, 1)),
            ('BACKGROUND', (0, 0), (-1, -1), BG_LIGHT),
            ('BOX', (0, 0), (-1, -1), 1, BORDER_COLOR),
            ('LINEBELOW', (0, 1), (-1, 1), 0.8, colors.HexColor('#e2e8f0')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ]))
        story.append(t)
        story.append(Spacer(1, 4 * mm))

    # ==========================================================================
    # PAGE 1: WELCOME NARRATIVE
    # ==========================================================================
    @classmethod
    def _build_welcome_narrative(cls, story: list, styles: dict, data: dict):
        welcome_html = (
            f"Dear <b>{data['guest_name']}</b>,<br/>"
            f"Thank you for choosing <b>{COMPANY_NAME}</b> for your upcoming expedition to <b>{data['destination']}</b>. "
            f"We have curated this comprehensive travel proposal tailored specifically to your preferences. "
            f"Your journey features guaranteed sanitized private AC mobility, dedicated hill-certified chauffeurs with 10+ years experience, "
            f"handpicked premium resort accommodations, and full concierge support throughout. "
            f"Please review our tiered holiday plans below to select the experience that best suits your requirements."
        )
        p = Paragraph(welcome_html, styles['BodyRegular'])
        story.append(p)
        story.append(Spacer(1, 4 * mm))

    # ==========================================================================
    # PAGE 1: TIERED PRICING COMPARISON TABLE (SALES CLOSER)
    # ==========================================================================
    @classmethod
    def _build_tiered_pricing_table(cls, story: list, styles: dict, data: dict):
        story.append(Paragraph("<b>SELECT YOUR HOLIDAY TIER (3-TIER COMPARISON)</b>", styles['SectionHeader']))

        headers = [
            Paragraph("<b>Plan Features</b>", styles['TableHead']),
            Paragraph("<b>Tier 1: Comfort</b>", styles['TableHead']),
            Paragraph("<b>Tier 2: Deluxe ★</b><br/><font size=7>(Recommended)</font>", styles['TableHead']),
            Paragraph("<b>Tier 3: Royal Luxury</b>", styles['TableHead']),
        ]

        rows = [
            headers,
            [
                Paragraph("<b>Vehicle Allocation</b>", styles['TableCellBold']),
                Paragraph("Sedan (Swift Dzire / Etios AC)", styles['TableCellCenter']),
                Paragraph("<b>Innova Crysta 2.4 ZX Luxury</b>", styles['TableCellCenter']),
                Paragraph("Force Urbania Executive / Benz", styles['TableCellCenter']),
            ],
            [
                Paragraph("<b>Hotel Category</b>", styles['TableCellBold']),
                Paragraph("3-Star Premium Hotel", styles['TableCellCenter']),
                Paragraph("<b>4-Star Scenic Hill Resort</b>", styles['TableCellCenter']),
                Paragraph("5-Star Heritage Palace / Villa", styles['TableCellCenter']),
            ],
            [
                Paragraph("<b>Meal Inclusions</b>", styles['TableCellBold']),
                Paragraph("CP Plan (Breakfast Only)", styles['TableCellCenter']),
                Paragraph("<b>MAP Plan (Breakfast + Dinner)</b>", styles['TableCellCenter']),
                Paragraph("AP Plan (All Meals Included)", styles['TableCellCenter']),
            ],
            [
                Paragraph("<b>Activities & Perks</b>", styles['TableCellBold']),
                Paragraph("Standard Sightseeing", styles['TableCellCenter']),
                Paragraph("<b>Campfire + Boating + Tea Tour</b>", styles['TableCellCenter']),
                Paragraph("Private Guide + Spa Voucher", styles['TableCellCenter']),
            ],
            [
                Paragraph("<b>Per Person Rate</b>", styles['TableCellBold']),
                Paragraph(f"₹{data['standard_per_pax']:,.2f}", styles['TableCellCenter']),
                Paragraph(f"<font color='#0d5c58'><b>₹{data['deluxe_per_pax']:,.2f}</b></font>", styles['TableCellCenter']),
                Paragraph(f"₹{data['luxury_per_pax']:,.2f}", styles['TableCellCenter']),
            ],
            [
                Paragraph("<b>Total Package Cost</b><br/><font size=6.5 color='#64748b'>(All Inclusive)</font>", styles['TableCellBold']),
                Paragraph(f"₹{data['standard_total']:,.2f}", styles['TableCellCenter']),
                Paragraph(f"<font color='#0d5c58' size=10><b>₹{data['deluxe_total']:,.2f}</b></font>", styles['TableCellCenter']),
                Paragraph(f"₹{data['luxury_total']:,.2f}", styles['TableCellCenter']),
            ]
        ]

        t = Table(rows, colWidths=[42 * mm, 46 * mm, 48 * mm, 46 * mm])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), PRIMARY_TEAL),
            ('BACKGROUND', (2, 0), (2, -1), colors.HexColor('#f0fdf4')),  # Highlight Tier 2 Deluxe
            ('BACKGROUND', (2, 0), (2, 0), colors.HexColor('#0b4f4c')),   # Darker Header for Tier 2
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ('BOX', (0, 0), (-1, -1), 1, PRIMARY_TEAL),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(t)
        story.append(Spacer(1, 2 * mm))

        callout_html = (
            "<font size=7.5 color='#0d5c58'><b>★ Travel Specialist Recommendation:</b> "
            "Our <b>Tier 2 Deluxe Package</b> is our highest-rated customer selection, combining generous Innova Crysta seating room, "
            "complimentary gourmet breakfast and dinner, and hill-resort balcony rooms with scenic panoramic vistas.</font>"
        )
        story.append(Paragraph(callout_html, styles['BodyRegular']))
        story.append(Spacer(1, 4 * mm))

    # ==========================================================================
    # PAGE 2+: DAY-BY-DAY VISUAL ITINERARY FLOW
    # ==========================================================================
    @classmethod
    def _build_itinerary_section(cls, story: list, styles: dict, data: dict):
        story.append(Paragraph("<b>DETAILED DAY-BY-DAY EXPEDITION ITINERARY</b>", styles['SectionHeader']))
        story.append(Paragraph(
            "<font size=8 color='#64748b'>Each day is fully customized to your pace with private vehicle and dedicated chauffeur on standby.</font>",
            styles['BodyRegular']
        ))
        story.append(Spacer(1, 3 * mm))

        for item in data['itinerary_days']:
            day_num = item.get('day_number', 1)
            title = item.get('title', 'Scenic Excursion')
            morning = item.get('morning', '')
            afternoon = item.get('afternoon', '')
            evening = item.get('evening', '')
            hotel = item.get('hotel', 'Selected Resort')
            star = item.get('star', '⭐⭐⭐⭐ 4-Star')
            meal_plan = item.get('meal_plan', 'MAP Plan')
            room_type = item.get('room_type', 'Deluxe Room')
            overnight = item.get('overnight', data['destination'])

            # Day Header
            header_table = Table(
                [[
                    Paragraph(f"<b>DAY {day_num:02d} • {title.upper()}</b>", styles['DayHeaderTitle']),
                    Paragraph(f"<font color='#fef3c7' size=8><b>Overnight: {overnight}</b></font>", styles['BadgeText'])
                ]],
                colWidths=[132 * mm, 50 * mm]
            )
            header_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), PRIMARY_TEAL),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ]))

            # Day Schedule & Stays Body
            body_rows = [
                [
                    Paragraph("<b>🌅 Morning</b>", styles['ScheduleLabel']),
                    Paragraph(morning, styles['BodyRegular']),
                ],
                [
                    Paragraph("<b>☀️ Afternoon</b>", styles['ScheduleLabel']),
                    Paragraph(afternoon, styles['BodyRegular']),
                ],
                [
                    Paragraph("<b>🌙 Evening</b>", styles['ScheduleLabel']),
                    Paragraph(evening, styles['BodyRegular']),
                ],
                [
                    Paragraph("<b>🏨 Stay & Food</b>", styles['ScheduleLabel']),
                    Paragraph(
                        f"<b>{hotel}</b> ({star})<br/>"
                        f"<b>Room:</b> {room_type} • <b>Plan:</b> <font color='#0d5c58'><b>{meal_plan}</b></font>",
                        styles['BodyRegular']
                    ),
                ]
            ]

            body_table = Table(body_rows, colWidths=[28 * mm, 154 * mm])
            body_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), BG_LIGHT),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LINEBELOW', (0, 0), (-1, -2), 0.5, colors.HexColor('#e2e8f0')),
                ('BOX', (0, 0), (-1, -1), 0.8, BORDER_COLOR),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ]))

            story.append(KeepTogether([
                header_table,
                body_table,
                Spacer(1, 3.5 * mm)
            ]))

    # ==========================================================================
    # INCLUSIONS & EXCLUSIONS MATRIX
    # ==========================================================================
    @classmethod
    def _build_inclusions_exclusions_matrix(cls, story: list, styles: dict, data: dict):
        story.append(Spacer(1, 2 * mm))
        story.append(Paragraph("<b>TRANSPARENT INCLUSIONS & EXCLUSIONS</b>", styles['SectionHeader']))

        inc_items = [
            "✓ Dedicated sanitized AC vehicle allocation throughout the entire tour itinerary.",
            "✓ Professional, uniform-clad chauffeur with verified 10+ years hill-route experience.",
            "✓ All vehicle fuel costs, inter-state boundary entry permits, and hill station parking charges.",
            "✓ All highway Fastag electronic tolls and driver daily overnight Bata/allowances included.",
            "✓ Handpicked resort accommodations on twin-sharing basis with verified hygiene scores.",
            "✓ Daily gourmet meals as designated in the selected holiday plan (CP / MAP / AP).",
            "✓ 24x7 real-time operations control room escort and emergency SOS telemetry standby."
        ]
        if data['inclusions_text']:
            custom_inc = [line.strip() for line in data['inclusions_text'].split('\n') if line.strip()]
            if len(custom_inc) > 2:
                inc_items = [f"✓ {c.lstrip('•-✓ ')}" for c in custom_inc]

        exc_items = [
            "✗ Airfare or express railway tickets from your home originating city.",
            "✗ Personal incidental expenses (room service, telephone, laundry, minibar).",
            "✗ Meals or beverages not explicitly designated under the selected hotel meal plan.",
            "✗ Any optional adventure water sports, camera permits, or personal tips to guides.",
            "✗ Expenses arising from natural calamities, road blockades, or unforeseen transit delays."
        ]
        if data['exclusions_text']:
            custom_exc = [line.strip() for line in data['exclusions_text'].split('\n') if line.strip()]
            if len(custom_exc) > 2:
                exc_items = [f"✗ {c.lstrip('•-✗ ')}" for c in custom_exc]

        inc_html = "<br/>".join([f"<font color='#065f46'>{i}</font>" for i in inc_items])
        exc_html = "<br/>".join([f"<font color='#991b1b'>{e}</font>" for e in exc_items])

        matrix_data = [
            [
                Paragraph("<b>✓ What Is Included (100% Hassle-Free)</b>", styles['TableHead']),
                Paragraph("<b>✗ What Is Excluded (Transparent)</b>", styles['TableHead'])
            ],
            [
                Paragraph(inc_html, styles['InclusionItem']),
                Paragraph(exc_html, styles['ExclusionItem'])
            ]
        ]

        t = Table(matrix_data, colWidths=[91 * mm, 91 * mm])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, 0), colors.HexColor('#065f46')),
            ('BACKGROUND', (1, 0), (1, 0), colors.HexColor('#991b1b')),
            ('BACKGROUND', (0, 1), (0, 1), BG_MINT),
            ('BACKGROUND', (1, 1), (1, 1), colors.HexColor('#fffbfa')),
            ('GRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(t)
        story.append(Spacer(1, 4 * mm))

    # ==========================================================================
    # INSTANT UPI ADVANCE PAYMENT & BANK DETAILS
    # ==========================================================================
    @classmethod
    def _build_booking_payment_section(cls, story: list, styles: dict, data: dict):
        adv_val = data['advance_token']
        note_str = f"Advance Deposit {data['ref_number']}"

        # Generate QR
        qr_flowable = generate_upi_qr_image(
            vpa=COMPANY_UPI_VPA,
            payee_name=COMPANY_NAME,
            amount=adv_val,
            note=note_str,
            size_mm=28.0
        )

        payment_content = [
            Paragraph(f"<b>LOCK IN YOUR VEHICLE & CHAUFFEUR WITH AN ADVANCE TOKEN</b>", styles['CalloutTitle']),
            Spacer(1, 1.5 * mm),
            Paragraph(
                f"You can confirm your booking instantly by transferring an advance token of "
                f"<font color='#0d5c58'><b>₹{adv_val:,.2f}</b></font>.<br/>"
                f"The remainder is payable conveniently upon arrival directly to your assigned chauffeur.",
                styles['BodyRegular']
            ),
            Spacer(1, 2 * mm),
            Paragraph(
                f"<b>Official Bank Account Details (NEFT / RTGS / IMPS):</b><br/>"
                f"• Beneficiary Name: <b>{COMPANY_NAME}</b><br/>"
                f"• Current Account Number: <b>{COMPANY_BANK_AC_NO}</b><br/>"
                f"• Bank & Branch: <b>{COMPANY_BANK_NAME}, {COMPANY_BANK_BRANCH}</b><br/>"
                f"• IFSC Code: <b>{COMPANY_BANK_IFSC}</b>",
                styles['BodyRegular']
            )
        ]

        qr_col = [
            qr_flowable,
            Spacer(1, 1 * mm),
            Paragraph(f"<font size=6.5 color='#64748b'><b>Scan to Pay ₹{adv_val:,.2f}</b><br/>GPay • PhonePe • Paytm</font>", styles['BadgeText'])
        ]

        t = Table(
            [[payment_content, qr_col]],
            colWidths=[140 * mm, 42 * mm]
        )
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#0d5c58')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (1, 0), (1, 0), 'CENTER'),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ]))

        story.append(KeepTogether([
            t,
            Spacer(1, 4 * mm)
        ]))

    # ==========================================================================
    # TERMS & CONDITIONS + SIGNATURE BLOCK
    # ==========================================================================
    @classmethod
    def _build_terms_and_signature_block(cls, story: list, styles: dict, data: dict):
        terms_html = (
            "<b>Terms & Cancellation Milestones:</b><br/>"
            "• <b>Confirmation:</b> 20% advance token secures vehicle allotment. Balance payable on boarding.<br/>"
            "• <b>Cancellation:</b> 100% refund for cancellations >15 days prior to travel; 50% refund 7-14 days prior; non-refundable within 7 days.<br/>"
            "• <b>Ghat Road Safety:</b> Night driving on high-gradient hill routes (Ooty/Kodaikanal) adheres to regional Nilgiris police safety regulations."
        )
        p_terms = Paragraph(terms_html, styles['BodyMuted'])

        sig_data = [
            [
                Paragraph(
                    f"<b>For {COMPANY_NAME}</b><br/>"
                    f"<font color='#0d5c58'><b>Authorized Chauffeur & Tour Operations Desk</b></font><br/>"
                    f"<font size=7 color='#64748b'>Digitally Certified Proposal • Coimbatore Hub</font>",
                    styles['BodyRegular']
                ),
                Paragraph(
                    f"<b>Client Acknowledgment & Acceptance</b><br/>"
                    f"<font color='#64748b'>Signature: __________________________</font><br/>"
                    f"<font size=7 color='#64748b'>Guest: {data['guest_name']}</font>",
                    styles['BodyRegular']
                )
            ]
        ]
        t_sig = Table(sig_data, colWidths=[91 * mm, 91 * mm])
        t_sig.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LINEABOVE', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))

        story.append(KeepTogether([
            p_terms,
            Spacer(1, 4 * mm),
            t_sig
        ]))
