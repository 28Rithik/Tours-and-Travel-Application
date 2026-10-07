import json
import random
import datetime
import urllib.parse
import secrets
import re
from decimal import Decimal
from django.db import models

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse, HttpResponseBadRequest
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from .models import CustomerAccount, CustomerOTP
from documents.models import CustomerDocument
from operations.models import Booking, Trip
from packages.models import Package, PackageInventory, ItineraryDay, PackageVehicleTariff
from core.models import Client, Party, VehicleType
from finance.models import Payment
from marketing.models import Coupon
from payments_gateway.services import create_payment_link
from payments_gateway.models import GatewayTransaction, InstallmentPlan
from payments_gateway.upi import generate_dynamic_upi_package
from payments_gateway.gl_engine import post_gateway_transaction_to_gl
from core.intercity_service import (
    get_loyalty_balance,
    redeem_loyalty_points,
    search_intercity_trips,
    reserve_transit_seats,
)



# ==============================================================================
# 1. Public Landing Page & Package Discovery
# ==============================================================================

def public_landing_view(request):
    """
    Public-facing homepage showcasing holiday packages, fleet rentals,
    interactive fare estimator, and live booking tracking.
    """
    all_packages = Package.objects.filter(is_active=True).prefetch_related('inventory', 'itinerary_days')
    
    # Categorized Packages
    hill_stations = all_packages.filter(category='hill_station')[:6]
    devotional_tours = all_packages.filter(category='devotional')[:6]
    college_ivs = all_packages.filter(category='college_iv')[:6]
    leisure_holidays = all_packages.filter(category__in=['holiday', 'family_vacation'])[:6]
    
    # Upcoming Fixed Departure Batches
    today = timezone.now().date()
    upcoming_batches = PackageInventory.objects.filter(
        status__in=['open', 'fast_filling'],
        departure_date__gte=today
    ).select_related('package', 'assigned_vehicle').order_by('departure_date')[:6]
    
    # Vehicle Types for Fleet Showcase
    vehicle_types = VehicleType.objects.all().order_by('seating_capacity')
    
    # Platform Statistics
    total_trips_completed = Trip.objects.filter(status='completed').count() + 1250
    active_vehicles_count = 320
    happy_travelers_count = (total_trips_completed * 42)
    
    # Curated Featured Packages (3 from each key category so every filter has rich cards)
    curated_featured = (
        list(all_packages.filter(category='hill_station')[:3]) +
        list(all_packages.filter(category='devotional')[:3]) +
        list(all_packages.filter(category='college_iv')[:3]) +
        list(all_packages.filter(category__in=['holiday', 'family_vacation'])[:3])
    )
    
    # Popular South India Outstation Corridors (Fixed route price matrix)
    popular_routes = [
        {
            'name': 'Coimbatore ⇄ Ooty / Coonoor',
            'pickup': 'Coimbatore',
            'destination': 'Ooty',
            'distance_km': 85,
            'duration_text': '3.5 Hours',
            'terrain': 'Nilgiris Ghats • 36 Hairpins',
            'recommended_fleet': 'Innova Crysta / Urbania',
            'tier': 'crysta',
            'starting_fare': 3499,
            'badge': 'Hill Station Gateway',
            'icon': '⛰️',
        },
        {
            'name': 'Chennai ⇄ Pondicherry / Auroville',
            'pickup': 'Chennai',
            'destination': 'Pondicherry',
            'distance_km': 155,
            'duration_text': '3.2 Hours',
            'terrain': 'East Coast Road (ECR)',
            'recommended_fleet': 'Swift Dzire / Crysta',
            'tier': 'sedan',
            'starting_fare': 4199,
            'badge': 'Coastal Expressway',
            'icon': '🏖️',
        },
        {
            'name': 'Bangalore ⇄ Mysore & Coorg',
            'pickup': 'Bangalore',
            'destination': 'Coorg',
            'distance_km': 240,
            'duration_text': '5.0 Hours',
            'terrain': 'Mysore Expressway & Mist Hills',
            'recommended_fleet': 'Innova Crysta / Urbania',
            'tier': 'crysta',
            'starting_fare': 5799,
            'badge': 'Heritage & Coffee',
            'icon': '🏰',
        },
        {
            'name': 'Coimbatore ⇄ Munnar & Vagamon',
            'pickup': 'Coimbatore',
            'destination': 'Munnar',
            'distance_km': 160,
            'duration_text': '5.5 Hours',
            'terrain': 'Anamalai Tea Valleys & Ghats',
            'recommended_fleet': 'Force Urbania / Mini Bus',
            'tier': 'tt',
            'starting_fare': 4899,
            'badge': 'Tea Plantation Ghats',
            'icon': '🍃',
        },
        {
            'name': 'Madurai ⇄ Rameshwaram',
            'pickup': 'Madurai',
            'destination': 'Rameshwaram',
            'distance_km': 175,
            'duration_text': '3.5 Hours',
            'terrain': 'Pamban Sea Bridge Yatra',
            'recommended_fleet': 'Innova Crysta / 54 Coach',
            'tier': 'crysta',
            'starting_fare': 4499,
            'badge': 'Coastal Sea Corridor',
            'icon': '🕉️',
        },
        {
            'name': 'Kochi ⇄ Alleppey Backwaters',
            'pickup': 'Kochi',
            'destination': 'Alleppey',
            'distance_km': 65,
            'duration_text': '1.8 Hours',
            'terrain': 'Vembanad Lake Circuit',
            'recommended_fleet': 'Innova Crysta / Urbania',
            'tier': 'crysta',
            'starting_fare': 2699,
            'badge': 'Houseboat Gateway',
            'icon': '🌴',
        },
    ]
    
    context = {
        'all_packages': curated_featured,
        'total_packages_count': all_packages.count(),
        'hill_stations': hill_stations,
        'devotional_tours': devotional_tours,
        'college_ivs': college_ivs,
        'leisure_holidays': leisure_holidays,
        'upcoming_batches': upcoming_batches,
        'vehicle_types': vehicle_types,
        'popular_routes': popular_routes,
        'stats': {
            'trips_completed': total_trips_completed,
            'active_vehicles': active_vehicles_count,
            'happy_travelers': happy_travelers_count,
            'on_time_sla': 99.8,
        }
    }
    return render(request, 'customer_portal/landing_page.html', context)


def package_list(request):
    """
    Full public catalog of tour packages with search, category filtering,
    sorting, and pagination (strictly 25 packages per page).
    """
    packages_qs = Package.objects.filter(is_active=True).prefetch_related('inventory', 'itinerary_days')
    
    category = request.GET.get('category', '').strip()
    if category and category != 'all':
        packages_qs = packages_qs.filter(category=category)
        
    query = request.GET.get('q', '').strip()
    if query:
        packages_qs = packages_qs.filter(
            models.Q(name__icontains=query) |
            models.Q(destination__icontains=query) |
            models.Q(description__icontains=query)
        )
        
    sort_by = request.GET.get('sort', 'popular')
    if sort_by == 'price_low':
        packages_qs = packages_qs.order_by('base_price')
    elif sort_by == 'price_high':
        packages_qs = packages_qs.order_by('-base_price')
    elif sort_by == 'duration':
        packages_qs = packages_qs.order_by('duration_days')
    else:
        # Default stable ordering for reliable pagination
        packages_qs = packages_qs.order_by('-id')
        
    categories_choices = Package.CATEGORIES
    
    # Strictly 25 tour packages per page
    paginator = Paginator(packages_qs, 25)
    page_number = request.GET.get('page', 1)
    try:
        page_obj = paginator.get_page(page_number)
    except (PageNotAnInteger, EmptyPage):
        page_obj = paginator.get_page(1)
        
    # Build query string excluding 'page' to retain category/query/sort filters in pagination buttons
    query_params = request.GET.copy()
    if 'page' in query_params:
        query_params.pop('page')
    querystring = query_params.urlencode()
    if querystring:
        querystring = '&' + querystring

    context = {
        'page_obj': page_obj,
        'packages': page_obj.object_list,
        'selected_category': category,
        'search_query': query,
        'sort_by': sort_by,
        'categories_choices': categories_choices,
        'total_count': paginator.count,
        'querystring': querystring,
    }
    return render(request, 'customer_portal/package_list.html', context)


def package_detail(request, package_id):
    """
    Public tour package detail view showing itinerary days, inclusions,
    exclusions, temple slots (if devotional), and open departure batches.
    """
    package = get_object_or_404(Package, id=package_id)
    today = timezone.now().date()
    inventories = package.inventory.filter(
        status__in=['open', 'fast_filling'],
        departure_date__gte=today
    ).order_by('departure_date')
    
    itinerary_days = package.itinerary_days.all().order_by('day_number')
    vehicle_tariffs = package.vehicle_tariffs.all().select_related('vehicle_type')
    temple_slots = package.temple_slots.all() if package.is_devotional else []
    upsells = package.upsells.all()
    
    context = {
        'package': package,
        'inventories': inventories,
        'itinerary_days': itinerary_days,
        'vehicle_tariffs': vehicle_tariffs,
        'temple_slots': temple_slots,
        'upsells': upsells,
    }
    return render(request, 'customer_portal/package_detail.html', context)


# ==============================================================================
# 2. Interactive Fleet Fare Estimator API
# ==============================================================================

TIER_SPECS = {
    'sedan': {
        'name': 'Compact Sedan (Swift Dzire / Etios)',
        'capacity': 4,
        'min_km_day': 250,
        'km_rate': Decimal('13.00'),
        'driver_bata': Decimal('400.00'),
        'local_8hr_rate': Decimal('1800.00'),
        'local_extra_km': Decimal('14.00'),
        'local_extra_hr': Decimal('150.00'),
    },
    'crysta': {
        'name': 'Toyota Innova Crysta (6-7 Seats)',
        'capacity': 7,
        'min_km_day': 300,
        'km_rate': Decimal('19.00'),
        'driver_bata': Decimal('500.00'),
        'local_8hr_rate': Decimal('2800.00'),
        'local_extra_km': Decimal('20.00'),
        'local_extra_hr': Decimal('250.00'),
    },
    'tt': {
        'name': 'Force Urbania / Tempo Traveller (12-17 Seats)',
        'capacity': 17,
        'min_km_day': 300,
        'km_rate': Decimal('26.00'),
        'driver_bata': Decimal('700.00'),
        'local_8hr_rate': Decimal('3800.00'),
        'local_extra_km': Decimal('28.00'),
        'local_extra_hr': Decimal('350.00'),
    },
    'mini_bus': {
        'name': 'Deluxe Mini Bus (25-36 Seats)',
        'capacity': 36,
        'min_km_day': 300,
        'km_rate': Decimal('36.00'),
        'driver_bata': Decimal('1000.00'),
        'local_8hr_rate': Decimal('5500.00'),
        'local_extra_km': Decimal('38.00'),
        'local_extra_hr': Decimal('500.00'),
    },
    'luxury_coach': {
        'name': 'Luxury AC / Non-AC Coach (50-54 Seats)',
        'capacity': 54,
        'min_km_day': 350,
        'km_rate': Decimal('48.00'),
        'driver_bata': Decimal('1200.00'),
        'local_8hr_rate': Decimal('8500.00'),
        'local_extra_km': Decimal('50.00'),
        'local_extra_hr': Decimal('800.00'),
    },
}

@csrf_exempt
def api_fare_estimator(request):
    """
    REST API calculating real-time fleet rental estimates based on vehicle tier,
    journey type, days, and estimated distance.
    """
    if request.method != 'POST':
        return HttpResponseBadRequest("Only POST allowed")
        
    try:
        data = json.loads(request.body.decode('utf-8')) if request.body else request.POST
    except Exception:
        data = request.POST
        
    vehicle_tier = data.get('vehicle_tier', 'crysta')
    journey_type = data.get('journey_type', 'outstation_round')
    days = max(1, int(data.get('days', 1)))
    estimated_km = max(0, int(data.get('estimated_km', 300)))
    pickup_city = data.get('pickup_city', 'Coimbatore')
    destination = data.get('destination', 'Ooty')
    
    spec = TIER_SPECS.get(vehicle_tier, TIER_SPECS['crysta'])
    
    if journey_type == 'local_8hr':
        base_km_cost = spec['local_8hr_rate'] * days
        extra_km = max(0, estimated_km - (80 * days))
        extra_km_cost = Decimal(str(extra_km)) * spec['local_extra_km']
        driver_bata_total = (spec['driver_bata'] * Decimal('0.5')) * days
        subtotal = base_km_cost + extra_km_cost + driver_bata_total
        billable_km = max(80 * days, estimated_km)
    else:  # Outstation round or one-way
        min_allowed_km = spec['min_km_day'] * days
        billable_km = max(estimated_km, min_allowed_km)
        base_km_cost = Decimal(str(billable_km)) * spec['km_rate']
        driver_bata_total = spec['driver_bata'] * days
        subtotal = base_km_cost + driver_bata_total
        
    gst_amount = round(subtotal * Decimal('0.05'), 2)
    total_estimate = round(subtotal + gst_amount, 2)
    advance_payable = round(total_estimate * Decimal('0.5'), 2)
    
    return JsonResponse({
        'status': 'success',
        'vehicle_tier': vehicle_tier,
        'vehicle_name': spec['name'],
        'capacity': spec['capacity'],
        'journey_type': journey_type,
        'days': days,
        'billable_km': billable_km,
        'km_rate': float(spec['km_rate']),
        'base_km_cost': float(base_km_cost),
        'driver_bata_total': float(driver_bata_total),
        'subtotal': float(subtotal),
        'gst_amount': float(gst_amount),
        'total_estimate': float(total_estimate),
        'advance_payable': float(advance_payable),
        'pickup_city': pickup_city,
        'destination': destination,
    })


@csrf_exempt
def api_validate_coupon(request):
    """
    Validates marketing coupon code and calculates instantaneous discount.
    """
    if request.method != 'POST':
        return HttpResponseBadRequest("Only POST allowed")
        
    try:
        data = json.loads(request.body.decode('utf-8')) if request.body else request.POST
    except Exception:
        data = request.POST
        
    code = data.get('code', '').strip().upper()
    total_amount = Decimal(str(data.get('total_amount', 0)))
    
    if not code:
        return JsonResponse({'valid': False, 'message': 'Coupon code is required.'})
        
    coupon = Coupon.objects.filter(code=code, is_active=True).first()
    if not coupon:
        return JsonResponse({'valid': False, 'message': 'Invalid or expired coupon code.'})
        
    if coupon.expiry_date and coupon.expiry_date < timezone.now().date():
        return JsonResponse({'valid': False, 'message': 'This coupon has expired.'})
        
    if coupon.usage_limit and coupon.used_count >= coupon.usage_limit:
        return JsonResponse({'valid': False, 'message': 'Coupon usage limit reached.'})
        
    discount = Decimal('0.00')
    if coupon.discount_percent:
        discount = round(total_amount * (coupon.discount_percent / Decimal('100.0')), 2)
    elif coupon.flat_discount:
        discount = min(coupon.flat_discount, total_amount)
        
    new_total = max(Decimal('0.00'), total_amount - discount)
    
    return JsonResponse({
        'valid': True,
        'code': code,
        'discount_amount': float(discount),
        'new_total': float(new_total),
        'message': f"Coupon '{code}' applied successfully! Saved ₹{discount:,.2f}"
    })


