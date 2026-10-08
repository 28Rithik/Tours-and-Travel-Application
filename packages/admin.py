from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline, StackedInline
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils import timezone

from .models import (
    PackageTemplate,
    Package,
    PackageVehicleTariff,
    ItineraryDay,
    PackageInventory,
    BoardingPoint,
    CollegeIVExpedition,
    TourPassengerManifest,
    TempleDarshanSlot,
    InternationalDocumentChecklist,
    PackageSeasonalRate,
    PackageHotelAllotment,
    PackageAddon,
    PackageB2BMargin,
    TourFeedbackLog,
)


# ==============================================================================
# Inlines
# ==============================================================================

class ItineraryDayInline(StackedInline):
    model = ItineraryDay
    extra = 1
    fields = (
        ('day_number', 'title'),
        ('route_segment', 'night_stay_location', 'meals_included'),
        'morning_activity',
        'sightseeing_spots',
        'evening_night_activity',
        'activities'
    )


class PackageVehicleTariffInline(TabularInline):
    model = PackageVehicleTariff
    extra = 0
    fields = ('vehicle_type', 'seating_tier', 'rate_type', 'package_rate', 'per_day_rate', 'included_km', 'extra_km_rate', 'driver_bata_per_day', 'toll_parking_included', 'interstate_permit_included')


class PackageSeasonalRateInline(TabularInline):
    model = PackageSeasonalRate
    extra = 0
    fields = ('season_name', 'season_type', 'start_date', 'end_date', 'surge_percentage', 'price_with_food_override', 'price_without_food_override', 'is_active')


class PackageHotelAllotmentInline(TabularInline):
    model = PackageHotelAllotment
    extra = 0
    fields = ('hotel_name', 'room_category', 'check_in_date', 'check_out_date', 'rooms_blocked', 'rooms_occupied', 'cost_per_room_night', 'status')


class PackageAddonInline(TabularInline):
    model = PackageAddon
    extra = 0
    fields = ('title', 'category', 'pricing_unit', 'cost_price', 'selling_price', 'is_mandatory_inclusion', 'is_active')


class PackageB2BMarginInline(TabularInline):
    model = PackageB2BMargin
    extra = 0
    fields = ('tier_name', 'commission_percent', 'fixed_discount_per_pax', 'is_active')


class TempleDarshanSlotInline(StackedInline):
    model = TempleDarshanSlot
    extra = 0
    classes = ('collapse',)
    fields = (
        ('temple_name', 'deity_or_circuit'),
        ('darshan_type', 'booked_slot_time'),
        ('token_ticket_number', 'reporting_location'),
        ('dress_code_notes', 'prasad_details'),
        'senior_citizen_support',
    )


class InternationalDocumentChecklistInline(TabularInline):
    model = InternationalDocumentChecklist
    extra = 0
    classes = ('collapse',)
    fields = ('document_name', 'is_mandatory', 'submission_deadline_days', 'notes')


# ==============================================================================
# Bulk Actions
# ==============================================================================

@admin.action(description="📄 Generate Tour Proposal Quotation for selected package")
def generate_proposal_action(modeladmin, request, queryset):
    pkg = queryset.first()
    if pkg:
        from django.shortcuts import redirect
        return redirect(f"/packages/quote/{pkg.id}/")


@admin.action(description="🚀 Create New Active Package from selected Template")
def clone_template_to_package(modeladmin, request, queryset):
    from decimal import Decimal
    from django.shortcuts import redirect
    created_pkgs = []
    for tmpl in queryset:
        pkg = Package.objects.create(
            template=tmpl,
            name=tmpl.name,
            destination=tmpl.destination,
            category=tmpl.category,
            duration_days=tmpl.duration_days,
            duration_nights=tmpl.duration_nights,
            base_price=tmpl.base_price,
            price_with_food=tmpl.base_price,
            price_without_food=tmpl.base_price * Decimal('0.75') if tmpl.base_price else Decimal('0'),
            description=tmpl.description,
            is_active=True
        )
        created_pkgs.append(pkg)
    
    if len(created_pkgs) == 1:
        modeladmin.message_user(request, f"✨ Successfully created new package from template '{queryset.first().name}'! Customize your itinerary and fleet tariffs below.")
        return redirect(f"/admin/packages/package/{created_pkgs[0].id}/change/")
    else:
        modeladmin.message_user(request, f"✨ Successfully generated {len(created_pkgs)} new packages from selected templates.")


# ==============================================================================
# 1. Package Template Admin
# ==============================================================================

@admin.register(PackageTemplate)
class PackageTemplateAdmin(ModelAdmin):
    list_display = ('name', 'category_badge', 'destination', 'duration_display', 'base_price_display', 'is_active')
    list_filter = ('category', 'destination', 'is_active')
    search_fields = ('name', 'destination')
    actions = [clone_template_to_package]

    @admin.display(description='Category')
    def category_badge(self, obj):
        return format_html(
            '<span class="badge" style="background-color: #334155; color: #f8fafc; padding: 4px 8px;">{}</span>',
            obj.get_category_display()
        )

    @admin.display(description='Duration')
    def duration_display(self, obj):
        return format_html(
            '<span style="color: #38bdf8; font-weight: 700;">{}N / {}D</span>',
            obj.duration_nights, obj.duration_days
        )

    @admin.display(description='Base Rate')
    def base_price_display(self, obj):
        return format_html('<span style="color: #10b981; font-weight: 700;">₹{}</span>', f"{obj.base_price:,.0f}")


