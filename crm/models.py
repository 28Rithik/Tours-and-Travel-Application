import datetime
import secrets
from decimal import Decimal
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

from core.models import Party, Client, Supplier, VehicleType
from operations.models import Booking


# ==============================================================================
# 1. ENHANCED INQUIRY (LEAD & QUERY TRACKER 2.0)
# ==============================================================================

class Inquiry(models.Model):
    STATUS_CHOICES = [
        ('new', 'New Lead'),
        ('in_progress', 'Under Review'),
        ('quoted', 'Quotation Sent'),
        ('negotiating', 'Negotiating'),
        ('won', 'Won (Converted)'),
        ('lost', 'Lost'),
    ]
    PRIORITY_CHOICES = [
        ('low', '🟢 Low Priority'),
        ('medium', '🟡 Medium Priority'),
        ('high', '🟠 High Priority'),
        ('urgent', '🔴 Urgent / VIP'),
    ]
    SOURCE_CHOICES = [
        ('website', '🌐 Website Inquiry Form'),
        ('whatsapp', '💬 WhatsApp Message'),
        ('phone', '📞 Direct Phone Call'),
        ('agent_referral', '🤝 B2B / FTO Agent Referral'),
        ('walk_in', '🏢 Walk-in Front Desk'),
        ('email', '✉️ Corporate Email'),
    ]
    JOURNEY_TYPES = Booking.JOURNEY_TYPES

    inquiry_number = models.CharField(max_length=30, unique=True, blank=True)
    party = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='inquiries')
    guest_name = models.CharField(max_length=255)
    guest_phone = models.CharField(max_length=30, blank=True)
    guest_email = models.EmailField(blank=True)

    pickup_location = models.CharField(max_length=255)
    destination = models.CharField(max_length=255)
    pickup_date = models.DateField()
    pickup_time = models.TimeField()
    drop_date = models.DateField(null=True, blank=True)

    journey_type = models.CharField(max_length=20, choices=JOURNEY_TYPES, default='outstation')
    vehicle_type = models.ForeignKey('core.VehicleType', on_delete=models.PROTECT, null=True, blank=True)
    adult_count = models.PositiveIntegerField(default=2)
    child_count = models.PositiveIntegerField(default=0)
    special_requirements = models.TextField(blank=True)

    # Lead Tracking & SLA TAT
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    source = models.CharField(max_length=30, choices=SOURCE_CHOICES, default='website')
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_inquiries')
    target_tat_hours = models.PositiveIntegerField(default=24, help_text="Target Turnaround Time in hours")
    tat_deadline = models.DateTimeField(null=True, blank=True)

    estimated_km = models.PositiveIntegerField(null=True, blank=True)
    quoted_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    created_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Inquiry'
        verbose_name_plural = 'Inquiries'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.inquiry_number} - {self.guest_name} ({self.destination})"

    @property
    def is_overdue(self):
        """Returns True if inquiry is not yet closed and has passed its TAT deadline."""
        if self.tat_deadline and self.status in ['new', 'in_progress']:
            return timezone.now() > self.tat_deadline
        return False

    @property
    def tat_remaining_hours(self):
        """Hours left until SLA breach (or negative if already breached)."""
        if not self.tat_deadline:
            return None
        diff = (self.tat_deadline - timezone.now()).total_seconds() / 3600.0
        return round(diff, 1)

    def save(self, *args, **kwargs):
        if not self.inquiry_number:
            last_inquiry = Inquiry.objects.order_by('-id').first()
            next_number = (last_inquiry.id + 1) if last_inquiry else 1
            self.inquiry_number = f'INQ-{next_number:04d}'
        if not self.tat_deadline:
            created_base = self.created_at or timezone.now()
            self.tat_deadline = created_base + datetime.timedelta(hours=self.target_tat_hours)
        super().save(*args, **kwargs)


class InquiryFollowUp(models.Model):
    INTERACTION_CHOICES = [
        ('phone', '📞 Phone Call'),
        ('whatsapp', '💬 WhatsApp Chat'),
        ('email', '✉️ Email Follow-up'),
        ('meeting', '🤝 In-Person Meeting'),
    ]
    inquiry = models.ForeignKey(Inquiry, on_delete=models.CASCADE, related_name='follow_ups')
    scheduled_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    performed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    interaction_type = models.CharField(max_length=20, choices=INTERACTION_CHOICES, default='phone')
    notes = models.TextField(help_text="Discussion points, feedback, and customer reaction")
    next_action = models.CharField(max_length=255, blank=True, help_text="e.g. Send revised quote with 4-star hotel")
    is_done = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-scheduled_at']
        verbose_name = 'Inquiry Follow-up'
        verbose_name_plural = 'Inquiry Follow-ups'

    def __str__(self):
        return f"Follow-up on {self.inquiry.inquiry_number} ({self.get_interaction_type_display()})"


class CustomerPreference(models.Model):
    client = models.OneToOneField(Client, on_delete=models.CASCADE, related_name='preferences')
    preferred_vehicle_type = models.ForeignKey('core.VehicleType', on_delete=models.SET_NULL, null=True, blank=True)
    dietary_requirements = models.TextField(blank=True)
    whatsapp_opt_in = models.BooleanField(default=True)
    email_opt_in = models.BooleanField(default=True)

    def __str__(self):
        return f"Preferences for {self.client.name}"


class CommunicationLog(models.Model):
    TYPES = [('whatsapp', 'WhatsApp'), ('email', 'Email')]
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='communications')
    booking = models.ForeignKey(Booking, on_delete=models.SET_NULL, null=True, blank=True)
    comm_type = models.CharField(max_length=20, choices=TYPES)
    message_content = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default='sent')

    class Meta:
        ordering = ['-sent_at']

    def __str__(self):
        return f"{self.comm_type.upper()} to {self.client.name} at {self.sent_at}"


# ==============================================================================
# 2. TRAVEL MASTER DATA (HOTELS, ENTRANCE, ACTIVITIES, GUIDES)
# ==============================================================================

