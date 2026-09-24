from decimal import Decimal
from django.db import models
from django.utils import timezone
from core.models import Vehicle, VehicleType, Driver, Party


# ==============================================================================
# 1. Package Templates & Reusable Circuits
# ==============================================================================

class PackageTemplate(models.Model):
    CATEGORIES = [
        ('devotional', '🕉️ Devotional & Pilgrimage Tour (Temple Circuits)'),
        ('college_iv', '🎓 College / School Industrial Visit (IV)'),
        ('international', '✈️ International Tour Package (Passports & Visas)'),
        ('hill_station', '⛰️ Hill Station Getaway (Ooty, Kodaikanal, Munnar, Coorg)'),
        ('holiday', '🏖️ Leisure & Beach Holiday (Goa, Pondicherry, Kerala)'),
        ('local_tour', '🚗 Local 1-Day Sightseeing / Hourly Rental'),
        ('family_vacation', '💐 Family & Custom Vacation Package'),
        ('corporate_offsite', '🏢 Corporate Outing & Team Building'),
        ('fixed_departure', '🚌 Fixed Departure Group Bus Trip'),
    ]

    name = models.CharField(max_length=255, help_text="e.g. Mysore - Coorg - Chikmagalur Circuit")
    destination = models.CharField(max_length=255, help_text="e.g. Tamilnadu / Karnataka")
    category = models.CharField(max_length=50, choices=CATEGORIES, default='hill_station')
    duration_days = models.PositiveIntegerField(default=3)
    duration_nights = models.PositiveIntegerField(default=2)
    description = models.TextField(blank=True)
    base_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.duration_nights}N/{self.duration_days}D)"


# ==============================================================================
# 2. Master Tour Package (Siva Gayathri Tours & Travels Proposal Specification)
# ==============================================================================

