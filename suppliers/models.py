from django.db import models
from django.utils import timezone
from core.models import Supplier, Party, Vehicle


class SupplierContract(models.Model):
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='contracts')
    title = models.CharField(max_length=255)
    valid_from = models.DateField()
    valid_to = models.DateField()
    contract_document = models.FileField(upload_to='supplier_contracts/', null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.title} - {self.supplier.name}"


class CommissionRule(models.Model):
    agent_name = models.CharField(max_length=255)
    commission_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.agent_name} ({self.commission_percentage}%)"


class OutsourcedTripSettlement(models.Model):
    """
    Settlement ledger for partner fleet operators when Sivagayathiri
    outsources a tour, outstation duty, or corporate commute to a partner bus/cab.
    Computes buy rate vs sell rate, statutory TDS under Sec 194C, fuel/advance deductions,
    and net vendor payout.
    """
    SETTLEMENT_STATUS = [
        ('draft', 'Draft (Pending Verification)'),
        ('verified', 'Verified by Dispatcher'),
        ('approved', 'Approved by Accounts'),
        ('paid', 'Settled & Paid'),
        ('disputed', 'Disputed / On Hold'),
    ]
    TDS_SECTIONS = [
        ('194C_INDIVIDUAL', 'Sec 194C - Individual / HUF Transporter (1.00%)'),
        ('194C_COMPANY', 'Sec 194C - Company / Firm / LLP (2.00%)'),
        ('206AA_NO_PAN', 'Sec 206AA - Non-Furnishing of PAN (20.00%)'),
        ('EXEMPT_DECLARATION', 'Exempt - Form 194C(6) <10 Goods/Passenger Vehicles (0.00%)'),
        ('CUSTOM', 'Custom Deducted Rate'),
    ]
    PAYMENT_MODES = [
        ('bank_neft', 'NEFT / RTGS Transfer'),
        ('upi', 'Instant UPI Transfer'),
        ('cheque', 'Account Payee Cheque'),
        ('cash', 'Cash Disbursement'),
    ]

    settlement_number = models.CharField(max_length=50, unique=True, db_index=True)
    trip = models.ForeignKey('operations.Trip', on_delete=models.CASCADE, related_name='outsourced_settlements', null=True, blank=True)
    contract_trip = models.ForeignKey('fleet_contracts.ContractTripLog', on_delete=models.CASCADE, related_name='outsourced_settlements', null=True, blank=True)
    supplier = models.ForeignKey(Party, on_delete=models.PROTECT, related_name='trip_settlements')
    vehicle = models.ForeignKey(Vehicle, on_delete=models.PROTECT, related_name='outsourced_settlements')
    settlement_date = models.DateField(default=timezone.now)

    # Crew & Operational Snapshots
    driver_name = models.CharField(max_length=150, blank=True)
    driver_phone = models.CharField(max_length=30, blank=True)
    odometer_start = models.PositiveIntegerField(null=True, blank=True)
    odometer_end = models.PositiveIntegerField(null=True, blank=True)
    total_km_run = models.PositiveIntegerField(default=0)
    duty_slip_number = models.CharField(max_length=50, blank=True)

    # Financial Breakdown
    customer_sell_rate = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Total customer revenue billed for this trip")
    agreed_buy_rate = models.DecimalField(max_digits=12, decimal_places=2, help_text="Agreed hire charge payable to partner supplier")
    toll_parking_allowance = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Actual toll/parking receipts reimbursable to partner")
    driver_bata_payable = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Driver night halt / bata payable to partner driver")

    # Deductions
    advance_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Cash/UPI advance given to partner before journey")
    fuel_deducted = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Fuel filled via Sivagayathiri company card")
    damage_penalty = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Breakdown, delay or passenger dispute penalty")

    # Statutory TDS Under Sec 194C
    tds_applicable = models.BooleanField(default=True)
    tds_section = models.CharField(max_length=30, choices=TDS_SECTIONS, default='194C_INDIVIDUAL')
    pan_number = models.CharField(max_length=15, blank=True)
    tds_rate_percent = models.DecimalField(max_digits=5, decimal_places=2, default=1.00)
    tds_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Net Computed
    gross_supplier_payable = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_deductions = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    net_payable_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    gross_margin_earned = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Profit Sivagayathiri earned on outsourcing this trip")

    # Status & Audit
    status = models.CharField(max_length=20, choices=SETTLEMENT_STATUS, default='draft')
    payment_mode = models.CharField(max_length=20, choices=PAYMENT_MODES, default='bank_neft')
    payment_reference = models.CharField(max_length=100, blank=True, help_text="Bank NEFT UTR / Cheque No / UPI Transaction ID")
    payment_cleared_date = models.DateField(null=True, blank=True)
    approved_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_settlements')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-settlement_date', '-id']
        verbose_name = 'Outsourced Trip Settlement'
        verbose_name_plural = 'Outsourced Trip Settlements'

    def __str__(self):
        return f"{self.settlement_number} - {self.supplier.name} (Net: ₹{self.net_payable_amount})"

    def recalculate_totals(self):
        """Calculates gross payable, total deductions, TDS, net payable, and gross margin."""
        from decimal import Decimal
        buy = Decimal(str(self.agreed_buy_rate or 0))
        toll = Decimal(str(self.toll_parking_allowance or 0))
        bata = Decimal(str(self.driver_bata_payable or 0))
        self.gross_supplier_payable = buy + toll + bata

        # TDS calculation on base buy_rate + bata (excluding pure reimbursements like toll)
        if self.tds_applicable:
            rate = Decimal(str(self.tds_rate_percent or 0))
            self.tds_amount = (buy * rate / Decimal('100')).quantize(Decimal('0.01'))
        else:
            self.tds_amount = Decimal('0.00')

        adv = Decimal(str(self.advance_paid or 0))
        fuel = Decimal(str(self.fuel_deducted or 0))
        penalty = Decimal(str(self.damage_penalty or 0))
        self.total_deductions = adv + fuel + penalty + self.tds_amount

        self.net_payable_amount = max(Decimal('0.00'), self.gross_supplier_payable - self.total_deductions)

        sell = Decimal(str(self.customer_sell_rate or 0))
        self.gross_margin_earned = sell - self.gross_supplier_payable