class HotelMaster(models.Model):
    STAR_CHOICES = [
        ('budget', 'Budget / Standard (2-Star)'),
        ('3_star', '3-Star Premium'),
        ('4_star', '4-Star Superior'),
        ('5_star', '5-Star Luxury'),
        ('heritage', 'Heritage Palace / Boutique'),
        ('resort', 'Scenic Hill Resort / Villa'),
    ]
    name = models.CharField(max_length=255)
    destination = models.CharField(max_length=100, db_index=True, help_text="e.g. Ooty, Munnar, Kodaikanal")
    star_category = models.CharField(max_length=30, choices=STAR_CHOICES, default='3_star')
    room_type = models.CharField(max_length=100, default='Deluxe Room')
    
    # Standard Season Base Rates
    ep_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Room Only (EP)")
    cp_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Bed & Breakfast (CP)")
    map_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Breakfast + Dinner (MAP)")
    ap_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="All Meals (AP)")
    extra_bed_rate = models.DecimalField(max_digits=10, decimal_places=2, default=800)
    peak_surge_percent = models.DecimalField(max_digits=5, decimal_places=2, default=20.00, help_text="Seasonal surge % (May, Dec)")

    contact_phone = models.CharField(max_length=50, blank=True)
    contact_email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['destination', 'name']
        verbose_name = 'Hotel Master & Tariff Sheet'
        verbose_name_plural = 'Hotel Master & Tariff Sheets'

    def __str__(self):
        return f"{self.name} ({self.destination}) - {self.get_star_category_display()}"


class MonumentEntranceMaster(models.Model):
    name = models.CharField(max_length=255, help_text="e.g. Botanical Gardens, Rose Garden, Pykara Falls")
    destination = models.CharField(max_length=100, db_index=True)
    domestic_adult_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    domestic_child_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    foreigner_adult_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    foreigner_child_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    camera_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    operating_hours = models.CharField(max_length=100, default='09:00 AM - 05:30 PM')
    closed_days = models.CharField(max_length=100, blank=True, help_text="e.g. Closed on Tuesdays")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['destination', 'name']
        verbose_name = 'Monument & Entrance Ticket Master'
        verbose_name_plural = 'Monument & Entrance Ticket Masters'

    def __str__(self):
        return f"{self.name} ({self.destination}) - Adult: ₹{self.domestic_adult_rate}"


class ActivityMaster(models.Model):
    PRICING_TYPES = [
        ('per_person', 'Per Person'),
        ('per_boat_vehicle', 'Per Boat / Vehicle'),
        ('fixed_group', 'Fixed Group Contract'),
    ]
    name = models.CharField(max_length=255, help_text="e.g. Ooty Lake Boating, Mudumalai Safari, Tea Factory Tour")
    destination = models.CharField(max_length=100, db_index=True)
    pricing_type = models.CharField(max_length=30, choices=PRICING_TYPES, default='per_person')
    standard_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    duration_minutes = models.PositiveIntegerField(default=60)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['destination', 'name']
        verbose_name = 'Sightseeing & Activity Master'
        verbose_name_plural = 'Sightseeing & Activity Masters'

    def __str__(self):
        return f"{self.name} ({self.destination}) - ₹{self.standard_rate} ({self.get_pricing_type_display()})"


class GuideChargeMaster(models.Model):
    LANGUAGES = [
        ('english', 'English Speaking Guide'),
        ('hindi', 'Hindi Speaking Guide'),
        ('tamil', 'Tamil Regional Guide'),
        ('french', 'French Speaking Foreign Escort'),
        ('german', 'German Speaking Foreign Escort'),
        ('other', 'Other Regional/Foreign Language'),
    ]
    destination = models.CharField(max_length=100, db_index=True)
    language = models.CharField(max_length=50, choices=LANGUAGES, default='english')
    half_day_rate = models.DecimalField(max_digits=10, decimal_places=2, default=800)
    full_day_rate = models.DecimalField(max_digits=10, decimal_places=2, default=1500)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['destination', 'language']
        verbose_name = 'Guide Charges Master'
        verbose_name_plural = 'Guide Charges Masters'

    def __str__(self):
        return f"{self.get_language_display()} - {self.destination} (Full: ₹{self.full_day_rate})"


# ==============================================================================
# 3. DYNAMIC AD-HOC QUOTATION BUILDER & MARKUP ENGINE
# ==============================================================================