# ==============================================================================
# 2. Master Tour Package Admin (Siva Gayathri Tours & Travels Proposal Format)
# ==============================================================================

@admin.register(Package)
class PackageAdmin(ModelAdmin):
    list_display = (
        'name_display', 'category_badge', 'destination_badge',
        'duration_display', 'dual_pricing_display', 'unit_margin_badge',
        'hotel_and_room_display', 'print_proposal_button', 'is_active'
    )
    list_filter = ('category', 'pricing_type', 'meal_plan', 'room_sharing_type', 'is_active')
    search_fields = ('name', 'destination', 'package_code', 'description')
    inlines = [
        ItineraryDayInline,
        PackageVehicleTariffInline,
        PackageSeasonalRateInline,
        PackageAddonInline,
        PackageHotelAllotmentInline,
        PackageB2BMarginInline,
        TempleDarshanSlotInline,
        InternationalDocumentChecklistInline
    ]
    actions = [generate_proposal_action]
    readonly_fields = ('unit_economics_summary_card',)

    fieldsets = (
        ('Step 1: Tour Identity & Duration', {
            'fields': (
                ('name', 'package_code'),
                ('category', 'destination'),
                ('duration_nights', 'duration_days', 'is_active'),
            ),
            'description': 'Core package identity, circuit destination, and duration.'
        }),
        ('Step 2: Headcount, Dual Pricing & Operating P&L Unit Economics', {
            'fields': (
                'pricing_type',
                ('min_pax', 'complementary_staff_count'),
                ('price_with_food', 'price_without_food'),
                'base_price',
                ('cost_hotel_per_pax', 'cost_coach_per_pax', 'cost_meals_per_pax'),
                ('cost_activities_per_pax', 'cost_misc_per_pax'),
                'unit_economics_summary_card',
            ),
            'classes': ('grp-pricing-dual',),
            'description': 'Configure selling price (With/Without Food) and direct procurement cost per head to monitor gross profit margins in real-time.'
        }),
        ('Step 3: Transit, Coach Fleet & Logistics', {
            'fields': (
                ('transit_mode', 'default_vehicle_type'),
                'flight_estimate_per_pax',
                'train_estimate_per_pax',
                ('vehicle_seating_desc', 'bus_amenities_desc'),
            ),
            'classes': ('grp-transit-specs',),
            'description': 'Configure All-Road Coach, Fly-Bus, or Rail-Bus transit parameters and fleet amenities.'
        }),
        ('Step 4: Stay, Dining & Experiences', {
            'fields': (
                ('hotel_star_category', 'room_sharing_type'),
                'meal_plan',
                ('has_campfire_dj', 'has_jeep_safari', 'has_boating', 'has_industrial_visit'),
                # Devotional specifications (Context-aware)
                'is_devotional',
                ('satvik_pure_veg_meals', 'senior_citizen_friendly'),
                ('temple_dress_code', 'temple_darshan_info'),
                # International specifications (Context-aware)
                'is_international',
                ('destination_country', 'currency_code'),
                ('visa_required', 'passport_validity_months', 'flight_inclusive'),
                ('visa_guidelines', 'overseas_dmc_partner', 'flight_details_note'),
            ),
            'classes': ('grp-stay-experience',),
            'description': 'Hotel accommodation, room sharing, DJ campfire, safari, plus optional pilgrimage or overseas specifications.'
        }),
        ('Step 5: Checklist, Inclusions & Proposal Terms', {
            'fields': (
                ('inclusions', 'exclusions'),
                ('terms_and_conditions', 'contact_persons_footer'),
                'description',
            ),
            'description': 'Side-by-side inclusion/exclusion checklist and proposal sign-off terms.'
        }),
    )

    change_form_template = 'admin/packages/package/change_form.html'

    class Media:
        css = {
            'all': ('packages/css/package_admin_custom.css',)
        }
        js = ()

    @admin.display(description='Package Name')
    def name_display(self, obj):
        code_str = f"[{obj.package_code}] " if obj.package_code else ""
        return format_html(
            '<span style="font-weight: 700; color: #f8fafc;"><i class="fas fa-umbrella-beach mr-1" style="color: #38bdf8;"></i>{}{}</span>',
            code_str, obj.name
        )

    @admin.display(description='Category')
    def category_badge(self, obj):
        colors = {
            'holiday': ('#14b8a6', 'fas fa-umbrella-beach', 'Leisure / Beach'),
            'devotional': ('#8b5cf6', 'fas fa-om', 'Devotional'),
            'college_iv': ('#f59e0b', 'fas fa-graduation-cap', 'College IV'),
            'international': ('#0284c7', 'fas fa-plane-departure', 'International'),
            'local_tour': ('#0ea5e9', 'fas fa-car', 'Local 1-Day'),
            'hill_station': ('#10b981', 'fas fa-mountain', 'Hill Station'),
            'fixed_departure': ('#6366f1', 'fas fa-bus', 'Fixed Departure'),
            'corporate_offsite': ('#3b82f6', 'fas fa-building', 'Corporate'),
            'family_vacation': ('#64748b', 'fas fa-users', 'Family / Custom'),
        }
        color, icon, label = colors.get(obj.category, ('#64748b', 'fas fa-tag', obj.category))
        return format_html(
            '<span class="badge" style="background-color: {}; color: #fff; padding: 4px 8px; font-size: 11px;">'
            '<i class="{} mr-1"></i>{}'
            '</span>',
            color, icon, label
        )

    @admin.display(description='Destination')
    def destination_badge(self, obj):
        dest_clean = (obj.destination or 'Tamil Nadu, India').strip()[:40]
        return format_html(
            '<span style="color: #fef08a; font-weight: 700; font-size: 12px;"><i class="fas fa-map-marker-alt text-danger mr-1"></i>{}</span>',
            dest_clean
        )

    @admin.display(description='Duration')
    def duration_display(self, obj):
        return format_html(
            '<span class="font-semibold text-slate-900 dark:text-slate-100">{}N / {}D</span>',
            obj.duration_nights, obj.duration_days
        )

    @admin.display(description='Dual Pricing Rates')
    def dual_pricing_display(self, obj):
        if obj.price_with_food or obj.price_without_food:
            return format_html(
                '<span style="color: #10b981; font-weight: 700;">₹{}</span> <small style="color: #94a3b8;">(With Food)</small><br>'
                '<span style="color: #38bdf8; font-weight: 700;">₹{}</span> <small style="color: #94a3b8;">(Without Food)</small>',
                f"{obj.price_with_food:,.0f}", f"{obj.price_without_food:,.0f}"
            )
        return format_html('<span style="color: #10b981; font-weight: 700;">₹{}</span>', f"{obj.base_price:,.0f}")

    @admin.display(description='Gross Margin P&L')
    def unit_margin_badge(self, obj):
        selling = obj.price_with_food or obj.base_price or 0
        if selling > 0 and obj.total_direct_cost_per_pax > 0:
            pct = obj.gross_margin_percentage
            margin = obj.gross_margin_per_pax
            color = '#10b981' if pct >= 18 else ('#f59e0b' if pct >= 10 else '#ef4444')
            return format_html(
                '<span class="badge" style="background-color: {}; color: #fff; padding: 4px 8px; font-size: 11px;">'
                '<i class="fas fa-coins mr-1"></i>+₹{} ({}%)'
                '</span>',
                color, f"{margin:,.0f}", f"{pct:.1f}"
            )
        return mark_safe('<span style="color: #64748b;">Cost not set</span>')

    @admin.display(description='Unit Economics & Gross Margin P&L')
    def unit_economics_summary_card(self, obj):
        if not obj or not obj.id:
            return mark_safe('<span style="color: #94a3b8;">Save package first to calculate unit economics.</span>')
        selling = obj.price_with_food or obj.base_price or 0
        total_cost = obj.total_direct_cost_per_pax
        margin = obj.gross_margin_per_pax
        margin_pct = obj.gross_margin_percentage
        batch_profit = obj.projected_batch_gross_profit

        margin_color = '#10b981' if margin_pct >= 18 else ('#f59e0b' if margin_pct >= 10 else '#ef4444')
        return format_html(
            '<div style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); border: 1px solid #334155; border-radius: 8px; padding: 16px; margin-top: 8px; max-width: 800px;">'
            '  <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #334155; padding-bottom: 10px; margin-bottom: 12px;">'
            '    <div style="font-weight: 700; color: #f8fafc; font-size: 14px;"><i class="fas fa-chart-line mr-2" style="color: #38bdf8;"></i>Tour Unit Economics & Operating Margin</div>'
            '    <span style="background-color: {}; color: #fff; padding: 4px 10px; border-radius: 6px; font-weight: 700; font-size: 12px;">'
            '      {}% Gross Margin'
            '    </span>'
            '  </div>'
            '  <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 12px;">'
            '    <div style="background: #1e293b; padding: 10px; border-radius: 6px; border: 1px solid #475569;">'
            '      <small style="color: #94a3b8;">Selling Rate (With Food)</small>'
            '      <div style="color: #38bdf8; font-size: 16px; font-weight: 700;">₹{} / pax</div>'
            '    </div>'
            '    <div style="background: #1e293b; padding: 10px; border-radius: 6px; border: 1px solid #475569;">'
            '      <small style="color: #94a3b8;">Direct COGS Cost</small>'
            '      <div style="color: #f87171; font-size: 16px; font-weight: 700;">₹{} / pax</div>'
            '    </div>'
            '    <div style="background: #1e293b; padding: 10px; border-radius: 6px; border: 1px solid #475569;">'
            '      <small style="color: #94a3b8;">Gross Profit / Pax</small>'
            '      <div style="color: {}; font-size: 16px; font-weight: 700;">₹{} / pax</div>'
            '    </div>'
            '    <div style="background: #1e293b; padding: 10px; border-radius: 6px; border: 1px solid #475569;">'
            '      <small style="color: #94a3b8;">Batch Profit ({} Pax)</small>'
            '      <div style="color: {}; font-size: 16px; font-weight: 700;">₹{}</div>'
            '    </div>'
            '  </div>'
            '  <div class="text-xs text-slate-700 dark:text-slate-300 bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-2 rounded">'
            '    <b>Cost Breakdown:</b> Hotel: ₹{} | Coach Transit: ₹{} | Meals: ₹{} | Activities & Safaris: ₹{} | Guide/Misc: ₹{}'
            '  </div>'
            '</div>',
            margin_color,
            margin_pct,
            f"{selling:,.0f}",
            f"{total_cost:,.0f}",
            margin_color,
            f"{margin:,.0f}",
            obj.min_pax or 50,
            margin_color,
            f"{batch_profit:,.0f}",
            f"{(obj.cost_hotel_per_pax or 0):,.0f}",
            f"{(obj.cost_coach_per_pax or 0):,.0f}",
            f"{(obj.cost_meals_per_pax or 0):,.0f}",
            f"{(obj.cost_activities_per_pax or 0):,.0f}",
            f"{(obj.cost_misc_per_pax or 0):,.0f}"
        )

    @admin.display(description='Hotel / Room / Meals')
    def hotel_and_room_display(self, obj):
        hotel_clean = (obj.hotel_star_category or 'Star Category Hotel & Resort').strip()[:35]
        sharing_clean = obj.get_room_sharing_type_display()[:15] if hasattr(obj, 'get_room_sharing_type_display') else 'Twin'
        return format_html(
            '<span class="text-xs text-slate-700 dark:text-slate-300"><i class="fas fa-hotel mr-1 text-amber-500"></i>{}</span><br>'
            '<small class="text-xs text-slate-500 dark:text-slate-400">{} | {}</small>',
            hotel_clean, sharing_clean, obj.meal_plan or 'AP'
        )

    @admin.display(description='Quotation & Voucher')
    def print_proposal_button(self, obj):
        return format_html(
            '<div style="display: flex; flex-direction: column; gap: 4px;">'
            '  <a href="/packages/quote/{}/" target="_blank" class="badge" '
            '     style="background-color: #0284c7; color: #fff; padding: 4px 8px; font-size: 11px; text-decoration: none; border-radius: 4px;">'
            '    <i class="fas fa-file-pdf mr-1"></i>Tour Proposal'
            '  </a>'
            '  <a href="/packages/voucher/{}/" target="_blank" class="badge" '
            '     style="background-color: #059669; color: #fff; padding: 4px 8px; font-size: 11px; text-decoration: none; border-radius: 4px;">'
            '    <i class="fas fa-ticket-alt mr-1"></i>Service Voucher'
            '  </a>'
            '</div>',
            obj.id, obj.id
        )


