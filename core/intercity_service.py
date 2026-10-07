"""
Sivagayathiri Intercity Bus CRS Client Service
=============================================
Provides seamless client-side communication from TravelERP (Port 8000)
to the Intercity Bus CRS platform (Port 8005) for:
  1. Live Loyalty Card & Points Balance Lookup
  2. Loyalty Points Atomic Redemption for Tour Package Discounts
  3. Intercity Scheduled Bus & Seat Availability Search
  4. Automatic Transit Seat Reservations (Connecting Bus Legs for Packages)
"""
import json
import logging
import urllib.request
import urllib.parse
from decimal import Decimal

logger = logging.getLogger(__name__)

INTERCITY_CRS_BASE_URL = 'http://127.0.0.1:8005'
DEFAULT_TIMEOUT_SECONDS = 3.5


def get_loyalty_balance(phone: str) -> dict:
    """
    Queries Intercity Bus CRS for a customer's loyalty card and points balance.
    Endpoint: GET /api/loyalty/balance/?phone=<phone>
    """
    clean_phone = ''.join(filter(str.isdigit, str(phone)))
    if not clean_phone:
        return {'status': 'error', 'message': 'Invalid phone number', 'points_balance': 0}

    url = f"{INTERCITY_CRS_BASE_URL}/api/loyalty/balance/?phone={urllib.parse.quote(clean_phone)}"
    req = urllib.request.Request(url, headers={'Accept': 'application/json'})

    try:
        with urllib.request.urlopen(req, timeout=DEFAULT_TIMEOUT_SECONDS) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode('utf-8'))
                return data
    except Exception as e:
        logger.warning(f"[IntercityService] Loyalty balance lookup failed for {clean_phone}: {e}")

    return {
        'status': 'offline',
        'phone': clean_phone,
        'points_balance': 0,
        'redemption_rate': 0.5,
        'cash_equivalent_inr': 0.0,
        'message': 'Intercity CRS offline or unreachable'
    }


def redeem_loyalty_points(phone: str, points: int, reference_id: str, source: str = 'holiday_tour_checkout') -> dict:
    """
    Redeems customer loyalty points for an instant discount on TravelERP.
    Endpoint: POST /api/loyalty/redeem/
    """
    clean_phone = ''.join(filter(str.isdigit, str(phone)))
    url = f"{INTERCITY_CRS_BASE_URL}/api/loyalty/redeem/"
    payload = {
        'phone': clean_phone,
        'points_to_redeem': int(points),
        'reference_id': str(reference_id),
        'source': source
    }
    raw_data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        url,
        data=raw_data,
        headers={
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=DEFAULT_TIMEOUT_SECONDS) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            return data
    except urllib.error.HTTPError as he:
        try:
            err_data = json.loads(he.read().decode('utf-8'))
            return err_data
        except Exception:
            return {'status': 'error', 'message': f'HTTP Error {he.code}'}
    except Exception as e:
        logger.error(f"[IntercityService] Loyalty redemption failed: {e}")
        return {'status': 'error', 'message': f'Intercity CRS unreachable: {e}'}


def search_intercity_trips(origin: str, destination: str, date_str: str) -> dict:
    """
    Searches available scheduled buses on Intercity CRS for connecting transit legs.
    Endpoint: GET /api/intercity/routes/search/?origin=<city>&destination=<city>&date=YYYY-MM-DD
    """
    params = urllib.parse.urlencode({
        'origin': origin.strip(),
        'destination': destination.strip(),
        'date': date_str.strip()
    })
    url = f"{INTERCITY_CRS_BASE_URL}/api/intercity/routes/search/?{params}"
    req = urllib.request.Request(url, headers={'Accept': 'application/json'})

    try:
        with urllib.request.urlopen(req, timeout=DEFAULT_TIMEOUT_SECONDS) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode('utf-8'))
                return data
    except Exception as e:
        logger.warning(f"[IntercityService] Trip search failed ({origin} -> {destination}): {e}")

    return {
        'status': 'offline',
        'query': {'origin': origin, 'destination': destination, 'date': date_str},
        'trips_count': 0,
        'trips': []
    }


def reserve_transit_seats(trip_id: int, seat_numbers: list, passenger_name: str,
                          passenger_phone: str, passenger_gender: str = 'M',
                          external_booking_ref: str = '') -> dict:
    """
    Reserves confirmed bus seats on Intercity CRS to bundle with a tour package.
    Endpoint: POST /api/intercity/reserve-transit-seats/
    """
    url = f"{INTERCITY_CRS_BASE_URL}/api/intercity/reserve-transit-seats/"
    payload = {
        'trip_id': int(trip_id),
        'seat_numbers': list(seat_numbers),
        'passenger_name': passenger_name,
        'passenger_phone': passenger_phone,
        'passenger_gender': passenger_gender,
        'external_booking_ref': external_booking_ref,
        'payment_mode': 'partner_b2b_ledger'
    }
    raw_data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        url,
        data=raw_data,
        headers={
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=DEFAULT_TIMEOUT_SECONDS) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            return data
    except urllib.error.HTTPError as he:
        try:
            return json.loads(he.read().decode('utf-8'))
        except Exception:
            return {'status': 'error', 'message': f'HTTP Error {he.code}'}
    except Exception as e:
        logger.error(f"[IntercityService] Seat reservation failed: {e}")
        return {'status': 'error', 'message': f'Intercity CRS unreachable: {e}'}