class Quotation(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft (Work in Progress)'),
        ('sent', 'Sent to Client / FTO'),
        ('negotiating', 'Negotiating / Revision Requested'),
        ('accepted', 'Accepted by Customer'),
        ('rejected', 'Declined / Lost'),
        ('converted', 'Converted to Confirmed Booking'),
    ]

    quotation_number = models.CharField(max_length=50, unique=True, blank=True)
    version = models.PositiveIntegerField(default=1)
    parent_quotation = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='revisions')
    inquiry = models.ForeignKey(Inquiry, on_delete=models.SET_NULL, null=True, blank=True, related_name='quotations')
    party = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='quotations')
    
    guest_name = models.CharField(max_length=255)
    guest_phone = models.CharField(max_length=30, blank=True)
    guest_email = models.EmailField(blank=True)
    title = models.CharField(max_length=255, default='Custom Tour Itinerary & Cost Proposal')
    destination = models.CharField(max_length=255)
    start_date = models.DateField()
    end_date = models.DateField()
    pax_count = models.PositiveIntegerField(default=2)
    vehicle_type = models.ForeignKey('core.VehicleType', on_delete=models.SET_NULL, null=True, blank=True)
    vehicle_count = models.PositiveIntegerField(default=1)

    # Cost Breakdown (Computed from Line Items)
    transport_cost = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    accommodation_cost = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    monuments_cost = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    activities_cost = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    guide_cost = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    other_services_cost = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    
    net_cost = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'), help_text="Total Cost to Company (Net Supplier Cost)")
    markup_percent = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('15.00'), help_text="Agency profit margin %")
    markup_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    gross_price = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'), help_text="Net + Markup")
    gst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('5.00'), help_text="GST % on Tour Package (standard 5%)")
    gst_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    total_quoted_price = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'), help_text="Final Client Payable")

    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='draft')
    inclusions = models.TextField(
        default="• Accommodation on twin sharing basis as per selected meal plan\n"
                "• All transfers, excursions, and inter-city drives by dedicated AC vehicle\n"
                "• Professional chauffeur, fuel charges, state permits, toll taxes, and driver night bata\n"
                "• All monument entrance tickets and activities specified in the itinerary\n"
                "• 24x7 control room emergency assistance"
    )
    exclusions = models.TextField(
        default="• Flight / Train tickets to and from originating city\n"
                "• Personal expenses such as laundry, telephone calls, room service, alcoholic beverages\n"
                "• Meals not explicitly listed under the designated hotel meal plan\n"
                "• Any professional camera permits or optional adventure activities"
    )
    terms_conditions = models.TextField(
        default="• 50% advance deposit required upon quotation acceptance to secure hotel rooms\n"
                "• Balance payment due 7 days prior to journey date\n"
                "• Standard cancellation rules apply: 100% refund >15 days, 50% refund 7-14 days, non-refundable <7 days"
    )

    booking = models.OneToOneField(Booking, on_delete=models.SET_NULL, null=True, blank=True, related_name='source_quotation')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_quotations')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Custom Tour Quotation'
        verbose_name_plural = 'Custom Tour Quotations'

    def __str__(self):
        v_str = f" (v{self.version})" if self.version > 1 else ""
        price = self.total_quoted_price or Decimal('0.00')
        return f"{self.quotation_number}{v_str} - {self.guest_name} ({self.destination}) [₹{price:,.2f}]"

    @property
    def duration_days(self):
        if self.start_date and self.end_date:
            return max(1, (self.end_date - self.start_date).days + 1)
        return 1

    @property
    def duration_nights(self):
        return max(0, self.duration_days - 1)

    @property
    def per_pax_price(self):
        if self.pax_count and self.pax_count > 0:
            return round(self.total_quoted_price / Decimal(str(self.pax_count)), 2)
        return self.total_quoted_price

    def recalculate_totals(self):
        """
        Calculates Net Cost from all itemized line items, applies the markup percentage,
        computes GST, and establishes the Final Quoted Price.
        """
        trans = Decimal('0.00')
        hotel = Decimal('0.00')
        monu = Decimal('0.00')
        act = Decimal('0.00')
        guide = Decimal('0.00')
        other = Decimal('0.00')

        for item in self.items.all():
            cat = item.category
            cost = item.total_cost
            if cat == 'transport':
                trans += cost
            elif cat == 'hotel':
                hotel += cost
            elif cat == 'monument':
                monu += cost
            elif cat == 'activity':
                act += cost
            elif cat == 'guide':
                guide += cost
            else:
                other += cost

        self.transport_cost = trans
        self.accommodation_cost = hotel
        self.monuments_cost = monu
        self.activities_cost = act
        self.guide_cost = guide
        self.other_services_cost = other

        self.net_cost = trans + hotel + monu + act + guide + other
        self.markup_amount = round(self.net_cost * (Decimal(str(self.markup_percent)) / Decimal('100.0')), 2)
        self.gross_price = self.net_cost + self.markup_amount
        self.gst_amount = round(self.gross_price * (Decimal(str(self.gst_rate)) / Decimal('100.0')), 2)
        self.total_quoted_price = self.gross_price + self.gst_amount

        self.save(update_fields=[
            'transport_cost', 'accommodation_cost', 'monuments_cost', 'activities_cost',
            'guide_cost', 'other_services_cost', 'net_cost', 'markup_amount',
            'gross_price', 'gst_amount', 'total_quoted_price', 'updated_at'
        ])
        return self.total_quoted_price

    def create_revision(self):
        """
        Generates a new version (e.g. V2, V3) during client price negotiation,
        cloning all day itineraries and itemized line items.
        """
        new_version = self.version + 1
        base_num = self.quotation_number.split('-v')[0]
        new_num = f"{base_num}-v{new_version}"

        new_quote = Quotation.objects.create(
            quotation_number=new_num,
            version=new_version,
            parent_quotation=self.parent_quotation or self,
            inquiry=self.inquiry,
            party=self.party,
            guest_name=self.guest_name,
            guest_phone=self.guest_phone,
            guest_email=self.guest_email,
            title=self.title,
            destination=self.destination,
            start_date=self.start_date,
            end_date=self.end_date,
            pax_count=self.pax_count,
            vehicle_type=self.vehicle_type,
            vehicle_count=self.vehicle_count,
            markup_percent=self.markup_percent,
            gst_rate=self.gst_rate,
            status='draft',
            inclusions=self.inclusions,
            exclusions=self.exclusions,
            terms_conditions=self.terms_conditions,
            created_by=self.created_by
        )

        # Clone Days and Items
        for day in self.days.all():
            new_day = QuotationDay.objects.create(
                quotation=new_quote,
                day_number=day.day_number,
                date=day.date,
                title=day.title,
                description=day.description,
                hotel=day.hotel,
                hotel_meal_plan=day.hotel_meal_plan,
                overnight_destination=day.overnight_destination
            )
            for item in day.items.all():
                QuotationItem.objects.create(
                    quotation=new_quote,
                    day=new_day,
                    category=item.category,
                    item_name=item.item_name,
                    quantity=item.quantity,
                    unit_cost=item.unit_cost,
                    total_cost=item.total_cost
                )

        # Items not linked to specific days
        for item in self.items.filter(day__isnull=True):
            QuotationItem.objects.create(
                quotation=new_quote,
                day=None,
                category=item.category,
                item_name=item.item_name,
                quantity=item.quantity,
                unit_cost=item.unit_cost,
                total_cost=item.total_cost
            )

        new_quote.recalculate_totals()
        return new_quote

    def convert_to_booking(self, user=None):
        """
        1-Click conversion: Converts an accepted quotation into an active
        confirmed Booking in the core operations module.
        """
        if self.booking:
            return self.booking

        default_vtype = self.vehicle_type or VehicleType.objects.first()
        booking = Booking.objects.create(
            party=self.party,
            guest_name=self.guest_name,
            guest_phone=self.guest_phone or self.party.phone or '9876543210',
            pickup_location=f"Arrival ({self.destination})",
            destination=self.destination,
            pickup_date=self.start_date,
            drop_date=self.end_date,
            pickup_time=datetime.time(9, 0),
            journey_type='outstation',
            vehicle_type=default_vtype,
            pax_count=self.pax_count,
            billing_type='package',
            quoted_price=self.total_quoted_price,
            gst_rate=self.gst_rate,
            status='confirmed'
        )

        self.booking = booking
        self.status = 'converted'
        self.save(update_fields=['booking', 'status', 'updated_at'])

        # Update Inquiry status if linked
        if self.inquiry:
            self.inquiry.status = 'won'
            self.inquiry.save(update_fields=['status'])

        return booking

    def save(self, *args, **kwargs):
        if not self.quotation_number:
            year = timezone.now().year
            last_quote = Quotation.objects.order_by('-id').first()
            next_idx = (last_quote.id + 1) if last_quote else 1
            self.quotation_number = f"QTN-{year}-{next_idx:04d}"
        super().save(*args, **kwargs)