# ==============================================================================
# 3. Vehicle Tariff Admin (4 to 60 Seats Matrix)
# ==============================================================================

@admin.register(PackageVehicleTariff)
class PackageVehicleTariffAdmin(ModelAdmin):
    list_display = (
        'package_link', 'seating_tier_badge', 'rate_type_badge',
        'package_rate_display', 'per_seat_split_display', 'per_day_rate_display',
        'included_km_display', 'extra_km_rate_display', 'bata_display'
    )
    list_filter = ('rate_type', 'seating_tier', 'vehicle_type', 'driver_bata_included', 'toll_parking_included')
    search_fields = ('package__name', 'vehicle_type__name')

    class Media:
        css = {
            'all': ('packages/css/package_admin_custom.css',)
        }

    @admin.display(description='Tour Package')
    def package_link(self, obj):
        return format_html(
            '<a href="/admin/packages/package/{}/change/" style="color: #38bdf8; text-decoration: none; font-weight: 600;">{}</a>',
            obj.package.id, obj.package.name
        )

    @admin.display(description='Seating Tier (4-60 Seats)')
    def seating_tier_badge(self, obj):
        colors = {
            '4_sedan': ('#38bdf8', 'fas fa-car-side'),
            '7_crysta': ('#3b82f6', 'fas fa-car'),
            '17_tt_urbania': ('#10b981', 'fas fa-van-shuttle'),
            '26_force_coach': ('#f59e0b', 'fas fa-bus-simple'),
            '36_mini_bus': ('#ec4899', 'fas fa-bus'),
            '54_luxury_coach': ('#8b5cf6', 'fas fa-bus-alt'),
            '60_super_coach': ('#ef4444', 'fas fa-shuttle-van'),
        }
        color, icon = colors.get(obj.seating_tier, ('#64748b', 'fas fa-car'))
        return format_html(
            '<span class="badge" style="background-color: {}; color: #fff; padding: 4px 8px; font-size: 11px;">'
            '<i class="{} mr-1"></i>{}'
            '</span>',
            color, icon, obj.get_seating_tier_display()
        )

    @admin.display(description='Rate Type')
    def rate_type_badge(self, obj):
        if obj.rate_type == 'local_1day':
            return mark_safe('<span class="badge" style="background-color: #0ea5e9; color: #fff;">1-Day Local</span>')
        return mark_safe('<span class="badge" style="background-color: #059669; color: #fff;">Outstation Multi-Day</span>')

    @admin.display(description='Total / 1-Day Rate')
    def package_rate_display(self, obj):
        return format_html('<span style="color: #10b981; font-weight: 700; font-size: 13px;">₹{}</span>', f"{obj.package_rate:,.0f}")

    @admin.display(description='Per Person / Seat Split')
    def per_seat_split_display(self, obj):
        seats = obj.vehicle_type.seating_capacity if (obj.vehicle_type and obj.vehicle_type.seating_capacity) else 4
        if obj.package_rate and seats > 0:
            per_head = obj.package_rate / seats
            per_head_str = f"{per_head:,.0f}"
            return format_html(
                '<span class="badge" style="background-color: #0284c7; color: #fff; padding: 4px 8px; font-size: 11px;">'
                '<i class="fas fa-users mr-1"></i>~₹{} / head</span><br>'
                '<small style="color: #94a3b8;">({} seats)</small>',
                per_head_str, seats
            )
        return mark_safe('<span style="color: #64748b;">—</span>')

    @admin.display(description='Per Day Rate')
    def per_day_rate_display(self, obj):
        if obj.per_day_rate:
            return format_html('<span class="font-semibold text-slate-900 dark:text-slate-100">₹{} / day</span>', f"{obj.per_day_rate:,.0f}")
        return mark_safe('<span style="color: #64748b;">—</span>')

    @admin.display(description='Included KMs')
    def included_km_display(self, obj):
        hours_str = f" ({obj.local_package_hours} hrs)" if obj.rate_type == 'local_1day' else ""
        return format_html('<span class="text-slate-800 dark:text-slate-200 font-medium">{} km{}</span>', f"{obj.included_km:,}", hours_str)

    @admin.display(description='Extra KM Rate')
    def extra_km_rate_display(self, obj):
        extra_hr = f" + ₹{obj.extra_hour_rate:,.0f}/hr" if obj.extra_hour_rate else ""
        return format_html('<span style="color: #fb923c;">₹{} / km{}</span>', f"{obj.extra_km_rate:,.2f}", extra_hr)

    @admin.display(description='Driver Bata / Crew')
    def bata_display(self, obj):
        double_driver = ' <span class="badge bg-warning text-dark">2 Drivers</span>' if obj.double_driver_included else ''
        return format_html(
            '<span class="text-slate-700 dark:text-slate-300 font-medium">₹{}/day</span>{}',
            f"{obj.driver_bata_per_day:,.0f}", mark_safe(double_driver)
        )


