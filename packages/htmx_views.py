import datetime
from decimal import Decimal
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from django.utils.html import escape

from packages.models import Package, PackageTemplate, PackageVehicleTariff
from core.models import VehicleType


CATEGORY_INTEL_DATA = {
    'devotional': {
        'badge': 'Temple & Pilgrimage Circuit',
        'badge_class': 'bg-purple-600 text-white',
        'title': 'Sacred Circuit & Darshan Logistics Protocol',
        'rules': [
            {'icon': 'temple_hindu', 'label': 'Devotional Protocol', 'desc': 'Satvik pure vegetarian meals strictly mandatory. Early morning temple darshan coordination active.'},
            {'icon': 'elderly', 'label': 'Senior Pilgrim Care', 'desc': 'Wheelchair assistance and ground-floor room allotments prioritized for senior citizens.'},
            {'icon': 'checkroom', 'label': 'Dress Code Enforced', 'desc': 'Traditional dhoti / saree mandatory for sanctum sanctorum entry. Checklist auto-populated.'},
            {'icon': 'schedule', 'label': 'Slot Coordination', 'desc': 'TempleDarshanSlot inline auto-activated below for reporting times and VIP passes.'},
        ],
        'jump_links': [
            {'target': 'step-4', 'label': 'Devotional Specifications'},
            {'target': 'templedarshanslot', 'label': 'Darshan Slots Inline'},
            {'target': 'step-2', 'label': 'Pricing & Units'},
        ],
        'recommended_inclusions': 'AC Deluxe Coach transit, Satvik Pure Veg Meals (Breakfast, Lunch, Dinner), Temple Special Entry Darshan Passes, Pilgrim Guide, Clean Hotel Accommodation (Twin/Triple Sharing), Toll, Parking & Interstate Permits.',
        'recommended_exclusions': 'Personal pooja / archana expenses, special tonsure (mottai) charges, extra prasad purchases, room service, laundry, anything not mentioned in inclusions.',
    },
    'college_iv': {
        'badge': 'College Industrial Visit & Expedition',
        'badge_class': 'bg-amber-600 text-white',
        'title': 'Industrial Visit & Student Tour Operations Protocol',
        'rules': [
            {'icon': 'factory', 'label': 'Industry Clearance', 'desc': 'Factory permission letter / entry clearance required. Document checklist auto-linked.'},
            {'icon': 'nightlife', 'label': 'Campfire & DJ', 'desc': 'Campfire with DJ setup permitted strictly up to 10:00 PM as per forest & local regulations.'},
            {'icon': 'local_police', 'label': 'Headcount Tracking', 'desc': 'Mandatory faculty in-charge escort ratio (1 faculty per 15 students free of cost).'},
            {'icon': 'badge', 'label': 'Digital Manifest', 'desc': 'Passenger manifest with roll numbers and emergency guardian contacts linked to this expedition.'},
        ],
        'jump_links': [
            {'target': 'step-2', 'label': 'Student Dual Pricing'},
            {'target': 'step-3', 'label': 'Coach Fleet Logistics'},
            {'target': 'step-4', 'label': 'Stay, DJ & Safaris'},
        ],
        'recommended_inclusions': '54-Seater Luxury Pushback Coach with 2x2 Seating, Music System & LED Lights, Deluxe Quad/Triple Sharing Hotel Stay, Daily Buffet Breakfast, Lunch & Dinner, DJ Night with Campfire, Factory Permission Assistance, Accompanying Faculty Free Accommodation.',
        'recommended_exclusions': 'Industrial entry ticket fees (if charged by plant), personal snacks/beverages, boating/safari tickets unless specified, student medical personal expenses.',
    },
    'international': {
        'badge': 'Overseas & Cross-Border Tour',
        'badge_class': 'bg-sky-600 text-white',
        'title': 'International Border, Visa & Currency Protocol',
        'rules': [
            {'icon': 'flight_takeoff', 'label': 'Airfare & DMC', 'desc': 'Return economy group airfare, airport transfers, and overseas DMC partner support.'},
            {'icon': 'pin', 'label': 'Passport Validity', 'desc': 'Minimum 6 months passport validity from intended date of departure strictly verified.'},
            {'icon': 'description', 'label': 'Tourist Visa', 'desc': 'eVisa / Embassy sticker visa processing timeline: minimum 15 business days advance.'},
            {'icon': 'currency_exchange', 'label': 'Forex Pricing', 'desc': 'Dual currency quotation (USD/AED/EUR + INR) with ROE fluctuation buffer included.'},
        ],
        'jump_links': [
            {'target': 'step-4', 'label': 'Overseas & Visa Specs'},
            {'target': 'internationaldocumentchecklist', 'label': 'Document Checklist Inline'},
            {'target': 'step-2', 'label': 'Dual Currency Pricing'},
        ],
        'recommended_inclusions': 'Return Economy Flight Tickets, 3-Star / 4-Star Luxury City Hotel, Daily Continental Breakfast & Indian Dinners, Tourist eVisa Processing Fees, Overseas Travel Insurance, Airport & Sightseeing Transfers in AC Coach, English-Speaking Tour Manager.',
        'recommended_exclusions': 'Passport renewal fees, personal baggage excess charges, optional adventure activities, tourism dirham / city tax payable directly at hotel, minibar.',
    },
    'hill_station': {
        'badge': 'Hill Station & Nature Expedition',
        'badge_class': 'bg-emerald-600 text-white',
        'title': 'Hill Station, Plantation & Jeep Safari Protocol',
        'rules': [
            {'icon': 'terrain', 'label': 'Ghat Road Transit', 'desc': 'Experienced ghat road hill captains assigned. Mini bus / Tempo Traveller recommended for hairpin bends.'},
            {'icon': 'forest', 'label': 'Tea/Coffee Estates', 'desc': 'Plantation walking tour, view point permits, and scenic lake boating included.'},
            {'icon': 'fire_hydrant', 'label': 'Estate Bonfire', 'desc': 'Cottage or resort bonfire arranged in the evening subject to weather conditions.'},
        ],
        'jump_links': [
            {'target': 'step-1', 'label': 'Tour Identity'},
            {'target': 'step-3', 'label': 'Coach Fleet Specs'},
            {'target': 'step-4', 'label': 'Resort & Activities'},
        ],
        'recommended_inclusions': 'AC/Non-AC Deluxe Hill Coach transit, Premium Tea Estate Resort / Valley View Cottages, Breakfast & Dinner, Sightseeing as per itinerary, Forest entry permits, Toll and Hill Interstate taxes.',
        'recommended_exclusions': 'Jeep safari tickets, boating fees, personal shopping (tea, homemade chocolates, spices), heater charges at hotel if requested.',
    },
    'local_tour': {
        'badge': '1-Day City Sightseeing & Pilgrimage',
        'badge_class': 'bg-cyan-600 text-white',
        'title': 'Single Day Rapid Circuit Protocol',
        'rules': [
            {'icon': 'directions_car', 'label': '1-Day Quick Transit', 'desc': 'Fixed 0 Nights / 1 Day circuit. Early morning departure and late evening return.'},
            {'icon': 'speed', 'label': 'Driver Bata & Tolls', 'desc': 'Single day driver allowance, toll fees, and parking charges inclusive.'},
        ],
        'jump_links': [
            {'target': 'step-1', 'label': 'Duration (0N/1D)'},
            {'target': 'step-2', 'label': 'Day Tariff'},
            {'target': 'step-5', 'label': 'Inclusions Checklist'},
        ],
        'recommended_inclusions': 'AC Sedan / Innova / Tempo Traveller for full day (up to 12 hours / 250 km), Fuel, Driver Bata, Toll & Parking charges.',
        'recommended_exclusions': 'Monument entry tickets, guide fees, breakfast/lunch meals, extra km/hours beyond agreed limits.',
    },
    'corporate_offsite': {
        'badge': 'Corporate MICE & Team Offsite',
        'badge_class': 'bg-blue-600 text-white',
        'title': 'Corporate Retreat & Leadership Workshop Protocol',
        'rules': [
            {'icon': 'corporate_fare', 'label': 'Conference Hall', 'desc': 'Banquet / conference facility with projector, audio system, and hi-tea arrangements.'},
            {'icon': 'groups', 'label': 'Team Activities', 'desc': 'Custom outbound team building activities, games coordinator, and evening cocktail dinner.'},
        ],
        'jump_links': [
            {'target': 'step-2', 'label': 'Corporate Unit Economics'},
            {'target': 'step-4', 'label': 'Resort & Banquet'},
            {'target': 'step-5', 'label': 'B2B GST Terms'},
        ],
        'recommended_inclusions': 'Luxury AC Coaches, 4-Star/5-Star Business Resort Stay, All Meals (Breakfast, Buffet Lunch, High Tea, Gala Dinner), Conference Hall with AV Equipment, Team Building Facilitator.',
        'recommended_exclusions': 'Alcoholic beverages (unless pre-contracted), spa treatments, personal telephone/laundry charges, 18% GST extra as applicable.',
    },
    'fixed_departure': {
        'badge': 'Fixed Seat Departure / Public Group',
        'badge_class': 'bg-indigo-600 text-white',
        'title': 'Public Group Seat-In-Coach (SIC) Protocol',
        'rules': [
            {'icon': 'departure_board', 'label': 'Seat Inventory', 'desc': 'Scheduled departures on confirmed calendar dates with per-seat seat reservation.'},
            {'icon': 'alt_route', 'label': 'Fixed Boarding Points', 'desc': 'Standard boarding and drop points strictly followed. Seat numbers allocated in advance.'},
        ],
        'jump_links': [
            {'target': 'step-2', 'label': 'Per-Pax Pricing'},
            {'target': 'step-3', 'label': 'Seat Allocation'},
            {'target': 'step-4', 'label': 'Hotel Rooming'},
        ],
        'recommended_inclusions': 'Confirmed Coach Seat, Hotel Accommodation on Twin/Triple Sharing, Breakfast & Dinner, Tour Escort, Tolls & Permits.',
        'recommended_exclusions': 'Single supplement room upgrade, monument entry fees, porterage, tips to driver & guide.',
    },
}