class QuotationDay(models.Model):
    MEAL_PLANS = [
        ('EP', 'European Plan (Room Only / EP)'),
        ('CP', 'Continental Plan (Bed & Breakfast / CP)'),
        ('MAP', 'Modified Plan (Breakfast + Dinner / MAP)'),
        ('AP', 'American Plan (All Meals / AP)'),
    ]
    quotation = models.ForeignKey(Quotation, on_delete=models.CASCADE, related_name='days')
    day_number = models.PositiveIntegerField(default=1)
    date = models.DateField(null=True, blank=True)
    title = models.CharField(max_length=255, help_text="e.g. Day 1: Arrival & Sightseeing in Ooty")
    description = models.TextField(help_text="Detailed day-by-day narrative for the client")
    hotel = models.ForeignKey(HotelMaster, on_delete=models.SET_NULL, null=True, blank=True)
    hotel_meal_plan = models.CharField(max_length=10, choices=MEAL_PLANS, default='CP')
    overnight_destination = models.CharField(max_length=100, default='Ooty')

    class Meta:
        ordering = ['day_number']
        unique_together = ('quotation', 'day_number')

    def __str__(self):
        return f"{self.quotation.quotation_number} - Day {self.day_number}: {self.title}"


class QuotationItem(models.Model):
    CATEGORIES = [
        ('transport', '🚗 Transport & Vehicle Hire'),
        ('hotel', '🏨 Hotel Accommodation'),
        ('monument', '🏛️ Monument / Entrance Fee'),
        ('activity', '🚣 Sightseeing & Activity Fee'),
        ('guide', '👤 Professional Guide / Escort'),
        ('other', '✨ Other Ancillary Service'),
    ]
    quotation = models.ForeignKey(Quotation, on_delete=models.CASCADE, related_name='items')
    day = models.ForeignKey(QuotationDay, on_delete=models.CASCADE, null=True, blank=True, related_name='items')
    category = models.CharField(max_length=30, choices=CATEGORIES, default='other')
    item_name = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField(default=1)
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.item_name} ({self.get_category_display()}): ₹{self.total_cost}"

    def save(self, *args, **kwargs):
        self.total_cost = round(Decimal(str(self.unit_cost)) * Decimal(str(self.quantity)), 2)
        super().save(*args, **kwargs)


# ==============================================================================
# 4. FTO, CORPORATE & B2C PARTNER MANAGEMENT (PHASE B)
# ==============================================================================

class PartnerProfile(models.Model):
    """
    Enterprise profile for Foreign Tour Operators (FTOs), Corporate MNCs, and B2B Travel Agencies.
    Tracks credit limits, agent categories, bank accounts, and legal agreements.
    """
    CATEGORY_CHOICES = [
        ('diamond', '💎 Diamond Tier 1 (Volume FTO / Global Inbound)'),
        ('gold', '🥇 Gold Tier 2 (National DMC Partner)'),
        ('silver', '🥈 Silver Tier 3 (Regional Retail Agency)'),
        ('corporate_mnc', '🏢 Corporate MNC (Contracted Business Accounts)'),
        ('b2b_local', '🤝 Local B2B Operator / Freelancer'),
    ]

    party = models.OneToOneField(Party, on_delete=models.CASCADE, related_name='partner_profile')
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default='silver')
    trade_name = models.CharField(max_length=255, blank=True, help_text="Brand or Doing-Business-As name")
    pan_number = models.CharField(max_length=20, blank=True)
    iata_number = models.CharField(max_length=50, blank=True, help_text="IATA / DOT Accreditation Code")
    credit_limit = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'), help_text="Authorized credit exposure limit")
    
    # Bank Information (For commission disbursements & credit adjustments)
    bank_beneficiary_name = models.CharField(max_length=255, blank=True)
    bank_name = models.CharField(max_length=150, blank=True)
    bank_account_number = models.CharField(max_length=60, blank=True)
    bank_ifsc = models.CharField(max_length=25, blank=True)
    bank_branch = models.CharField(max_length=100, blank=True)
    swift_bic = models.CharField(max_length=30, blank=True, help_text="SWIFT/BIC for foreign inward remittances")

    # Business Agreements & Contracts
    agreement_file = models.FileField(upload_to='agreements/partners/', null=True, blank=True, help_text="Signed SLA / corporate contract")
    agreement_valid_from = models.DateField(null=True, blank=True)
    agreement_valid_until = models.DateField(null=True, blank=True)
    contract_notes = models.TextField(blank=True, help_text="Special commission tiers, payment terms, or discounts")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'FTO & Corporate Partner Profile'
        verbose_name_plural = 'FTO & Corporate Partner Profiles'

    def __str__(self):
        return f"{self.party.name} [{self.get_category_display()}]"


class PartyContactPerson(models.Model):
    """
    Multiple contact directory for any Party (FTO, Corporate, Supplier, B2C).
    Allows dedicated contacts for Operations Desk, Accounts, Management, and 24x7 Emergency Escalation.
    """
    CONTACT_TYPES = [
        ('operations', '🛎️ Operations / Booking Desk'),
        ('accounts', '💰 Accounts & Billing'),
        ('management', '👔 Management / Director'),
        ('emergency', '🚨 24x7 Emergency Escalation'),
        ('sales', '📈 Sales & Contracting'),
    ]

    party = models.ForeignKey(Party, on_delete=models.CASCADE, related_name='contact_persons')
    name = models.CharField(max_length=255)
    designation = models.CharField(max_length=100, blank=True)
    contact_type = models.CharField(max_length=30, choices=CONTACT_TYPES, default='operations')
    phone = models.CharField(max_length=30)
    mobile = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    is_primary = models.BooleanField(default=False)

    class Meta:
        ordering = ['-is_primary', 'name']
        verbose_name = 'Contact Person'
        verbose_name_plural = 'Contact Persons Directory'

    def __str__(self):
        return f"{self.name} ({self.get_contact_type_display()}) - {self.party.name}"