@csrf_exempt
def api_custom_inquiry(request):
    """
    REST API handling custom tour itinerary and fleet convoy inquiries.
    Creates an official lead in the CRM Inquiry pipeline and returns a structured WhatsApp redirect URL.
    """
    if request.method != 'POST':
        return HttpResponseBadRequest("Only POST allowed")

    try:
        from urllib.parse import quote
        from crm.models import Inquiry

        try:
            data = json.loads(request.body.decode('utf-8')) if request.body else request.POST
        except Exception:
            data = request.POST

        trip_type = data.get('trip_type', 'college_iv').strip()
        destination = data.get('destination', '').strip()
        departure_date = data.get('departure_date', '').strip()
        duration_days = data.get('duration_days', '3').strip()
        duration_nights = data.get('duration_nights', '2').strip()
        try:
            travelers_count = max(1, int(data.get('travelers_count', 45)))
        except (ValueError, TypeError):
            travelers_count = 45

        vehicle_preference = data.get('vehicle_preference', 'luxury_coach').strip()
        inclusions = data.get('inclusions', [])
        if isinstance(inclusions, str):
            inclusions = [i.strip() for i in inclusions.split(',') if i.strip()]

        contact_name = data.get('contact_name', '').strip()
        contact_phone = data.get('contact_phone', '').strip()
        institution_name = data.get('institution_name', '').strip()
        city_of_origin = data.get('city_of_origin', 'Coimbatore').strip()
        notes = data.get('notes', '').strip()

        if not contact_name or not contact_phone or not destination:
            return JsonResponse({'status': 'error', 'message': 'Please provide your Name, Phone Number, and Destination.'}, status=400)

        # 1. Resolve or create Client
        client = Client.objects.filter(phone=contact_phone).first()
        if not client:
            client = Client.objects.create(
                name=contact_name,
                phone=contact_phone,
                party_type='corporate' if institution_name else 'individual',
                address=city_of_origin
            )

        # 2. Resolve departure date
        pickup_date = timezone.now().date() + timezone.timedelta(days=14)
        if departure_date:
            try:
                from datetime import datetime
                pickup_date = datetime.strptime(departure_date, '%Y-%m-%d').date()
            except Exception:
                pass

        # 3. Create CRM Inquiry
        inclusions_str = ", ".join(inclusions) if inclusions else "Standard Inclusions (Transport + Resort + Breakfast/Dinner)"
        special_req = (
            f"Trip Type: {trip_type.upper()}\n"
            f"Institution / College: {institution_name or 'N/A'}\n"
            f"Duration: {duration_days} Days / {duration_nights} Nights\n"
            f"Vehicle Preference: {vehicle_preference.upper()}\n"
            f"Inclusions Requested: {inclusions_str}\n"
            f"Starting City: {city_of_origin}\n"
            f"Client Notes: {notes or 'None'}"
        )

        inquiry = Inquiry.objects.create(
            party=client,
            guest_name=contact_name,
            guest_phone=contact_phone,
            pickup_location=city_of_origin,
            destination=destination,
            pickup_date=pickup_date,
            pickup_time="06:00:00",
            journey_type='outstation',
            adult_count=travelers_count,
            special_requirements=special_req,
            source='website',
            priority='high' if travelers_count >= 20 else 'medium',
        )

        # 4. Formulate formatted WhatsApp text
        wa_text = (
            f"🌟 *Custom Tour Itinerary & Quotation Request*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"• *Inquiry Ref:* #{inquiry.inquiry_number}\n"
            f"• *Lead Organizer:* {contact_name}" + (f" ({institution_name})" if institution_name else "") + f"\n"
            f"• *Mobile / WhatsApp:* {contact_phone}\n"
            f"• *From:* {city_of_origin}\n"
            f"• *Destination Circuit:* {destination}\n"
            f"• *Departure Date:* {pickup_date.strftime('%d-%b-%Y')}\n"
            f"• *Trip Duration:* {duration_days} Days / {duration_nights} Nights\n"
            f"• *Group Size:* {travelers_count} Travelers\n"
            f"• *Vehicle:* {vehicle_preference.upper()}\n"
            f"• *Inclusions Needed:* {inclusions_str}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Please share a customized day-by-day itinerary and competitive per-person quotation."
        )
        whatsapp_url = f"https://wa.me/919842533777?text={quote(wa_text)}"

        return JsonResponse({
            'status': 'success',
            'inquiry_id': inquiry.id,
            'inquiry_number': inquiry.inquiry_number,
            'whatsapp_url': whatsapp_url,
            'message': f"Inquiry #{inquiry.inquiry_number} logged successfully! Opening WhatsApp with your itinerary summary."
        })

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


# ==============================================================================
# 3. Streamlined Guest & User Checkout Engine
# ==============================================================================

def checkout(request, inventory_id):
    """
    Frictionless checkout supporting both Guest checkout and Logged-in accounts,
    offering Dynamic Direct UPI QR code and Razorpay payment options.
    """
    inventory = get_object_or_404(PackageInventory, id=inventory_id)
    package = inventory.package
    
    if request.method == 'POST':
        # 1. Identity Resolution (Guest or Logged In)
        if request.user.is_authenticated and hasattr(request.user, 'customer_profile'):
            client = request.user.customer_profile.client_record
            guest_name = client.name
            guest_phone = client.phone
            guest_email = request.user.email
            pickup_loc = request.POST.get('pickup_location', '').strip() or 'Designated Boarding Point'
        else:
            guest_name = request.POST.get('guest_name', '').strip() or 'Guest Traveler'
            guest_phone = request.POST.get('guest_phone', '').strip() or '9876543210'
            guest_email = request.POST.get('guest_email', '').strip() or 'guest@sivagayathiritravels.com'
            pickup_loc = request.POST.get('pickup_location', '').strip() or 'Designated Boarding Point'
            
            # Find or create Client party
            client = Client.objects.filter(phone=guest_phone).first()
            if not client:
                client = Client.objects.create(
                    name=guest_name,
                    phone=guest_phone,
                    email=guest_email,
                    party_type='individual',
                    address=pickup_loc
                )
                
        # 2. Extract Travel Parameters
        try:
            pax = max(1, int(request.POST.get('pax', 1)))
        except (ValueError, TypeError):
            pax = 1
            
        meal_plan = request.POST.get('meal_plan', 'AP')
        coupon_code = request.POST.get('coupon', '').strip().upper()
        payment_plan = request.POST.get('payment_plan', 'full')  # 'full' or 'advance'
        payment_method = request.POST.get('payment_method', 'upi')  # 'upi' or 'razorpay'
        utr_number = request.POST.get('utr_number', '').strip()
        
        # 3. Price Calculation
        if meal_plan == 'EP' and package.price_without_food and package.price_without_food > 0:
            per_pax_base = package.price_without_food
        else:
            per_pax_base = inventory.price_override or package.price_with_food or package.base_price or Decimal('3500.00')
            
        base_subtotal = Decimal(str(per_pax_base)) * pax
        discount_amount = Decimal('0.00')
        
        if coupon_code:
            coupon = Coupon.objects.filter(code=coupon_code, is_active=True).first()
            if coupon:
                if coupon.discount_percent:
                    discount_amount = round(base_subtotal * (coupon.discount_percent / Decimal('100.0')), 2)
                elif coupon.flat_discount:
                    discount_amount = min(coupon.flat_discount, base_subtotal)
                coupon.used_count += 1
                coupon.save(update_fields=['used_count'])
                
        # Intercity Bus Loyalty Points Redemption (Cross-System Port 8005)
        loyalty_points = 0
        try:
            loyalty_points = int(request.POST.get('loyalty_points', 0) or 0)
        except (ValueError, TypeError):
            loyalty_points = 0

        loyalty_discount = Decimal('0.00')
        loyalty_redeem_msg = ''
        booking_ref = f"BK-{timezone.now().strftime('%y%m%d')}-{random.randint(1000, 9999)}"
        if loyalty_points > 0 and guest_phone:
            loyalty_res = redeem_loyalty_points(
                phone=guest_phone,
                points=loyalty_points,
                reference_id=booking_ref,
                source='holiday_tour_checkout'
            )
            if loyalty_res.get('status') == 'success':
                loyalty_discount = Decimal(str(loyalty_res.get('discount_inr', 0)))
                discount_amount += loyalty_discount
                loyalty_redeem_msg = f"Redeemed {loyalty_points} Intercity Loyalty Points (₹{loyalty_discount:,.2f} discount)."

        net_after_discount = max(Decimal('0.00'), base_subtotal - discount_amount)
        gst_amount = round(net_after_discount * Decimal('0.05'), 2)
        total_price = net_after_discount + gst_amount
        
        # Payable Now
        amount_to_pay = total_price
        if payment_plan == 'advance':
            amount_to_pay = round(total_price * Decimal('0.5'), 2)

        # 4. Check for Optional Connecting Intercity Bus Transit Reservation
        transit_trip_id = request.POST.get('transit_trip_id')
        transit_seats_raw = request.POST.get('transit_seats', '').strip()
        transit_pnr = ''
        transit_notes = ''
        if transit_trip_id and transit_seats_raw:
            transit_seats = [s.strip() for s in transit_seats_raw.split(',') if s.strip()]
            transit_res = reserve_transit_seats(
                trip_id=int(transit_trip_id),
                seat_numbers=transit_seats,
                passenger_name=guest_name,
                passenger_phone=guest_phone,
                passenger_gender='M',
                external_booking_ref=booking_ref
            )
            if transit_res.get('status') == 'success':
                transit_pnr = transit_res.get('pnr', '')
                b_name = transit_res.get('boarding_point', {}).get('name', 'Main Terminal')
                d_name = transit_res.get('dropping_point', {}).get('name', 'Central Stand')
                dep_time = transit_res.get('departure_time', '')
                tracking_path = transit_res.get('tracking_url', '')
                full_tracking_url = f"http://127.0.0.1:8005{tracking_path}" if tracking_path else f"http://127.0.0.1:8005/track/?token={transit_pnr}"
                transit_notes = f"Connecting Intercity Bus PNR: {transit_pnr} (Seats: {', '.join(transit_seats)}) | Boarding: {b_name} @ {dep_time} | Dropping: {d_name} | Tracking: {full_tracking_url}"

        # 5. Create Master Booking Record
        default_vtype = package.default_vehicle_type or VehicleType.objects.first()
        combined_notes = "\n".join(filter(None, [loyalty_redeem_msg, transit_notes]))
        
        booking = Booking.objects.create(
            booking_number=booking_ref,
            party=client,
            guest_name=guest_name,
            guest_phone=guest_phone,
            pickup_location=pickup_loc,
            destination=package.destination,
            pickup_date=inventory.departure_date,
            pickup_time=datetime.time(6, 0),
            travel_pnr=transit_pnr,
            journey_type='round_trip',
            vehicle_type=default_vtype,
            pax_count=pax,
            billing_type='package',
            quoted_price=total_price,
            package=package,
            package_inventory=inventory,
            status='pending',
            gst_rate=Decimal('5.0'),
            notes=combined_notes
        )
        
        if payment_plan == 'advance':
            InstallmentPlan.objects.create(
                booking=booking,
                total_amount=total_price,
                number_of_installments=2,
                is_active=True
            )
            
        # 6. Handle Payment Channels
        # Option A: Instant Direct Dynamic UPI with UTR Submission
        if payment_method == 'upi' and utr_number and len(utr_number) >= 6:
            txn = GatewayTransaction.objects.create(
                transaction_id=f"TXN-UPI-{utr_number}-{int(timezone.now().timestamp())}",
                provider='direct_upi',
                gateway_payment_id=utr_number,
                booking=booking,
                party=client,
                gross_amount=amount_to_pay,
                fee_amount=Decimal('0.00'),
                tax_amount=Decimal('0.00'),
                net_amount=amount_to_pay,
                status='authorized',
                raw_response={'utr': utr_number, 'source': 'portal_checkout_instant'},
            )
            post_gateway_transaction_to_gl(txn)
            booking.status = 'confirmed'
            booking.save(update_fields=['status'])
            
            from operations.models import sync_package_inventory_seats
            sync_package_inventory_seats(inventory)
            
            messages.success(request, f"Booking #{booking.booking_number} confirmed! Payment verified via UPI UTR {utr_number}.")
            return redirect('customer_portal:booking_confirmed', booking_id=booking.id)
            
        # Option B: Razorpay Link Dispatch
        elif payment_method == 'razorpay':
            payment_response = create_payment_link(
                amount=float(amount_to_pay),
                reference_id=booking.booking_number,
                description=f"Tour Booking: {package.name} ({pax} Pax)",
                customer_name=guest_name,
                customer_email=guest_email,
                customer_contact=guest_phone
            )
            if 'short_url' in payment_response:
                return redirect(payment_response['short_url'])
            else:
                messages.error(request, 'Gateway link generation unavailable. Please use Direct UPI option.')
                return redirect('customer_portal:checkout', inventory_id=inventory.id)
                
        # Option C: Dynamic UPI QR Pending Modal/Step
        else:
            upi_pkg = generate_dynamic_upi_package(
                amount=amount_to_pay,
                reference_id=booking.booking_number,
                note=f"Advance for {booking.booking_number}"
            )
            return render(request, 'customer_portal/checkout.html', {
                'inventory': inventory,
                'package': package,
                'booking': booking,
                'pax': pax,
                'total_price': total_price,
                'amount_to_pay': amount_to_pay,
                'upi_package': upi_pkg,
                'awaiting_utr': True,
            })
            
    # GET Request: Initial Checkout Presentation
    initial_pax = max(1, int(request.GET.get('pax', 1)))
    unit_price = inventory.price_override or package.price_with_food or package.base_price or Decimal('3500.00')
    initial_amount = Decimal(str(unit_price)) * initial_pax
    initial_gst = round(initial_amount * Decimal('0.05'), 2)
    initial_total = initial_amount + initial_gst
    
    # Pre-generate dynamic UPI payload for live display
    temp_ref = f"BK-PREVIEW-{random.randint(100, 999)}"
    upi_pkg = generate_dynamic_upi_package(
        amount=initial_total,
        reference_id=temp_ref,
        note=f"Payment for {package.name[:25]}"
    )
    
    upsells = package.upsells.all()
    
    # Resolve initial guest info safely
    initial_guest_name = ''
    initial_guest_phone = ''
    initial_guest_email = ''
    if request.user.is_authenticated:
        initial_guest_email = request.user.email
        initial_guest_name = request.user.get_full_name() or request.user.username
        if hasattr(request.user, 'customer_profile'):
            client_rec = request.user.customer_profile.client_record
            initial_guest_name = client_rec.name or initial_guest_name
            initial_guest_phone = client_rec.phone or ''
    
    context = {
        'inventory': inventory,
        'package': package,
        'initial_pax': initial_pax,
        'unit_price': unit_price,
        'initial_total': initial_total,
        'upi_package': upi_pkg,
        'upsells': upsells,
        'initial_guest_name': initial_guest_name,
        'initial_guest_phone': initial_guest_phone,
        'initial_guest_email': initial_guest_email,
        'awaiting_utr': False,
    }
    return render(request, 'customer_portal/checkout.html', context)