class Package(models.Model):
    CATEGORIES = [
        ('devotional', '🕉️ Devotional & Pilgrimage Tour (Temple Circuits)'),
        ('college_iv', '🎓 College / School Industrial Visit (IV)'),
        ('international', '✈️ International Tour Package (Passports & Visas)'),
        ('hill_station', '⛰️ Hill Station Getaway (Ooty, Kodaikanal, Munnar, Coorg)'),
        ('holiday', '🏖️ Leisure & Beach Holiday (Goa, Pondicherry, Kerala)'),
        ('local_tour', '🚗 Local 1-Day Sightseeing / Hourly Rental'),
        ('family_vacation', '💐 Family & Custom Vacation Package'),
        ('corporate_offsite', '🏢 Corporate Outing & Team Building'),
        ('fixed_departure', '🚌 Fixed Departure Group Bus Trip'),
    ]
    PRICING_TYPES = [
        ('per_person', 'Per Person / Head Rate (with/without food)'),
        ('vehicle_rate', 'Per Vehicle Hire Rate (Local 1-N Day)'),
        ('lump_sum', 'Lump Sum Group Contract Rate'),
    ]
    ROOM_SHARING_TYPES = [
        ('twin_sharing', 'Twin Sharing (2 Pax) - Couples & Staff'),
        ('3_sharing', '3 Sharing (Triple) - Standard Family'),
        ('4_sharing', '4 Sharing (Quad) - Standard IV & Youth Groups'),
        ('6_sharing', '6 Sharing (Family Suite / 6-Bed Room)'),
        ('8_sharing', '8 Sharing (Group Cottage / Private Villa)'),
        ('dormitory', 'Dormitory / Bunk Beds / Group Hall (10+ Pax)'),
        ('mixed_custom', 'Custom Mixed Sharing (Twin, Quad, Suites as per Hotel)'),
        ('single', 'Single Occupancy'),
    ]
    MEAL_PLANS = [
        ('AP', 'AP Plan (All Meals: Breakfast, Lunch, Dinner)'),
        ('MAP', 'MAP Plan (Modified: Breakfast + Dinner)'),
        ('CP', 'CP Plan (Continental: Bed & Breakfast Only)'),
        ('EP', 'EP Plan (European: Room Only / Without Food)'),
    ]
    TRANSIT_MODES = [
        ('road_coach', '🚌 All-Way Road Coach (Ex-Garage Convoy)'),
        ('flight_coach', '✈️ Flight + Destination Coach (Fly-Bus Tour)'),
        ('train_coach', '🚆 Train + Destination Coach (Rail-Bus Tour)'),
        ('land_only', '📍 Land Package Only (Ex-Destination Airport/Station)'),
    ]

    template = models.ForeignKey(PackageTemplate, on_delete=models.SET_NULL, null=True, blank=True, related_name='packages')
    package_code = models.CharField(max_length=50, blank=True, help_text="e.g. PKG-MY-CRG-03D")
    name = models.CharField(max_length=255, help_text="e.g. 2 NIGHTS 3 DAYS MYSORE-COORG-CHIKMANGALUR")
    destination = models.CharField(max_length=255, help_text="e.g. TAMILNADU/KARNATAKA")
    category = models.CharField(max_length=50, choices=CATEGORIES, default='college_iv')
    transit_mode = models.CharField(max_length=30, choices=TRANSIT_MODES, default='road_coach', verbose_name="Tour Transit Mode")
    flight_estimate_per_pax = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Estimated return flight fare per person (e.g. ₹9,500 CJB-DEL-CJB)")
    train_estimate_per_pax = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Estimated return train fare per person (e.g. ₹2,200 3AC)")
    duration_days = models.PositiveIntegerField(default=3, help_text="Number of Days (e.g. 3 days)")
    duration_nights = models.PositiveIntegerField(default=2, help_text="Number of Nights (e.g. 2 nights)")
    pricing_type = models.CharField(max_length=30, choices=PRICING_TYPES, default='per_person')

    # Dual Pricing Breakdown (Matching Real-World PDF Page 5)
    base_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Default display rate")
    price_with_food = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Tour cost per person WITH food / AP Plan (e.g. ₹5,700)"
    )
    price_without_food = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Tour cost per person WITHOUT food / EP Plan (e.g. ₹4,600)"
    )

    @property
    def price_without_food_flight_inclusive(self):
        return (self.price_without_food or 0) + (self.flight_estimate_per_pax or 0)

    @property
    def price_with_food_flight_inclusive(self):
        return (self.price_with_food or 0) + (self.flight_estimate_per_pax or 0)

    # ==========================================================================
    # Package Unit Economics & Direct Operational Cost Breakdown (Per Pax)
    # ==========================================================================
    cost_hotel_per_pax = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        help_text="Estimated hotel accommodation cost per person (e.g. ₹2,200)"
    )
    cost_coach_per_pax = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        help_text="Estimated bus transit & fuel cost per person (e.g. ₹1,500)"
    )
    cost_meals_per_pax = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        help_text="Estimated meal catering cost per person for AP/MAP plan (e.g. ₹1,400)"
    )
    cost_activities_per_pax = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        help_text="Estimated entry tickets, jeep safari & permits per person (e.g. ₹450)"
    )
    cost_misc_per_pax = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        help_text="Guide batta, emergency first aid, parking/toll contingency (e.g. ₹200)"
    )

    @property
    def total_direct_cost_per_pax(self):
        return (
            (self.cost_hotel_per_pax or 0) +
            (self.cost_coach_per_pax or 0) +
            (self.cost_meals_per_pax or 0) +
            (self.cost_activities_per_pax or 0) +
            (self.cost_misc_per_pax or 0)
        )

    @property
    def gross_margin_per_pax(self):
        selling = self.price_with_food or self.base_price or 0
        return max(0, selling - self.total_direct_cost_per_pax)

    @property
    def gross_margin_percentage(self):
        selling = self.price_with_food or self.base_price or 0
        if selling > 0:
            return round((float(self.gross_margin_per_pax) / float(selling)) * 100, 1)
        return 0.0

    @property
    def projected_batch_gross_profit(self):
        return self.gross_margin_per_pax * (self.min_pax or 50)

    def get_effective_price(self, travel_date=None, with_food=True):
        """Returns the effective tour price per pax taking into account active seasonal peak/off-peak surcharges."""
        base = self.price_with_food if with_food else self.price_without_food
        if not base or base == 0:
            base = self.base_price or 0
        if travel_date:
            active_season = self.seasonal_rates.filter(
                is_active=True,
                start_date__lte=travel_date,
                end_date__gte=travel_date
            ).first()
            if active_season:
                if with_food and active_season.price_with_food_override:
                    return active_season.price_with_food_override
                elif not with_food and active_season.price_without_food_override:
                    return active_season.price_without_food_override
                elif active_season.surge_percentage:
                    from decimal import Decimal
                    multiplier = Decimal('1') + (active_season.surge_percentage / Decimal('100'))
                    return round(base * multiplier, 2)
        return base

    # Group & Headcount Parameters
    min_pax = models.PositiveIntegerField(default=50, help_text="Standard group size (e.g. 50 members)")
    complementary_staff_count = models.PositiveIntegerField(
        default=2,
        help_text="Number of complimentary faculty/staff traveling free (e.g. 50 + 2 staffs)"
    )

    # Hotel & Accommodation Specs (Matching Real-World PDF Page 1)
    hotel_star_category = models.CharField(max_length=100, default='Star Category Hotel & Resort', help_text="e.g. Star Category / 3-Star Resort")
    room_sharing_type = models.CharField(max_length=50, choices=ROOM_SHARING_TYPES, default='4_sharing')
    meal_plan = models.CharField(max_length=30, choices=MEAL_PLANS, default='AP')

    # Bus & Crew Specifications (Matching Real-World PDF Page 1 & 4)
    default_vehicle_type = models.ForeignKey(VehicleType, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_packages')
    vehicle_seating_desc = models.CharField(max_length=150, default='Non AC 54 seated Luxurious Bus', help_text="e.g. Non AC 54 seated / 52 Seated AC Coach")
    bus_amenities_desc = models.CharField(
        max_length=255,
        default='52/54 seated bus, 1 Driver & 1 cleaner, Laser Light, JBL Sound systems, First aid kit',
        help_text="Bus amenities shown on quote"
    )

    # Key Experience Flags
    has_campfire_dj = models.BooleanField(default=True, verbose_name="DJ with Campfire Included")
    has_jeep_safari = models.BooleanField(default=True, verbose_name="Jeep Safari Included (e.g. Mullayanagiri Peak)")
    has_boating = models.BooleanField(default=False, verbose_name="Boating / Trekking Included")
    has_industrial_visit = models.BooleanField(default=True, verbose_name="College IV Clearance Included")

    # Devotional & Pilgrimage Circuit Parameters
    is_devotional = models.BooleanField(default=False, verbose_name="🕉️ Devotional / Pilgrimage Circuit")
    temple_darshan_info = models.TextField(blank=True, help_text="Temple darshan procedures, special entry tickets, pooja timings")
    satvik_pure_veg_meals = models.BooleanField(default=False, verbose_name="100% Pure Vegetarian / Satvik Meals Guaranteed")
    senior_citizen_friendly = models.BooleanField(default=False, verbose_name="Senior Citizen Care (Wheelchair / Low-Step Bus)")
    temple_dress_code = models.CharField(max_length=255, default="Traditional Dhoti/Kurta for Men, Saree/Chudidar for Women", help_text="Temple dress code requirements")

    # International Tour Package Parameters
    is_international = models.BooleanField(default=False, verbose_name="✈️ International Tour Package")
    destination_country = models.CharField(max_length=150, blank=True, help_text="e.g. Dubai, UAE / Singapore & Malaysia / Thailand / Sri Lanka")
    visa_required = models.BooleanField(default=False, verbose_name="Visa Required")
    visa_guidelines = models.TextField(blank=True, help_text="Visa application steps, tourist eVisa, processing duration")
    passport_validity_months = models.PositiveIntegerField(default=6, help_text="Minimum passport validity required (usually 6 months)")
    currency_code = models.CharField(
        max_length=10,
        default='INR',
        choices=[
            ('INR', '₹ INR (Indian Rupee)'),
            ('AED', 'AED (UAE Dirham)'),
            ('SGD', 'SGD (Singapore Dollar)'),
            ('MYR', 'MYR (Malaysian Ringgit)'),
            ('THB', 'THB (Thai Baht)'),
            ('USD', '$ USD (US Dollar)'),
            ('EUR', '€ EUR (Euro)'),
        ],
        help_text="Primary currency for local tour expenses"
    )
    flight_inclusive = models.BooleanField(default=False, verbose_name="Flight Airfare Included in Package")
    flight_details_note = models.CharField(max_length=255, blank=True, help_text="e.g. Indigo / Air India Express Ex-Coimbatore or Chennai")
    overseas_dmc_partner = models.CharField(max_length=200, blank=True, help_text="Local overseas Destination Management Company (DMC)")

    # Full Inclusions Checklist (Matching Real-World PDF Page 3)
    inclusions = models.TextField(
        default=(
            "Tamilnadu-Karnataka-by bus.\n"
            "All parking, toll gate & permit charges.\n"
            "Accommodation on sharing basis in hotel and resort.\n"
            "All transfer & transportation.\n"
            "All sightseeing as per the itinerary based on time.\n"
            "Tour in charge from Siva Gayathri Tours and Travels.\n"
            "Guide service.\n"
            "Local entrances.\n"
            "DJ with campfire.\n"
            "Jeep safari."
        ),
        help_text="Items covered in tour cost (one per line)"
    )

    # Full Exclusions Checklist (Matching Real-World PDF Page 3)
    exclusions = models.TextField(
        default=(
            "Natural disturbance if any.\n"
            "Any damages or breakages.\n"
            "Optional tours if any.\n"
            "First aid kit.\n"
            "Personal expenses.\n"
            "Company expenses."
        ),
        help_text="Items excluded from tour cost (one per line)"
    )

    # Terms & Conditions (Matching Real-World PDF Page 4)
    terms_and_conditions = models.TextField(
        default=(
            "Camp Fire & Boating Subject to weather Conditions.\n"
            "Playing in Sea / Pool is at Customers Own risk.\n"
            "Payment - 50% advance while confirming the Trip & rest 50% before starting the trip.\n"
            "Any damages caused by the tour members to the vehicle or to any of the properties at the resort should be paid before the end of the trip.\n"
            "All sightseeing can be seen only according to the road and other situation during the trip.\n"
            "ITINERARY can be changed to customer's interest and comfort.\n"
            "Tour members are requested to co-operate with us to maintain the timings of Itinerary to serve you better.\n"
            "Customers drunk will not be allowed for Trekking."
        ),
        help_text="Terms & Conditions for quotation sheet"
    )

    contact_persons_footer = models.TextField(
        default="Rithik CA (+91 98425 33777), Anandh C (+91 94381 7131 / +91 38209 9979)",
        help_text="Staff names and mobile numbers printed in quotation sign-off"
    )

    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.duration_nights}N/{self.duration_days}D)"