# ==============================================================================
# 4. Devotional Temple Darshan Slots Admin
# ==============================================================================

@admin.register(TempleDarshanSlot)
class TempleDarshanSlotAdmin(ModelAdmin):
    list_display = ('temple_name', 'deity_or_circuit', 'darshan_type_badge', 'booked_slot_time', 'token_ticket_number', 'senior_citizen_badge')
    list_filter = ('darshan_type', 'senior_citizen_support', 'package')
    search_fields = ('temple_name', 'deity_or_circuit', 'token_ticket_number')

    @admin.display(description='Darshan Type')
    def darshan_type_badge(self, obj):
        return format_html(
            '<span class="badge" style="background-color: #8b5cf6; color: #fff; padding: 4px 8px;">'
            '<i class="fas fa-om mr-1 text-warning"></i>{}'
            '</span>',
            obj.get_darshan_type_display()
        )

    @admin.display(description='Senior Citizen Assistance')
    def senior_citizen_badge(self, obj):
        if obj.senior_citizen_support:
            return mark_safe('<span style="color: #10b981; font-weight: 600;"><i class="fas fa-wheelchair mr-1"></i>Wheelchair & Buggy Ready</span>')
        return mark_safe('<span style="color: #64748b;">Standard Walk</span>')


# ==============================================================================
# 5. International Document Checklist Admin
# ==============================================================================