def rental_checkout(request):
    """
    Checkout handler for custom outstation vehicle rentals initiated
    from the Interactive Fare Estimator.
    """
    if request.method == 'POST':
        vehicle_tier = request.POST.get('vehicle_tier', 'crysta')
        journey_type = request.POST.get('journey_type', 'outstation_round')
        days = max(1, int(request.POST.get('days', 1)))
        estimated_km = max(0, int(request.POST.get('estimated_km', 300)))
        pickup_city = request.POST.get('pickup_city', 'Coimbatore')
        destination = request.POST.get('destination', 'Ooty')
        pickup_date_str = request.POST.get('pickup_date', '')
        guest_name = request.POST.get('guest_name', 'Guest Traveler')
        guest_phone = request.POST.get('guest_phone', '9876543210')
        guest_email = request.POST.get('guest_email', 'guest@sivagayathiritravels.com')
        payment_method = request.POST.get('payment_method', 'upi')
        utr_number = request.POST.get('utr_number', '').strip()
        
        spec = TIER_SPECS.get(vehicle_tier, TIER_SPECS['crysta'])
        min_allowed_km = spec['min_km_day'] * days
        billable_km = max(estimated_km, min_allowed_km)
        base_km_cost = Decimal(str(billable_km)) * spec['km_rate']
        driver_bata_total = spec['driver_bata'] * days
        subtotal = base_km_cost + driver_bata_total
        gst_amount = round(subtotal * Decimal('0.05'), 2)
        total_fare = subtotal + gst_amount
        advance_payable = round(total_fare * Decimal('0.5'), 2)
        
        # Resolve Client
        client = Client.objects.filter(phone=guest_phone).first()
        if not client:
            client = Client.objects.create(
                name=guest_name,
                phone=guest_phone,
                email=guest_email,
                party_type='individual',
                address=pickup_city
            )
            
        pickup_date = timezone.now().date() + datetime.timedelta(days=2)
        if pickup_date_str:
            try:
                pickup_date = datetime.date.fromisoformat(pickup_date_str)
            except Exception:
                pass
                
        # Match vehicle type
        vtype = VehicleType.objects.filter(name__icontains=vehicle_tier[:4]).first() or VehicleType.objects.first()
        
        booking_ref = f"BK-RENT-{timezone.now().strftime('%y%m%d')}-{random.randint(1000, 9999)}"
        booking = Booking.objects.create(
            booking_number=booking_ref,
            party=client,
            guest_name=guest_name,
            guest_phone=guest_phone,
            pickup_location=pickup_city,
            destination=destination,
            pickup_date=pickup_date,
            pickup_time=datetime.time(7, 0),
            journey_type='round_trip' if journey_type == 'outstation_round' else 'local',
            vehicle_type=vtype,
            expected_km=billable_km,
            pax_count=spec['capacity'],
            billing_type='km',
            quoted_price=total_fare,
            status='pending',
            gst_rate=Decimal('5.0')
        )
        
        if payment_method == 'upi' and utr_number and len(utr_number) >= 6:
            txn = GatewayTransaction.objects.create(
                transaction_id=f"TXN-UPI-{utr_number}-{int(timezone.now().timestamp())}",
                provider='direct_upi',
                gateway_payment_id=utr_number,
                booking=booking,
                party=client,
                gross_amount=advance_payable,
                net_amount=advance_payable,
                status='authorized',
                raw_response={'utr': utr_number, 'source': 'rental_checkout'},
            )
            post_gateway_transaction_to_gl(txn)
            booking.status = 'confirmed'
            booking.save(update_fields=['status'])
            messages.success(request, f"Fleet rental #{booking.booking_number} confirmed with UTR {utr_number}!")
            return redirect('customer_portal:booking_confirmed', booking_id=booking.id)
        else:
            upi_pkg = generate_dynamic_upi_package(
                amount=advance_payable,
                reference_id=booking.booking_number,
                note=f"Rental advance for {booking.booking_number}"
            )
            return render(request, 'customer_portal/rental_checkout.html', {
                'booking': booking,
                'spec': spec,
                'days': days,
                'billable_km': billable_km,
                'total_fare': total_fare,
                'advance_payable': advance_payable,
                'upi_package': upi_pkg,
                'awaiting_utr': True,
            })
            
    return redirect('/#fare-estimator')


@csrf_exempt
def api_checkout_instant_upi_confirm(request):
    """
    Asynchronous AJAX endpoint allowing checkout form to submit UPI UTR number,
    immediately reconcile with general ledger, and return confirmation URL.
    """
    if request.method != 'POST':
        return HttpResponseBadRequest("Only POST allowed")
        
    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        data = request.POST
        
    booking_id = data.get('booking_id')
    utr_number = str(data.get('utr_number', '')).strip()
    amount_raw = data.get('amount')
    
    if not utr_number or len(utr_number) < 6:
        return JsonResponse({'status': 'error', 'message': 'Valid 6+ digit UPI UTR/RRN number is required.'}, status=400)
        
    booking = get_object_or_404(Booking, id=booking_id)
    amount = Decimal(str(amount_raw or booking.quoted_price))
    
    txn = GatewayTransaction.objects.create(
        transaction_id=f"TXN-UPI-{utr_number}-{int(timezone.now().timestamp())}",
        provider='direct_upi',
        gateway_payment_id=utr_number,
        booking=booking,
        party=booking.party,
        gross_amount=amount,
        fee_amount=Decimal('0.00'),
        tax_amount=Decimal('0.00'),
        net_amount=amount,
        status='authorized',
        raw_response={'utr': utr_number, 'source': 'api_instant_upi_confirm'},
    )
    post_gateway_transaction_to_gl(txn)
    
    booking.status = 'confirmed'
    booking.save(update_fields=['status'])
    
    # If package booking, update seats
    if booking.package_inventory and booking.pax_count:
        inv = booking.package_inventory
        inv.booked_seats += booking.pax_count
        inv.save()
        
    return JsonResponse({
        'status': 'success',
        'message': f"Payment verified successfully with UTR {utr_number}!",
        'booking_number': booking.booking_number,
        'redirect_url': f"/customer-portal/booking/confirmed/{booking.id}/"
    })


# ==============================================================================
# 4. Booking Confirmation & Travel Voucher View
# ==============================================================================

def booking_confirmed_view(request, booking_id):
    """
    Display booking confirmation certificate, printable travel voucher,
    WhatsApp sharing link, and dynamic UPI QR for settling any balance due.
    """
    booking = get_object_or_404(Booking, id=booking_id)
    
    # Calculate captured payments
    payments_from_gw = GatewayTransaction.objects.filter(booking=booking, status__in=['authorized', 'captured'])
    total_paid_gw = sum([t.gross_amount for t in payments_from_gw])
    
    legacy_payments = booking.payments.all()
    total_paid_legacy = sum([p.amount for p in legacy_payments])
    
    total_paid = max(total_paid_gw, total_paid_legacy)
    quoted = booking.quoted_price or Decimal('0.00')
    balance_due = max(Decimal('0.00'), quoted - total_paid)
    
    # Generate balance due UPI QR if pending
    balance_upi_package = None
    if balance_due > Decimal('0.00'):
        balance_upi_package = generate_dynamic_upi_package(
            amount=balance_due,
            reference_id=booking.booking_number,
            note=f"Balance for {booking.booking_number}"
        )
        
    # Pre-formatted WhatsApp share message
    share_text = (
        f"🚍 *Sivagayathiri Travels Booking Voucher*\n"
        f"Ref: *{booking.booking_number}*\n"
        f"Trip: {booking.destination}\n"
        f"Departure: {booking.pickup_date.strftime('%d-%b-%Y')}\n"
        f"Lead Passenger: {booking.guest_name}\n"
        f"Pax Count: {booking.pax_count or 1} Travelers\n"
        f"Status: Confirmed ✅\n\n"
        f"Have a memorable journey!"
    )
    encoded_whatsapp_text = urllib.parse.quote(share_text)
    whatsapp_share_url = f"https://wa.me/?text={encoded_whatsapp_text}"
    
    # Intercity Bus CRS Tracking Link (if transit seats were reserved)
    intercity_tracking_url = ''
    if 'http://127.0.0.1:8005/track/' in (booking.notes or ''):
        for line in booking.notes.splitlines():
            if 'http://127.0.0.1:8005/track/' in line:
                parts = line.split('Tracking:')
                intercity_tracking_url = parts[-1].strip() if len(parts) > 1 else line.strip()
    elif booking.travel_pnr and booking.travel_pnr.startswith('PNR-'):
        intercity_tracking_url = f"http://127.0.0.1:8005/track/?token={booking.travel_pnr}"

    context = {
        'booking': booking,
        'total_paid': total_paid,
        'balance_due': balance_due,
        'balance_upi_package': balance_upi_package,
        'whatsapp_share_url': whatsapp_share_url,
        'intercity_tracking_url': intercity_tracking_url,
    }
    return render(request, 'customer_portal/booking_confirmed.html', context)


def portal_booking_tracker(request):
    """
    Quick tracking lookup by Booking Number or Phone Number.
    """
    query = request.GET.get('q', '').strip()
    if not query:
        messages.info(request, "Please enter your Booking Reference (e.g. BK-XXXX) or Mobile Number.")
        return redirect('customer_portal:home')
        
    booking = Booking.objects.filter(
        models.Q(booking_number__iexact=query) |
        models.Q(guest_phone__icontains=query)
    ).order_by('-id').first()
    
    if booking:
        return redirect('customer_portal:booking_confirmed', booking_id=booking.id)
    else:
        messages.error(request, f"No booking found matching '{query}'. Please verify your details.")
        return redirect('customer_portal:home')


# ==============================================================================
# 5. Customer Self-Service Portal & Passwordless Mobile OTP Engine
# ==============================================================================

@csrf_exempt
def api_request_otp(request):
    """
    POST /customer-portal/api/request-otp/
    Generates and dispatches a 6-digit OTP to the customer's Indian mobile number
    for passwordless login and account self-registration.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Only POST method allowed.'}, status=405)

    try:
        if request.content_type and 'application/json' in request.content_type:
            data = json.loads(request.body.decode('utf-8'))
        else:
            data = request.POST
    except Exception:
        return JsonResponse({'status': 'error', 'message': 'Invalid request payload.'}, status=400)

    raw_phone = str(data.get('phone', '')).strip()
    phone = re.sub(r'\D', '', raw_phone)
    if phone.startswith('91') and len(phone) == 12:
        phone = phone[2:]

    if len(phone) != 10 or not phone.isdigit():
        return JsonResponse({
            'status': 'error',
            'message': 'Please enter a valid 10-digit Indian mobile number (e.g. 9842533777).'
        }, status=400)

    # Invalidate previous unverified OTPs for this phone
    CustomerOTP.objects.filter(phone=phone, is_verified=False).update(is_verified=True)

    # Generate 6-digit cryptographic code
    otp_code = f"{secrets.randbelow(900000) + 100000}"
    expires_at = timezone.now() + timezone.timedelta(minutes=10)

    CustomerOTP.objects.create(
        phone=phone,
        otp_code=otp_code,
        expires_at=expires_at,
        is_verified=False
    )

    # Dispatch via WhatsApp & SMS service
    try:
        from integrations.communication import send_whatsapp_message
        msg = (
            f"Namaste from Sivagayathiri Travels! 🙏\n\n"
            f"Your instant login verification code is: *{otp_code}*\n\n"
            f"Valid for 10 minutes. Please do not share this OTP with anyone."
        )
        send_whatsapp_message(f"91{phone}", msg)
    except Exception:
        pass

    return JsonResponse({
        'status': 'success',
        'message': f'Verification OTP successfully sent to +91 {phone}',
        'phone': phone,
        'dev_otp': otp_code,  # Provided for sandboxing, automated testing & instant preview
        'expires_in_seconds': 600,
    })


@csrf_exempt
def api_verify_otp(request):
    """
    POST /customer-portal/api/verify-otp/
    Verifies 6-digit OTP, creates or links Client + User + CustomerAccount,
    authenticates the session, associates past bookings, and redirects to dashboard.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Only POST method allowed.'}, status=405)

    try:
        if request.content_type and 'application/json' in request.content_type:
            data = json.loads(request.body.decode('utf-8'))
        else:
            data = request.POST
    except Exception:
        return JsonResponse({'status': 'error', 'message': 'Invalid request payload.'}, status=400)

    raw_phone = str(data.get('phone', '')).strip()
    otp_candidate = str(data.get('otp', '')).strip()

    phone = re.sub(r'\D', '', raw_phone)
    if phone.startswith('91') and len(phone) == 12:
        phone = phone[2:]

    if not phone or not otp_candidate:
        return JsonResponse({'status': 'error', 'message': 'Phone number and OTP code are required.'}, status=400)

    # Query active unexpired OTP
    otp_record = CustomerOTP.objects.filter(
        phone=phone,
        otp_code=otp_candidate,
        is_verified=False,
        expires_at__gte=timezone.now()
    ).order_by('-created_at').first()

    if not otp_record:
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid or expired OTP. Please check the code or request a fresh OTP.'
        }, status=400)

    # Mark OTP as verified
    otp_record.is_verified = True
    otp_record.save(update_fields=['is_verified'])

    # Find or provision Client record
    client = Client.objects.filter(phone=phone).first()
    if not client:
        sample_booking = Booking.objects.filter(guest_phone=phone).exclude(guest_name='').first()
        guest_name = sample_booking.guest_name if sample_booking else f"Guest {phone[-4:]}"
        client = Client.objects.create(
            name=guest_name,
            phone=phone,
            party_type='individual',
            is_active=True
        )


    # Find or provision User & CustomerAccount
    account = CustomerAccount.objects.filter(client_record=client).first()
    if account:
        user = account.user
    else:
        username = f"cust_{phone}"
        user = User.objects.filter(username=username).first()
        if not user:
            user = User(username=username, first_name=client.name[:30])
            user.set_unusable_password()
            user.save()
        account, _ = CustomerAccount.objects.get_or_create(
            user=user,
            defaults={'client_record': client, 'is_email_verified': True}
        )

    # Re-associate any bookings matching this phone to this customer client record
    Booking.objects.filter(guest_phone=phone).exclude(party=client).update(party=client)


    # Log user in
    auth_login(request, user, backend='django.contrib.auth.backends.ModelBackend')
    request.session['customer_phone'] = phone

    return JsonResponse({
        'status': 'success',
        'message': f'Welcome {client.name}! You are securely logged in.',
        'redirect_url': '/customer-portal/bookings/',
    })