# ==============================================================================
# 3. Vehicle-wise Tariff Matrix (For Local 1-N Day Packages)
# ==============================================================================

class PackageVehicleTariff(models.Model):
    RATE_TYPES = [
        ('outstation_multiday', 'Outstation Multi-Day (Per-Day Rate + Included KMs)'),
        ('local_1day', '1-Day Local Package (8 Hr / 80 Km or 10 Hr / 100 Km)'),
        ('lumpsum_fixed', 'Lump Sum Fixed Route Package Rate'),
    ]
    SEATING_TIERS = [
        ('4_sedan', 'Compact Sedan (4 Seats - Dzire, Etios)'),
        ('7_crysta', 'Premium MPV / SUV (6-7 Seats - Innova Crysta, Hycross)'),
        ('17_tt_urbania', 'Executive Van (12-17 Seats - Force Urbania, Tempo Traveller)'),
        ('26_force_coach', 'Maxi Coach (20-26 Seats - Force Traveller, Mini Coach)'),
        ('36_mini_bus', 'Deluxe Mini Bus (32-36 Seats)'),
        ('54_luxury_coach', 'Luxury Tour Coach (50-54 Seats - Non-AC / AC)'),
        ('60_super_coach', 'Super Coach (55-60 Seats - Long Distance Convoy)'),
    ]

    package = models.ForeignKey(Package, on_delete=models.CASCADE, related_name='vehicle_tariffs')
    vehicle_type = models.ForeignKey(VehicleType, on_delete=models.CASCADE, related_name='package_tariffs')
    rate_type = models.CharField(max_length=30, choices=RATE_TYPES, default='outstation_multiday')
    seating_tier = models.CharField(max_length=30, choices=SEATING_TIERS, default='4_sedan')

    # Pricing Parameters
    package_rate = models.DecimalField(max_digits=10, decimal_places=2, help_text="Total hire rate (or 1-day package rate)")
    per_day_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Per day vehicle hire rate for multi-day tours")
    included_km = models.PositiveIntegerField(default=300, help_text="KMs included in this package")
    extra_km_rate = models.DecimalField(max_digits=6, decimal_places=2, default=16.00, help_text="Rate per extra KM beyond package")
    
    # 1-Day Local Package Specifics
    local_package_hours = models.PositiveIntegerField(default=8, help_text="Included hours for 1-Day Local Package (e.g. 8 or 10 hrs)")
    extra_hour_rate = models.DecimalField(max_digits=8, decimal_places=2, default=0, help_text="Rate per extra hour beyond local package")

    # Driver Allowances & Inclusions
    driver_bata_included = models.BooleanField(default=True)
    driver_bata_per_day = models.DecimalField(max_digits=8, decimal_places=2, default=500, help_text="Driver day bata allowance")
    night_halt_charge = models.DecimalField(max_digits=8, decimal_places=2, default=0, help_text="Night halt charge (10:00 PM to 06:00 AM)")
    double_driver_included = models.BooleanField(default=False, verbose_name="Double Driver Assigned (Overnight / Long-Haul > 500 km)")
    toll_parking_included = models.BooleanField(default=True)
    interstate_permit_included = models.BooleanField(default=False)

    class Meta:
        unique_together = ('package', 'vehicle_type')
        verbose_name = 'Vehicle-Wise Tariff'
        verbose_name_plural = 'Vehicle-Wise Tariffs (4 to 60 Seats)'

    def __str__(self):
        rate = self.package_rate or Decimal('0.00')
        pkg_name = self.package.name if self.package_id else "No Package"
        veh_name = self.vehicle_type.name if self.vehicle_type_id else "No Vehicle Type"
        return f"{pkg_name} — {veh_name} ({self.get_seating_tier_display()}): ₹{rate:,.0f}"