@admin.register(InternationalDocumentChecklist)
class InternationalDocumentChecklistAdmin(ModelAdmin):
    list_display = ('package', 'document_name', 'is_mandatory_badge', 'submission_deadline_display')
    list_filter = ('is_mandatory', 'package')
    search_fields = ('package__name', 'document_name')

    @admin.display(description='Mandatory')
    def is_mandatory_badge(self, obj):
        if obj.is_mandatory:
            return mark_safe('<span class="badge bg-danger text-white">Required</span>')
        return mark_safe('<span class="badge bg-secondary text-white">Optional</span>')

    @admin.display(description='Submission Deadline')
    def submission_deadline_display(self, obj):
        return f"{obj.submission_deadline_days} days prior to flight departure"


# ==============================================================================
# 4. Itinerary Day Admin
# ==============================================================================

@admin.register(ItineraryDay)
class ItineraryDayAdmin(ModelAdmin):
    list_display = ('package_link', 'day_badge', 'title_display', 'route_segment', 'stay_display', 'meals_display')
    list_filter = ('package',)
    search_fields = ('title', 'route_segment', 'night_stay_location', 'package__name')
    ordering = ('package', 'day_number')

    @admin.display(description='Tour Package')
    def package_link(self, obj):
        return format_html(
            '<a href="/admin/packages/package/{}/change/" style="color: #93c5fd; text-decoration: none;">{}</a>',
            obj.package.id, obj.package.name
        )

    @admin.display(description='Day #')
    def day_badge(self, obj):
        label = f"Day 0{obj.day_number}" if obj.day_number >= 0 and obj.day_number < 10 else f"Day {obj.day_number}"
        return format_html(
            '<span class="badge" style="background-color: #0f766e; color: #fff; padding: 4px 8px; font-size: 11px;">{}</span>',
            label
        )

    @admin.display(description='Day Title')
    def title_display(self, obj):
        return format_html('<span style="color: #f8fafc; font-weight: 600;">{}</span>', obj.title)

    @admin.display(description='Night Stay')
    def stay_display(self, obj):
        if obj.night_stay_location:
            return format_html(
                '<span style="color: #e2e8f0; font-size: 12px;"><i class="fas fa-bed mr-1 text-warning"></i>{}</span>',
                obj.night_stay_location
            )
        return mark_safe('<span style="color: #64748b;">Overnight Transit</span>')

    @admin.display(description='Meals')
    def meals_display(self, obj):
        return format_html(
            '<span style="color: #38bdf8; font-size: 12px;"><i class="fas fa-utensils mr-1"></i>{}</span>',
            obj.meals_included
        )


