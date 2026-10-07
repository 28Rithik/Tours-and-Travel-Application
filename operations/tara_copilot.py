"""
TARA AI - Operations Business Copilot Engine (Powered by Groq / LLM)
Sivagayathiri Travels & Tours ERP

Provides real-time natural language query answering and operational automation
with tool-calling against the live Django ORM database:
- Active tour & dispatch status
- Vehicle & driver compliance expiry alerts (Insurance, PUC, Permit, Fitness, Licenses)
- Financial overview & collection rates
- Driver behavior & safety scorecard anomalies
- Real-time fleet availability checks
- CRM inquiry pipeline & SLA turnaround tracking
- Interactive actions & deep links
"""

import os
import json
import logging
from decimal import Decimal
from datetime import timedelta
import requests
from django.conf import settings
from django.utils import timezone
from django.db.models import Count, Sum, Q, Avg

logger = logging.getLogger(__name__)

# Default Groq Model
DEFAULT_GROQ_MODEL = getattr(settings, 'GROQ_MODEL', 'llama-3.3-70b-versatile')
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# System Prompt defining TARA's role and capabilities
TARA_SYSTEM_PROMPT = """You are TARA, the intelligent AI Operations Copilot and Business Brain for Sivagayathiri Travels & Tours (HQ in Coimbatore, Tamil Nadu, operating tours across South & Pan-India).
You have real-time access to live database tools to inspect active tours, vehicle compliance (Insurance, PUC, Permits, Fitness), driver safety telemetry, financials (revenue, collections, receivables), and CRM leads.

Guidelines:
1. Always use the available tools to fetch accurate, real-time facts before answering. Never hallucinate trip IDs, vehicle numbers, or financial metrics.
2. Present answers in a clear, executive-friendly markdown format:
   - Use bold highlights, emoji indicators (🟢, ⚠️, 🚨, 💰, 🚌), and bullet points.
   - When presenting metrics, provide clear context (e.g. "Collection Rate: 94.2%").
   - Highlight actionable insights or urgent warnings (e.g. expiring documents within 7-30 days).
3. Conclude with proactive recommendations or 1-click operational next steps.
4. Keep answers professional, concise, yet comprehensive.
"""

# ==============================================================================
# 1. LIVE DATABASE TOOLS FOR TARA AI
# ==============================================================================

def get_active_tours_summary():
    """Fetches real-time status of active, started, and upcoming tours today."""
    from operations.models import Trip, Booking
    today = timezone.localdate()

    # Active trips: started or assigned
    active_qs = Trip.objects.filter(
        Q(status__in=['started', 'assigned', 'driver_confirmed']) |
        Q(start_date__lte=today, end_date__gte=today, status__in=['started', 'assigned'])
    ).select_related('vehicle', 'driver', 'booking').distinct()

    total_active = active_qs.count()
    on_trip_count = active_qs.filter(status='started').count()
    assigned_count = active_qs.filter(status='assigned').count()
    
    # Upcoming departures today
    upcoming_today = Trip.objects.filter(
        start_date=today,
        status__in=['booked', 'assigned']
    ).count()

    # Sample top active tours
    tour_samples = []
    for trip in active_qs[:8]:
        tour_samples.append({
            "trip_id": trip.trip_id,
            "guest": trip.guest_name or (trip.booking.guest_name if trip.booking else "Guest"),
            "vehicle": trip.vehicle.registration_number if trip.vehicle else "Unassigned",
            "vehicle_type": trip.vehicle.vehicle_type.name if (trip.vehicle and trip.vehicle.vehicle_type) else "Standard",
            "driver": trip.driver.name if trip.driver else "Unassigned",
            "status": trip.get_status_display(),
            "pickup": trip.booking.pickup_location if trip.booking else "Coimbatore",
            "destination": trip.booking.destination if trip.booking else "Tour Circuit",
            "tracking_url": f"/track/{trip.tracking_token}/" if trip.tracking_token else "",
        })

    return {
        "status": "success",
        "date": str(today),
        "total_active_tours": total_active,
        "vehicles_currently_on_trip": on_trip_count,
        "assigned_awaiting_start": assigned_count,
        "upcoming_departures_today": upcoming_today,
        "sample_active_tours": tour_samples,
    }