# ==============================================================================
# 4. Itinerary Day Details (Matching Real-World PDF Page 2)
# ==============================================================================

class ItineraryDay(models.Model):
    package = models.ForeignKey(Package, on_delete=models.CASCADE, related_name='itinerary_days')
    day_number = models.IntegerField(default=1, help_text="0 for overnight journey (Day 00), 1, 2, 3...")
    title = models.CharField(max_length=255, help_text="e.g. Arriving Mysore - KRS Dam - Proceed Coorg")
    route_segment = models.CharField(max_length=255, blank=True, help_text="e.g. Coimbatore to Mysore by luxurious bus")
    activities = models.TextField(blank=True, help_text="Full day plan description")
    morning_activity = models.TextField(blank=True, help_text="e.g. Check in to hotel, refreshment")
    sightseeing_spots = models.TextField(blank=True, help_text="e.g. Mysore Palace, Brindavan Garden, KRS Dam, St. Philomena's Cathedral")
    evening_night_activity = models.TextField(blank=True, help_text="e.g. Proceed to Coorg, dinner, DJ with Campfire")
    night_stay_location = models.CharField(max_length=255, blank=True, help_text="e.g. Hotel / Resort in Coorg")
    meals_included = models.CharField(max_length=255, default="Breakfast, Lunch, Dinner", help_text="e.g. Breakfast, Lunch, Dinner")
    hotel_info = models.CharField(max_length=255, blank=True, help_text="Suggested hotel or resort name")
    transport_info = models.CharField(max_length=255, blank=True, help_text="e.g. 54-Seated Bus Transfer / 4x4 Jeep Safari")

    class Meta:
        ordering = ['day_number']
        unique_together = ('package', 'day_number')

    def __str__(self):
        day_label = f"Day 0{self.day_number}" if self.day_number >= 0 and self.day_number < 10 else f"Day {self.day_number}"
        return f"{day_label}: {self.title}"


# ==============================================================================
# 5. Fixed Departure Batches / Package Inventory
# ==============================================================================

class PackageInventory(models.Model):
    STATUS_CHOICES = [
        ('open', '🟢 Open for Booking'),
        ('fast_filling', '🟡 Fast Filling (Few Seats Left)'),
        ('sold_out', '🔴 Sold Out / Full'),
        ('departed', '🚍 Departed / On Route'),
        ('completed', '✅ Tour Completed'),
        ('cancelled', '❌ Cancelled'),
    ]

    package = models.ForeignKey(Package, on_delete=models.CASCADE, related_name='inventory')
    departure_date = models.DateField()
    return_date = models.DateField(null=True, blank=True)
    assigned_vehicle = models.ForeignKey(Vehicle, on_delete=models.SET_NULL, null=True, blank=True, related_name='tour_inventories')
    assigned_driver = models.ForeignKey(Driver, on_delete=models.SET_NULL, null=True, blank=True, related_name='tour_inventories')
    total_seats = models.PositiveIntegerField(default=52)
    available_seats = models.PositiveIntegerField(default=52)
    booked_seats = models.PositiveIntegerField(default=0)
    price_override = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')

    class Meta:
        verbose_name = 'Tour Bus Departure Batch'
        verbose_name_plural = 'Tour Bus Departure Batches'
        unique_together = ('package', 'departure_date')

    def save(self, *args, **kwargs):
        if self.total_seats and self.booked_seats is not None:
            self.available_seats = max(0, self.total_seats - self.booked_seats)
            if self.available_seats == 0 and self.status == 'open':
                self.status = 'sold_out'
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.package.name} — {self.departure_date} ({self.available_seats}/{self.total_seats} seats free)"

# Alias for Tour Bus Departures
TourBusDeparture = PackageInventory


# ==============================================================================
# 6. Boarding Points & Highway Pickup Timetable
# ==============================================================================

class BoardingPoint(models.Model):
    departure = models.ForeignKey(PackageInventory, on_delete=models.CASCADE, related_name='boarding_points')
    stop_order = models.PositiveIntegerField(default=1)
    stop_name = models.CharField(max_length=200, help_text="e.g. Coimbatore Gandhipuram Bus Stand")
    pickup_time = models.TimeField(help_text="e.g. 05:30 AM")
    landmark = models.CharField(max_length=255, blank=True, help_text="e.g. Opposite SETC Bus Stand")
    coordinator_phone = models.CharField(max_length=30, blank=True, help_text="Pickup coordinator mobile")

    class Meta:
        ordering = ['departure', 'stop_order']
        verbose_name = 'Tour Boarding Point'
        verbose_name_plural = 'Tour Boarding Points'

    def __str__(self):
        return f"Stop #{self.stop_order}: {self.stop_name} @ {self.pickup_time.strftime('%I:%M %p')}"


# ==============================================================================
# 7. College & School Industrial Visit (IV) Expeditions
# ==============================================================================