class B2CCustomerProfile(models.Model):
    """
    Direct Retail Customer (B2C) Profile with passport credentials, emergency contacts,
    and social media links.
    """
    party = models.OneToOneField(Party, on_delete=models.CASCADE, related_name='b2c_profile')
    full_name = models.CharField(max_length=255)
    alternate_phone = models.CharField(max_length=30, blank=True)
    nationality = models.CharField(max_length=100, default='Indian')
    passport_number = models.CharField(max_length=50, blank=True, help_text="Required for NRI/Foreign tourist reporting")
    passport_expiry = models.DateField(null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    anniversary_date = models.DateField(null=True, blank=True)
    is_vip = models.BooleanField(default=False, help_text="Priority VIP customer flag")

    # Address Details
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    pincode = models.CharField(max_length=20, blank=True)

    # Social Media Links
    facebook_url = models.URLField(blank=True)
    instagram_handle = models.CharField(max_length=100, blank=True)
    linkedin_url = models.URLField(blank=True)
    twitter_handle = models.CharField(max_length=100, blank=True)

    # Bank Information (For security refunds & deposit returns)
    refund_bank_name = models.CharField(max_length=150, blank=True)
    refund_account_no = models.CharField(max_length=60, blank=True)
    refund_ifsc = models.CharField(max_length=25, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['full_name']
        verbose_name = 'B2C Customer Profile'
        verbose_name_plural = 'B2C Customer Profiles'

    def __str__(self):
        vip_tag = " [VIP]" if self.is_vip else ""
        return f"{self.full_name}{vip_tag} ({self.nationality})"


# ==============================================================================
# 5. SUPPLIER MANAGEMENT & CONTRACTED SEASONAL RATES (PHASE B)
# ==============================================================================

class SupplierProfile(models.Model):
    """
    Vendor / Supplier Profile for Hoteliers, Sightseeing Operators, Subcontractor Transporters,
    and Guide Agencies with banking payout details and signed contracts.
    """
    SUPPLIER_TYPES = [
        ('hotelier', '🏨 Hotelier / Resort / Homestay'),
        ('sightseeing', '🚣 Sightseeing / Activity Vendor'),
        ('transporter', '🚗 Subcontractor Transporter / Fleet Vendor'),
        ('guide_agency', '👤 Guide Agency / Escort Services'),
        ('restaurant', '🍽️ Restaurant / Catering Vendor'),
        ('other', '✨ Other Ancillary Supplier'),
    ]

    party = models.OneToOneField(Party, on_delete=models.CASCADE, related_name='supplier_profile')
    supplier_type = models.CharField(max_length=30, choices=SUPPLIER_TYPES, default='hotelier')
    trade_name = models.CharField(max_length=255, blank=True)
    destination_city = models.CharField(max_length=100, help_text="e.g. Ooty, Munnar, Kodaikanal, Madurai")
    pan_number = models.CharField(max_length=20, blank=True)
    gstin = models.CharField(max_length=15, blank=True)

    # Bank Details for Payouts
    bank_beneficiary_name = models.CharField(max_length=255, blank=True)
    bank_name = models.CharField(max_length=150, blank=True)
    bank_account_number = models.CharField(max_length=60, blank=True)
    bank_ifsc = models.CharField(max_length=25, blank=True)
    bank_branch = models.CharField(max_length=100, blank=True)

    # Contract Document
    contract_document = models.FileField(upload_to='agreements/suppliers/', null=True, blank=True)
    contract_valid_from = models.DateField(null=True, blank=True)
    contract_valid_until = models.DateField(null=True, blank=True)
    is_preferred = models.BooleanField(default=False, help_text="Preferred DMC partner flag")

    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def company_name(self):
        return self.trade_name or (self.party.name if self.party else "Unknown Supplier")

    class Meta:
        ordering = ['destination_city', 'party__name']
        verbose_name = 'Supplier Profile & Master'
        verbose_name_plural = 'Supplier Profiles & Masters'

    def __str__(self):
        return f"{self.party.name} ({self.destination_city}) - {self.get_supplier_type_display()}"


class SupplierContractedRate(models.Model):
    """
    Contracted B2B Buy Rates negotiated with suppliers, accounting for seasonality
    (Peak season, regular season, and monsoon off-season).
    """
    SEASON_CHOICES = [
        ('peak', '🔥 Peak Season (Summer & Dec-Jan)'),
        ('regular', '🌤️ Regular Season (Autumn & Spring)'),
        ('offpeak', '🌧️ Off-Season / Monsoon Special'),
    ]
    SERVICE_CATEGORIES = [
        ('hotel_room', '🏨 Hotel Room / Villa'),
        ('activity', '🚣 Sightseeing / Boat / Safari'),
        ('transport', '🚗 Fleet / Vehicle Rental'),
        ('guide', '👤 Tour Escort / Guide Service'),
        ('meal', '🍽️ Buffet / Meal Package'),
        ('other', '✨ Other Service'),
    ]

    supplier = models.ForeignKey(SupplierProfile, on_delete=models.CASCADE, related_name='contracted_rates')
    service_category = models.CharField(max_length=30, choices=SERVICE_CATEGORIES, default='hotel_room')
    service_name = models.CharField(max_length=255, help_text="e.g. Deluxe Garden Room, 2-Hr Motorboat, Tempo 14-Seater")
    room_type = models.CharField(max_length=100, blank=True, help_text="For hotels: Deluxe, Premium, Cottage")
    meal_plan = models.CharField(max_length=10, choices=QuotationDay.MEAL_PLANS, blank=True, default='CP')
    seasonality = models.CharField(max_length=20, choices=SEASON_CHOICES, default='regular')
    
    valid_from = models.DateField(null=True, blank=True)
    valid_to = models.DateField(null=True, blank=True)

    rack_rate = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), help_text="Published public tariff")
    contracted_buy_rate = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), help_text="Special negotiated DMC net rate")
    tax_inclusive = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['supplier', 'seasonality', 'service_name']
        verbose_name = 'Supplier Contracted Rate'
        verbose_name_plural = 'Supplier Contracted Rates'

    def __str__(self):
        return f"{self.supplier.party.name} - {self.service_name} ({self.get_seasonality_display()}): Net ₹{self.contracted_buy_rate}"

    @property
    def savings_percent(self):
        """Calculates margin savings compared to published rack rate."""
        if self.rack_rate and self.rack_rate > self.contracted_buy_rate:
            diff = self.rack_rate - self.contracted_buy_rate
            return round((diff / self.rack_rate) * Decimal('100.0'), 1)
        return Decimal('0.0')


# ==============================================================================
# 6. SERVICE VOUCHERS & PURCHASE ORDERS (PHASE B)
# ==============================================================================

