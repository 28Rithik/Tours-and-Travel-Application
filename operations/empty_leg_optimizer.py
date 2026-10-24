"""
operations/empty_leg_optimizer.py
Empty-Leg Return Deadhead Trip Marketplace & Optimizer
Sivagayathiri Tours & Travels ERP

Detects scheduled & completed outstation one-way drops (Bangalore, Chennai,
Madurai, Kochi, Mysore) that leave vehicles stranded with empty return miles (deadhead).
Computes break-even running cost, recommends high-conversion discounted tariffs,
generates instant B2B WhatsApp broadcasts, and monetizes otherwise lost fuel burn.
"""

from decimal import Decimal
import random
from datetime import timedelta
from django.utils import timezone
from core.models import Vehicle, Driver
from operations.models import Trip, EmptyLegTripOffer


SOUTH_INDIA_ONE_WAY_CORRIDORS = [
    {
        'origin': 'Bengaluru Airport (BLR)',
        'dest': 'Coimbatore Central HQ',
        'distance_km': 360,
        'std_sedan': Decimal('6500.00'),
        'std_suv': Decimal('8500.00'),
        'std_tempo': Decimal('13500.00'),
        'toll_est': Decimal('620.00'),
    },
    {
        'origin': 'Chennai Central / Koyambedu',
        'dest': 'Coimbatore Central HQ',
        'distance_km': 510,
        'std_sedan': Decimal('8500.00'),
        'std_suv': Decimal('11500.00'),
        'std_tempo': Decimal('18000.00'),
        'toll_est': Decimal('850.00'),
    },
    {
        'origin': 'Madurai Junction (MDU)',
        'dest': 'Coimbatore Central HQ',
        'distance_km': 215,
        'std_sedan': Decimal('4200.00'),
        'std_suv': Decimal('5600.00'),
        'std_tempo': Decimal('8500.00'),
        'toll_est': Decimal('280.00'),
    },
    {
        'origin': 'Munnar Tea Estates (KL)',
        'dest': 'Coimbatore Central HQ',
        'distance_km': 160,
        'std_sedan': Decimal('4000.00'),
        'std_suv': Decimal('5200.00'),
        'std_tempo': Decimal('7800.00'),
        'toll_est': Decimal('150.00'),
    },
    {
        'origin': 'Mysore Palace (KA)',
        'dest': 'Coimbatore Central HQ',
        'distance_km': 200,
        'std_sedan': Decimal('4500.00'),
        'std_suv': Decimal('6000.00'),
        'std_tempo': Decimal('9000.00'),
        'toll_est': Decimal('220.00'),
    },
]


def get_empty_leg_dashboard_metrics():
    """
    Computes summary metrics for active empty-leg offers and recovered deadhead revenue.
    """
    offers = EmptyLegTripOffer.objects.all()
    total_offers = offers.count()
    active_available = offers.filter(status__in=['available', 'broadcasted']).count()
    booked_count = offers.filter(status__in=['booked', 'completed']).count()

    total_recovered_revenue = sum(o.discounted_empty_leg_rate for o in offers.filter(status__in=['booked', 'completed']))
    total_net_margin = sum(o.net_margin_generated for o in offers.filter(status__in=['booked', 'completed']))
    deadhead_km_avoided = booked_count * 320  # average corridor distance

    return {
        'total_offers': total_offers,
        'active_available': active_available,
        'booked_count': booked_count,
        'total_recovered_revenue': total_recovered_revenue,
        'total_net_margin': total_net_margin,
        'deadhead_km_avoided': deadhead_km_avoided,
    }


def calculate_empty_leg_pricing(corridor, vehicle_type_str='suv'):
    """
    Computes standard vs discounted empty-leg tariff based on fuel economy and tolls.
    """
    std_tariff = corridor.get(f'std_{vehicle_type_str}', corridor['std_suv'])
    tolls = corridor['toll_est']
    dist = corridor['distance_km']

    # Fuel cost estimation:
    # SUV ~ 12 km/l @ ₹95/l => ~ ₹8.0/km
    # Sedan ~ 17 km/l @ ₹95/l => ~ ₹5.6/km
    # Tempo ~ 9 km/l @ ₹95/l => ~ ₹10.5/km
    fuel_rate = Decimal('8.00')
    if vehicle_type_str == 'sedan':
        fuel_rate = Decimal('5.60')
    elif vehicle_type_str == 'tempo':
        fuel_rate = Decimal('10.50')

    fuel_cost = (Decimal(str(dist)) * fuel_rate).quantize(Decimal('0.01'))
    break_even_cost = fuel_cost + tolls

    # Empty leg discount is typically 30% to 40% below standard rate
    # but priced at break_even_cost + 20-30% margin
    target_discounted_rate = max(
        (std_tariff * Decimal('0.65')).quantize(Decimal('0.01')),
        (break_even_cost * Decimal('1.25')).quantize(Decimal('0.01'))
    )
    net_margin = target_discounted_rate - break_even_cost

    return {
        'std_tariff': std_tariff,
        'discounted_rate': target_discounted_rate,
        'fuel_cost': fuel_cost,
        'toll_cost': tolls,
        'net_margin': net_margin,
        'discount_percent': round(float((std_tariff - target_discounted_rate) / std_tariff) * 100),
    }