class CollegeIVExpedition(models.Model):
    STATUS_CHOICES = [
        ('inquiry', '📝 Quotation / Initial Inquiry'),
        ('letter_submitted', '📄 Industry Permission Letter Submitted'),
        ('confirmed', '✅ Confirmed & Booked'),
        ('on_tour', '🚍 On Tour / Traveling'),
        ('completed', '🎉 Tour Completed'),
        ('cancelled', '❌ Cancelled'),
    ]

    package = models.ForeignKey(Package, on_delete=models.SET_NULL, null=True, blank=True, related_name='college_iv_trips')
    college_name = models.CharField(max_length=255, help_text="e.g. PSG College of Technology")
    department_and_batch = models.CharField(max_length=200, help_text="e.g. B.E. Mechanical Engineering (Batch 2023-27)")
    faculty_incharge_name = models.CharField(max_length=150, help_text="HOD / Faculty Coordinator Name")
    faculty_incharge_phone = models.CharField(max_length=30, help_text="Direct mobile number")
    
    # Headcounts & Free Faculty Ratio (Matching Real-World PDF Page 5)
    student_count_male = models.PositiveIntegerField(default=30)
    student_count_female = models.PositiveIntegerField(default=20)
    faculty_count = models.PositiveIntegerField(default=2, help_text="Accompanying faculty/staff (Traveling free)")
    total_pax = models.PositiveIntegerField(default=52, help_text="Total group size (Students + Faculty)")

    # Industrial Visit Clearance
    industry_visit_targets = models.TextField(help_text="Factories/plants to visit (e.g. Ashok Leyland Hosur, Tea Factory Ooty, ISRO)")
    permission_status = models.CharField(
        max_length=30,
        choices=[
            ('pending', 'Pending Approval'),
            ('letter_submitted', 'Letter Submitted to Industry HR'),
            ('approved', 'Official Industry Clearance Approved'),
            ('completed', 'Industrial Visit Completed')
        ],
        default='pending'
    )
    permission_letter_file = models.FileField(upload_to='college_iv/letters/', null=True, blank=True, help_text="Signed college permission letter / company gate pass")

    # Convoy & Tour Logistics
    transit_mode = models.CharField(max_length=30, choices=Package.TRANSIT_MODES, default='road_coach', verbose_name="Tour Transit Mode")
    onward_transit_details = models.CharField(max_length=200, blank=True, help_text="e.g. IndiGo 6E-241 (CJB 08:30 AM -> DEL 11:20 AM) or Train #12678")
    return_transit_details = models.CharField(max_length=200, blank=True, help_text="e.g. IndiGo 6E-242 (DEL 07:45 PM -> CJB 10:35 PM) or Return Train details")
    transit_pnr_or_booking_ref = models.CharField(max_length=100, blank=True, help_text="Airline Group PNR / IRCTC PNR (e.g. Q8W9XY)")
    baggage_allowance = models.CharField(max_length=150, blank=True, help_text="e.g. 15 kg Check-in + 7 kg Cabin Baggage per passenger")
    reporting_terminal = models.CharField(max_length=200, blank=True, help_text="Assembly point for departure (e.g. Coimbatore Airport CJB or CBE Junction)")
    destination_city = models.CharField(max_length=100, blank=True, help_text="Destination city for flight/coach (e.g. Delhi / Agra / Jaipur)")
    destination_coach_partner = models.CharField(max_length=200, blank=True, help_text="Destination DMC / Coach fleet provider in destination city")
    aadhaar_id_mandatory = models.BooleanField(default=True, verbose_name="Govt Photo ID / Aadhaar Mandatory for Check-in")
    linked_trip = models.ForeignKey('operations.Trip', on_delete=models.SET_NULL, null=True, blank=True, related_name='college_iv_expeditions', help_text="Linked Operational Trip dispatched for this expedition")

    bus_count = models.PositiveIntegerField(default=1, help_text="Number of buses in the convoy")
    tour_manager_assigned = models.CharField(max_length=150, blank=True, default="Rithik CA / Anandh C", help_text="Tour manager traveling with the students")
    has_dj_campfire = models.BooleanField(default=True, verbose_name="DJ & Campfire Arrangement")
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='confirmed')
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = 'College Industrial Visit (IV) Expedition'
        verbose_name_plural = 'College IV Expeditions'

    def save(self, *args, **kwargs):
        self.total_pax = self.student_count_male + self.student_count_female + self.faculty_count
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.college_name} - {self.department_and_batch} ({self.total_pax} Pax)"


# ==============================================================================
# 8. Tour Passenger Manifest & 4-Sharing Room Allocation
# ==============================================================================