# ==============================================================================
# 6. Seasonal Pricing Tiers Admin
# ==============================================================================

@admin.register(PackageSeasonalRate)
class PackageSeasonalRateAdmin(ModelAdmin):
    list_display = ('season_name', 'package_link', 'season_type_badge', 'date_range_display', 'surge_badge', 'override_prices_display', 'is_active')
    list_filter = ('season_type', 'is_active', 'package')
    search_fields = ('season_name', 'package__name')

    @admin.display(description='Tour Package')
    def package_link(self, obj):
        return format_html(
            '<a href="/admin/packages/package/{}/change/" style="color: #38bdf8; text-decoration: none; font-weight: 500;">{}</a>',
            obj.package.id, obj.package.name
        )

    @admin.display(description='Season Type')
    def season_type_badge(self, obj):
        colors = {
            'peak': ('#ef4444', 'fas fa-fire', 'Peak Season'),
            'festival': ('#f59e0b', 'fas fa-calendar-star', 'Festival'),
            'weekend': ('#3b82f6', 'fas fa-umbrella-beach', 'Weekend'),
            'off_peak': ('#06b6d4', 'fas fa-snowflake', 'Off-Peak'),
        }
        color, icon, label = colors.get(obj.season_type, ('#64748b', 'fas fa-tag', obj.season_type))
        return format_html(
            '<span class="badge" style="background-color: {}; color: #fff; padding: 4px 8px;">'
            '<i class="{} mr-1"></i>{}</span>',
            color, icon, label
        )

    @admin.display(description='Date Range')
    def date_range_display(self, obj):
        return format_html(
            '<span style="color: #e2e8f0; font-size: 12px;"><i class="far fa-calendar-alt text-info mr-1"></i>{} → {}</span>',
            obj.start_date.strftime('%d/%m/%y'), obj.end_date.strftime('%d/%m/%y')
        )

    @admin.display(description='Surge Multiplier')
    def surge_badge(self, obj):
        sign = "+" if obj.surge_percentage >= 0 else ""
        color = '#ef4444' if obj.surge_percentage > 0 else ('#10b981' if obj.surge_percentage < 0 else '#64748b')
        return format_html(
            '<span class="badge" style="background-color: {}; color: #fff; padding: 4px 8px; font-weight: 700;">{}{}%</span>',
            color, sign, obj.surge_percentage
        )

    @admin.display(description='Price Overrides')
    def override_prices_display(self, obj):
        if obj.price_with_food_override:
            return format_html('<span style="color: #10b981; font-weight: 600;">₹{} (Food)</span>', f"{obj.price_with_food_override:,.0f}")
        return mark_safe('<span style="color: #64748b;">Formula Multiplier</span>')


# ==============================================================================
# 7. Hotel Room Allotment Admin
# ==============================================================================