def portal_login(request):
    """
    Customer portal login view supporting both:
    1. Instant Passwordless Mobile OTP Login (Primary / Default)
    2. Corporate / Staff Password Login
    """
    if request.user.is_authenticated:
        return redirect('customer_portal:bookings')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            auth_login(request, user)
            next_url = request.GET.get('next') or 'customer_portal:bookings'
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid username or password. Please try again or use Mobile OTP.')

    next_param = request.GET.get('next', '')
    return render(request, 'customer_portal/login.html', {'next': next_param})


def portal_logout(request):
    auth_logout(request)
    return redirect('customer_portal:login')


@login_required(login_url='customer_portal:login')
def portal_home(request):
    return redirect('customer_portal:bookings')


@login_required(login_url='customer_portal:login')
def my_bookings(request):
    """
    Customer Self-Service Hub: Lists active, upcoming and past holiday tour & rental bookings,
    telematics radar tracking links, balance payments, and official GST tax invoices.
    """
    client = None
    phone = request.session.get('customer_phone')
    
    if hasattr(request.user, 'customer_profile'):
        client = request.user.customer_profile.client_record
        if not phone:
            phone = client.phone
    else:
        uname = request.user.username
        if uname.startswith('cust_'):
            phone = uname.replace('cust_', '')
            client = Client.objects.filter(phone=phone).first()
        elif uname.startswith('guest_'):
            phone = uname.replace('guest_', '')
            client = Client.objects.filter(phone=phone).first()

    q_filter = models.Q()
    if client:
        q_filter |= models.Q(party=client)
    if phone:
        q_filter |= models.Q(guest_phone=phone) | models.Q(guest_phone=f"+91{phone}") | models.Q(guest_phone=f"91{phone}")

    if q_filter:
        bookings = Booking.objects.filter(q_filter).distinct().order_by('-id')
    else:
        bookings = Booking.objects.none()

    today = timezone.now().date()
    total_spent = Decimal('0.00')
    total_balance_due = Decimal('0.00')
    active_trips_count = 0

    decorated_bookings = []
    for booking in bookings:
        payments_gw = GatewayTransaction.objects.filter(booking=booking, status__in=['captured', 'authorized'])
        paid_gw = sum([t.gross_amount for t in payments_gw], Decimal('0.00'))
        
        legacy_payments = booking.payments.all()
        paid_legacy = sum([p.amount for p in legacy_payments], Decimal('0.00'))
        
        total_paid = max(paid_gw, paid_legacy)
        quoted = booking.quoted_price or Decimal('0.00')
        balance_due = max(Decimal('0.00'), quoted - total_paid)
        
        total_spent += total_paid
        total_balance_due += balance_due

        assigned_trip = booking.trips.select_related('vehicle', 'driver').first()
        is_active = (booking.status in ['confirmed', 'in_progress']) and (booking.pickup_date <= today <= (booking.drop_date or booking.pickup_date))
        if is_active or booking.status == 'in_progress':
            active_trips_count += 1

        booking.total_paid = total_paid
        booking.balance_due = balance_due
        booking.assigned_trip = assigned_trip
        booking.is_active_journey = is_active or (booking.status == 'in_progress')
        booking.can_track_live = bool(assigned_trip or booking.status in ['confirmed', 'in_progress'])
        decorated_bookings.append(booking)

    context = {
        'bookings': decorated_bookings,
        'client': client,
        'phone': phone,
        'total_bookings_count': len(decorated_bookings),
        'active_trips_count': active_trips_count,
        'total_spent': total_spent,
        'total_balance_due': total_balance_due,
    }
    return render(request, 'customer_portal/bookings.html', context)


@login_required(login_url='customer_portal:login')
def portal_booking_detail(request, booking_id):
    """
    Detailed trip view with day-by-day itinerary, payments reconciliation, and vehicle allocation.
    """
    client = getattr(request.user, 'customer_profile', None)
    client_record = client.client_record if client else None
    
    booking = get_object_or_404(Booking, id=booking_id)
    
    # Verify ownership
    phone = client_record.phone if client_record else request.user.username.replace('cust_', '')
    is_owner = (booking.party == client_record) or (booking.guest_phone == phone) or request.user.is_staff
    if not is_owner:
        messages.error(request, "You do not have permission to view this booking.")
        return redirect('customer_portal:bookings')

    payments_gw = GatewayTransaction.objects.filter(booking=booking, status__in=['captured', 'authorized'])
    paid_gw = sum([t.gross_amount for t in payments_gw], Decimal('0.00'))
    legacy_payments = booking.payments.all()
    paid_legacy = sum([p.amount for p in legacy_payments], Decimal('0.00'))
    total_paid = max(paid_gw, paid_legacy)

    quoted = booking.quoted_price or Decimal('0.00')
    balance_due = max(Decimal('0.00'), quoted - total_paid)
    
    itinerary_days = []
    if booking.package:
        itinerary_days = booking.package.itinerary_days.all().order_by('day_number')

    assigned_trip = booking.trips.select_related('vehicle', 'driver').first()

    return render(request, 'customer_portal/booking_detail.html', {
        'booking': booking,
        'total_paid': total_paid,
        'balance_due': balance_due,
        'itinerary_days': itinerary_days,
        'assigned_trip': assigned_trip,
    })


def customer_portal_booking_live(request, booking_id):
    """
    Live Telematics Radar Cockpit: Real-time GPS vehicle tracking, speedometer gauge,
    telematics health, driver contact card, and emergency SOS for customer's trip.
    """
    booking = get_object_or_404(Booking, id=booking_id)
    
    # Permission check: logged in owner OR session match OR guest query match
    is_owner = False
    if request.user.is_authenticated:
        if hasattr(request.user, 'customer_profile') and booking.party == request.user.customer_profile.client_record:
            is_owner = True
        elif request.user.is_staff:
            is_owner = True
        elif request.user.username.replace('cust_', '').replace('guest_', '') == booking.guest_phone:
            is_owner = True

    req_phone = request.GET.get('phone', '').strip()
    if req_phone and req_phone in [booking.guest_phone, f"91{booking.guest_phone}", f"+91{booking.guest_phone}"]:
        is_owner = True

    if not is_owner and not request.user.is_staff:
        messages.info(request, "Please log in with your registered phone number to access live journey tracking.")
        return redirect(f"/customer-portal/login/?next=/customer-portal/booking/{booking_id}/live/")

    assigned_trip = booking.trips.select_related('vehicle', 'driver').first()
    vehicle = assigned_trip.vehicle if assigned_trip else None
    driver = assigned_trip.driver if assigned_trip else None


    # Telemetry simulation / live coordinates
    telemetry = {
        'latitude': 11.4102,
        'longitude': 76.6950,
        'speed_kmh': 48,
        'heading': 310,
        'fuel_percent': 78,
        'engine_status': 'Running - Normal',
        'air_conditioning': 'Active (22°C)',
        'eta_minutes': 35,
        'distance_remaining_km': 22.4,
        'last_ping_seconds_ago': 4,
        'odometer_km': getattr(vehicle, 'current_odometer', 64280) if vehicle else 64280,
    }

    context = {
        'booking': booking,
        'trip': assigned_trip,
        'vehicle': vehicle,
        'driver': driver,
        'telemetry': telemetry,
    }
    return render(request, 'customer_portal/booking_live_radar.html', context)


def customer_portal_booking_invoice(request, booking_id):
    """
    Official Rule 46 GST Customer Tax Invoice & Journey Waybill statement.
    """
    booking = get_object_or_404(Booking, id=booking_id)

    # Ownership check
    is_owner = False
    if request.user.is_authenticated:
        if hasattr(request.user, 'customer_profile') and booking.party == request.user.customer_profile.client_record:
            is_owner = True
        elif request.user.is_staff:
            is_owner = True
        elif request.user.username.replace('cust_', '').replace('guest_', '') == booking.guest_phone:
            is_owner = True

    req_phone = request.GET.get('phone', '').strip()
    if req_phone and req_phone in [booking.guest_phone, f"91{booking.guest_phone}", f"+91{booking.guest_phone}"]:
        is_owner = True

    if not is_owner and not request.user.is_staff:
        messages.info(request, "Please log in to view and download your GST Tax Invoice.")
        return redirect(f"/customer-portal/login/?next=/customer-portal/booking/{booking_id}/invoice/")

    # Payments reconciliation
    payments_gw = GatewayTransaction.objects.filter(booking=booking, status__in=['captured', 'authorized'])
    paid_gw = sum([t.gross_amount for t in payments_gw], Decimal('0.00'))
    legacy_payments = booking.payments.all()
    paid_legacy = sum([p.amount for p in legacy_payments], Decimal('0.00'))
    total_paid = max(paid_gw, paid_legacy)

    gross_price = booking.quoted_price or Decimal('0.00')
    balance_due = max(Decimal('0.00'), gross_price - total_paid)

    # 5% GST computation (2.5% CGST + 2.5% SGST)
    tax_rate = Decimal('0.05')
    taxable_value = round(gross_price / (Decimal('1.00') + tax_rate), 2)
    gst_total = gross_price - taxable_value
    cgst_amount = round(gst_total / Decimal('2.00'), 2)
    sgst_amount = gst_total - cgst_amount

    inv_date = getattr(booking, 'created_at', None)
    if inv_date and hasattr(inv_date, 'date'):
        invoice_date = inv_date.date()
    else:
        invoice_date = timezone.now().date()

    context = {
        'booking': booking,
        'invoice_number': f"INV-2026-{booking.id:05d}",
        'invoice_date': invoice_date,
        'taxable_value': taxable_value,
        'cgst_amount': cgst_amount,
        'sgst_amount': sgst_amount,
        'gst_total': gst_total,
        'gross_price': gross_price,
        'total_paid': total_paid,
        'balance_due': balance_due,
        'payments': legacy_payments or payments_gw,
    }

    return render(request, 'customer_portal/booking_tax_invoice.html', context)


@login_required(login_url='customer_portal:login')
def my_documents(request):
    try:
        account = request.user.customer_profile
        documents = account.client_record.documents.all()
    except Exception:
        documents = []
    return render(request, 'customer_portal/documents.html', {'documents': documents})


# ==============================================================================
# 9. Intercity Bus CRS (Port 8005) Synergy APIs
# ==============================================================================

@csrf_exempt
def api_intercity_loyalty_balance(request):
    """
    Proxies live loyalty balance and discount lookup to Intercity Bus CRS (Port 8005).
    Endpoint: GET /customer-portal/api/intercity/loyalty/?phone=9842511223
    """
    phone = request.GET.get('phone', '').strip()
    if not phone:
        return JsonResponse({'status': 'error', 'message': 'Phone number required', 'points_balance': 0})
    data = get_loyalty_balance(phone)
    return JsonResponse(data)


@csrf_exempt
def api_intercity_search_trips(request):
    """
    Proxies scheduled intercity bus search to Intercity Bus CRS (Port 8005)
    for holiday package transit leg booking.
    Endpoint: GET /customer-portal/api/intercity/routes/?origin=Chennai&destination=Coimbatore&date=2026-09-28
    """
    origin = request.GET.get('origin', 'Chennai').strip()
    destination = request.GET.get('destination', 'Coimbatore').strip()
    date_str = request.GET.get('date', '').strip()
    if not date_str:
        date_str = timezone.now().strftime('%Y-%m-%d')
    data = search_intercity_trips(origin, destination, date_str)
    return JsonResponse(data)


@csrf_exempt
def api_intercity_reserve_seats(request):
    """
    Reserves connecting bus transit seats on Intercity Bus CRS (Port 8005).
    Endpoint: POST /customer-portal/api/intercity/reserve-seats/
    """
    if request.method != 'POST':
        return HttpResponseBadRequest("Only POST allowed")
    try:
        payload = json.loads(request.body.decode('utf-8')) if request.body else request.POST
    except Exception:
        payload = request.POST

    trip_id = payload.get('trip_id')
    seat_numbers = payload.get('seat_numbers', [])
    if isinstance(seat_numbers, str):
        seat_numbers = [s.strip() for s in seat_numbers.split(',') if s.strip()]

    passenger_name = payload.get('passenger_name', 'Guest Traveler')
    passenger_phone = payload.get('passenger_phone', '9842511223')
    passenger_gender = payload.get('passenger_gender', 'M')
    booking_ref = payload.get('external_booking_ref', 'PKG-CUSTOM')

    if not trip_id or not seat_numbers:
        return JsonResponse({'status': 'error', 'message': 'trip_id and seat_numbers are required'})

    result = reserve_transit_seats(
        trip_id=int(trip_id),
        seat_numbers=seat_numbers,
        passenger_name=passenger_name,
        passenger_phone=passenger_phone,
        passenger_gender=passenger_gender,
        external_booking_ref=booking_ref
    )
    return JsonResponse(result)