class TourPassengerManifest(models.Model):
    CATEGORIES = [
        ('student', 'Student'),
        ('faculty', 'Faculty / Staff (Complimentary)'),
        ('adult', 'Adult'),
        ('child', 'Child'),
        ('senior', 'Senior Citizen'),
    ]
    GENDERS = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ]

    departure = models.ForeignKey(PackageInventory, on_delete=models.CASCADE, related_name='passengers', null=True, blank=True)
    iv_expedition = models.ForeignKey(CollegeIVExpedition, on_delete=models.SET_NULL, null=True, blank=True, related_name='student_manifest')
    passenger_name = models.CharField(max_length=150)
    roll_number = models.CharField(max_length=50, blank=True, help_text="College Roll Number / Student Register ID")
    gender = models.CharField(max_length=10, choices=GENDERS, default='male')
    age = models.PositiveIntegerField(null=True, blank=True)
    category = models.CharField(max_length=20, choices=CATEGORIES, default='student')
    bus_assignment = models.CharField(max_length=50, blank=True, help_text="e.g. Bus 01, Bus 02")
    seat_number = models.CharField(max_length=10, blank=True, help_text="e.g. 12A, 12B")
    room_sharing_number = models.CharField(max_length=100, blank=True, help_text="e.g. Room 204 (4 Sharing)")
    boarding_point = models.ForeignKey(BoardingPoint, on_delete=models.SET_NULL, null=True, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    emergency_contact = models.CharField(max_length=150, blank=True, help_text="Parent / Emergency contact number")
    
    # Devotional, Flight & International Extended Manifest
    aadhaar_number = models.CharField(max_length=20, blank=True, help_text="Aadhaar / Govt Photo ID number for Flight/Train e-Boarding")
    ticket_or_pnr_status = models.CharField(max_length=50, blank=True, default="Confirmed", help_text="Ticket / Group PNR status")
    senior_assistance_needed = models.BooleanField(default=False, verbose_name="Senior Citizen Wheelchair / Special Assistance")
    passport_number = models.CharField(max_length=30, blank=True, help_text="Required for International Packages")
    passport_expiry_date = models.DateField(null=True, blank=True)
    visa_number = models.CharField(max_length=50, blank=True, help_text="Tourist eVisa / Entry Pass Number")

    class Meta:
        verbose_name = 'Tour Passenger & Rooming Entry'
        verbose_name_plural = 'Tour Passenger Manifest & Rooming List'

    def __str__(self):
        seat_str = f" [Seat {self.seat_number}]" if self.seat_number else ""
        room_str = f" [{self.room_sharing_number}]" if self.room_sharing_number else ""
        return f"{self.passenger_name}{seat_str}{room_str}"


# ==============================================================================
# 9. Devotional & Pilgrimage Temple Darshan Slots
# ==============================================================================

class TempleDarshanSlot(models.Model):
    DARSHAN_TYPES = [
        ('special_entry_300', 'Special Entry Darshan (₹300 / Fast Track)'),
        ('vip_break', 'VIP Break / Protocol Darshan'),
        ('general', 'General Sarva Darshanam'),
        ('abhishekam_seva', 'Abhishekam / Archanai Seva'),
        ('virtual_q', 'Virtual Q Token Pass (Sabarimala / Palani)'),
        ('winch_ropeway', 'Ropeway / Winch / Battery Car Pass'),
    ]

    package = models.ForeignKey(Package, on_delete=models.CASCADE, related_name='temple_slots')
    itinerary_day = models.ForeignKey(ItineraryDay, on_delete=models.SET_NULL, null=True, blank=True, related_name='temple_slots')
    temple_name = models.CharField(max_length=200, help_text="e.g. Tirumala Venkateswara Temple / Palani Dhandayuthapani / Madurai Meenakshi")
    deity_or_circuit = models.CharField(max_length=150, blank=True, help_text="e.g. Lord Balaji / Navagraha Suryanar Kovil / Arupadai Veedu")
    darshan_type = models.CharField(max_length=30, choices=DARSHAN_TYPES, default='special_entry_300')
    booked_slot_time = models.CharField(max_length=100, blank=True, help_text="e.g. 09:30 AM - 10:30 AM Slot")
    token_ticket_number = models.CharField(max_length=100, blank=True, help_text="e.g. TTD-2025-SE-98421 / Palani Token #44")
    reporting_location = models.CharField(max_length=200, blank=True, help_text="e.g. Vaikuntam Queue Complex 1 / North Gate")
    dress_code_notes = models.CharField(max_length=255, default="Strict Traditional: Dhoti/Kurta for Men, Saree/Chudidar for Women")
    prasad_details = models.CharField(max_length=255, blank=True, default="Special Laddu / Panchamirtham Prasadam Included")
    senior_citizen_support = models.BooleanField(default=True, verbose_name="Wheelchair / Battery Buggy Assistance Available")

    class Meta:
        verbose_name = 'Temple Darshan Slot'
        verbose_name_plural = 'Temple & Darshan Slots'

    def __str__(self):
        return f"{self.temple_name} ({self.get_darshan_type_display()}) - {self.booked_slot_time}"


# ==============================================================================
# 10. International Tour Document Checklist
# ==============================================================================

class InternationalDocumentChecklist(models.Model):
    package = models.ForeignKey(Package, on_delete=models.CASCADE, related_name='intl_documents')
    document_name = models.CharField(max_length=150, help_text="e.g. Passport copy (min 6 months validity), 35x45mm white background photo")
    is_mandatory = models.BooleanField(default=True)
    submission_deadline_days = models.PositiveIntegerField(default=7, help_text="Days prior to departure for submission")
    notes = models.CharField(max_length=255, blank=True, help_text="e.g. Scanned copy in PDF/JPEG under 2MB")

    class Meta:
        verbose_name = 'International Document Requirement'
        verbose_name_plural = 'International Document Checklist'

    def __str__(self):
        return f"{self.package.name} — {self.document_name}"


# ==============================================================================
# 11. Seasonal Rates & Peak Surge Management
# ==============================================================================

class PackageSeasonalRate(models.Model):
    SEASON_TYPES = [
        ('peak', '🔥 Peak Season Surcharge (May-June Summer / Dec Holidays)'),
        ('festival', '🎉 Festival / Long Weekend Surge (Diwali / Pongal / New Year)'),
        ('weekend', '🏖️ Weekend Standard Hike (Fri - Sun Departure)'),
        ('off_peak', '❄️ Off-Peak / Monsoon Special Discount'),
    ]

    package = models.ForeignKey(Package, on_delete=models.CASCADE, related_name='seasonal_rates')
    season_name = models.CharField(max_length=200, help_text="e.g. Ooty/Kodaikanal Summer Peak 2025")
    season_type = models.CharField(max_length=30, choices=SEASON_TYPES, default='peak')
    start_date = models.DateField(help_text="Season start date")
    end_date = models.DateField(help_text="Season end date")
    surge_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        help_text="Percentage multiplier on base tour rates (e.g. +20.00% or -10.00%)"
    )
    price_with_food_override = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="Flat rate per person WITH food during this season (overrides base price)"
    )
    price_without_food_override = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="Flat rate per person WITHOUT food during this season"
    )
    vehicle_tariff_surge_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        help_text="Percentage surge on bus/vehicle hire rates during this season"
    )
    notes = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['start_date']
        verbose_name = 'Seasonal Pricing Tier'
        verbose_name_plural = 'Seasonal Pricing Tiers (Peak / Off-Peak)'

    def __str__(self):
        sign = "+" if self.surge_percentage >= 0 else ""
        return f"{self.package.name} — {self.season_name} ({sign}{self.surge_percentage}%)"