def generate_whatsapp_broadcast_text(offer):
    """
    Creates an enticing, copy-ready WhatsApp broadcast message for B2B sub-agents & travel desks.
    """
    disc_pct = 0
    if offer.standard_tariff > 0:
        disc_pct = round(((offer.standard_tariff - offer.discounted_empty_leg_rate) / offer.standard_tariff) * 100)

    msg = (
        f"🚨 *SIVAGAYATHIRI EMPTY-LEG DEAL ({disc_pct}% OFF)* 🚨\n\n"
        f"🚐 *Route:* {offer.origin_city} ➔ {offer.destination_city}\n"
        f"🚘 *Vehicle:* {offer.vehicle.registration_number} ({offer.vehicle.brand} {offer.vehicle.model})\n"
        f"📅 *Window:* {offer.available_from.strftime('%d-%b %I:%M %p')} to {offer.available_until.strftime('%I:%M %p')}\n"
        f"💰 *Special Fare:* ₹{offer.discounted_empty_leg_rate:,.0f} (Regular: ~₹{offer.standard_tariff:,.0f})\n"
        f"✨ *Includes:* AC, sanitized vehicle, professional chauffeur, toll estimate.\n\n"
        f"📞 *Book Instantly:* Call 98421 00000 / 0422 2490000\n"
        f"Offer Ref: #{offer.offer_code}"
    )
    return msg


def seed_sample_empty_leg_offers():
    """
    Populates sample empty return legs for vehicles stationed at outstation destinations.
    """
    if EmptyLegTripOffer.objects.exists():
        return

    now = timezone.now()
    vehicles = list(Vehicle.objects.all()[:5])
    drivers = list(Driver.objects.filter(status='active')[:5])
    trips = list(Trip.objects.all()[:5])

    if not vehicles:
        return

    sample_legs = [
        {
            'corridor': SOUTH_INDIA_ONE_WAY_CORRIDORS[0],  # BLR -> CJB
            'v_type': 'suv',
            'status': 'available',
            'hrs_from_now': 6,
            'duration_hrs': 18,
            'notes': 'Dropped corporate executive team at Bangalore Airport T2. Returning empty to Coimbatore depot.',
        },
        {
            'corridor': SOUTH_INDIA_ONE_WAY_CORRIDORS[1],  # MAA -> CJB
            'v_type': 'tempo',
            'status': 'broadcasted',
            'hrs_from_now': 12,
            'duration_hrs': 24,
            'notes': 'College faculty drop at Chennai Central. 14-seater AC Tempo Traveller available for return load.',
        },
        {
            'corridor': SOUTH_INDIA_ONE_WAY_CORRIDORS[2],  # MDU -> CJB
            'v_type': 'suv',
            'status': 'booked',
            'hrs_from_now': -24,
            'duration_hrs': 12,
            'notes': 'Rameshwaram pilgrimage tour drop. Picked up returning family from Madurai to Tirupur/Coimbatore.',
        },
        {
            'corridor': SOUTH_INDIA_ONE_WAY_CORRIDORS[3],  # Munnar -> CJB
            'v_type': 'sedan',
            'status': 'available',
            'hrs_from_now': 4,
            'duration_hrs': 16,
            'notes': 'Honeymoon couple drop at Munnar Tea County. Returning to Coimbatore via Pollachi.',
        },
        {
            'corridor': SOUTH_INDIA_ONE_WAY_CORRIDORS[4],  # Mysore -> CJB
            'v_type': 'suv',
            'status': 'completed',
            'hrs_from_now': -48,
            'duration_hrs': 18,
            'notes': 'Mysore Palace drop completed. Booked return passenger at ₹4,200.',
        },
    ]

    for idx, s in enumerate(sample_legs):
        v = vehicles[idx % len(vehicles)]
        d = drivers[idx % len(drivers)] if drivers else None
        t = trips[idx % len(trips)] if trips else None
        corridor = s['corridor']
        pricing = calculate_empty_leg_pricing(corridor, s['v_type'])

        start_time = now + timedelta(hours=s['hrs_from_now'])
        end_time = start_time + timedelta(hours=s['duration_hrs'])

        EmptyLegTripOffer.objects.create(
            offer_code=f"EL-202610-00{idx+1}",
            parent_trip=t,
            vehicle=v,
            driver=d,
            origin_city=corridor['origin'],
            destination_city=corridor['dest'],
            available_from=start_time,
            available_until=end_time,
            standard_tariff=pricing['std_tariff'],
            discounted_empty_leg_rate=pricing['discounted_rate'],
            estimated_fuel_cost=pricing['fuel_cost'],
            estimated_toll_cost=pricing['toll_cost'],
            net_margin_generated=pricing['net_margin'],
            status=s['status'],
            notes=s['notes'],
        )