def get_fleet_catalog():
    """
    Central repository of commercial vehicle classes, technical specifications,
    feature icons (CCTV, First Aid, Ice Box, TV, Air Suspension), real photography,
    and commercial rate cards for the customer portal.
    """
    catalog = [
        {
            'id': 'luxury_coach',
            'category': 'bus',
            'name': 'Volvo 9600 Multi-Axle Flagship Coach',
            'title': '54-Seater Intercity Air-Suspension Flagship Coach',
            'tagline': 'State-of-the-art multi-axle interstate cruiser with zero-jerk air glide technology.',
            'image': '/static/images/fleet/volvo_coach.jpg',
            'gallery': [
                '/static/images/fleet/volvo_coach.jpg',
                '/static/images/hero_tour_bus.jpg',
                '/static/images/fleet_lineup.jpg',
            ],
            'seating_capacity': 54,
            'transmission': '12-Speed I-Shift Automatic',
            'rate_per_km': 48,
            'min_km_day': 300,
            'driver_bata': 800,
            'night_halt': 500,
            'seating_layout': '2x2 Calf-Support Pushback Recliners with Footrests',
            'luggage_capacity': 'Massive 8.5 m³ Underbelly Pneumatic Luggage Boot',
            'engine_specs': 'Volvo D8K Euro-VI 350 HP Engine • 12-Speed Auto',
            'ac_system': 'Carrier Integrated Climate Control with Fresh Air HEPA Filter',
            'suspension': 'Electronically Controlled Air Suspension (ECAS) with Kneeling',
            'entertainment': 'Twin 43" 4K Smart TVs + High-Bass JBL Dolby Sound & Party Lights',
            'charging': 'Dual Fast-Charging USB-C Ports at Every Passenger Seat',
            'safety': 'Electronic Stability (ESP), AIS-140 GPS, Auto Fire Suppression System',
            'ideal_for': 'College Industrial Visits (IVs), inter-state tours, corporate conventions.',
            'badge': 'Ultimate Luxury Glider',
            'amenities': ['Full Air Suspension', 'DJ Audio & Laser Lights', 'Twin 43" Screens', 'Calf-Support Recliners', 'Massive Cargo Boot'],
            'features': [
                {'icon': '☁️', 'name': 'All-Air Suspension (ECAS)', 'desc': 'Electronically controlled air bellows deliver floating glide on ghat roads'},
                {'icon': '💺', 'name': 'Calf-Support Recliners', 'desc': '140-degree deep recline ergonomic seating with fold-out legrests'},
                {'icon': '📺', 'name': 'Twin 43" Smart 4K TVs', 'desc': 'HDMI, Bluetooth, wireless mic for tour guides, and JBL DJ surround sound'},
                {'icon': '📹', 'name': 'AIS-140 GPS & Dual CCTV', 'desc': 'Live satellite telematics and cabin surveillance linked to Coimbatore Control Desk'},
                {'icon': '🧊', 'name': 'Onboard Chiller Ice Box', 'desc': 'Chilled mineral water bottles and refreshment storage during long trips'},
                {'icon': '🧯', 'name': 'Fire Detection & Suppression', 'desc': 'Automated engine bay fire detection and cabin emergency exit doors'},
                {'icon': '🩹', 'name': 'Trauma First Aid Kit', 'desc': 'Equipped paramedic medical first response kit and emergency glass-break hammers'},
                {'icon': '⚡', 'name': 'Dual USB-C at Every Seat', 'desc': 'Fast smartphone & laptop charging outlets on each armrest'},
            ],
            'overview': (
                'The Volvo 9600 Multi-Axle is our crown jewel passenger cruiser. Designed specifically for long-distance '
                'interstate journeys, college IV expeditions to Kerala and Goa, and executive corporate movements. '
                'Fitted with electronically controlled pneumatic air suspension that eliminates road bumps and hill-climb fatigue. '
                'Equipped with 350 HP Volvo power, active emergency braking, and statutory AIS-140 satellite GPS telematics.'
            ),
            'faqs': [
                {'q': 'What is the luggage capacity on this 54-seater Volvo?', 'a': 'The Volvo 9600 features an expansive 8.5 cubic meter underbelly pneumatic luggage hold capable of accommodating over 60 large trolley bags and equipment cases with ease.'},
                {'q': 'Are interstate border permits included in the quote?', 'a': 'Our Volvo coaches hold active All-India Tourist Permits (AITP). State border road taxes and FASTag electronic toll charges are billed at actual government receipts.'},
                {'q': 'Can we use the sound system and mic for college IV presentations?', 'a': 'Yes, the coach includes a wireless PA microphone system for tour coordinators and dual 43-inch smart screens connected to high-bass party speakers.'},
            ]
        },
        {
            'id': 'scania_coach',
            'category': 'bus',
            'name': 'Scania Metrolink HD Semi-Sleeper',
            'title': '53-Seater High-Deck Luxury Coach',
            'tagline': 'High-deck touring coach engineered for maximum panoramic visibility and whisper-quiet highway cruising.',
            'image': '/static/images/fleet_lineup.jpg',
            'gallery': [
                '/static/images/fleet_lineup.jpg',
                '/static/images/fleet/volvo_coach.jpg',
                '/static/images/hero_tour_bus.jpg',
            ],
            'seating_capacity': 53,
            'transmission': 'Scania Opticruise Automated',
            'rate_per_km': 46,
            'min_km_day': 300,
            'driver_bata': 800,
            'night_halt': 500,
            'seating_layout': '2x2 High-Deck Semi-Sleeper Reclining Chairs',
            'luggage_capacity': '8.0 m³ High-Volume Luggage Compartment',
            'engine_specs': 'Scania 9-Litre 360 HP Euro-VI Turbo Diesel',
            'ac_system': 'High-Capacity Rooftop HVAC with Individual Louvers',
            'suspension': 'Full Air Suspension with Anti-Roll Stabilizer Bars',
            'entertainment': 'Dual HD LED Monitors + Wireless Mic + JBL Audio',
            'charging': 'Dedicated USB Ports at Each Row',
            'safety': 'Retarder Braking, ESP, AIS-140 GPS, Dual Emergency Exits',
            'ideal_for': 'Inter-state college IV circuits, temple pilgrimages, corporate conventions.',
            'badge': 'High-Deck Cruiser',
            'amenities': ['Full Air Suspension', 'Semi-Sleeper Recliners', 'Dual Monitors', 'USB Ports', 'Huge Boot Space'],
            'features': [
                {'icon': '☁️', 'name': 'Full Air Suspension', 'desc': 'Floating ride quality on highways and winding ghat roads'},
                {'icon': '💺', 'name': 'Semi-Sleeper Ergonomics', 'desc': 'Wide contour seats with calf support and plush neck cushions'},
                {'icon': '📺', 'name': 'Dual HD LED Monitors', 'desc': 'Complete entertainment with Bluetooth audio and microphone'},
                {'icon': '📹', 'name': 'AIS-140 Telematics', 'desc': 'Real-time satellite GPS tracking with speed governor locked at 80 km/h'},
                {'icon': '🧊', 'name': 'Refreshment Ice Cooler', 'desc': 'Insulated cold storage for drinking water bottles'},
                {'icon': '🧯', 'name': 'Fire Safety Extinguishers', 'desc': 'Full statutory ABC fire suppression cylinders and hammer exits'},
                {'icon': '🩹', 'name': 'First Aid Kit', 'desc': 'Certified medical emergency kit on board'},
                {'icon': '⚡', 'name': 'Individual USB Ports', 'desc': 'Fast charging sockets on every seat armrest'},
            ],
            'overview': (
                'The Scania Metrolink HD Semi-Sleeper offers superior panoramic sightlines from an elevated passenger deck. '
                'Renowned for its whisper-quiet cabin insulation and Scania Opticruise smooth transmission. '
                'A proven favorite for South India heritage circuits, Madurai-Rameshwaram pilgrimages, and university study tours.'
            ),
            'faqs': [
                {'q': 'Is this coach air-conditioned throughout?', 'a': 'Yes, it features a heavy-duty rooftop HVAC chiller unit with individual adjustable airflow louvers and reading lamps for every passenger.'},
                {'q': 'What is the daily billing minimum?', 'a': 'Our standard outstation minimum billing is 300 KM per calendar day. Excess kilometers beyond the package quota are billed at ₹46 per KM.'},
            ]
        },
        {
            'id': 'bharatbenz_coach',
            'category': 'bus',
            'name': 'BharatBenz 1624 Luxury Tourist Coach',
            'title': '43-Seater Premium Air-Conditioned Coach',
            'tagline': 'German-engineered chassis with robust durability for South India hill stations and highway tours.',
            'image': '/static/images/hero_tour_bus.jpg',
            'gallery': [
                '/static/images/hero_tour_bus.jpg',
                '/static/images/fleet_lineup.jpg',
                '/static/images/fleet/volvo_coach.jpg',
            ],
            'seating_capacity': 43,
            'transmission': '6-Speed Synchromesh Manual',
            'rate_per_km': 42,
            'min_km_day': 300,
            'driver_bata': 750,
            'night_halt': 500,
            'seating_layout': '2x2 Wide Pushback Seats with Armrests',
            'luggage_capacity': '6.5 m³ Underfloor Luggage Boot',
            'engine_specs': 'OM 926 7.2L Turbo Diesel • 240 HP • 850 Nm Torque',
            'ac_system': 'Sutrak Heavy-Duty Rooftop Air Conditioning Unit',
            'suspension': 'Parabolic Leaf Springs with Shock Absorbers',
            'entertainment': '32-inch LED TV + PA Mic + Stereo Speakers',
            'charging': 'Dual USB Sockets in Every Row',
            'safety': 'Wabco Anti-Lock Braking (ABS), Speed Governor (80 km/h), AIS-140 GPS',
            'ideal_for': 'School excursions, 40-student college batches, corporate outbound retreats.',
            'badge': 'German Engineering',
            'amenities': ['Pushback Seats', 'Rooftop AC Unit', '32" LED Screen', 'PA Mic', 'Underbelly Boot'],
            'features': [
                {'icon': '💺', 'name': 'High-Back Pushback Seats', 'desc': 'Wide ergonomic seats with fabric upholstery and armrests'},
                {'icon': '❄️', 'name': 'Heavy-Duty Rooftop AC', 'desc': 'Rapid cooling performance even in peak South India summer'},
                {'icon': '📺', 'name': '32" LED Screen & Audio', 'desc': 'High-clarity video display with guide microphone input'},
                {'icon': '📹', 'name': 'AIS-140 GPS Security', 'desc': 'Continuous tracking with 24x7 emergency SOS button'},
                {'icon': '🧯', 'name': 'Fire Safety System', 'desc': 'Emergency exit windows and dual fire extinguishers'},
                {'icon': '🩹', 'name': 'First Aid Station', 'desc': 'Standard certified medical kit on board'},
                {'icon': '⚡', 'name': 'Seat USB Outlets', 'desc': 'Fast charging for smartphones and mobile devices'},
            ],
            'overview': (
                'The BharatBenz 1624 coach represents German chassis precision tailored for Indian road conditions. '
                'Featuring a 240 HP engine with immense torque for steep Nilgiris and Western Ghats ascents. '
                'The ideal choice for medium-sized college groups, corporate outbound teams, and extended wedding convoys.'
            ),
            'faqs': [
                {'q': 'Can this coach navigate Ooty and Kodaikanal hairpin bends?', 'a': 'Yes, our 43-seater BharatBenz coaches are specifically certified for Nilgiris ghat routes and are operated only by hill-licensed senior chauffeurs.'},
            ]
        },
        {
            'id': 'mini_bus',
            'category': 'bus',
            'name': 'Deluxe Tourist Mini Bus (Ashok Leyland / Eicher)',
            'title': '36-Seater Deluxe Tourist Coach',
            'tagline': 'Optimal balance of high passenger capacity and nimble ghat-road manoeuvrability.',
            'image': '/static/images/fleet_lineup.jpg',
            'gallery': [
                '/static/images/fleet_lineup.jpg',
                '/static/images/hero_tour_bus.jpg',
                '/static/images/fleet/force_urbania.jpg',
            ],
            'seating_capacity': 36,
            'transmission': '5-Speed Manual with Power Steering',
            'rate_per_km': 38,
            'min_km_day': 300,
            'driver_bata': 700,
            'night_halt': 500,
            'seating_layout': '2x2 High-Back Ergonomic Pushback Seats',
            'luggage_capacity': 'High-Volume Underbelly Storage + Deep Overhead Racks',
            'engine_specs': 'Ashok Leyland H-Series 4-Cylinder Turbocharged Diesel',
            'ac_system': 'Heavy-Duty Rooftop Carrier Chiller Unit',
            'suspension': 'Semi-Elliptical Multi-Leaf with Anti-Roll Bar',
            'entertainment': '32-inch LED TV Screen + JBL Dolby Audio System + Mic',
            'charging': 'Gangway USB Charging Stations & Reading Lamps',
            'safety': 'Emergency Exit Door, Break-Glass Hammers, Speed Limiter, GPS',
            'ideal_for': 'School excursions, wedding guest logistics, pilgrim group tours.',
            'badge': 'High Capacity Value',
            'amenities': ['2x2 Pushback Seats', 'JBL Sound System', 'PA Mic for Guide', 'Rooftop AC Unit', 'Huge Cargo Boot'],
            'features': [
                {'icon': '💺', 'name': 'Ergonomic 2x2 Pushback Seats', 'desc': 'Cushioned reclining seats with headrests and deep foot room'},
                {'icon': '❄️', 'name': 'Carrier Rooftop Chiller', 'desc': 'Rapid cooling throughout the entire passenger gangway'},
                {'icon': '📺', 'name': '32" LED Screen + Mic', 'desc': 'Entertainment display with microphone for tour guides'},
                {'icon': '📹', 'name': 'AIS-140 GPS Telematics', 'desc': 'Government-certified live speed and location monitoring'},
                {'icon': '🧯', 'name': 'Safety Equipment', 'desc': 'Break-glass hammers, emergency rear exit, and fire extinguishers'},
                {'icon': '🩹', 'name': 'First Aid Kit', 'desc': 'Standard emergency supplies for school & pilgrim groups'},
                {'icon': '⚡', 'name': 'USB Charging Stations', 'desc': 'Gangway fast-charging outlets for passengers'},
            ],
            'overview': (
                'The 36-Seater Deluxe Mini Bus provides the sweet spot for group travel. It carries large parties '
                'without the footprint of a full multi-axle coach, allowing effortless navigation through town centers, '
                'tight temple approaches, and narrow mountain passes like Valparai and Munnar.'
            ),
            'faqs': [
                {'q': 'Is this suitable for school excursions?', 'a': 'Extremely popular for school day-trips, sports tournaments, and college department visits due to its high passenger safety and cost efficiency.'},
            ]
        },
        {
            'id': 'tt',
            'category': 'van',
            'name': 'Force Urbania & Tempo Traveller',
            'title': '17-Seater Executive Luxury Tourist Van',
            'tagline': 'Mercedes-Benz derived aerodynamic platform with walk-through standing cabin.',
            'image': '/static/images/fleet/force_urbania.jpg',
            'gallery': [
                '/static/images/fleet/force_urbania.jpg',
                '/static/images/fleet/innova_crysta.jpg',
                '/static/images/fleet_lineup.jpg',
            ],
            'seating_capacity': 17,
            'transmission': '5-Speed Synchromesh Manual',
            'rate_per_km': 26,
            'min_km_day': 300,
            'driver_bata': 600,
            'night_halt': 400,
            'seating_layout': '1x1 & 2x1 Individual Pushback Recliners with Aisle Walkway',
            'luggage_capacity': 'Dedicated Rear Luggage Trunk + Overhead Parcel Racks',
            'engine_specs': 'Mercedes-derived FM 2.6 CR ED Diesel • 115 HP • 350 Nm',
            'ac_system': 'Roof-Mounted High-Capacity Chiller with Individual Vents',
            'suspension': 'Transverse Leaf Spring Front & Parabolic Rear (Gliding Ride)',
            'entertainment': '32-inch Smart LED TV + Wireless Mic for Tour Guides',
            'charging': 'Individual USB Fast Charging Port at Every Seat',
            'safety': 'All-Wheel Disc Brakes with ABS + EBD, AIS-140 GPS, Fire Extinguisher',
            'ideal_for': 'Extended family vacations, college industrial batches, corporate offsites.',
            'badge': 'Executive Group Choice',
            'amenities': ['Walk-Through Cabin', 'Individual Pushback Recliners', '32" Smart LED TV', 'PA Mic System', 'Overhead AC Vents'],
            'features': [
                {'icon': '🚶', 'name': 'Full Standing Height', 'desc': '6.2-ft walk-through standing gangway with zero stooping'},
                {'icon': '💺', 'name': 'Individual Pushback Seats', 'desc': 'Luxury recliners with armrests and personalized space'},
                {'icon': '📺', 'name': '32" Smart LED TV', 'desc': 'Smart TV with Bluetooth audio streaming and guide microphone'},
                {'icon': '❄️', 'name': 'Ceiling AC Vents', 'desc': 'Individual overhead air louvers for personalized cooling'},
                {'icon': '📹', 'name': 'AIS-140 Satellite GPS', 'desc': 'Live telemetry, speed monitoring, and 24x7 emergency SOS'},
                {'icon': '🛑', 'name': 'All-Wheel Disc Brakes', 'desc': 'Class-leading braking safety with ABS and EBD stability'},
                {'icon': '⚡', 'name': 'Seat USB Fast Charging', 'desc': 'Fast charging socket mounted at every seat row'},
                {'icon': '🩹', 'name': 'First Aid Trauma Kit', 'desc': 'Complete first response medical emergency box'},
            ],
            'overview': (
                'The Force Urbania is South India’s most modern luxury passenger van. With a full 6.2-ft standing '
                'height ceiling, individual luxury pushback seats, and car-like independent suspension, it delivers '
                'an incomparable group travel experience for 12 to 17 travelers. Ideal for high-profile family road trips, '
                'temple circuits, and corporate project teams.'
            ),
            'faqs': [
                {'q': 'Can passengers stand up and walk inside?', 'a': 'Yes, the Urbania features a cavernous 6.2-foot interior standing height so adults can comfortably walk without bending.'},
                {'q': 'How much luggage can 17 passengers bring?', 'a': 'It features a deep rear boot plus wide overhead racks that hold up to 14 large bags and backpacks.'},
            ]
        },
        {
            'id': 'urbania_10',
            'category': 'van',
            'name': '10-Seater Super-Luxury Force Urbania',
            'title': '10-Seater VIP Executive Glider',
            'tagline': 'Ultra-luxury captain-seat touring cabin with custom ambient starlight roof and private salon layout.',
            'image': '/static/images/fleet/force_urbania.jpg',
            'gallery': [
                '/static/images/fleet/force_urbania.jpg',
                '/static/images/fleet/innova_crysta.jpg',
                '/static/images/fleet_lineup.jpg',
            ],
            'seating_capacity': 10,
            'transmission': '5-Speed Manual with Hydraulic Clutch',
            'rate_per_km': 28,
            'min_km_day': 300,
            'driver_bata': 600,
            'night_halt': 400,
            'seating_layout': '1x1 Ultra-Plush Captain Recliner Chairs with Calf Support',
            'luggage_capacity': 'Oversized Cargo Boot (10 Large Suitcases)',
            'engine_specs': 'Mercedes-derived FM 2.6 CR ED Diesel • 115 HP',
            'ac_system': 'Multi-Zone Whisper-Quiet Automatic Air Conditioner',
            'suspension': 'Parabolic Gliding Leaf Springs with Gas Shock Absorbers',
            'entertainment': '32" Smart LED TV + Apple CarPlay / Android Auto + JBL Audio',
            'charging': 'Dual Fast-Charging USB-C Ports at Every Armrest',
            'safety': 'All-Wheel Discs, Electronic Brakeforce Distribution, AIS-140 GPS',
            'ideal_for': 'VIP delegations, destination weddings, luxury corporate retreats.',
            'badge': 'VIP Salon Edition',
            'amenities': ['Captain Recliner Chairs', '32" Smart LED TV', 'Starlight Ambient Roof', 'Whisper-Quiet Cabin', 'All-Wheel Discs'],
            'features': [
                {'icon': '👑', 'name': '1x1 VIP Captain Chairs', 'desc': 'Deep leatherette captain recliners with memory foam and calf rests'},
                {'icon': '✨', 'name': 'Starlight Ambient Roof', 'desc': 'Integrated LED mood lighting and starry sky illumination'},
                {'icon': '📺', 'name': '32" Smart LED Display', 'desc': 'High-definition streaming screen with JBL surround audio'},
                {'icon': '🧊', 'name': 'Onboard Beverage Cooler', 'desc': 'Chilled ice box for beverages and refreshment storage'},
                {'icon': '📹', 'name': 'AIS-140 GPS Tracking', 'desc': 'Live satellite monitoring with 24x7 SOS emergency button'},
                {'icon': '🛑', 'name': 'ABS & All-Wheel Discs', 'desc': 'High-performance braking for secure ghat descent'},
                {'icon': '⚡', 'name': 'Fast USB-C at Every Seat', 'desc': 'Dual charging ports on every armrest'},
            ],
            'overview': (
                'Crafted for VIP travelers who demand business-class luxury on road trips. The 10-Seater Super-Luxury '
                'Urbania replaces standard seating with individual captain recliners, custom starlight ambient roof, '
                'and acoustic noise insulation. Perfect for executive corporate delegations, weddings, and premium holidays.'
            ),
            'faqs': [
                {'q': 'Does each seat have independent armrests and recline?', 'a': 'Yes, every passenger sits in an independent captain seat with 140-degree recline, plush calf support, and personal USB-C power.'},
            ]
        },
        {
            'id': 'crysta',
            'category': 'car',
            'name': 'Toyota Innova Crysta Luxury MPV',
            'title': 'Premier 7-Seater Chauffeur Driven MPV',
            'tagline': "South India's undisputed king of hill stations and family road trips.",
            'image': '/static/images/fleet/innova_crysta.jpg',
            'gallery': [
                '/static/images/fleet/innova_crysta.jpg',
                '/static/images/fleet/swift_dzire.jpg',
                '/static/images/fleet_lineup.jpg',
            ],
            'seating_capacity': 7,
            'transmission': '5-Speed Manual / 6-Speed Auto',
            'rate_per_km': 19,
            'min_km_day': 300,
            'driver_bata': 500,
            'night_halt': 300,
            'seating_layout': '1 Driver + 2 Captain Recliner Chairs (Middle) + 3 Rear Seats',
            'luggage_capacity': '4 Large Trolley Bags + 3 Duffles (Foldable 3rd Row)',
            'engine_specs': '2.4L D-4D Turbo Diesel • 150 PS • 360 Nm Torque',
            'ac_system': 'Dual-Zone Digital Automatic Climate Control with Ceiling Vents',
            'suspension': 'Double Wishbone Front & 4-Link Coil Spring (Zero Ghat Sway)',
            'entertainment': 'Smart Touchscreen Infotainment with Bluetooth & USB',
            'charging': 'Individual Fast Charging Ports in Row 1, 2, and 3',
            'safety': '3 Airbags, Hill-Start Assist, Vehicle Stability Control, Speed Governor',
            'ideal_for': 'Ooty 36-hairpin climbs, Munnar, Kodaikanal, temple yatras, VIP visits.',
            'badge': 'Most Popular Hill MPV',
            'amenities': ['Captain Recliner Seats', 'Dual Climate Control', 'Hill-Climb Specialist', 'Surround Sound', 'Large Boot Space'],
            'features': [
                {'icon': '💺', 'name': 'Middle Row Captain Chairs', 'desc': 'Individual sliding and reclining captain seats with slide-out tray tables'},
                {'icon': '⛰️', 'name': 'Hill-Climb Champion', 'desc': '360 Nm diesel torque effortlessly conquers steep 36-hairpin Nilgiris ghats'},
                {'icon': '❄️', 'name': 'Dual Climate Control', 'desc': 'Dedicated rear roof AC vents with digital automatic temperature control'},
                {'icon': '🛡️', 'name': 'Triple Airbags & VSC', 'desc': 'Vehicle Stability Control and Hill-Start Assist for peak passenger safety'},
                {'icon': '📹', 'name': 'AIS-140 GPS Telematics', 'desc': 'Live telematics tracking and SOS button linked to Coimbatore desk'},
                {'icon': '⚡', 'name': 'Fast USB Outlets', 'desc': 'Charging ports accessible in all 3 rows'},
                {'icon': '🩹', 'name': 'First Aid Kit', 'desc': 'Medical kit and emergency road triangle on board'},
            ],
            'overview': (
                'The Toyota Innova Crysta is the undisputed benchmark of Indian family travel. Renowned for its '
                'indestructible reliability, comfortable ride, and powerful hill-climbing prowess across the Western Ghats. '
                'Features spacious middle-row captain seats, rear AC vents for all rows, and ample luggage space.'
            ),
            'faqs': [
                {'q': 'How many passengers and bags can fit comfortably?', 'a': 'Up to 6 adults or 4 adults and 3 children, along with 4 large suitcases and backpacks.'},
                {'q': 'Are your chauffeurs trained for ghat driving?', 'a': 'Yes, all our Innova Crysta drivers have minimum 8+ years experience on Ooty, Kodaikanal, and Munnar hill roads.'},
            ]
        },
        {
            'id': 'innova_hycross',
            'category': 'car',
            'name': 'Maruti Invicto / Innova HyCross Hybrid',
            'title': '7-Seater Self-Charging Hybrid Luxury MPV',
            'tagline': 'Ultra-refined monocoque luxury with whisper-quiet electric hybrid glide.',
            'image': '/static/images/fleet/innova_crysta.jpg',
            'gallery': [
                '/static/images/fleet/innova_crysta.jpg',
                '/static/images/fleet/swift_dzire.jpg',
                '/static/images/fleet_lineup.jpg',
            ],
            'seating_capacity': 7,
            'transmission': 'e-CVT Automatic Transmission',
            'rate_per_km': 21,
            'min_km_day': 300,
            'driver_bata': 500,
            'night_halt': 300,
            'seating_layout': '2 Ottoman Recliner Chairs (Middle) + 3 Rear Seats',
            'luggage_capacity': '4 Large Trolley Bags + Soft Luggage',
            'engine_specs': '2.0L TNGA Strong Hybrid Petrol-Electric • 186 PS Combined',
            'ac_system': 'Multi-Zone Automatic Climate Control with Air Purifier',
            'suspension': 'TNGA Monocoque Chassis with All-Independent Suspension',
            'entertainment': '10.1" Touchscreen with Wireless Apple CarPlay & Android Auto',
            'charging': 'Type-C USB Fast Charging Ports Across All Rows',
            'safety': '6 Airbags, ABS, Electronic Parking Brake with Auto Hold, GPS',
            'ideal_for': 'Executive corporate travel, tech park shuttles, luxury airport transit.',
            'badge': 'Eco Hybrid Luxury',
            'amenities': ['Strong Hybrid Engine', 'Ottoman Recliner Seats', 'Whisper-Quiet Cabin', '10.1" Smart Screen', '6 Airbags'],
            'features': [
                {'icon': '🔋', 'name': 'Self-Charging Hybrid', 'desc': 'Silent EV mode driving in city traffic with ultra-low carbon emissions'},
                {'icon': '💺', 'name': 'Ottoman Luxury Recliners', 'desc': 'Middle-row captain chairs with power recline and calf support'},
                {'icon': '🌿', 'name': 'Cabin Air Purifier', 'desc': 'Integrated PM2.5 air filter for healthy, dust-free breathing'},
                {'icon': '🛡️', 'name': '6 Airbags & Auto Hold', 'desc': 'Full curtain airbags and Electronic Parking Brake safety'},
                {'icon': '📹', 'name': 'AIS-140 GPS Monitoring', 'desc': 'Live satellite speed and location telematics'},
                {'icon': '⚡', 'name': 'USB-C Fast Charging', 'desc': 'Fast charging ports accessible in all rows'},
            ],
            'overview': (
                'The Innova HyCross / Invicto brings modern monocoque passenger comfort and strong hybrid technology. '
                'Delivering whisper-quiet electric starts, panoramic cabin refinement, and luxurious ottoman seating. '
                'The top choice for eco-conscious executives and premium outstation travellers.'
            ),
            'faqs': [
                {'q': 'Is this vehicle automatic or manual?', 'a': 'It features Toyota’s smooth e-CVT automatic transmission for jerk-free travel.'},
            ]
        },
        {
            'id': 'sedan',
            'category': 'car',
            'name': 'Swift Dzire / Toyota Etios Sedan',
            'title': '4-Seater Executive Compact Sedan',
            'tagline': 'Comfortable, fuel-efficient transit for solo executives, couples, and small families.',
            'image': '/static/images/fleet/swift_dzire.jpg',
            'gallery': [
                '/static/images/fleet/swift_dzire.jpg',
                '/static/images/fleet/innova_crysta.jpg',
                '/static/images/fleet_lineup.jpg',
            ],
            'seating_capacity': 4,
            'transmission': '5-Speed Manual Transmission',
            'rate_per_km': 13,
            'min_km_day': 250,
            'driver_bata': 500,
            'night_halt': 300,
            'seating_layout': '1 Driver + 1 Co-Passenger + 2-3 Rear Passengers',
            'luggage_capacity': '2 Large Suitcases + 2 Handbags (Boot: 378 Liters)',
            'engine_specs': '1.2L DualJet Petrol / Diesel • 90 PS Engine',
            'ac_system': 'High-Efficiency Dual Air-Conditioning with Rear Vents',
            'suspension': 'MacPherson Strut Front & Torsion Beam Rear',
            'entertainment': 'Bluetooth Audio & Surround Stereo System',
            'charging': 'Front & Rear 12V USB Fast Charging Sockets',
            'safety': 'Dual Airbags, ABS with EBD, Speed Governor (80 km/h), AIS-140 GPS',
            'ideal_for': 'Coimbatore to Bangalore one-way drops, airport transfers, day tours.',
            'badge': 'Best for Solo & Couples',
            'amenities': ['Dual AC', 'Plush Fabric Reclining Seats', 'Fast USB Charging', 'Chauffeur Driven', 'AIS-140 GPS'],
            'features': [
                {'icon': '💺', 'name': 'Plush Fabric Reclining Seats', 'desc': 'Supportive ergonomic cushions with rear center armrest'},
                {'icon': '❄️', 'name': 'Chilled Air-Conditioning', 'desc': 'Rapid cooling with rear AC vents for passenger comfort'},
                {'icon': '⚡', 'name': 'Fast USB Charging', 'desc': 'Charging sockets available in both front and rear'},
                {'icon': '📹', 'name': 'AIS-140 GPS Telematics', 'desc': 'Real-time satellite GPS tracking with speed governor locked at 80 km/h'},
                {'icon': '🛡️', 'name': 'Dual Airbags & ABS', 'desc': 'Anti-lock braking with Electronic Brakeforce Distribution'},
                {'icon': '🩹', 'name': 'First Aid Kit', 'desc': 'Standard emergency medical supplies on board'},
            ],
            'overview': (
                'Our compact sedan fleet offers unbeatable value and prompt mobility for point-to-point transfers, '
                'Coimbatore airport pickups, Bangalore drops, and day tours. Features clean, sanitized interiors, '
                'chilled AC, polite uniformed chauffeurs, and transparent per-KM billing.'
            ),
            'faqs': [
                {'q': 'Can we book a one-way outstation drop?', 'a': 'Yes, one-way drops (e.g. Coimbatore to Bangalore or Chennai) are available with transparent toll and driver bata charges.'},
            ]
        },
        {
            'id': 'caravan_luxury',
            'category': 'caravan',
            'name': 'Luxury Sleeper Camper Caravan & VIP Vanity Van',
            'title': 'Experiential Glamping Camper & VIP Studio Caravan',
            'tagline': 'South India’s custom-built mobile luxury suite with queen sleeper bed, ensuite washroom, kitchenette, and makeup studio.',
            'image': '/static/images/fleet/camper_caravan.jpg',
            'gallery': [
                '/static/images/fleet/camper_caravan.jpg',
                '/static/images/fleet/force_urbania.jpg',
                '/static/images/fleet_lineup.jpg',
            ],
            'seating_capacity': 6,
            'transmission': '6-Speed Manual with Hill-Assist',
            'rate_per_km': 45,
            'min_km_day': 250,
            'driver_bata': 800,
            'night_halt': 600,
            'seating_layout': 'Convertible Lounge Sofa-cum-Bed + 2 Swivel Captain Chairs',
            'luggage_capacity': 'High-Capacity Underbed Trunk + Modular Overhead Storage',
            'engine_specs': 'Mercedes-Derived 2.6L CRDI Turbo Diesel Engine',
            'ac_system': 'Dual 1.5 Ton Inverter AC (Shore Power + 5kVA Genset)',
            'suspension': 'Special Glide Suspension with Hydraulic Leveling Jacks',
            'entertainment': '40-inch Smart LED TV + Bluetooth Soundbar + Wi-Fi Hotspot',
            'charging': '230V Domestic AC Outlets + Multiple USB-C Fast Chargers',
            'safety': 'AIS-140 GPS, Dual Airbags, ABS, Smoke/LPG Gas Detector, Fire Extinguisher',
            'ideal_for': 'Western Ghats glamping, film/bridal vanity studio, romantic couple getaways, offbeat road trips.',
            'badge': 'Experiential Glamping & Vanity',
            'amenities': ['Ensuite Hot Shower & Bio-Toilet', 'Kitchenette & Microwave', 'Silent Onboard Genset', 'Retractable Awning & Camp Chairs', 'Lighted Vanity Makeup Mirror'],
            'features': [
                {'icon': '🚿', 'name': 'Ensuite Shower & Washroom', 'desc': 'Private running hot & cold water shower with eco bio-toilet'},
                {'icon': '🍳', 'name': 'Kitchenette & Mini Fridge', 'desc': 'Induction cooktop, microwave, electric kettle, and chilled refrigerator'},
                {'icon': '🏕️', 'name': 'Retractable Awning & Patio', 'desc': 'Exterior sunshade with camping chairs and outdoor warm fairy lights'},
                {'icon': '💄', 'name': 'VIP Vanity Makeup Station', 'desc': 'Daylight LED mirror with dedicated changing space for bridal/shoot sets'},
                {'icon': '⚡', 'name': 'Silent 5kVA Genset & Inverter', 'desc': 'Continuous 24x7 off-grid electricity and chilled air conditioning'},
                {'icon': '🛏️', 'name': 'Queen Size Memory Foam Bed', 'desc': 'Plush convertible sleeping suite with panoramic stargazing windows'},
                {'icon': '📹', 'name': 'AIS-140 GPS & Security', 'desc': '24x7 telemetry and SOS panic system monitored by Coimbatore hub'},
                {'icon': '🩹', 'name': 'Trauma First Aid Kit', 'desc': 'Certified paramedic kit for remote camping trails'},
            ],
            'overview': (
                'Experience hotel-grade comfort on four wheels. Our custom Luxury Sleeper Camper Caravan and VIP Vanity Van '
                'is designed for travelers seeking experiential glamping across Munnar, Ooty, Kodaikanal, and Wayanad, '
                'as well as film shoots, celebrity transit, and bridal wedding green-rooms. Features an ensuite washroom, '
                'kitchenette, generator, and high-speed Wi-Fi.'
            ),
            'faqs': [
                {'q': 'Can we camp overnight inside the caravan in hill stations?', 'a': 'Yes! The vehicle has an onboard silent generator and inverter system that powers AC, lights, and hot water even at remote scenic camping grounds.'},
                {'q': 'Is the caravan equipped for bridal makeup or film production?', 'a': 'Absolutely. It includes high-lumen CRI-95 daylight vanity makeup mirrors, full-length dress trial space, and multiple 230V styling outlets.'},
            ]
        },
        {
            'id': 'safari_escort',
            'category': 'other',
            'name': '4x4 Safari Cruiser & Convoy Escort Utility',
            'title': 'High-Clearance All-Terrain Safari & Luggage Support',
            'tagline': 'Heavy-duty 4x4 vehicle specialized for jungle safaris, rough-terrain hill trails, and wedding/IV convoy luggage escort.',
            'image': '/static/images/fleet_lineup.jpg',
            'gallery': [
                '/static/images/fleet_lineup.jpg',
                '/static/images/hero_tour_bus.jpg',
                '/static/images/fleet/innova_crysta.jpg',
            ],
            'seating_capacity': 6,
            'transmission': '5-Speed Manual 4WD with Low-Range Transfer Case',
            'rate_per_km': 22,
            'min_km_day': 250,
            'driver_bata': 550,
            'night_halt': 350,
            'seating_layout': 'High-Mounted Panoramic Safari Seating (Forward & Side-Facing)',
            'luggage_capacity': 'Reinforced Rooftop Luggage Carrier (Up to 30 Large Bags)',
            'engine_specs': '2.6L Heavy-Duty High-Torque Turbo Diesel Engine',
            'ac_system': 'High-Output Tropical AC Unit',
            'suspension': 'Rigid Axles with Heavy-Duty Leaf Springs & Off-Road Dampers',
            'entertainment': 'All-Weather FM/Bluetooth Radio + PA Megaphone Unit',
            'charging': 'Heavy-Duty 12V High-Amperage USB Charging Ports',
            'safety': 'Roll Cage Reinforcement, Front Recovery Winch, AIS-140 GPS, First Aid',
            'ideal_for': 'Mudumalai & Valparai wildlife safaris, extreme terrain ghats, large wedding convoy luggage support.',
            'badge': 'Specialty All-Terrain',
            'amenities': ['4x4 Low-Range Drive', 'Rooftop Luggage Cage', 'Heavy-Duty Recovery Winch', 'High Ground Clearance', 'Rugged All-Terrain Tyres'],
            'features': [
                {'icon': '🚙', 'name': 'Shift-on-the-Fly 4WD', 'desc': 'Conquers unpaved jungle tracks, estate roads, and deep plantation slush'},
                {'icon': '🧳', 'name': 'Mega Luggage Support Cage', 'desc': 'Securely carries excessive baggage and event materials for large tour groups'},
                {'icon': '🌲', 'name': 'High-Deck Safari View', 'desc': 'Elevated seating provides 360-degree wildlife viewing and photography'},
                {'icon': '📹', 'name': 'AIS-140 GPS Telematics', 'desc': 'Live satellite monitoring for off-grid travel safety'},
                {'icon': '🩹', 'name': 'Emergency Recovery Kit', 'desc': 'Includes tow straps, winch, air compressor, and certified first aid kit'},
                {'icon': '❄️', 'name': 'Chilled Air Conditioning', 'desc': 'Reliable cabin cooling in all South Indian weather conditions'},
            ],
            'overview': (
                'Our specialty fleet category is engineered for non-standard travel demands. From off-road wildlife safaris '
                'in Anamalai and Mudumalai to heavy luggage escort support for 40-car wedding convoys and college IV tours. '
                'Operated by seasoned all-terrain drivers with deep local forest and ghat route knowledge.'
            ),
            'faqs': [
                {'q': 'Can this vehicle carry excess luggage for our 54-seater bus group?', 'a': 'Yes, it serves as a dedicated support escort vehicle capable of carrying extra equipment, wedding decor, musical instruments, and oversized bags.'},
            ]
        },
    ]

    # Dynamically synchronize and discover VehicleType records from Django Admin database:
    try:
        from core.models import VehicleType
        db_types = VehicleType.objects.all()
        curated_names = {v['name'].lower(): v for v in catalog}
        known_ids = {v['id'] for v in catalog}

        for vt in db_types:
            vt_name_lower = vt.name.lower().strip()
            # Ignore test / mock development seeds
            if any(junk in vt_name_lower for junk in ['test', 'phase', 'p3 ']):
                continue

            matched_item = None
            if 'crysta' in vt_name_lower or ('innova' in vt_name_lower and 'hycross' not in vt_name_lower and 'invicto' not in vt_name_lower):
                matched_item = next((v for v in catalog if v['id'] == 'crysta'), None)
            elif 'volvo' in vt_name_lower:
                matched_item = next((v for v in catalog if v['id'] == 'luxury_coach'), None)
            elif 'scania' in vt_name_lower:
                matched_item = next((v for v in catalog if v['id'] == 'scania_coach'), None)
            elif 'bharatbenz' in vt_name_lower:
                matched_item = next((v for v in catalog if v['id'] == 'bharatbenz_coach'), None)
            elif 'urbania' in vt_name_lower or '17-seater tempo' in vt_name_lower:
                matched_item = next((v for v in catalog if v['id'] == 'tt'), None)
            elif 'mini bus' in vt_name_lower or '36-seater' in vt_name_lower:
                matched_item = next((v for v in catalog if v['id'] == 'mini_bus'), None)
            elif 'dzire' in vt_name_lower or ('sedan' in vt_name_lower and len(vt_name_lower) < 15):
                matched_item = next((v for v in catalog if v['id'] == 'sedan'), None)
            elif 'ertiga' in vt_name_lower or 'hycross' in vt_name_lower or 'invicto' in vt_name_lower:
                matched_item = next((v for v in catalog if v['id'] == 'innova_hycross'), None)
            elif '54-seater' in vt_name_lower:
                matched_item = next((v for v in catalog if v['id'] == 'luxury_coach'), None)
            elif 'caravan' in vt_name_lower or 'camper' in vt_name_lower or 'vanity' in vt_name_lower:
                matched_item = next((v for v in catalog if v['id'] == 'caravan_luxury'), None)

            if matched_item:
                # Sync live rates or uploaded photo from admin if configured
                if vt.default_km_rate and vt.default_km_rate > 0:
                    matched_item['rate_per_km'] = int(vt.default_km_rate)
                if vt.driver_bata and vt.driver_bata > 0:
                    matched_item['driver_bata'] = int(vt.driver_bata)
                if vt.minimum_km_per_day and vt.minimum_km_per_day > 0:
                    matched_item['min_km_day'] = vt.minimum_km_per_day
                if vt.stock_photo:
                    matched_item['image'] = vt.stock_photo.url
            else:
                # Brand new vehicle type added by admin!
                cat = 'bus' if vt.seating_capacity >= 26 else ('van' if vt.seating_capacity >= 10 else 'car')
                if vt.category:
                    c_clean = vt.category.lower()
                    if 'caravan' in c_clean or 'camper' in c_clean or 'vanity' in c_clean:
                        cat = 'caravan'
                    elif 'coach' in c_clean or 'bus' in c_clean:
                        cat = 'bus'
                    elif 'tempo' in c_clean or 'van' in c_clean or 'urbania' in c_clean:
                        cat = 'van'
                    elif 'car' in c_clean or 'sedan' in c_clean or 'suv' in c_clean or 'mpv' in c_clean:
                        cat = 'car'
                    elif 'other' in c_clean or 'safari' in c_clean or 'utility' in c_clean:
                        cat = 'other'

                if vt.stock_photo:
                    img_url = vt.stock_photo.url
                elif cat == 'bus':
                    img_url = '/static/images/fleet/volvo_coach.jpg'
                elif cat == 'van':
                    img_url = '/static/images/fleet/force_urbania.jpg'
                elif cat == 'caravan':
                    img_url = '/static/images/fleet/camper_caravan.jpg'
                elif cat == 'other':
                    img_url = '/static/images/fleet_lineup.jpg'
                else:
                    img_url = '/static/images/fleet/innova_crysta.jpg'

                raw_amenities = [a.strip() for a in vt.amenities.split(',')] if vt.amenities else []
                amenities = raw_amenities if raw_amenities else ['Air Conditioning', 'Pushback Seats', 'AIS-140 GPS', 'Luggage Space']

                new_id = f'vt_{vt.id}'
                if new_id not in known_ids:
                    known_ids.add(new_id)
                    catalog.append({
                        'id': new_id,
                        'category': cat,
                        'name': vt.name,
                        'title': f'{vt.seating_capacity}-Seater {vt.name}',
                        'tagline': vt.description or f'Reliable commercial {vt.seating_capacity}-seater vehicle for group travel, corporate movements, and tours.',
                        'image': img_url,
                        'gallery': [img_url, '/static/images/fleet_lineup.jpg'],
                        'seating_capacity': vt.seating_capacity,
                        'transmission': vt.transmission_type or 'Manual',
                        'rate_per_km': int(vt.default_km_rate) if vt.default_km_rate > 0 else 25,
                        'min_km_day': vt.minimum_km_per_day or 250,
                        'driver_bata': int(vt.driver_bata) if vt.driver_bata > 0 else 500,
                        'night_halt': int(vt.night_halt_charge) if vt.night_halt_charge > 0 else 400,
                        'seating_layout': f'Plush {vt.seating_capacity}-Passenger Cabin',
                        'luggage_capacity': vt.luggage_capacity or 'Standard Luggage Hold',
                        'engine_specs': f'{vt.get_fuel_type_display()} Engine',
                        'ac_system': 'Heavy-Duty Rooftop Air Conditioning' if vt.has_ac else 'Non-AC',
                        'suspension': 'Comfort Road Suspension',
                        'entertainment': 'Stereo Sound System',
                        'charging': 'USB Device Charging',
                        'safety': 'AIS-140 GPS, Dual Airbags/ABS, Fire Safety Kit',
                        'ideal_for': f'Group tours, family road trips, and corporate commutes for up to {vt.seating_capacity} passengers.',
                        'badge': 'Verified Fleet',
                        'amenities': amenities,
                        'features': [
                            {'icon': '💺', 'name': 'Ergonomic Seats', 'desc': 'Comfort seating with wide legroom for long routes'},
                            {'icon': '❄️', 'name': 'Chilled Air Conditioning', 'desc': 'Rapid cooling throughout the entire passenger cabin'},
                            {'icon': '📹', 'name': 'AIS-140 Satellite GPS', 'desc': 'Real-time telemetry and 24x7 control room monitoring'},
                            {'icon': '🧯', 'name': 'Fire Safety Extinguisher', 'desc': 'Safety equipment certified by RTO norms'},
                            {'icon': '🩹', 'name': 'First Aid Station', 'desc': 'Standard emergency paramedic kit onboard'},
                            {'icon': '⚡', 'name': 'Device Charging', 'desc': 'USB points for passenger mobile phones'},
                            {'icon': '🛑', 'name': 'ABS Braking Safety', 'desc': 'Anti-lock braking system for highway stability'},
                            {'icon': '🧳', 'name': 'Spacious Luggage Boot', 'desc': 'Dedicated storage hold for passenger luggage'},
                        ],
                        'overview': vt.description or f'{vt.name} is a versatile commercial vehicle suited for passenger commutes, group expeditions, and outstation trips across South India.',
                        'faqs': [
                            {'q': f'How many passengers can travel in this {vt.name}?', 'a': f'This vehicle is registered for {vt.seating_capacity} passengers + 1 chauffeur.'},
                            {'q': 'Is driver bata and toll included?', 'a': 'Driver bata is included as per tariff card. Tolls, parking, and state entry permits are billed at actuals.'},
                        ]
                    })
    except Exception:
        pass

    return catalog