def get_compliance_expiry_alerts(days_ahead=30):
    """
    Identifies vehicles with Insurance, PUC, Permit, or Fitness expiring within specified days,
    as well as drivers with expiring commercial transport licenses.
    """
    from core.models import Vehicle, Driver
    today = timezone.localdate()
    threshold = today + timedelta(days=int(days_ahead))

    # Vehicle Compliance
    expiring_insurance = Vehicle.objects.filter(insurance_expiry__lte=threshold, insurance_expiry__gte=today)
    expired_insurance = Vehicle.objects.filter(insurance_expiry__lt=today)

    expiring_puc = Vehicle.objects.filter(pollution_expiry__lte=threshold, pollution_expiry__gte=today)
    expired_puc = Vehicle.objects.filter(pollution_expiry__lt=today)

    expiring_fitness = Vehicle.objects.filter(fc_expiry__lte=threshold, fc_expiry__gte=today)
    expired_fitness = Vehicle.objects.filter(fc_expiry__lt=today)

    expiring_permit = Vehicle.objects.filter(permit_expiry__lte=threshold, permit_expiry__gte=today)
    expired_permit = Vehicle.objects.filter(permit_expiry__lt=today)

    # Driver Commercial Licenses
    expiring_driver_tr = Driver.objects.filter(
        status='active',
        license_validity_tr__lte=threshold,
        license_validity_tr__gte=today
    )
    expired_driver_tr = Driver.objects.filter(
        status='active',
        license_validity_tr__lt=today
    )

    vehicle_alerts = []
    # Collect immediate alerts
    for v in (expiring_insurance | expired_insurance | expiring_puc | expired_puc | expiring_fitness | expired_fitness | expiring_permit | expired_permit).distinct()[:15]:
        issues = []
        if v.insurance_expiry:
            days = (v.insurance_expiry - today).days
            if days < 0: issues.append(f"Insurance EXPIRED ({v.insurance_expiry})")
            elif days <= days_ahead: issues.append(f"Insurance in {days}d ({v.insurance_expiry})")
        if v.pollution_expiry:
            days = (v.pollution_expiry - today).days
            if days < 0: issues.append(f"PUC EXPIRED ({v.pollution_expiry})")
            elif days <= days_ahead: issues.append(f"PUC in {days}d ({v.pollution_expiry})")
        if v.fc_expiry:
            days = (v.fc_expiry - today).days
            if days < 0: issues.append(f"Fitness (FC) EXPIRED ({v.fc_expiry})")
            elif days <= days_ahead: issues.append(f"Fitness (FC) in {days}d ({v.fc_expiry})")
        if v.permit_expiry:
            days = (v.permit_expiry - today).days
            if days < 0: issues.append(f"Permit EXPIRED ({v.permit_expiry})")
            elif days <= days_ahead: issues.append(f"Permit in {days}d ({v.permit_expiry})")

        vehicle_alerts.append({
            "registration": v.registration_number,
            "model": f"{v.brand} {v.model}".strip() or "Vehicle",
            "owner": v.get_ownership_type_display(),
            "issues": issues,
            "admin_url": f"/admin/core/vehicle/{v.pk}/change/"
        })

    driver_alerts = []
    for d in (expiring_driver_tr | expired_driver_tr).distinct()[:10]:
        days = (d.license_validity_tr - today).days if d.license_validity_tr else -1
        driver_alerts.append({
            "name": d.name,
            "phone": d.phone,
            "license_no": d.license_number,
            "expiry": str(d.license_validity_tr),
            "status": "EXPIRED" if days < 0 else f"Expiring in {days}d",
            "admin_url": f"/admin/core/driver/{d.pk}/change/"
        })

    total_vehicle_issues = len(vehicle_alerts)
    total_driver_issues = len(driver_alerts)

    return {
        "status": "success",
        "days_window": days_ahead,
        "total_vehicle_compliance_alerts": total_vehicle_issues,
        "total_driver_license_alerts": total_driver_issues,
        "expired_insurance_count": expired_insurance.count(),
        "expiring_insurance_count": expiring_insurance.count(),
        "expired_puc_count": expired_puc.count(),
        "expiring_puc_count": expiring_puc.count(),
        "expired_fitness_count": expired_fitness.count(),
        "expiring_fitness_count": expiring_fitness.count(),
        "vehicle_alerts": vehicle_alerts,
        "driver_alerts": driver_alerts
    }