class HotelConfirmationVoucher(models.Model):
    """
    Formal 1-click confirmation voucher and rooming manifest sent to partner
    hotels & resorts during tour package execution.
    """
    STATUS_CHOICES = [
        ('issued', 'Issued / Sent to Hotel'),
        ('confirmed', 'Confirmed by Hotel Reservations'),
        ('checked_in', 'Guests Checked In'),
        ('checked_out', 'Checked Out & Completed'),
        ('cancelled', 'Booking Cancelled'),
    ]
    MEAL_PLANS = [
        ('EP', 'European Plan (Room Only - No Meals)'),
        ('CP', 'Continental Plan (Bed & Breakfast Included)'),
        ('MAP', 'Modified American Plan (Breakfast + Dinner Included)'),
        ('AP', 'American Plan (All Meals - Breakfast, Lunch, Dinner Included)'),
    ]
    ROOM_CATEGORIES = [
        ('standard', 'Standard AC Room'),
        ('deluxe', 'Deluxe Room'),
        ('super_deluxe', 'Super Deluxe Room'),
        ('executive_suite', 'Executive Suite'),
        ('family_cottage', 'Family Cottage / Villa'),
        ('luxury_tent', 'Luxury Glamping Tent / Treehouse'),
    ]
    BILLING_INSTRUCTIONS = [
        ('bill_to_company', 'Bill Entire Accommodation to Sivagayathiri Travels (Credit Account)'),
        ('direct_payment', 'Room Only Billed to Company, Extras Direct by Guest'),
        ('guest_direct_all', 'All Charges Payable Directly by Guest at Reception'),
    ]

    voucher_number = models.CharField(max_length=50, unique=True, db_index=True)
    trip = models.ForeignKey('operations.Trip', on_delete=models.CASCADE, related_name='hotel_vouchers')
    trip_hotel = models.ForeignKey('operations.TripHotel', on_delete=models.SET_NULL, null=True, blank=True, related_name='vouchers')

    # Hotel Master Details
    hotel_name = models.CharField(max_length=255)
    hotel_city = models.CharField(max_length=100, default='Coimbatore')
    hotel_address = models.TextField(blank=True)
    hotel_phone = models.CharField(max_length=30, blank=True)
    hotel_email = models.EmailField(blank=True)
    reservation_contact = models.CharField(max_length=100, blank=True)
    hotel_confirmation_code = models.CharField(max_length=100, blank=True, help_text="Reservation booking ID from hotel CRS")

    # Dates & Stay Timeline
    check_in_date = models.DateField()
    check_in_time = models.TimeField(default='12:00')
    check_out_date = models.DateField()
    check_out_time = models.TimeField(default='11:00')
    total_nights = models.PositiveIntegerField(default=1)

    # Lead Guest Details
    lead_guest_name = models.CharField(max_length=200)
    lead_guest_phone = models.CharField(max_length=30)
    total_adults = models.PositiveIntegerField(default=2)
    total_children = models.PositiveIntegerField(default=0)
    total_rooms = models.PositiveIntegerField(default=1)

    # Room Specification & Meals
    room_category = models.CharField(max_length=30, choices=ROOM_CATEGORIES, default='deluxe')
    meal_plan = models.CharField(max_length=10, choices=MEAL_PLANS, default='MAP')
    inclusions_notes = models.TextField(blank=True, default="Welcome Drink, Wi-Fi Access, Complimentary Breakfast and Dinner.")
    special_requests = models.TextField(blank=True, help_text="e.g. Free driver accommodation/food, Non-smoking room, Interconnecting rooms")

    # Accounting & Billing
    billing_instruction = models.CharField(max_length=30, choices=BILLING_INSTRUCTIONS, default='bill_to_company')
    agreed_hotel_tariff = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Total amount Sivagayathiri pays the hotel")
    advance_paid_to_hotel = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    balance_payable_to_hotel = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # Status & Transmissions
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='issued')
    whatsapp_dispatched_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-check_in_date', '-id']
        verbose_name = 'Hotel Confirmation Voucher'
        verbose_name_plural = 'Hotel Confirmation Vouchers'

    def __str__(self):
        return f"{self.voucher_number} - {self.hotel_name} ({self.lead_guest_name})"

    def recalculate_balance(self):
        from decimal import Decimal
        tariff = Decimal(str(self.agreed_hotel_tariff or 0))
        advance = Decimal(str(self.advance_paid_to_hotel or 0))
        self.balance_payable_to_hotel = max(Decimal('0.00'), tariff - advance)


class HotelVoucherGuest(models.Model):
    """Guest rooming manifest attached to hotel confirmation voucher."""
    ID_TYPES = [
        ('aadhaar', 'Aadhaar Card'),
        ('passport', 'Passport'),
        ('driving_license', 'Driving License'),
        ('voter_id', 'Voter ID Card'),
        ('other', 'Other ID'),
    ]
    voucher = models.ForeignKey(HotelConfirmationVoucher, on_delete=models.CASCADE, related_name='guest_manifest')
    room_label = models.CharField(max_length=50, default='Room 1')
    guest_name = models.CharField(max_length=200)
    age = models.PositiveIntegerField(null=True, blank=True)
    gender = models.CharField(max_length=15, blank=True)
    id_proof_type = models.CharField(max_length=30, choices=ID_TYPES, default='aadhaar')
    id_proof_number = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return f"{self.guest_name} ({self.room_label})"