class SupplierServiceVoucher(models.Model):
    """
    Official DMC Service Voucher & Purchase Order (LPO) issued to Hoteliers, Transporters,
    and Sightseeing Vendors for confirmed traveler reservations.
    Includes automated dispatch and token-based confirmation extranet.
    """
    VOUCHER_TYPES = [
        ('hotel_reservation', '🏨 Hotel Accommodation Voucher'),
        ('transport_order', '🚗 Chauffeur Transport Service Order'),
        ('activity_permit', '🚣 Sightseeing & Activity Entry Voucher'),
        ('guide_escort', '👤 Guide / Escort Booking Voucher'),
    ]
    STATUS_CHOICES = [
        ('draft', 'Draft (Work in Progress)'),
        ('issued', 'Issued to Supplier (Pending Confirmation)'),
        ('confirmed', 'Confirmed by Supplier Desk'),
        ('amended', 'Amended / Re-issued'),
        ('cancelled', 'Cancelled / Released'),
    ]

    voucher_number = models.CharField(max_length=50, unique=True, blank=True)
    voucher_type = models.CharField(max_length=30, choices=VOUCHER_TYPES, default='hotel_reservation')
    supplier = models.ForeignKey(SupplierProfile, on_delete=models.CASCADE, related_name='vouchers')
    quotation = models.ForeignKey(Quotation, on_delete=models.SET_NULL, null=True, blank=True, related_name='service_vouchers')
    booking = models.ForeignKey(Booking, on_delete=models.SET_NULL, null=True, blank=True, related_name='service_vouchers')

    # Guest Info
    guest_name = models.CharField(max_length=255)
    guest_phone = models.CharField(max_length=30, blank=True)
    pax_count = models.PositiveIntegerField(default=2)

    # Dates
    service_date_start = models.DateField(help_text="Check-in / Service start date")
    service_date_end = models.DateField(help_text="Check-out / Service end date")
    duration_nights = models.PositiveIntegerField(default=1)

    # Service Specifications
    hotel_room_type = models.CharField(max_length=100, blank=True)
    hotel_meal_plan = models.CharField(max_length=10, blank=True, default='CP')
    room_count = models.PositiveIntegerField(default=1)
    
    vehicle_type_name = models.CharField(max_length=100, blank=True)
    pickup_location = models.CharField(max_length=255, blank=True)
    drop_location = models.CharField(max_length=255, blank=True)
    pickup_time = models.TimeField(null=True, blank=True)

    activity_name = models.CharField(max_length=255, blank=True)
    special_instructions = models.TextField(blank=True, help_text="e.g. Late check-in, honeymoon cake, child cot")

    # Financial / Settlement
    contracted_unit_cost = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total_payable_to_supplier = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    payment_terms = models.CharField(max_length=100, default='Settlement via Direct Bank Transfer as per monthly DMC credit terms')

    # Lifecycle & Confirmation
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    issued_at = models.DateTimeField(null=True, blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    confirmation_reference = models.CharField(max_length=100, blank=True, help_text="Supplier confirmation ID / Reservation code")
    confirmation_token = models.CharField(max_length=64, unique=True, blank=True, help_text="Secret token for supplier extranet confirmation")
    supplier_notes = models.TextField(blank=True, help_text="Notes returned by supplier upon confirmation")

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Supplier Service Voucher & Purchase Order'
        verbose_name_plural = 'Supplier Service Vouchers & Purchase Orders'

    def __str__(self):
        return f"{self.voucher_number} - {self.supplier.party.name} ({self.guest_name}) [{self.get_status_display()}]"

    def save(self, *args, **kwargs):
        if not self.voucher_number:
            year = timezone.now().year
            last_vch = SupplierServiceVoucher.objects.order_by('-id').first()
            next_idx = (last_vch.id + 1) if last_vch else 1
            self.voucher_number = f"VCH-{year}-{next_idx:04d}"
        if not self.confirmation_token:
            self.confirmation_token = secrets.token_urlsafe(24)
        super().save(*args, **kwargs)


# ==============================================================================
# 7. DMC OPERATIONAL TASK MANAGEMENT & TO-DO ENGINE (PHASE C)
# ==============================================================================

class DmcTask(models.Model):
    """
    Enterprise DMC Task Management (To-Do List) for allocating operations,
    sales follow-ups, and booking fulfillment tasks to staff members with priority levels.
    """
    PRIORITY_CHOICES = [
        ('urgent', '🔴 Urgent / Immediate'),
        ('high', '🟠 High Priority'),
        ('medium', '🟡 Medium Priority'),
        ('low', '🟢 Low Priority'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    title = models.CharField(max_length=255, help_text="e.g. Call Kuoni regarding revised Ooty quote")
    description = models.TextField(blank=True)
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_dmc_tasks')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_dmc_tasks')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    due_date = models.DateField(default=timezone.now)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    related_inquiry = models.ForeignKey(Inquiry, on_delete=models.SET_NULL, null=True, blank=True, related_name='tasks')
    related_quotation = models.ForeignKey(Quotation, on_delete=models.SET_NULL, null=True, blank=True, related_name='tasks')
    related_booking = models.ForeignKey(Booking, on_delete=models.SET_NULL, null=True, blank=True, related_name='dmc_tasks')

    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['due_date', 'status']
        verbose_name = 'DMC Operational Task'
        verbose_name_plural = 'DMC Operational Tasks'

    def __str__(self):
        return f"[{self.get_priority_display()}] {self.title} ({self.get_status_display()})"

    @property
    def is_overdue(self):
        if self.status != 'completed' and self.due_date:
            due = self.due_date
            if isinstance(due, str):
                try:
                    due = datetime.date.fromisoformat(due)
                except (ValueError, TypeError):
                    return False
            return due < timezone.now().date()
        return False


# ==============================================================================
# 8. MARKETING PROXY MODELS (PRESERVED)
# ==============================================================================

from marketing.models import Coupon as OriginalCoupon
from marketing.models import EmailCampaign as OriginalEmailCampaign
from marketing.models import UpsellRecommendation as OriginalUpsellRecommendation


class CouponProxy(OriginalCoupon):
    class Meta:
        proxy = True
        app_label = 'crm'
        verbose_name = 'Coupon'
        verbose_name_plural = 'Coupons'


class EmailCampaignProxy(OriginalEmailCampaign):
    class Meta:
        proxy = True
        app_label = 'crm'
        verbose_name = 'Email Campaign'
        verbose_name_plural = 'Email Campaigns'


class UpsellRecommendationProxy(OriginalUpsellRecommendation):
    class Meta:
        proxy = True
        app_label = 'crm'
        verbose_name = 'Upsell Recommendation'
        verbose_name_plural = 'Upsell Recommendations'


# ==============================================================================
# 9. FLIGHT MASTER (TRANSIT MASTER DATA)
# ==============================================================================

class FlightMaster(models.Model):
    airline = models.CharField(max_length=100)
    flight_number = models.CharField(max_length=50, unique=True)
    origin_airport = models.CharField(max_length=100, help_text="e.g. CJB (Coimbatore) or BLR (Bengaluru)")
    destination_airport = models.CharField(max_length=100, help_text="e.g. DEL (Delhi) or DXB (Dubai)")
    departure_time = models.TimeField()
    arrival_time = models.TimeField()
    operating_days = models.CharField(max_length=100, default='Daily', help_text="e.g. Daily, Mon/Wed/Fri")
    cabin_class = models.CharField(
        max_length=30,
        choices=[('economy', 'Economy'), ('premium_economy', 'Premium Economy'), ('business', 'Business Class')],
        default='economy'
    )
    baggage_allowance = models.CharField(max_length=100, default='15 KG Check-in + 7 KG Cabin')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['airline', 'flight_number']
        verbose_name = 'Flight Master'
        verbose_name_plural = 'Flight Master Data'

    def __str__(self):
        return f"{self.airline} ({self.flight_number}) : {self.origin_airport} -> {self.destination_airport}"


# ==============================================================================
# 10. ENTERPRISE DOCUMENT VAULT & MARKETING ASSETS
# ==============================================================================

class DmcDocument(models.Model):
    CATEGORY_CHOICES = [
        ('brochure', '🎨 Tour Brochure / Flyer'),
        ('itinerary_template', '📑 Itinerary Template'),
        ('rate_sheet', '📊 Supplier Tariff / Rate Sheet'),
        ('business_agreement', '🤝 Corporate / FTO Agreement'),
        ('emailer', '📧 Marketing Emailer / Creative'),
        ('client_kyc_passport', '🪪 Guest ID / Passport / Visa'),
        ('voucher_invoice', '🧾 Supplier Bill / Tax Invoice'),
        ('other', '📂 General Document'),
    ]

    title = models.CharField(max_length=255)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='brochure')
    document_file = models.FileField(upload_to='dmc_vault/%Y/%m/')
    description = models.TextField(blank=True)
    
    related_inquiry = models.ForeignKey(Inquiry, on_delete=models.SET_NULL, null=True, blank=True, related_name='attached_documents')
    related_booking = models.ForeignKey('operations.Booking', on_delete=models.SET_NULL, null=True, blank=True, related_name='dmc_documents')
    related_partner = models.ForeignKey(PartnerProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='documents')
    related_supplier = models.ForeignKey(SupplierProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='documents')

    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'DMC Enterprise Document'
        verbose_name_plural = 'DMC Document Vault'

    def __str__(self):
        return f"[{self.get_category_display()}] {self.title}"


# ==============================================================================
# 11. COMPLAINT & SERVICE QUALITY MANAGEMENT
# ==============================================================================

def generate_complaint_number():
    from django.utils import timezone
    import random
    ts = timezone.now().strftime('%Y%m')
    rn = random.randint(1000, 9999)
    return f"CMP-{ts}-{rn}"


class TravelComplaint(models.Model):
    CATEGORY_CHOICES = [
        ('hotel_quality', '🏨 Hotel Room / Cleanliness / Service Issue'),
        ('vehicle_condition', '🚗 Vehicle AC / Cleanliness / Breakdown'),
        ('driver_conduct', '👤 Driver Punctuality / Route / Behavior'),
        ('guide_behavior', '🗣️ Tour Guide Knowledge / Language'),
        ('food_meals', '🍲 Meal Quality / Restaurant Service'),
        ('itinerary_delay', '⏱️ Sightseeing Skipped / Schedule Delay'),
        ('billing_dispute', '💰 Unexpected Charges / Billing Dispute'),
        ('other', '⚠️ Other Quality Issue'),
    ]

    STATUS_CHOICES = [
        ('lodged', '🔴 Lodged (New Complaint)'),
        ('under_investigation', '🟡 Under Investigation'),
        ('supplier_escalated', '🟠 Escalated to Supplier'),
        ('resolved', '🟢 Resolved with Client'),
        ('closed', '⚪ Closed & Documented'),
    ]

    SEVERITY_CHOICES = [
        ('critical', '🔴 Critical (VIP / Immediate Escalation)'),
        ('high', '🟠 High'),
        ('medium', '🟡 Medium'),
        ('low', '🟢 Low'),
    ]

    COMPLAINANT_TYPES = [
        ('fto_agent', '🏢 Foreign Tour Operator (FTO) / Travel Agent'),
        ('corporate', '💼 Corporate Account Coordinator'),
        ('b2c_traveler', '👤 Direct Retail Traveler'),
    ]

    complaint_number = models.CharField(max_length=50, unique=True, default=generate_complaint_number)
    complainant_type = models.CharField(max_length=30, choices=COMPLAINANT_TYPES, default='b2c_traveler')
    complainant_name = models.CharField(max_length=255)
    complainant_phone = models.CharField(max_length=50, blank=True)
    complainant_email = models.EmailField(blank=True)

    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='hotel_quality')
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='medium')
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='lodged')

    related_booking = models.ForeignKey('operations.Booking', on_delete=models.SET_NULL, null=True, blank=True, related_name='complaints')
    related_inquiry = models.ForeignKey(Inquiry, on_delete=models.SET_NULL, null=True, blank=True, related_name='complaints')
    supplier_involved = models.ForeignKey(SupplierProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='complaints')
    
    supplier_rating_awarded = models.PositiveSmallIntegerField(
        null=True, blank=True,
        help_text="Supplier evaluation rating (1 = Poor, 5 = Excellent)"
    )

    issue_description = models.TextField(help_text="Detailed description of the incident / complaint")
    investigation_remarks = models.TextField(blank=True, help_text="Root-cause analysis and operational investigation findings")
    resolution_notes = models.TextField(blank=True, help_text="Action taken (apology, room upgrade, discount, compensation, supplier penalty)")

    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_complaints')
    lodged_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-lodged_at']
        verbose_name = 'DMC Quality Complaint'
        verbose_name_plural = 'DMC Quality Complaints'

    def __str__(self):
        return f"{self.complaint_number} - {self.complainant_name} ({self.get_category_display()})"