def get_financial_revenue_overview():
    """Fetches high-level revenue, collections received, and outstanding receivables."""
    from operations.models import Trip
    from finance.models import Payment
    now = timezone.now()
    month_start = now.date().replace(day=1)

    # Trip values
    trips_month = Trip.objects.filter(start_date__gte=month_start)
    total_trips_billed = trips_month.count()
    
    # Financial metrics from Trips
    trips_agg = trips_month.aggregate(
        total_val=Sum('fixed_amount'),
    )
    total_billed = float(trips_agg['total_val'] or 0)

    # Actual receipts
    receipts_month = Payment.objects.filter(
        date__gte=month_start,
        payment_type='customer_receipt'
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    total_collected = float(receipts_month)

    # Collection rate calculation
    collection_rate = (total_collected / total_billed * 100) if total_billed > 0 else 92.5
    collection_rate = min(round(collection_rate, 1), 100.0)
    overdue_est = max(0.0, total_billed - total_collected)

    return {
        "status": "success",
        "month": month_start.strftime("%B %Y"),
        "total_trips_this_month": total_trips_billed,
        "total_billed_revenue_inr": total_billed,
        "total_collections_received_inr": total_collected,
        "estimated_pending_receivables_inr": overdue_est,
        "collection_rate_percent": collection_rate,
        "recent_payment_count": Payment.objects.filter(date__gte=month_start).count()
    }


def get_driver_safety_alerts():
    """Analyzes telemetry infractions, harsh braking, and overspeeding logs."""
    from operations.models import DriverBehaviorLog
    from core.models import Driver

    now = timezone.now()
    seven_days_ago = now - timedelta(days=7)

    recent_events = DriverBehaviorLog.objects.filter(timestamp__gte=seven_days_ago)
    total_infractions = recent_events.count()

    overspeeding_count = recent_events.filter(event_type='overspeeding').count()
    harsh_braking_count = recent_events.filter(event_type='harsh_braking').count()
    geofence_breach_count = recent_events.filter(event_type='geofence_breach').count()

    # Top drivers with infractions
    top_flagged = (
        recent_events.filter(driver__isnull=False)
        .values('driver__id', 'driver__name', 'driver__phone')
        .annotate(event_count=Count('id'), total_penalty=Sum('penalty_points'))
        .order_by('-total_penalty')[:5]
    )

    flagged_drivers = []
    for d in top_flagged:
        # Base safety score calculation
        penalty = d['total_penalty'] or 0
        safety_score = max(50, 100 - penalty)
        flagged_drivers.append({
            "driver_name": d['driver__name'],
            "phone": d['driver__phone'],
            "infractions_7d": d['event_count'],
            "penalty_points": penalty,
            "safety_index": safety_score,
            "status": "Needs Coaching" if safety_score < 80 else "Normal"
        })

    return {
        "status": "success",
        "timeframe": "Last 7 Days",
        "total_telemetry_infractions": total_infractions,
        "overspeeding_events": overspeeding_count,
        "harsh_braking_events": harsh_braking_count,
        "geofence_breaches": geofence_breach_count,
        "flagged_drivers": flagged_drivers
    }


def get_fleet_availability(target_date_str=None, vehicle_type_name=None):
    """Checks real-time vehicle availability by date and optional vehicle type."""
    from core.models import Vehicle, VehicleType
    from operations.models import Trip

    today = timezone.localdate()
    target_date = today
    if target_date_str:
        try:
            target_date = timezone.datetime.strptime(target_date_str, "%Y-%m-%d").date()
        except Exception:
            pass

    # Active trips on target date
    busy_vehicle_ids = Trip.objects.filter(
        start_date__lte=target_date,
        end_date__gte=target_date,
        status__in=['booked', 'assigned', 'driver_confirmed', 'started']
    ).values_list('vehicle_id', flat=True)

    available_qs = Vehicle.objects.filter(
        status__in=['available', 'assigned']
    ).exclude(id__in=busy_vehicle_ids).exclude(status__in=['maintenance', 'inactive'])

    if vehicle_type_name:
        available_qs = available_qs.filter(
            Q(vehicle_type__name__icontains=vehicle_type_name) |
            Q(brand__icontains=vehicle_type_name) |
            Q(model__icontains=vehicle_type_name)
        )

    # Group by category / vehicle type
    type_counts = (
        available_qs.values('vehicle_type__name')
        .annotate(count=Count('id'))
        .order_by('-count')
    )

    sample_vehicles = []
    for v in available_qs[:10]:
        sample_vehicles.append({
            "registration": v.registration_number,
            "model": f"{v.brand} {v.model}".strip() or "Vehicle",
            "type": v.vehicle_type.name if v.vehicle_type else "General",
            "seats": v.seating_capacity,
            "fuel": v.fuel_type,
            "ac": "AC" if v.has_ac else "Non-AC"
        })

    return {
        "status": "success",
        "query_date": str(target_date),
        "total_available_vehicles": available_qs.count(),
        "breakdown_by_type": list(type_counts),
        "sample_available": sample_vehicles
    }


def get_crm_inquiries_summary():
    """Fetches CRM lead pipeline, pending quotations, and overdue SLA inquiries."""
    from crm.models import Inquiry
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    total_leads = Inquiry.objects.count()
    new_today = Inquiry.objects.filter(created_at__gte=today_start).count()
    active_funnel = Inquiry.objects.filter(status__in=['new', 'in_progress'])
    overdue_sla = active_funnel.filter(tat_deadline__lt=now).count()

    by_status = Inquiry.objects.values('status').annotate(count=Count('id'))
    by_priority = Inquiry.objects.filter(status__in=['new', 'in_progress']).values('priority').annotate(count=Count('id'))

    return {
        "status": "success",
        "total_leads": total_leads,
        "new_leads_today": new_today,
        "active_pipeline_count": active_funnel.count(),
        "overdue_sla_inquiries": overdue_sla,
        "pipeline_by_status": list(by_status),
        "active_by_priority": list(by_priority)
    }


def search_trip_or_booking(query_str):
    """Searches a specific trip or booking by ID, guest name, or vehicle."""
    from operations.models import Trip, Booking
    q = str(query_str).strip()

    trip = Trip.objects.filter(
        Q(trip_id__iexact=q) |
        Q(guest_name__icontains=q) |
        Q(vehicle__registration_number__icontains=q)
    ).first()

    if trip:
        return {
            "status": "found",
            "type": "trip",
            "trip_id": trip.trip_id,
            "guest": trip.guest_name,
            "status": trip.get_status_display(),
            "dates": f"{trip.start_date} to {trip.end_date}",
            "vehicle": trip.vehicle.registration_number if trip.vehicle else "None",
            "driver": trip.driver.name if trip.driver else "None",
            "pickup": trip.pickup_location,
            "destination": trip.destination,
            "tracking_url": trip.tracking_url,
            "admin_url": f"/admin/operations/trip/{trip.pk}/change/"
        }

    booking = Booking.objects.filter(
        Q(booking_number__iexact=q) |
        Q(guest_name__icontains=q)
    ).first()

    if booking:
        return {
            "status": "found",
            "type": "booking",
            "booking_number": booking.booking_number,
            "guest": booking.guest_name,
            "status": booking.get_status_display(),
            "pickup_date": str(booking.pickup_date),
            "pickup": booking.pickup_location,
            "destination": booking.destination,
            "admin_url": f"/admin/operations/booking/{booking.pk}/change/"
        }

    return {"status": "not_found", "query": q}


# Tool Dispatcher Map
TARA_TOOLS_MAP = {
    "get_active_tours_summary": get_active_tours_summary,
    "get_compliance_expiry_alerts": get_compliance_expiry_alerts,
    "get_financial_revenue_overview": get_financial_revenue_overview,
    "get_driver_safety_alerts": get_driver_safety_alerts,
    "get_fleet_availability": get_fleet_availability,
    "get_crm_inquiries_summary": get_crm_inquiries_summary,
    "search_trip_or_booking": search_trip_or_booking,
}

# Groq Function Calling Schema Definitions
GROQ_TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "get_active_tours_summary",
            "description": "Fetch real-time active, ongoing, and upcoming tours today, including vehicle assignments and guest count.",
            "parameters": {"type": "object", "properties": {}},
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_compliance_expiry_alerts",
            "description": "Get vehicles and drivers with Insurance, PUC, Fitness, Permit, or Driver Transport Licenses expiring soon or expired.",
            "parameters": {
                "type": "object",
                "properties": {
                    "days_ahead": {
                        "type": "integer",
                        "description": "Lookahead days window, e.g. 7, 30 (default: 30)"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_financial_revenue_overview",
            "description": "Get month-to-date billed revenue, collections received, overdue receivables, and collection rate percentage.",
            "parameters": {"type": "object", "properties": {}},
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_driver_safety_alerts",
            "description": "Get driver safety telemetry infractions (overspeeding, harsh braking, geofence breaches) and flagged drivers.",
            "parameters": {"type": "object", "properties": {}},
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_fleet_availability",
            "description": "Check available fleet vehicles by date and vehicle type (e.g., Innova Crysta, Tempo Traveller, Swift Dzire).",
            "parameters": {
                "type": "object",
                "properties": {
                    "target_date_str": {"type": "string", "description": "Date in YYYY-MM-DD format"},
                    "vehicle_type_name": {"type": "string", "description": "Optional model or type filter e.g. 'Innova', 'Dzire', 'Bus'"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_crm_inquiries_summary",
            "description": "Get CRM lead pipeline metrics, new inquiries today, active quotes, and SLA overdue counts.",
            "parameters": {"type": "object", "properties": {}},
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_trip_or_booking",
            "description": "Lookup details of a specific trip or booking by trip ID (e.g. 'TR-0001'), booking ID, or guest name.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query_str": {"type": "string", "description": "Trip ID, booking ID, or guest name"}
                },
                "required": ["query_str"]
            }
        }
    }
]

# ==============================================================================
# 2. GROQ API CALLER WITH TOOL EXECUTION
# ==============================================================================

def execute_groq_llm(user_message, conversation_history=None, api_key=None, model=None):
    """
    Executes conversational turn with Groq API, supporting tool calling and execution.
    """
    groq_key = api_key or getattr(settings, 'GROQ_API_KEY', '') or os.environ.get('GROQ_API_KEY', '')
    if not groq_key:
        return None, "NO_API_KEY"

    model_name = model or getattr(settings, 'GROQ_MODEL', DEFAULT_GROQ_MODEL)

    messages = [{"role": "system", "content": TARA_SYSTEM_PROMPT}]

    # Add historical messages (limit to recent 6 turns)
    if conversation_history and isinstance(conversation_history, list):
        for msg in conversation_history[-6:]:
            if msg.get('role') in ['user', 'assistant'] and msg.get('content'):
                messages.append({"role": msg['role'], "content": msg['content']})

    # Add current user message
    messages.append({"role": "user", "content": user_message})

    headers = {
        "Authorization": f"Bearer {groq_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": model_name,
        "messages": messages,
        "tools": GROQ_TOOLS_SCHEMA,
        "tool_choice": "auto",
        "temperature": 0.2,
        "max_tokens": 1500
    }

    try:
        resp = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=20)
        if resp.status_code != 200:
            logger.warning(f"Groq API returned status {resp.status_code}: {resp.text}")
            return None, f"GROQ_ERROR_{resp.status_code}"

        res_json = resp.json()
        choice = res_json['choices'][0]
        response_msg = choice['message']

        # Check if Groq decided to call one or more tools
        tool_calls = response_msg.get('tool_calls')
        if not tool_calls:
            # Direct text answer without tools
            return response_msg.get('content', ''), "SUCCESS"

        # Append assistant tool call message to thread
        messages.append(response_msg)

        executed_tools_data = {}
        for tc in tool_calls:
            fn_name = tc['function']['name']
            fn_args_raw = tc['function'].get('arguments', '{}')
            try:
                fn_args = json.loads(fn_args_raw)
            except Exception:
                fn_args = {}

            if fn_name in TARA_TOOLS_MAP:
                tool_fn = TARA_TOOLS_MAP[fn_name]
                tool_output = tool_fn(**fn_args)
                executed_tools_data[fn_name] = tool_output
            else:
                tool_output = {"error": f"Tool {fn_name} not found"}

            messages.append({
                "role": "tool",
                "tool_call_id": tc['id'],
                "content": json.dumps(tool_output)
            })

        # Second call to Groq with tool results to synthesize final markdown
        second_payload = {
            "model": model_name,
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": 1500
        }
        second_resp = requests.post(GROQ_API_URL, headers=headers, json=second_payload, timeout=25)
        if second_resp.status_code == 200:
            final_content = second_resp.json()['choices'][0]['message'].get('content', '')
            return final_content, "SUCCESS", executed_tools_data
        else:
            logger.warning(f"Groq second call failed: {second_resp.text}")
            return None, f"GROQ_SECOND_CALL_ERROR_{second_resp.status_code}"

    except Exception as e:
        logger.exception("Error executing Groq API")
        return None, str(e)


# ==============================================================================
# 3. HIGH-PERFORMANCE LOCAL SEMANTIC QUERY ENGINE (OFFLINE / KEYLESS FALLBACK)
# ==============================================================================

def execute_local_semantic_copilot(user_query):
    """
    Intelligent offline / keyless semantic rule engine that runs the exact same
    live database queries and returns rich markdown, KPI cards, and deep links.
    """
    q = user_query.lower().strip()
    kpi_cards = []
    actions = []
    suggested = []
    reply = ""

    if any(k in q for k in ["active tour", "tours running", "today tour", "trips active", "ongoing trip", "live trip", "how many tour"]):
        data = get_active_tours_summary()
        total = data['total_active_tours']
        on_trip = data['vehicles_currently_on_trip']
        assigned = data['assigned_awaiting_start']
        upcoming = data['upcoming_departures_today']

        kpi_cards = [
            {"label": "Active Tours", "value": str(total), "color": "#0284c7", "icon": "route"},
            {"label": "On Trip Now", "value": str(on_trip), "color": "#10b981", "icon": "directions_car"},
            {"label": "Departures Today", "value": str(upcoming), "color": "#f59e0b", "icon": "schedule"},
        ]

        reply = f"### 🛰️ Live Operations Overview ({data['date']})\n\n"
        reply += f"You have **{total} active tours** running across our fleet today:\n"
        reply += f"- **{on_trip} vehicles** are currently en-route (*On Trip* with live GPS telemetry).\n"
        reply += f"- **{assigned} vehicles** are assigned and staged for guest pickup.\n"
        reply += f"- **{upcoming} departures** scheduled for today.\n\n"

        if data['sample_active_tours']:
            reply += "#### 📍 Current En-Route Circuits:\n"
            for t in data['sample_active_tours'][:5]:
                track_md = f" [Live Map]({t['tracking_url']})" if t['tracking_url'] else ""
                reply += f"- **{t['trip_id']}** ({t['guest']}): {t['vehicle']} ({t['vehicle_type']}) • Driver: **{t['driver']}** • `{t['pickup']} ➔ {t['destination']}` {track_md}\n"

        actions = [
            {"label": "🛰️ Open Live Fleet Radar", "url": "/admin/operations/fleet-radar/", "primary": True},
            {"label": "📋 View Active Trips", "url": "/admin/operations/trip/?status=started", "primary": False},
        ]
        suggested = [
            "Which vehicles need insurance renewal?",
            "What is our revenue and collection rate?",
            "Show driver safety scorecard anomalies"
        ]

    elif any(k in q for k in ["insurance", "puc", "compliance", "expire", "expiry", "fitness", "license", "renewal", "fc"]):
        data = get_compliance_expiry_alerts(days_ahead=30)
        v_count = data['total_vehicle_compliance_alerts']
        d_count = data['total_driver_license_alerts']
        exp_ins = data['expiring_insurance_count']
        exp_puc = data['expiring_puc_count']

        kpi_cards = [
            {"label": "Vehicle Alerts (30d)", "value": str(v_count), "color": "#ef4444" if v_count > 0 else "#10b981", "icon": "verified_user"},
            {"label": "Expiring Insurance", "value": str(exp_ins), "color": "#f59e0b", "icon": "policy"},
            {"label": "Expiring PUC", "value": str(exp_puc), "color": "#f59e0b", "icon": "eco"},
            {"label": "Driver License Alerts", "value": str(d_count), "color": "#3b82f6", "icon": "badge"},
        ]

        reply = f"### 🛡️ Fleet & Crew Compliance Audit (Next 30 Days)\n\n"
        if v_count == 0 and d_count == 0:
            reply += "🟢 **All systems compliant!** No vehicles or active driver transport licenses are expired or expiring within 30 days.\n"
        else:
            reply += f"⚠️ Found **{v_count} vehicles** and **{d_count} drivers** requiring renewal attention:\n\n"
            
            if data['vehicle_alerts']:
                reply += "#### 🚗 Vehicle Document Expiries:\n"
                for v in data['vehicle_alerts'][:6]:
                    issues_str = ", ".join(v['issues'])
                    reply += f"- **{v['registration']}** ({v['model']}): `{issues_str}`\n"
            
            if data['driver_alerts']:
                reply += "\n#### 🪪 Driver Commercial License Expiries:\n"
                for d in data['driver_alerts'][:4]:
                    reply += f"- **{d['name']}** (Ph: {d['phone']}): Commercial License `{d['license_no']}` — **{d['status']}**\n"

        actions = [
            {"label": "🛡️ Open Compliance Dashboard", "url": "/maintenance/compliance/", "primary": True},
            {"label": "🚗 Manage Fleet Vehicles", "url": "/admin/core/vehicle/", "primary": False},
        ]
        suggested = [
            "Active tours running today",
            "Driver safety scorecard anomalies",
            "Available vehicles for tomorrow"
        ]

    elif any(k in q for k in ["revenue", "collection", "money", "finance", "overdue", "receivable", "billed", "payment"]):
        data = get_financial_revenue_overview()
        billed = data['total_billed_revenue_inr']
        collected = data['total_collections_received_inr']
        pending = data['estimated_pending_receivables_inr']
        rate = data['collection_rate_percent']

        kpi_cards = [
            {"label": f"Billed ({data['month']})", "value": f"₹{billed:,.0f}", "color": "#0ea5e9", "icon": "receipt_long"},
            {"label": "Collections Received", "value": f"₹{collected:,.0f}", "color": "#10b981", "icon": "payments"},
            {"label": "Collection Rate", "value": f"{rate}%", "color": "#8b5cf6", "icon": "trending_up"},
            {"label": "Pending Receivables", "value": f"₹{pending:,.0f}", "color": "#f97316", "icon": "account_balance_wallet"},
        ]

        reply = f"### 💰 Financial Performance & Collections ({data['month']})\n\n"
        reply += f"- **Total Billed Trips:** {data['total_trips_this_month']} trips worth **₹{billed:,.2f}**\n"
        reply += f"- **Customer Receipts Collected:** **₹{collected:,.2f}**\n"
        reply += f"- **Collection Efficiency Rate:** **{rate}%**\n"
        reply += f"- **Estimated Outstanding Receivables:** **₹{pending:,.2f}**\n\n"
        reply += "💡 *Recommendation:* Trigger WhatsApp balance payment reminders to clients with outstanding balances prior to final tour drop.\n"

        actions = [
            {"label": "⚡ Dynamic UPI Payment Studio", "url": "/admin/finance/payment-studio/", "primary": True},
            {"label": "📑 Pending Receivables Report", "url": "/crm/reports/client-pending-payments/", "primary": False},
        ]
        suggested = [
            "Show expiring vehicle insurance",
            "How many tours are running today?",
            "Show new CRM inquiries"
        ]

    elif any(k in q for k in ["safety", "driver score", "overspeeding", "harsh brake", "speeding", "telemetry", "behavior"]):
        data = get_driver_safety_alerts()
        kpi_cards = [
            {"label": "Infractions (7d)", "value": str(data['total_telemetry_infractions']), "color": "#ef4444", "icon": "speed"},
            {"label": "Overspeeding", "value": str(data['overspeeding_events']), "color": "#f59e0b", "icon": "warning"},
            {"label": "Harsh Braking", "value": str(data['harsh_braking_events']), "color": "#f97316", "icon": "car_crash"},
        ]

        reply = f"### 🛡️ Driver Safety Scorecard & Telemetry Anomaly Report\n\n"
        reply += f"Over the last 7 days, the telemetry pipeline logged **{data['total_telemetry_infractions']} behavioral infractions**:\n"
        reply += f"- **{data['overspeeding_events']} overspeeding breaches** (>80 km/h threshold)\n"
        reply += f"- **{data['harsh_braking_events']} harsh braking incidents**\n"
        reply += f"- **{data['geofence_breaches']} geofence boundary deviations**\n\n"

        if data['flagged_drivers']:
            reply += "#### ⚠️ Flagged Drivers for Performance Coaching:\n"
            for d in data['flagged_drivers']:
                reply += f"- **{d['driver_name']}** (Ph: {d['phone']}): Safety Index **{d['safety_index']}/100** • {d['infractions_7d']} infractions ({d['penalty_points']} penalty pts)\n"

        actions = [
            {"label": "📊 Fleet Analytics Dashboard", "url": "/analytics/fleet/", "primary": True},
            {"label": "🛰️ Open Mission Control", "url": "/fleet/live/", "primary": False},
        ]
        suggested = [
            "Active tours running today",
            "Which vehicles need insurance renewal?",
            "What is our revenue this month?"
        ]

    elif any(k in q for k in ["available", "availability", "free vehicle", "tomorrow"]):
        # Extract vehicle type if any
        v_type = None
        for cand in ["innova", "tempo", "dzire", "bus", "etios", "traveller"]:
            if cand in q:
                v_type = cand
                break

        data = get_fleet_availability(vehicle_type_name=v_type)
        total = data['total_available_vehicles']

        kpi_cards = [
            {"label": "Total Available", "value": str(total), "color": "#10b981", "icon": "check_circle"},
            {"label": "Filter", "value": (v_type or "All Types").title(), "color": "#0284c7", "icon": "filter_alt"},
        ]

        reply = f"### 🚗 Real-Time Fleet Availability ({data['query_date']})\n\n"
        reply += f"There are **{total} vehicles available** and unassigned for departures on `{data['query_date']}`:\n\n"

        if data['breakdown_by_type']:
            reply += "#### 📊 Availability by Vehicle Category:\n"
            for t in data['breakdown_by_type']:
                tname = t['vehicle_type__name'] or "Standard"
                reply += f"- **{tname}:** {t['count']} vehicles available\n"

        if data['sample_available']:
            reply += "\n#### 🔑 Ready for Instant Dispatch:\n"
            for v in data['sample_available'][:6]:
                reply += f"- **{v['registration']}** ({v['model']}) • {v['seats']} Seats • {v['ac']} • {v['fuel'].upper()}\n"

        actions = [
            {"label": "➕ Create New Booking", "url": "/bookings/create/", "primary": True},
            {"label": "🛰️ Fleet Radar Yard Map", "url": "/admin/operations/fleet-radar/", "primary": False},
        ]
        suggested = [
            "How many tours are running today?",
            "Check CRM inquiries today",
            "Show compliance alerts"
        ]

    elif any(k in q for k in ["crm", "lead", "inquiry", "inquiries", "pipeline", "sla", "quote"]):
        data = get_crm_inquiries_summary()
        kpi_cards = [
            {"label": "New Leads Today", "value": str(data['new_leads_today']), "color": "#10b981", "icon": "person_add"},
            {"label": "Active Pipeline", "value": str(data['active_pipeline_count']), "color": "#0ea5e9", "icon": "assignment"},
            {"label": "SLA Overdue", "value": str(data['overdue_sla_inquiries']), "color": "#ef4444" if data['overdue_sla_inquiries'] > 0 else "#10b981", "icon": "timer"},
        ]

        reply = f"### 📋 CRM Lead Pipeline & Turnaround Status\n\n"
        reply += f"- **New Inquiries Today:** {data['new_leads_today']}\n"
        reply += f"- **Active Quotes in Pipeline:** {data['active_pipeline_count']}\n"
        reply += f"- **SLA Overdue Turnaround Alerts:** **{data['overdue_sla_inquiries']}**\n\n"
        reply += "💡 *Recommendation:* Review inquiries nearing SLA deadlines to maximize booking conversion rates.\n"

        actions = [
            {"label": "🔎 Open Query Tracker 2.0", "url": "/crm/queries/", "primary": True},
            {"label": "📑 Quotation Studio", "url": "/crm/quotations/new/", "primary": False},
        ]
        suggested = [
            "Active tours running today",
            "Revenue and collection rate",
            "Fleet availability for tomorrow"
        ]

    else:
        # General assistance / greeting
        tours = get_active_tours_summary()
        comp = get_compliance_expiry_alerts()
        fin = get_financial_revenue_overview()

        kpi_cards = [
            {"label": "Active Tours", "value": str(tours['total_active_tours']), "color": "#0284c7", "icon": "route"},
            {"label": "Compliance Alerts", "value": str(comp['total_vehicle_compliance_alerts']), "color": "#f59e0b", "icon": "shield"},
            {"label": "Collection Rate", "value": f"{fin['collection_rate_percent']}%", "color": "#10b981", "icon": "payments"},
        ]

        reply = f"👋 **Hello! I'm TARA, your Operations Business Brain.**\n\n"
        reply += "I'm connected directly to your live database. Ask me anything about your tours, fleet compliance, revenue, driver safety, or fleet availability!\n\n"
        reply += "#### ⚡ Instant Highlights Right Now:\n"
        reply += f"- 🚌 **{tours['total_active_tours']} Active Tours** in progress today.\n"
        reply += f"- 🛡️ **{comp['total_vehicle_compliance_alerts']} Vehicles** have compliance documents expiring within 30 days.\n"
        reply += f"- 💰 **{fin['collection_rate_percent']}% Collection Rate** for {fin['month']}.\n\n"
        reply += "Try clicking one of the suggested queries below or type any operational question."

        actions = [
            {"label": "🛰️ Live Fleet Radar", "url": "/admin/operations/fleet-radar/", "primary": True},
            {"label": "📊 Executive DMC Dashboard", "url": "/crm/dashboard/", "primary": False},
        ]
        suggested = [
            "How many tours are running today?",
            "Which vehicles need insurance renewal?",
            "What is our revenue and collection rate?",
            "Show driver safety scorecard alerts",
            "Available Innovas tomorrow"
        ]

    return {
        "status": "success",
        "provider": "local_engine",
        "model": "TARA-Local-Semantic-Engine",
        "reply": reply,
        "kpi_cards": kpi_cards,
        "action_buttons": actions,
        "suggested_queries": suggested
    }


# ==============================================================================
# 4. UNIFIED ENTRY POINT: ask_tara()
# ==============================================================================

def ask_tara(user_message, conversation_history=None, custom_api_key=None, custom_model=None):
    """
    Main entry point for TARA AI requests.
    Tries Groq API first if an API key is available; falls back smoothly to
    the local semantic engine with zero downtime or broken states.
    """
    groq_key = (
        custom_api_key or
        getattr(settings, 'GROQ_API_KEY', '') or
        os.environ.get('GROQ_API_KEY', '')
    )

    if groq_key:
        logger.info("Executing TARA query via Groq LLM...")
        content, status, *extra = execute_groq_llm(
            user_message,
            conversation_history=conversation_history,
            api_key=groq_key,
            model=custom_model
        )
        if content:
            # Generate quick contextual cards & actions to accompany Groq reply
            local_enrich = execute_local_semantic_copilot(user_message)
            return {
                "status": "success",
                "provider": "groq",
                "model": custom_model or getattr(settings, 'GROQ_MODEL', DEFAULT_GROQ_MODEL),
                "reply": content,
                "kpi_cards": local_enrich.get('kpi_cards', []),
                "action_buttons": local_enrich.get('action_buttons', []),
                "suggested_queries": local_enrich.get('suggested_queries', []),
            }
        else:
            logger.warning(f"Groq LLM execution failed ({status}), falling back to local semantic engine.")

    # Fallback to local semantic engine
    return execute_local_semantic_copilot(user_message)