# ==============================================================================
# 12. Hotel Room Allotment & Block Inventory Management
# ==============================================================================

class PackageHotelAllotment(models.Model):
    ROOM_CATEGORIES = [
        ('deluxe_ac', 'Deluxe AC Room'),
        ('executive_suite', 'Executive Suite / Family Room'),
        ('standard_non_ac', 'Standard Non-AC Room'),
        ('private_villa', 'Private Resort Villa / Cottage (6-8 Pax)'),
        ('dormitory', 'Group Dormitory / Bunk Beds (10+ Pax)'),
    ]
    STATUS_CHOICES = [
        ('blocked', '🟡 Tentatively Blocked (Awaiting Advance)'),
        ('confirmed', '🟢 Confirmed with Hotel Voucher'),
        ('partially_released', '🟠 Partially Released Unsold Rooms'),
        ('billed', '✅ Billed & Settled with Hotelier'),
        ('cancelled', '❌ Cancelled / Released'),
    ]

    package = models.ForeignKey(Package, on_delete=models.CASCADE, related_name='hotel_allotments')
    departure = models.ForeignKey(PackageInventory, on_delete=models.SET_NULL, null=True, blank=True, related_name='hotel_allotments')
    hotel_name = models.CharField(max_length=255, help_text="e.g. Sterling Fern Hill Ooty / Royal Orchid Coorg")
    hotel_partner = models.ForeignKey('core.Party', on_delete=models.SET_NULL, null=True, blank=True, related_name='package_hotel_allotments', limit_choices_to={'party_type': 'supplier'}, help_text="Hotel supplier ledger in Finance")
    room_category = models.CharField(max_length=40, choices=ROOM_CATEGORIES, default='deluxe_ac')
    check_in_date = models.DateField()
    check_out_date = models.DateField()
    rooms_blocked = models.PositiveIntegerField(default=10, help_text="Total rooms contracted from hotelier")
    rooms_occupied = models.PositiveIntegerField(default=0, help_text="Rooms allocated to tour guests")
    cost_per_room_night = models.DecimalField(max_digits=10, decimal_places=2, default=2500, help_text="Contracted rate per room per night")
    cutoff_release_date = models.DateField(null=True, blank=True, help_text="Deadline to release unsold rooms without retention charges")
    confirmation_voucher_no = models.CharField(max_length=100, blank=True, help_text="Hotel confirmation voucher number")
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='confirmed')
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['check_in_date']
        verbose_name = 'Hotel Room Allotment'
        verbose_name_plural = 'Hotel Room Allotments & Block Inventory'

    @property
    def nights_count(self):
        if self.check_in_date and self.check_out_date:
            return max(1, (self.check_out_date - self.check_in_date).days)
        return 1

    @property
    def total_cost(self):
        return (self.rooms_blocked or 0) * (self.cost_per_room_night or 0) * self.nights_count

    @property
    def occupancy_rate(self):
        if self.rooms_blocked and self.rooms_blocked > 0:
            return round((self.rooms_occupied / self.rooms_blocked) * 100, 1)
        return 0.0

    @property
    def rooms_available(self):
        return max(0, self.rooms_blocked - self.rooms_occupied)

    def __str__(self):
        return f"{self.hotel_name} ({self.get_room_category_display()}): {self.rooms_occupied}/{self.rooms_blocked} Rooms"


# ==============================================================================
# 13. Dynamic Experience, Safari & Excursion Add-On Bundler
# ==============================================================================

class PackageAddon(models.Model):
    CATEGORIES = [
        ('safari_adventure', '🚙 4x4 Jeep Safari / Off-Road Adventure'),
        ('sightseeing_entry', '🎟️ Monument / Palace / National Park Entry'),
        ('boating_water', '🚤 Speedboat / Houseboat / Scuba Diving'),
        ('meal_upgrade', '🍽️ Special Gala Dinner / Barbecue / Seafood'),
        ('entertainment_dj', '🎧 DJ Sound System & Campfire Night'),
        ('insurance_health', '🛡️ Travel Accident & Medical Insurance Cover'),
        ('vip_pass', '👑 Fast-Track VIP Temple / Attraction Pass'),
    ]
    PRICING_UNITS = [
        ('per_person', 'Per Person / Head Rate'),
        ('per_vehicle_group', 'Per Vehicle / Jeep (Up to 6-8 Pax)'),
        ('flat_per_group', 'Flat Lump Sum per Tour Group'),
    ]

    package = models.ForeignKey(Package, on_delete=models.CASCADE, related_name='addons')
    title = models.CharField(max_length=200, help_text="e.g. 4x4 Off-Road Jeep Safari to Mullayanagiri Peak")
    category = models.CharField(max_length=40, choices=CATEGORIES, default='safari_adventure')
    pricing_unit = models.CharField(max_length=30, choices=PRICING_UNITS, default='per_person')
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Direct procurement/vendor cost")
    selling_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Guest quotation price")
    is_mandatory_inclusion = models.BooleanField(default=False, verbose_name="Mandatory Standard Inclusion (Included in base fare)")
    supplier_partner = models.ForeignKey('core.Party', on_delete=models.SET_NULL, null=True, blank=True, related_name='package_addons', limit_choices_to={'party_type': 'supplier'})
    description = models.TextField(blank=True, help_text="What's included in this excursion/activity")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['title']
        verbose_name = 'Experience & Safari Add-on'
        verbose_name_plural = 'Experience & Safari Add-ons'

    @property
    def margin_per_unit(self):
        return max(0, (self.selling_price or 0) - (self.cost_price or 0))

    @property
    def margin_percentage(self):
        if self.selling_price and self.selling_price > 0:
            return round((float(self.margin_per_unit) / float(self.selling_price)) * 100, 1)
        return 0.0

    def __str__(self):
        price = self.selling_price or Decimal('0.00')
        return f"{self.title} (₹{price:,.0f} {self.get_pricing_unit_display()})"