# ==============================================================================
# 12. SUPPLIER PAYMENT REQUISITIONS & COST-TO-COMPANY LEDGER
# ==============================================================================

def generate_requisition_number():
    from django.utils import timezone
    import random
    ts = timezone.now().strftime('%Y%m')
    rn = random.randint(1000, 9999)
    return f"REQ-{ts}-{rn}"


class SupplierPaymentRequisition(models.Model):
    PAYMENT_TYPES = [
        ('full', 'Full Settlement'),
        ('partial', 'Partial / Stage Payment'),
        ('advance', 'Advance Deposit'),
        ('credit_settlement', 'Monthly Credit Bill Settlement'),
    ]

    STATUS_CHOICES = [
        ('draft', 'Draft Requisition'),
        ('pending_approval', 'Pending Finance Approval'),
        ('approved', 'Approved for Payment'),
        ('disbursed', 'Disbursed / Paid'),
        ('rejected', 'Rejected'),
    ]

    requisition_number = models.CharField(max_length=50, unique=True, default=generate_requisition_number)
    supplier = models.ForeignKey(SupplierProfile, on_delete=models.CASCADE, related_name='payment_requisitions')
    related_voucher = models.ForeignKey(SupplierServiceVoucher, on_delete=models.SET_NULL, null=True, blank=True, related_name='payment_requisitions')
    
    amount_requested = models.DecimalField(max_digits=12, decimal_places=2)
    payment_type = models.CharField(max_length=30, choices=PAYMENT_TYPES, default='full')
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='pending_approval')

    cost_to_company = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Net Supplier buy cost")
    cost_to_client = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Quoted sell price to client for this service component")

    invoice_number = models.CharField(max_length=100, blank=True, help_text="Supplier's bill / tax invoice number")
    invoice_attachment = models.FileField(upload_to='supplier_invoices/%Y/%m/', null=True, blank=True)

    bank_account_number = models.CharField(max_length=50, blank=True)
    ifsc_code = models.CharField(max_length=30, blank=True)
    bank_name = models.CharField(max_length=100, blank=True)
    transaction_reference = models.CharField(max_length=100, blank=True, help_text="NEFT/RTGS/UPI UTR Number upon disbursement")

    notes = models.TextField(blank=True)
    requested_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    disbursed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Supplier Payment Requisition'
        verbose_name_plural = 'Supplier Payment Requisitions'

    @property
    def gross_margin(self):
        return self.cost_to_client - self.cost_to_company

    def __str__(self):
        return f"{self.requisition_number} : {self.supplier.company_name} (₹{self.amount_requested})"