@login_required
@require_http_methods(["GET", "POST"])
def package_category_intel(request):
    """
    HTMX endpoint that returns dynamic category operational intelligence,
    protocol rules, and recommended inclusions/exclusions.
    """
    params = request.POST if request.method == 'POST' else request.GET
    category = params.get('category') or params.get('id_category') or 'college_iv'
    package_id = params.get('package_id')

    package = None
    if package_id:
        try:
            package = Package.objects.filter(pk=package_id).first()
        except Exception:
            package = None

    intel = CATEGORY_INTEL_DATA.get(category, CATEGORY_INTEL_DATA['college_iv'])

    return render(request, 'packages/partials/category_intel_card.html', {
        'category': category,
        'intel': intel,
        'package': package,
    })


@login_required
@require_http_methods(["GET", "POST"])
def package_unit_economics(request):
    """
    HTMX endpoint calculating live unit economics, gross margins, breakeven,
    and convoy operating P&L for Siva Gayathri Tours.
    """
    params = request.POST if request.method == 'POST' else request.GET

    def parse_dec(key, default='0.00'):
        raw = params.get(key, default)
        if raw is None or str(raw).strip() == '':
            return Decimal(default)
        try:
            clean = str(raw).replace(',', '').replace('₹', '').strip()
            return Decimal(clean)
        except Exception:
            return Decimal(default)

    def parse_int(key, default=50):
        raw = params.get(key, default)
        try:
            val = int(str(raw).strip())
            return val if val > 0 else default
        except Exception:
            return default

    min_pax = parse_int('min_pax', 50)
    price_with_food = parse_dec('price_with_food', '0.00')
    price_without_food = parse_dec('price_without_food', '0.00')
    base_price = parse_dec('base_price', '0.00')

    cost_hotel = parse_dec('cost_hotel_per_pax', '0.00')
    cost_coach = parse_dec('cost_coach_per_pax', '0.00')
    cost_meals = parse_dec('cost_meals_per_pax', '0.00')
    cost_activities = parse_dec('cost_activities_per_pax', '0.00')
    cost_misc = parse_dec('cost_misc_per_pax', '0.00')

    # Total direct costs
    total_direct_cost = cost_hotel + cost_coach + cost_meals + cost_activities + cost_misc
    total_direct_no_meals = cost_hotel + cost_coach + cost_activities + cost_misc

    # Effective selling price
    effective_selling_with_food = price_with_food if price_with_food > 0 else base_price
    effective_selling_no_food = price_without_food if price_without_food > 0 else (effective_selling_with_food * Decimal('0.75') if effective_selling_with_food > 0 else Decimal('0.00'))

    # Unit margins
    unit_margin_with_food = effective_selling_with_food - total_direct_cost
    margin_pct_with_food = (unit_margin_with_food / effective_selling_with_food * 100) if effective_selling_with_food > 0 else Decimal('0.0')

    unit_margin_no_food = effective_selling_no_food - total_direct_no_meals
    margin_pct_no_food = (unit_margin_no_food / effective_selling_no_food * 100) if effective_selling_no_food > 0 else Decimal('0.0')

    # Total convoy economics (Convoy = min_pax)
    convoy_turnover = effective_selling_with_food * min_pax
    convoy_direct_cost = total_direct_cost * min_pax
    convoy_gross_profit = convoy_turnover - convoy_direct_cost

    # Health status badge
    if effective_selling_with_food <= 0 or total_direct_cost <= 0:
        health_status = 'neutral'
        health_label = 'Configure Costs & Rates'
        health_color = 'bg-slate-700 text-slate-200'
    elif margin_pct_with_food >= 20:
        health_status = 'exceptional'
        health_label = f'Robust Margin (+{margin_pct_with_food:.1f}%)'
        health_color = 'bg-emerald-600 text-white'
    elif margin_pct_with_food >= 14:
        health_status = 'healthy'
        health_label = f'Healthy Margin (+{margin_pct_with_food:.1f}%)'
        health_color = 'bg-teal-600 text-white'
    elif margin_pct_with_food >= 8:
        health_status = 'thin'
        health_label = f'Thin Margin (+{margin_pct_with_food:.1f}%)'
        health_color = 'bg-amber-600 text-white'
    else:
        health_status = 'danger'
        health_label = f'Low Margin Warning ({margin_pct_with_food:.1f}%)'
        health_color = 'bg-rose-600 text-white'

    breakeven_pax_at_selling = (total_direct_cost * min_pax / effective_selling_with_food) if effective_selling_with_food > 0 else min_pax

    context = {
        'min_pax': min_pax,
        'price_with_food': effective_selling_with_food,
        'price_without_food': effective_selling_no_food,
        'cost_hotel': cost_hotel,
        'cost_coach': cost_coach,
        'cost_meals': cost_meals,
        'cost_activities': cost_activities,
        'cost_misc': cost_misc,
        'total_direct_cost': total_direct_cost,
        'total_direct_no_meals': total_direct_no_meals,
        'unit_margin_with_food': unit_margin_with_food,
        'margin_pct_with_food': margin_pct_with_food,
        'unit_margin_no_food': unit_margin_no_food,
        'margin_pct_no_food': margin_pct_no_food,
        'convoy_turnover': convoy_turnover,
        'convoy_gross_profit': convoy_gross_profit,
        'breakeven_rate': total_direct_cost,
        'breakeven_pax': int(breakeven_pax_at_selling + Decimal('0.99')),
        'health_label': health_label,
        'health_color': health_color,
        'health_status': health_status,
    }

    return render(request, 'packages/partials/unit_economics_card.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def package_tariff_calculate(request):
    """
    HTMX helper for fleet vehicle tariff calculations based on vehicle type and duration.
    """
    params = request.POST if request.method == 'POST' else request.GET
    vtype_id = params.get('vehicle_type_id') or params.get('vehicle_type')
    duration_days = int(params.get('duration_days') or 3)
    rate_type = params.get('rate_type') or 'daily'

    vtype = None
    if vtype_id:
        try:
            vtype = VehicleType.objects.filter(pk=vtype_id).first()
        except Exception:
            vtype = None

    if not vtype:
        vtype = VehicleType.objects.first()

    if not vtype:
        return JsonResponse({'error': 'No vehicle types available'}, status=400)

    # Standard Siva Gayathri fleet computation
    km_per_day = 300
    total_km = km_per_day * duration_days
    base_km_rate = vtype.default_km_rate or Decimal('25.00')

    # Driver bata per day based on vehicle category
    driver_bata = Decimal('800.00') if vtype.category in ['bus', 'van'] else Decimal('500.00')
    per_day_hire = (base_km_rate * Decimal(str(km_per_day))) + driver_bata
    package_rate = per_day_hire * Decimal(str(duration_days))

    data = {
        'vehicle_type_id': vtype.id,
        'vehicle_type_name': vtype.name,
        'seating_capacity': vtype.seating_capacity,
        'duration_days': duration_days,
        'included_km': total_km,
        'extra_km_rate': float(base_km_rate),
        'driver_bata_per_day': float(driver_bata),
        'per_day_rate': float(per_day_hire),
        'package_rate': float(package_rate),
    }

    if request.headers.get('HX-Request') or 'html' in request.GET.get('format', ''):
        return render(request, 'packages/partials/tariff_calc_fragment.html', data)

    return JsonResponse(data)


@login_required
@require_http_methods(["GET"])
def package_whatsapp_briefing(request):
    """
    HTMX modal endpoint generating formatted WhatsApp briefing pitches
    ready to 1-click copy or launch in WhatsApp Web / App.
    """
    package_id = request.GET.get('package_id')
    package = None
    if package_id:
        try:
            package = Package.objects.filter(pk=package_id).first()
        except Exception:
            package = None

    name = package.name if package else (request.GET.get('name') or 'Custom Tour Expedition')
    dest = package.destination if package else (request.GET.get('destination') or 'Tamil Nadu / South India')
    days = package.duration_days if package else int(request.GET.get('duration_days') or 3)
    nights = package.duration_nights if package else int(request.GET.get('duration_nights') or 2)
    p_food = package.price_with_food if package else Decimal(request.GET.get('price_with_food') or '0')
    p_nofood = package.price_without_food if package else Decimal(request.GET.get('price_without_food') or '0')

    # 1. Client Proposal Pitch
    client_pitch = f"""✨ *SIVA GAYATHRI TOURS & TRAVELS* ✨
📍 *Tour Circuit:* {name} ({dest})
🗓️ *Duration:* {nights} Nights / {days} Days

💰 *Dual Rate Options per Head:*
👉 *With Food (Full Boarding):* ₹{p_food:,.0f} / pax
👉 *Without Food (Accom Only):* ₹{p_nofood:,.0f} / pax

🚍 *Inclusions:*
✔️ Pushback AC Luxury Coach with Music & LED
✔️ Hotel Accommodation (Twin/Triple Sharing)
✔️ Daily Buffet Meals as per plan
✔️ All Sightseeing & Viewpoint Permits
✔️ Driver Bata, Toll & Interstate Permits

📄 *View Detailed Proposal Quotation:*
https://sivagayathritours.com/packages/quote/{package.id if package else 'preview'}/

📞 For bookings & customization, reply to this message!"""

    # 2. Driver / Coach Logistics Dispatch
    driver_dispatch = f"""🚍 *TRIP DISPATCH & FLEET BRIEFING* 🚍
🚩 *Package:* {name}
📍 *Circuit:* {dest}
🗓️ *Days:* {days}D / {nights}N
⚠️ *Vehicle Class:* Luxury Coach / Mini Bus
⛽ Please ensure full tank diesel, FASTag recharge, and mandatory safety pre-trip inspection completed.
📞 Fleet Dispatch Desk: 919876543210"""

    # 3. Faculty / Group Coordinator Briefing
    faculty_briefing = f"""🎓 *COLLEGE INDUSTRIAL VISIT CONFIRMATION* 🎓
🏛️ *Expedition:* {name}
🗓️ *Duration:* {days} Days / {nights} Nights
👥 *Faculty Escort Ratio:* 1:15 Free of Cost
🏢 Industrial Visit Plant Clearances & Bonfire DJ organized.
📋 Please submit final student passenger manifest before departure date."""

    return render(request, 'packages/partials/whatsapp_modal.html', {
        'package': package,
        'client_pitch': client_pitch,
        'driver_dispatch': driver_dispatch,
        'faculty_briefing': faculty_briefing,
    })


@login_required
@require_http_methods(["GET"])
def package_proposal_preview_modal(request):
    """
    HTMX modal endpoint displaying live PDF proposal quotation preview.
    """
    package_id = request.GET.get('package_id')
    package = None
    if package_id:
        try:
            package = Package.objects.filter(pk=package_id).first()
        except Exception:
            package = None

    quote_url = f"/packages/quote/{package.id}/" if package else "/packages/quote/preview/"

    return render(request, 'packages/partials/proposal_modal.html', {
        'package': package,
        'quote_url': quote_url,
    })