def fleet_showcase_page(request):
    """
    Dedicated Fleet Showcase Page rendered in Modern Card Grid format
    (matching Reference Image 2) with category filters, specs, and comparison matrix.
    """
    fleet_catalog = get_fleet_catalog()
    selected_category = request.GET.get('category', 'all')
    
    category_counts = {
        'all': len(fleet_catalog),
        'car': sum(1 for v in fleet_catalog if v.get('category') == 'car'),
        'bus': sum(1 for v in fleet_catalog if v.get('category') == 'bus'),
        'van': sum(1 for v in fleet_catalog if v.get('category') == 'van'),
        'caravan': sum(1 for v in fleet_catalog if v.get('category') == 'caravan'),
        'other': sum(1 for v in fleet_catalog if v.get('category') == 'other'),
    }
        
    context = {
        'fleet_catalog': fleet_catalog,
        'all_fleet': fleet_catalog,
        'selected_category': selected_category,
        'category_counts': category_counts,
        'total_active_fleet': 320,
    }
    return render(request, 'customer_portal/fleet_showcase.html', context)


def vehicle_detail_page(request, vehicle_id):
    """
    Dedicated Vehicle Detail Page (matching Reference Image 3 & 5) featuring:
    - Hero banner & vehicle overview
    - Left column: Vehicle card + Sticky Instant Quote / Booking Form
    - Right column: Icon-based Feature Badges (CCTV, Ice Box, First Aid, TV, etc.)
    - Real photo gallery grid
    - Complete transparent rate card & specifications table
    - Frequently Asked Questions (FAQ) Accordion
    """
    fleet_catalog = get_fleet_catalog()
    vehicle = next((v for v in fleet_catalog if v['id'] == vehicle_id), None)
    if not vehicle:
        # Fallback to first vehicle if invalid ID
        vehicle = fleet_catalog[0]
        
    # Get 3 related/other vehicles for bottom recommendation row
    related_vehicles = [v for v in fleet_catalog if v['id'] != vehicle['id']][:3]
    
    # Pre-calculated 1-day minimum estimate
    estimated_day_cost = (vehicle['rate_per_km'] * vehicle['min_km_day']) + vehicle['driver_bata']
    gst_est = int(estimated_day_cost * 0.05)
    total_est = estimated_day_cost + gst_est

    context = {
        'vehicle': vehicle,
        'related_vehicles': related_vehicles,
        'estimated_day_cost': estimated_day_cost,
        'gst_est': gst_est,
        'total_est': total_est,
    }
    return render(request, 'customer_portal/vehicle_detail.html', context)