# ==============================================================================
# 14. B2B Sub-Agent Reseller Commission & Markup Policy
# ==============================================================================

class PackageB2BMargin(models.Model):
    TIERS = [
        ('silver_agent', '🥈 Silver Travel Agent (Standard Commission)'),
        ('gold_agent', '🥇 Gold Preferred Partner (High Volume)'),
        ('platinum_dmc', '💎 Platinum DMC / Wholesaler'),
        ('corporate_affiliate', '🏢 Corporate Affinity Partner'),
    ]

    package = models.ForeignKey(Package, on_delete=models.CASCADE, related_name='b2b_margins')
    tier_name = models.CharField(max_length=40, choices=TIERS, default='silver_agent')
    commission_percent = models.DecimalField(max_digits=5, decimal_places=2, default=8.00, help_text="Commission percentage on tour package selling price")
    fixed_discount_per_pax = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Alternative flat discount per head for B2B partner")
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('package', 'tier_name')
        verbose_name = 'B2B Sub-Agent Commission Rule'
        verbose_name_plural = 'B2B Sub-Agent Commission Rules'

    @property
    def net_b2b_rate_with_food(self):
        from decimal import Decimal
        base = self.package.price_with_food or self.package.base_price or Decimal('0')
        if self.fixed_discount_per_pax > 0:
            return max(Decimal('0'), base - self.fixed_discount_per_pax)
        comm_amount = base * (self.commission_percent / Decimal('100'))
        return max(Decimal('0'), round(base - comm_amount, 2))

    @property
    def net_b2b_rate_without_food(self):
        from decimal import Decimal
        base = self.package.price_without_food or Decimal('0')
        if self.fixed_discount_per_pax > 0:
            return max(Decimal('0'), base - self.fixed_discount_per_pax)
        comm_amount = base * (self.commission_percent / Decimal('100'))
        return max(Decimal('0'), round(base - comm_amount, 2))

    def __str__(self):
        return f"{self.package.name} — {self.get_tier_name_display()} ({self.commission_percent}%)"


# ==============================================================================
# 15. Post-Trip Customer Feedback & Quality Governance System
# ==============================================================================

class TourFeedbackLog(models.Model):
    RATING_CHOICES = [
        (5, '⭐⭐⭐⭐⭐ 5 - Excellent'),
        (4, '⭐⭐⭐⭐ 4 - Good'),
        (3, '⭐⭐⭐ 3 - Average'),
        (2, '⭐⭐ 2 - Poor'),
        (1, '⭐ 1 - Terrible'),
    ]
    FLAG_CHOICES = [
        ('positive', '🟢 Positive / Brand Ambassador'),
        ('neutral', '🟡 Neutral / Standard Experience'),
        ('escalated_complaint', '🔴 Escalated Quality Complaint (Needs Resolution)'),
        ('resolved', '✅ Complaint Resolved by Management'),
    ]

    package = models.ForeignKey(Package, on_delete=models.CASCADE, related_name='feedback_logs')
    departure = models.ForeignKey(PackageInventory, on_delete=models.SET_NULL, null=True, blank=True, related_name='feedback_logs')
    iv_expedition = models.ForeignKey(CollegeIVExpedition, on_delete=models.SET_NULL, null=True, blank=True, related_name='feedback_logs')
    guest_name = models.CharField(max_length=150, help_text="Customer / Faculty / Team lead name")
    guest_phone = models.CharField(max_length=30, blank=True)
    trip_date = models.DateField(default=timezone.now)

    # 5-Dimensional Quality Scorecard
    overall_rating = models.PositiveIntegerField(choices=RATING_CHOICES, default=5, verbose_name="Overall Tour Rating")
    coach_driver_rating = models.PositiveIntegerField(choices=RATING_CHOICES, default=5, verbose_name="Coach Condition & Driver Punctuality")
    hotel_rating = models.PositiveIntegerField(choices=RATING_CHOICES, default=5, verbose_name="Hotel Room & Resort Cleanliness")
    food_rating = models.PositiveIntegerField(choices=RATING_CHOICES, default=5, verbose_name="Meal Quality & Dining Experience")
    schedule_rating = models.PositiveIntegerField(choices=RATING_CHOICES, default=5, verbose_name="Itinerary Execution & Sightseeing")

    # NPS (Net Promoter Score)
    nps_score = models.PositiveIntegerField(default=10, help_text="Likelihood to recommend to family/friends (0 to 10)")
    customer_review_text = models.TextField(blank=True, help_text="Detailed feedback or comments from guest")
    flag_status = models.CharField(max_length=30, choices=FLAG_CHOICES, default='positive')
    manager_resolution_notes = models.TextField(blank=True, help_text="Root-cause investigation and corrective action taken")
    is_verified = models.BooleanField(default=True, verbose_name="Verified Post-Trip Customer")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-trip_date', '-created_at']
        verbose_name = 'Post-Trip Customer Feedback'
        verbose_name_plural = 'Post-Trip Customer Feedback & Quality Logs'

    @property
    def average_dimension_score(self):
        scores = [
            self.overall_rating,
            self.coach_driver_rating,
            self.hotel_rating,
            self.food_rating,
            self.schedule_rating
        ]
        return round(sum(scores) / len(scores), 1)

    @property
    def nps_category(self):
        if self.nps_score >= 9:
            return "Promoter 🟢"
        elif self.nps_score >= 7:
            return "Passive 🟡"
        return "Detractor 🔴"

    def __str__(self):
        return f"{self.guest_name} — {self.package.name} ({self.overall_rating}★ / NPS {self.nps_score})"