# ==============================================================================
# 13. DMC PROFORMA & TAX INVOICING SUITE
# ==============================================================================

def generate_invoice_number(prefix="INV"):
    from django.utils import timezone
    import random
    ts = timezone.now().strftime('%Y%m')
    rn = random.randint(1000, 9999)
    return f"{prefix}-{ts}-{rn}"


class DmcInvoice(models.Model):
    INVOICE_TYPES = [
        ('proforma', 'Proforma Invoice / Advance Bill'),
        ('tax_invoice', 'Official Tax Invoice'),
    ]
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('issued', 'Issued to Client'),
        ('paid', 'Fully Paid'),
        ('partially_paid', 'Partially Paid'),
        ('cancelled', 'Cancelled'),
    ]
    TAX_REGIMES = [
        ('intra_state', 'Intra-State (CGST + SGST)'),
        ('inter_state', 'Inter-State (IGST)'),
        ('exempt', 'Exempt / Zero-Rated (SEZ / Inward Remittance)'),
    ]

    invoice_number = models.CharField(max_length=50, unique=True, blank=True)
    invoice_type = models.CharField(max_length=20, choices=INVOICE_TYPES, default='tax_invoice')
    invoice_date = models.DateField(default=timezone.now)
    due_date = models.DateField(null=True, blank=True)

    party = models.ForeignKey(Party, on_delete=models.PROTECT, related_name='dmc_invoices')
    booking = models.ForeignKey('operations.Booking', on_delete=models.SET_NULL, null=True, blank=True, related_name='invoices')
    quotation = models.ForeignKey(Quotation, on_delete=models.SET_NULL, null=True, blank=True, related_name='invoices')

    # Billed Entity Details (Captured snapshot)
    billing_name = models.CharField(max_length=255)
    billing_address = models.TextField(blank=True)
    client_gstin = models.CharField(max_length=20, blank=True)
    client_pan = models.CharField(max_length=20, blank=True)
    place_of_supply = models.CharField(max_length=100, default='Tamil Nadu (33)')

    # Service / HSN Information
    sac_code = models.CharField(max_length=20, default='998555', help_text="Tour Operator Services SAC")
    description_of_service = models.CharField(max_length=255, default='Tour Package & Ground Handling Operations')

    # Amounts & Taxes
    taxable_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    tax_regime = models.CharField(max_length=20, choices=TAX_REGIMES, default='intra_state')
    gst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('5.00'), help_text="Total GST Rate (e.g. 5.0, 12.0, 18.0)")
    cgst_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    sgst_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    igst_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    total_tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    total_invoice_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    balance_due = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    # Bank Settlement Details
    bank_account_info = models.TextField(
        blank=True,
        default="Bank: State Bank of India\nA/C: 38291048201\nIFSC: SBIN0001234\nUPI: travels@sbi\nBranch: Coimbatore Main"
    )
    terms_and_conditions = models.TextField(
        blank=True,
        default="1. 100% settlement required 48 hours prior to journey.\n2. Subject to Coimbatore jurisdiction.\n3. Cheques/Transfers subject to realization."
    )

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-invoice_date', '-id']
        verbose_name = 'DMC Commercial Invoice'
        verbose_name_plural = 'DMC Commercial Invoices'

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            pfx = "PI" if self.invoice_type == 'proforma' else "INV"
            self.invoice_number = generate_invoice_number(pfx)
        
        taxable = Decimal(str(self.taxable_amount or '0.00'))
        rate = Decimal(str(self.gst_rate or '5.00'))
        tot_tax = (taxable * rate / Decimal('100.00')).quantize(Decimal('0.01'))

        if self.tax_regime == 'intra_state':
            half_tax = (tot_tax / Decimal('2.00')).quantize(Decimal('0.01'))
            self.cgst_amount = half_tax
            self.sgst_amount = tot_tax - half_tax
            self.igst_amount = Decimal('0.00')
        elif self.tax_regime == 'inter_state':
            self.cgst_amount = Decimal('0.00')
            self.sgst_amount = Decimal('0.00')
            self.igst_amount = tot_tax
        else:
            self.cgst_amount = Decimal('0.00')
            self.sgst_amount = Decimal('0.00')
            self.igst_amount = Decimal('0.00')
            tot_tax = Decimal('0.00')

        self.total_tax_amount = tot_tax
        self.total_invoice_amount = taxable + tot_tax
        self.balance_due = max(Decimal('0.00'), self.total_invoice_amount - Decimal(str(self.paid_amount or '0.00')))
        
        if self.balance_due <= Decimal('0.00') and self.total_invoice_amount > Decimal('0.00'):
            self.status = 'paid'
        elif self.paid_amount > Decimal('0.00') and self.balance_due > Decimal('0.00'):
            self.status = 'partially_paid'
            
        super().save(*args, **kwargs)

    @property
    def half_gst_rate(self):
        return round(Decimal(str(self.gst_rate or '5.00')) / Decimal('2.0'), 2)

    def __str__(self):
        return f"{self.invoice_number} - {self.billing_name} (₹{self.total_invoice_amount})"