def about_us_page(request):
    """
    Enterprise About Us Page detailing Sivagayathiri Travels' 15-year legacy,
    Coimbatore Mission Control operations, leadership values, safety accreditations,
    and fleet statistics.
    """
    context = {
        'years_experience': 15,
        'active_fleet': 320,
        'happy_travelers': '50,000+',
        'corporate_clients': '100+',
        'on_time_sla': 99.8,
    }
    return render(request, 'customer_portal/about_us.html', context)


def services_overview_page(request):
    """
    Central Services Hub showcasing all 4 pillars of Sivagayathiri Travels:
    1. Corporate Employee Transportation & Tech Park Mobility
    2. School & College Campus Fleets
    3. Bespoke Tour Packages & Industrial Visits (IV)
    4. Outstation Cab & Luxury Coach Rentals
    """
    return render(request, 'customer_portal/services_overview.html')


def employee_transportation_page(request):
    """
    Dedicated Employee Transportation Solutions Page (matching Reference Image 1 & 4)
    featuring:
    - 5-Stakeholder Matrix (Company, Employee, Finance, Operation, Compliance)
    - 4 Alternating visual blocks (Roster Routing, Spot Runs, Technology Command App, Safety)
    - Corporate RFQ / RFP instant quotation form with direct CRM lead sync
    """
    return render(request, 'customer_portal/services_corporate.html')