@admin.register(PackageHotelAllotment)
class PackageHotelAllotmentAdmin(ModelAdmin):
    list_display = ('hotel_name', 'package_link', 'room_category_badge', 'date_range_display', 'occupancy_gauge', 'cost_display', 'status_badge')
    list_filter = ('room_category', 'status', 'package')
    search_fields = ('hotel_name', 'package__name', 'confirmation_voucher_no')

    @admin.display(description='Tour Package')
    def package_link(self, obj):
        return format_html(
            '<a href="/admin/packages/package/{}/change/" style="color: #38bdf8; text-decoration: none; font-weight: 500;">{}</a>',
            obj.package.id, obj.package.name
        )

    @admin.display(description='Room Category')
    def room_category_badge(self, obj):
        return format_html(
            '<span class="badge" style="background-color: #334155; color: #f8fafc; border: 1px solid #475569; padding: 4px 8px;">'
            '<i class="fas fa-bed mr-1 text-warning"></i>{}</span>',
            obj.get_room_category_display()
        )

    @admin.display(description='Stay Period')
    def date_range_display(self, obj):
        return format_html(
            '<span class="text-xs text-slate-700 dark:text-slate-300">{} → {} ({}N)</span>',
            obj.check_in_date.strftime('%d/%m/%y'), obj.check_out_date.strftime('%d/%m/%y'), obj.nights_count
        )

    @admin.display(description='Room Occupancy')
    def occupancy_gauge(self, obj):
        color = '#10b981' if obj.occupancy_rate >= 80 else ('#f59e0b' if obj.occupancy_rate >= 50 else '#38bdf8')
        return format_html(
            '<span style="color: {}; font-weight: 700; font-size: 13px;">{}/{} Rooms ({}%)</span><br>'
            '<small style="color: #64748b;">{} Available</small>',
            color, obj.rooms_occupied, obj.rooms_blocked, f"{obj.occupancy_rate:.0f}", obj.rooms_available
        )

    @admin.display(description='Rate & Total Cost')
    def cost_display(self, obj):
        return format_html(
            '<span class="font-semibold text-slate-900 dark:text-slate-100">₹{} / night</span><br>'
            '<small class="text-slate-500 dark:text-slate-400">Total: ₹{}</small>',
            f"{obj.cost_per_room_night:,.0f}", f"{obj.total_cost:,.0f}"
        )

    @admin.display(description='Status')
    def status_badge(self, obj):
        colors = {
            'blocked': ('#d97706', 'Tentative Block'),
            'confirmed': ('#059669', 'Confirmed'),
            'partially_released': ('#f59e0b', 'Partially Released'),
            'billed': ('#0284c7', 'Billed'),
            'cancelled': ('#ef4444', 'Cancelled'),
        }
        color, label = colors.get(obj.status, ('#64748b', obj.status))
        return format_html('<span class="badge" style="background-color: {}; color: #fff; padding: 4px 8px;">{}</span>', color, label)


# ==============================================================================
# 8. Experience & Safari Add-Ons Admin
# ==============================================================================

@admin.register(PackageAddon)
class PackageAddonAdmin(ModelAdmin):
    list_display = ('title', 'package_link', 'category_badge', 'pricing_unit', 'cost_price_display', 'selling_price_display', 'margin_badge', 'is_mandatory_inclusion', 'is_active')
    list_filter = ('category', 'pricing_unit', 'is_mandatory_inclusion', 'is_active', 'package')
    search_fields = ('title', 'package__name')

    @admin.display(description='Tour Package')
    def package_link(self, obj):
        return format_html(
            '<a href="/admin/packages/package/{}/change/" style="color: #38bdf8; text-decoration: none; font-weight: 500;">{}</a>',
            obj.package.id, obj.package.name
        )

    @admin.display(description='Category')
    def category_badge(self, obj):
        return format_html('<span class="badge" style="background-color: #0369a1; color: #fff; padding: 4px 8px;">{}</span>', obj.get_category_display())

    @admin.display(description='Procurement Cost')
    def cost_price_display(self, obj):
        return format_html('<span style="color: #f87171;">₹{}</span>', f"{(obj.cost_price or 0):,.0f}")

    @admin.display(description='Selling Rate')
    def selling_price_display(self, obj):
        return format_html('<span style="color: #38bdf8; font-weight: 700;">₹{}</span>', f"{(obj.selling_price or 0):,.0f}")

    @admin.display(description='Margin')
    def margin_badge(self, obj):
        return format_html(
            '<span class="badge" style="background-color: #059669; color: #fff; padding: 4px 8px;">'
            '+₹{} ({}%)</span>',
            f"{obj.margin_per_unit:,.0f}", f"{obj.margin_percentage:.1f}"
        )


# ==============================================================================
# 9. B2B Sub-Agent Margins Admin
# ==============================================================================

@admin.register(PackageB2BMargin)
class PackageB2BMarginAdmin(ModelAdmin):
    list_display = ('tier_name_badge', 'package_link', 'commission_display', 'b2b_net_rates_display', 'is_active')
    list_filter = ('tier_name', 'is_active', 'package')
    search_fields = ('package__name',)

    @admin.display(description='B2B Partner Tier')
    def tier_name_badge(self, obj):
        return format_html('<span class="badge" style="background-color: #475569; color: #fff; padding: 4px 8px;">{}</span>', obj.get_tier_name_display())

    @admin.display(description='Tour Package')
    def package_link(self, obj):
        return format_html(
            '<a href="/admin/packages/package/{}/change/" style="color: #38bdf8; text-decoration: none;">{}</a>',
            obj.package.id, obj.package.name
        )

    @admin.display(description='Commission / Discount')
    def commission_display(self, obj):
        if obj.fixed_discount_per_pax > 0:
            return format_html('<span style="color: #10b981; font-weight: 700;">Flat ₹{} Off/pax</span>', f"{obj.fixed_discount_per_pax:,.0f}")
        return format_html('<span style="color: #10b981; font-weight: 700;">{}% Commission</span>', obj.commission_percent)

    @admin.display(description='B2B Net Buying Price')
    def b2b_net_rates_display(self, obj):
        return format_html(
            '<span style="color: #38bdf8; font-weight: 600;">₹{} (With Food)</span> | '
            '<span style="color: #94a3b8;">₹{} (No Food)</span>',
            f"{obj.net_b2b_rate_with_food:,.0f}", f"{obj.net_b2b_rate_without_food:,.0f}"
        )


# ==============================================================================
# 10. Post-Trip Customer Feedback & NPS Admin
# ==============================================================================