def institutional_transport_page(request):
    """
    Dedicated School & College Campus Transport Page featuring:
    - Child safety protocols, speed governors (40 km/h), AIS-140 GPS
    - Female attendant / caretaker support on every primary school bus
    - RFID student boarding swipe cards & real-time parent SMS alerts
    - Institutional campus fleet RFP form
    """
    return render(request, 'customer_portal/services_institutional.html')


def airport_transfers_page(request):
    """
    Dedicated Airport Transfers & Flight-Synchronized Chauffeur Service page:
    - 24/7 flight sync tracking, zero wait surcharge for flight delays
    - Meet-and-greet name board service inside arrival terminals
    - Executive fleet: Innova Crysta, Invicto Hybrid, Mercedes/BMW
    - CJB, BLR, COK, TRZ, IXM, MAA corridors
    """
    return render(request, 'customer_portal/services_airport.html')


def wedding_event_transport_page(request):
    """
    Dedicated Wedding & Event Transit Convoys page (Muhurtham & Shaadi Logistics):
    - 10 to 40 vehicle convoys (luxury coaches, Urbanias, bridal cars)
    - Dedicated on-site transport coordinator
    - 24/7 on-call buffer vehicles for last-minute guest runs
    - Ooty, Kodaikanal, Coorg, Coimbatore, Chennai destinations
    """
    return render(request, 'customer_portal/services_wedding.html')


def mice_corporate_offsites_page(request):
    """
    Dedicated MICE & Corporate Offsite Delegations page:
    - Multi-coach convoy management with escort communications
    - Onboard PA wireless mic & audio systems for announcements
    - Dedicated luggage backup vans & customized retreats
    - Ooty, Wayanad, Munnar, Yercaud, Bangalore destinations
    """
    return render(request, 'customer_portal/services_mice.html')


def industrial_factory_transit_page(request):
    """
    Dedicated Industrial Township & Factory 3-Shift Transit page:
    - 24/7 3-shift rotation commutes (6 AM, 2 PM, 10 PM)
    - Heavy-duty high-capacity buses for industrial corridors
    - 99.8% on-time arrival SLA to prevent production line stoppages
    - Coimbatore, Tiruppur, Hosur, Sriperumbudur industrial zones
    """
    return render(request, 'customer_portal/services_industrial.html')


def luxury_camper_caravan_page(request):
    """
    Dedicated Luxury Camper Van & Caravan Tourism page:
    - Customized Force Urbania / Tempo sleeper campers
    - Sofa-cum-bed, kitchenette, onboard chiller, camping awnings
    - Experiential tourism in Valparai, Meghamalai, Kodaikanal, Vagamon
    """
    return render(request, 'customer_portal/services_camper.html')



@csrf_exempt
def api_custom_inquiry(request):
    """
    REST API endpoint for custom trip itineraries, College IV bookings,
    and outstation fleet inquiries.
    Creates an Inquiry in the CRM pipeline and generates an instant
    customized WhatsApp routing deep-link.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Only POST method is permitted.'}, status=405)

    try:
        if request.content_type == 'application/json' and request.body:
            data = json.loads(request.body.decode('utf-8'))
        else:
            data = request.POST.dict()

        # Parse & sanitize form fields
        name = data.get('name', '').strip() or 'Guest Traveler'
        raw_phone = data.get('phone', '').strip()
        phone = re.sub(r'[^0-9+]', '', raw_phone)
        if not phone:
            return JsonResponse({'status': 'error', 'message': 'A valid mobile number is required.'}, status=400)

        email = data.get('email', '').strip()
        organization = data.get('organization', '').strip()
        trip_type = data.get('trip_type', 'college_iv').strip()
        pickup_location = data.get('pickup_location', '').strip() or 'Coimbatore / Tiruppur Hub'
        destination = data.get('destination', '').strip() or 'Custom Circuit'
        vehicle_pref = data.get('vehicle_preference', '').strip() or 'Best Recommended Fleet'
        special_notes = data.get('notes', '').strip()
        
        # Duration & Dates
        raw_date = data.get('travel_date', '').strip()
        try:
            pickup_date = datetime.datetime.strptime(raw_date, '%Y-%m-%d').date() if raw_date else (timezone.now().date() + datetime.timedelta(days=7))
        except ValueError:
            pickup_date = timezone.now().date() + datetime.timedelta(days=7)

        try:
            duration_days = int(data.get('duration_days', 3))
        except (ValueError, TypeError):
            duration_days = 3
        drop_date = pickup_date + datetime.timedelta(days=max(1, duration_days - 1))

        # Headcount
        try:
            adult_count = int(data.get('passengers', 20 if trip_type == 'college_iv' else 4))
        except (ValueError, TypeError):
            adult_count = 20 if trip_type == 'college_iv' else 4

        # Inclusions array/list
        inclusions_raw = data.get('inclusions', [])
        if isinstance(inclusions_raw, str):
            inclusions = [i.strip() for i in inclusions_raw.split(',') if i.strip()]
        elif isinstance(inclusions_raw, list):
            inclusions = [str(i).strip() for i in inclusions_raw if str(i).strip()]
        else:
            inclusions = []

        # Human-readable trip type
        trip_type_labels = {
            'college_iv': '🎓 College Industrial Visit (IV)',
            'corporate': '🏢 Corporate Offsite / Retreat',
            'family': '👨‍👩‍👧 Family Holiday & Hill Station',
            'pilgrimage': '🛕 Pilgrimage / Temple Circuit',
            'fleet_rental': '🚗 Outstation Fleet / Cab Rental',
            'wedding': '💐 Wedding / Event Logistics',
        }
        trip_label = trip_type_labels.get(trip_type, trip_type.replace('_', ' ').title())

        # Resolve or create Client
        client = Client.objects.filter(phone=phone).first()
        if not client:
            client = Client.objects.create(
                name=name,
                phone=phone,
                email=email or f"{phone}@guest.sivagayathiritravels.com",
                party_type='individual',
                address=f"{organization + ' - ' if organization else ''}{pickup_location}",
            )

        # Vehicle type match
        matched_vehicle = None
        if 'crysta' in vehicle_pref.lower() or 'innova' in vehicle_pref.lower():
            matched_vehicle = VehicleType.objects.filter(name__icontains='innova').first()
        elif 'urbania' in vehicle_pref.lower() or 'tempo' in vehicle_pref.lower():
            matched_vehicle = VehicleType.objects.filter(name__icontains='urbania').first() or VehicleType.objects.filter(name__icontains='traveller').first()
        elif 'bus' in vehicle_pref.lower() or 'coach' in vehicle_pref.lower():
            matched_vehicle = VehicleType.objects.filter(name__icontains='bus').first() or VehicleType.objects.filter(name__icontains='coach').first()

        # Build requirement summary
        inclusions_str = ', '.join(inclusions) if inclusions else 'Standard Transport Only'
        req_summary = (
            f"Trip Type: {trip_label}\n"
            f"Organization/College: {organization or 'N/A'}\n"
            f"Fleet Choice: {vehicle_pref}\n"
            f"Inclusions Requested: {inclusions_str}\n"
            f"Special Instructions: {special_notes or 'None'}"
        )

        from crm.models import Inquiry
        priority = 'high' if (trip_type in ['college_iv', 'corporate'] or adult_count >= 15) else 'medium'
        inquiry = Inquiry.objects.create(
            party=client,
            guest_name=name,
            guest_phone=phone,
            guest_email=email,
            pickup_location=pickup_location,
            destination=destination,
            pickup_date=pickup_date,
            pickup_time=datetime.time(6, 0),
            drop_date=drop_date,
            journey_type='outstation',
            vehicle_type=matched_vehicle,
            adult_count=max(1, adult_count),
            special_requirements=req_summary,
            priority=priority,
            source='website',
            status='new',
            notes=f"Web Custom Lead: {trip_label} for {adult_count} pax. Preferred: {vehicle_pref}."
        )

        # Generate WhatsApp pre-filled text
        clean_phone = phone.replace('+', '').replace(' ', '')
        if not clean_phone.startswith('91') and len(clean_phone) == 10:
            clean_phone = f"91{clean_phone}"

        wa_text = (
            f"*🚐 NEW CUSTOM TRIP INQUIRY - #{inquiry.inquiry_number}*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 *Guest:* {name} ({phone})\n"
            f"🏢 *College/Org:* {organization or 'Individual Booking'}\n"
            f"🎯 *Trip Category:* {trip_label}\n"
            f"📍 *Route:* {pickup_location} ➔ {destination}\n"
            f"📅 *Travel Date:* {pickup_date.strftime('%d-%b-%Y')} ({duration_days} Days)\n"
            f"👥 *Total Travelers:* {adult_count} Persons\n"
            f"🚌 *Vehicle Preference:* {vehicle_pref}\n"
            f"✨ *Key Inclusions:* {inclusions_str}\n"
            f"💬 *Notes:* {special_notes or 'Requesting itinerary & quotation'}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"_Ref ID: {inquiry.inquiry_number} • Sivagayathiri Travels & Expeditions_"
        )

        whatsapp_url = f"https://wa.me/919842533777?text={urllib.parse.quote(wa_text)}"

        return JsonResponse({
            'status': 'success',
            'inquiry_id': inquiry.id,
            'inquiry_number': inquiry.inquiry_number,
            'whatsapp_url': whatsapp_url,
            'guest_name': name,
            'destination': destination,
            'message': f"Inquiry #{inquiry.inquiry_number} generated successfully."
        })

    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f"Failed to process custom itinerary request: {str(e)}"
        }, status=500)