@admin.register(TourFeedbackLog)
class TourFeedbackLogAdmin(ModelAdmin):
    list_display = (
        'guest_name_display', 'package_link', 'trip_date',
        'star_rating_display', 'dimension_scores_display', 'nps_badge',
        'flag_status_badge', 'verified_badge'
    )
    list_filter = ('overall_rating', 'flag_status', 'is_verified', 'trip_date', 'package')
    search_fields = ('guest_name', 'guest_phone', 'customer_review_text', 'package__name')
    date_hierarchy = 'trip_date'
    actions = ['mark_feedback_verified', 'resolve_quality_complaint']

    @admin.action(description="✅ Mark selected feedback as Verified")
    def mark_feedback_verified(self, request, queryset):
        queryset.update(is_verified=True)
        self.message_user(request, f"{queryset.count()} review(s) marked as verified.")

    @admin.action(description="🎉 Mark complaints as Resolved by Management")
    def resolve_quality_complaint(self, request, queryset):
        queryset.update(flag_status='resolved')
        self.message_user(request, f"{queryset.count()} complaint(s) marked as resolved.")

    @admin.display(description='Customer')
    def guest_name_display(self, obj):
        phone_str = f"<br><small style='color: #94a3b8;'>{obj.guest_phone}</small>" if obj.guest_phone else ""
        return format_html(
            '<span style="font-weight: 700; color: #f8fafc;"><i class="fas fa-user-check text-success mr-1"></i>{}</span>{}',
            obj.guest_name, mark_safe(phone_str)
        )

    @admin.display(description='Tour Package')
    def package_link(self, obj):
        return format_html(
            '<a href="/admin/packages/package/{}/change/" style="color: #38bdf8; text-decoration: none; font-weight: 500;">{}</a>',
            obj.package.id, obj.package.name
        )

    @admin.display(description='Overall Rating')
    def star_rating_display(self, obj):
        stars = "★" * obj.overall_rating + "☆" * (5 - obj.overall_rating)
        color = '#fbbf24' if obj.overall_rating >= 4 else ('#f59e0b' if obj.overall_rating == 3 else '#ef4444')
        return format_html(
            '<span style="color: {}; font-size: 14px; font-weight: 700;">{}</span> '
            '<small style="color: #94a3b8;">({}/5)</small>',
            color, stars, obj.overall_rating
        )

    @admin.display(description='5D Quality Scores')
    def dimension_scores_display(self, obj):
        return format_html(
            '<small class="text-xs text-slate-600 dark:text-slate-400">Coach: <b class="text-slate-900 dark:text-slate-100">{}★</b> | Hotel: <b class="text-slate-900 dark:text-slate-100">{}★</b> | Food: <b class="text-slate-900 dark:text-slate-100">{}★</b> | Route: <b class="text-slate-900 dark:text-slate-100">{}★</b></small>',
            obj.coach_driver_rating, obj.hotel_rating, obj.food_rating, obj.schedule_rating
        )

    @admin.display(description='NPS Score')
    def nps_badge(self, obj):
        colors = {
            'Promoter 🟢': '#059669',
            'Passive 🟡': '#d97706',
            'Detractor 🔴': '#dc2626',
        }
        cat = obj.nps_category
        return format_html(
            '<span class="badge" style="background-color: {}; color: #fff; padding: 4px 8px;">NPS {} ({})</span>',
            colors.get(cat, '#334155'), obj.nps_score, cat
        )

    @admin.display(description='Quality Status')
    def flag_status_badge(self, obj):
        colors = {
            'positive': ('#059669', 'Positive'),
            'neutral': ('#64748b', 'Neutral'),
            'escalated_complaint': ('#dc2626', 'Escalated Complaint'),
            'resolved': ('#10b981', 'Resolved'),
        }
        color, label = colors.get(obj.flag_status, ('#64748b', obj.flag_status))
        return format_html(
            '<span class="badge" style="background-color: {}; color: #fff; padding: 4px 8px;">{}</span>',
            color, label
        )

    @admin.display(description='Verified')
    def verified_badge(self, obj):
        if obj.is_verified:
            return mark_safe('<span style="color: #10b981;"><i class="fas fa-check-circle"></i> Verified</span>')
        return mark_safe('<span style="color: #94a3b8;">Unverified</span>')


# ==============================================================================
# Hidden Registrations for URL & Autocomplete Support
# ==============================================================================

@admin.register(PackageInventory)
class PackageInventoryHiddenAdmin(ModelAdmin):
    search_fields = ('package__name',)
    def has_module_permission(self, request):
        return False

@admin.register(BoardingPoint)
class BoardingPointHiddenAdmin(ModelAdmin):
    search_fields = ('stop_name',)
    def has_module_permission(self, request):
        return False

@admin.register(CollegeIVExpedition)
class CollegeIVExpeditionHiddenAdmin(ModelAdmin):
    search_fields = ('college_name', 'department_and_batch')
    def has_module_permission(self, request):
        return False

@admin.register(TourPassengerManifest)
class TourPassengerManifestHiddenAdmin(ModelAdmin):
    search_fields = ('passenger_name', 'seat_number')
    def has_module_permission(self, request):
        return False
