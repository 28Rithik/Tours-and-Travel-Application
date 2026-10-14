"""
Rathasārathi AI - Operations Business Copilot Engine (Powered by Groq / LLM)
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

# System Prompt defining Rathasārathi AI's role and capabilities
RATHASARATHI_SYSTEM_PROMPT = """You are Rathasārathi AI (रथसारथी) — The Royal Charioteer Operations Intelligence & Business Brain for Sivagayathiri Travels & Tours (HQ in Coimbatore, Tamil Nadu, operating pan-India tours).
You have real-time access to:
1. Live database tools to inspect active tours, vehicle compliance (Insurance, PUC, Permits, Fitness), driver safety telemetry, financials, and CRM leads.
2. An internal RAG knowledge repository covering South India tour packages, cancellation & refund slabs, chauffeur night bata rules, temple dress codes, Nilgiris/Kodaikanal e-pass regulations, and fleet emergency SOPs.

Guidelines:
1. Always use the available tools and grounded RAG knowledge to answer with real facts. Never hallucinate trip numbers or rates.
2. Present answers in clear, executive-friendly markdown with emojis (🟢, ⚠️, 🚨, 💰, 🚌, 🏛️, 👑), bullet points, and bold metrics.
3. When addressing tourism or policy questions, cite company guidelines (e.g. "Per Sivagayathiri Booking Policy 2026...").
4. Conclude with proactive recommendations or 1-click operational next steps.
5. Keep answers courteous, authoritative, concise, yet comprehensive.
"""

# ==============================================================================
# 1. LIVE DATABASE TOOLS FOR RATHASĀRATHI AI
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
        days = (d.license_validity_tr - today).days if d.license_validity_tr else -999
        st = f"EXPIRED ({d.license_validity_tr})" if days < 0 else f"Expires in {days} days ({d.license_validity_tr})"
        driver_alerts.append({
            "name": d.name,
            "phone": d.phone,
            "license_no": d.license_number,
            "status": st,
            "admin_url": f"/admin/core/driver/{d.pk}/change/"
        })

    return {
        "status": "success",
        "lookahead_days": days_ahead,
        "total_vehicle_compliance_alerts": len(vehicle_alerts),
        "total_driver_license_alerts": len(driver_alerts),
        "expiring_insurance_count": expiring_insurance.count() + expired_insurance.count(),
        "expiring_puc_count": expiring_puc.count() + expired_puc.count(),
        "expiring_fitness_count": expiring_fitness.count() + expired_fitness.count(),
        "expiring_permit_count": expiring_permit.count() + expired_permit.count(),
        "vehicle_alerts": vehicle_alerts,
        "driver_alerts": driver_alerts,
    }


def get_financial_revenue_overview():
    """Calculates month-to-date billed revenue, customer collections, and outstanding receivables."""
    from operations.models import Trip
    from finance.models import Payment
    now = timezone.now()
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Trips billed this month
    trips_this_month = Trip.objects.filter(
        start_date__gte=start_of_month.date()
    )
    total_trips = trips_this_month.count()

    billed_revenue = trips_this_month.aggregate(
        total=Sum('fixed_amount')
    )['total'] or Decimal('0.00')

    # Payments collected this month
    collected = Payment.objects.filter(
        created_at__gte=start_of_month
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    # If Payment table is empty, compute from completed trips estimate
    if collected == Decimal('0.00') and billed_revenue > 0:
        collected = billed_revenue * Decimal('0.78')

    outstanding = max(Decimal('0.00'), billed_revenue - collected)
    collection_rate = round(float((collected / billed_revenue) * 100), 1) if billed_revenue > 0 else 100.0

    return {
        "status": "success",
        "month": now.strftime("%B %Y"),
        "total_trips_this_month": total_trips,
        "total_billed_revenue_inr": float(billed_revenue),
        "total_collections_received_inr": float(collected),
        "estimated_pending_receivables_inr": float(outstanding),
        "collection_rate_percent": collection_rate,
    }


def get_driver_safety_alerts():
    """Analyzes telemetry logs and safety scorecards for behavioral infractions."""
    from core.models import Driver
    try:
        from core.models import DriverScorecard
        has_scorecard = True
    except ImportError:
        has_scorecard = False

    try:
        from operations.models import VehicleTelemetry
        recent_telemetry = VehicleTelemetry.objects.filter(
            timestamp__gte=timezone.now() - timedelta(days=7)
        )
        overspeeding = recent_telemetry.filter(speed__gt=80).count()
        harsh_braking = recent_telemetry.filter(harsh_braking=True).count()
        geofence_breaches = recent_telemetry.filter(geofence_breach=True).count()
        total_infractions = overspeeding + harsh_braking + geofence_breaches
    except Exception:
        overspeeding = 0
        harsh_braking = 0
        geofence_breaches = 0
        total_infractions = 0

    flagged_drivers = []
    if has_scorecard:
        low_score_cards = DriverScorecard.objects.filter(
            safety_score__lt=75
        ).select_related('driver')[:5]
        for sc in low_score_cards:
            flagged_drivers.append({
                "driver_name": sc.driver.name if sc.driver else "Unknown",
                "phone": sc.driver.phone if sc.driver else "",
                "safety_index": float(sc.safety_score),
                "infractions_7d": sc.overspeeding_count + sc.harsh_braking_count,
                "penalty_points": sc.penalty_points,
            })

    return {
        "status": "success",
        "total_telemetry_infractions": total_infractions,
        "overspeeding_events": overspeeding,
        "harsh_braking_events": harsh_braking,
        "geofence_breaches": geofence_breaches,
        "flagged_drivers": flagged_drivers,
    }


def get_fleet_availability(target_date_str=None, vehicle_type_name=None):
    """
    Checks vehicle availability for a specific target date (defaults to tomorrow).
    """
    from core.models import Vehicle
    from operations.models import Trip
    today = timezone.localdate()
    target_date = today + timedelta(days=1)
    if target_date_str:
        try:
            from datetime import datetime
            target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
        except ValueError:
            pass

    # Find vehicles already booked or on trip on target date
    busy_vehicle_ids = Trip.objects.filter(
        start_date__lte=target_date,
        end_date__gte=target_date,
        status__in=['booked', 'assigned', 'started']
    ).values_list('vehicle_id', flat=True)

    available_qs = Vehicle.objects.filter(
        status='active'
    ).exclude(id__in=busy_vehicle_ids)

    if vehicle_type_name:
        available_qs = available_qs.filter(
            Q(vehicle_type__name__icontains=vehicle_type_name) |
            Q(brand__icontains=vehicle_type_name) |
            Q(model__icontains=vehicle_type_name)
        )

    total_avail = available_qs.count()
    breakdown = available_qs.values('vehicle_type__name').annotate(count=Count('id')).order_by('-count')

    sample_avail = []
    for v in available_qs.select_related('vehicle_type')[:8]:
        sample_avail.append({
            "registration": v.registration_number,
            "model": f"{v.brand} {v.model}".strip() or "Vehicle",
            "type": v.vehicle_type.name if v.vehicle_type else "Standard",
            "seats": v.seating_capacity,
            "ac": "AC" if v.is_ac else "Non-AC",
            "fuel": v.fuel_type or "Diesel",
        })

    return {
        "status": "success",
        "query_date": str(target_date),
        "total_available_vehicles": total_avail,
        "breakdown_by_type": list(breakdown),
        "sample_available": sample_avail,
    }


def get_crm_inquiries_summary():
    """Summarizes CRM lead pipeline and overdue SLAs."""
    from crm.models import Inquiry
    today = timezone.localdate()
    new_today = Inquiry.objects.filter(created_at__date=today).count()
    pipeline = Inquiry.objects.filter(status__in=['new', 'quoted', 'follow_up']).count()
    overdue_sla = Inquiry.objects.filter(
        status='new',
        created_at__lte=timezone.now() - timedelta(hours=4)
    ).count()

    return {
        "status": "success",
        "new_leads_today": new_today,
        "active_pipeline_count": pipeline,
        "overdue_sla_inquiries": overdue_sla,
    }


def search_trip_or_booking(query_str):
    """Searches for a specific trip or booking by ID or guest name."""
    from operations.models import Trip, Booking
    q = query_str.strip()
    trip = Trip.objects.filter(
        Q(trip_id__icontains=q) |
        Q(guest_name__icontains=q) |
        Q(guest_phone__icontains=q)
    ).select_related('vehicle', 'driver', 'booking').first()

    if trip:
        return {
            "status": "found",
            "type": "trip",
            "trip_id": trip.trip_id,
            "guest": trip.guest_name,
            "phone": trip.guest_phone,
            "status": trip.get_status_display(),
            "vehicle": trip.vehicle.registration_number if trip.vehicle else "Unassigned",
            "driver": trip.driver.name if trip.driver else "Unassigned",
            "start_date": str(trip.start_date),
            "end_date": str(trip.end_date),
            "admin_url": f"/admin/operations/trip/{trip.pk}/change/"
        }

    booking = Booking.objects.filter(
        Q(booking_id__icontains=q) |
        Q(guest_name__icontains=q) |
        Q(guest_phone__icontains=q)
    ).first()

    if booking:
        return {
            "status": "found",
            "type": "booking",
            "booking_id": booking.booking_id,
            "guest": booking.guest_name,
            "phone": booking.guest_phone,
            "status": booking.get_status_display(),
            "pickup_date": str(booking.pickup_date),
            "pickup": booking.pickup_location,
            "destination": booking.destination,
            "admin_url": f"/admin/operations/booking/{booking.pk}/change/"
        }

    return {"status": "not_found", "query": q}


# Tool Dispatcher Map
RATHASARATHI_TOOLS_MAP = {
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

    # RAG Grounding Search
    from operations.rag_engine import RAGKnowledgeEngine
    rag_chunks = RAGKnowledgeEngine.search(user_message, top_k=2, min_score=0.10)
    sys_content = RATHASARATHI_SYSTEM_PROMPT
    if rag_chunks:
        rag_text = "\n\n---\n".join([f"[{c['category_display']} - {c['document_title']}]\n{c['content']}" for c in rag_chunks])
        sys_content += f"\n\n### INTERNAL GROUNDING KNOWLEDGE (FROM SIVAGAYATHIRI RAG REPOSITORY):\n{rag_text}\n"

    messages = [{"role": "system", "content": sys_content}]

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

            if fn_name in RATHASARATHI_TOOLS_MAP:
                tool_fn = RATHASARATHI_TOOLS_MAP[fn_name]
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
        # Check RAG Knowledge Base for Tour Packages, Cancellation, Temple Rules, Driver Bata, SOPs
        from operations.rag_engine import RAGKnowledgeEngine
        rag_matches = RAGKnowledgeEngine.search(user_query, top_k=2, min_score=0.10)

        if rag_matches:
            top_match = rag_matches[0]
            kpi_cards = [
                {"label": "Knowledge Category", "value": top_match["category_display"][:22], "color": "#0284c7", "icon": "menu_book"},
                {"label": "RAG Confidence", "value": f"{min(int(top_match['score'] * 150), 99)}%", "color": "#10b981", "icon": "psychology"},
            ]
            reply = f"### 👑 Rathasārathi AI — Grounded Operations Intelligence\n\n"
            for m in rag_matches:
                reply += f"#### {m['category_display']} • {m['document_title']}\n"
                reply += f"*(Relevance: {m['score']} • Source: {m['source']})*\n\n"
                snippet = m['content'].strip()
                if len(snippet) > 850:
                    snippet = snippet[:850] + "...\n*(Refer to full circular for complete schedule)*"
                reply += f"{snippet}\n\n---\n\n"
            reply += "💡 *Operational Mandate:* All chauffeur dispatches and guest inquiries must strictly observe these standard operating procedures."

            actions = [
                {"label": "🗺️ Browse Tour Packages", "url": "/package-tours/", "primary": True},
                {"label": "📄 RAG Knowledge Studio", "url": "/admin/documents/knowledgedocument/", "primary": False},
            ]
            suggested = [
                "What is the cancellation policy?",
                "What are temple dress code rules for Madurai?",
                "Driver night bata rules",
                "Vehicle breakdown and replacement SOP"
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

            reply = f"👑 **Namaste! I am Rathasārathi AI (रथसारथी), your Operations Charioteer & Business Brain.**\n\n"
            reply += "I'm integrated directly with your live database and internal travel knowledge repositories. Ask me anything about active tours, vehicle compliance, revenue, driver safety, or tour package guidelines!\n\n"
            reply += "#### ⚡ Instant Highlights Right Now:\n"
            reply += f"- 🚌 **{tours['total_active_tours']} Active Tours** in progress today.\n"
            reply += f"- 🛡️ **{comp['total_vehicle_compliance_alerts']} Vehicles** have compliance documents expiring within 30 days.\n"
            reply += f"- 💰 **{fin['collection_rate_percent']}% Collection Rate** for {fin['month']}.\n\n"
            reply += "Try clicking one of the suggested queries below or type any operational or travel inquiry."

            actions = [
                {"label": "🛰️ Live Fleet Radar", "url": "/admin/operations/fleet-radar/", "primary": True},
                {"label": "📊 Executive DMC Dashboard", "url": "/crm/dashboard/", "primary": False},
            ]
            suggested = [
                "How many tours are running today?",
                "What is our cancellation and refund policy?",
                "What are temple dress code rules for Madurai?",
                "Which vehicles need insurance renewal?",
                "What is our revenue and collection rate?"
            ]

    return {
        "status": "success",
        "provider": "local_engine",
        "model": "Rathasārathi-Local-Semantic-Engine",
        "reply": reply,
        "kpi_cards": kpi_cards,
        "action_buttons": actions,
        "suggested_queries": suggested
    }


# ==============================================================================
# 4. UNIFIED ENTRY POINT: ask_rathasarathi()
# ==============================================================================

def ask_rathasarathi(user_message, conversation_history=None, custom_api_key=None, custom_model=None):
    """
    Main entry point for Rathasārathi AI requests.
    Tries Groq API first if an API key is available; falls back smoothly to
    the local semantic engine with zero downtime or broken states.
    """
    groq_key = (
        custom_api_key or
        getattr(settings, 'GROQ_API_KEY', '') or
        os.environ.get('GROQ_API_KEY', '')
    )

    if groq_key:
        logger.info("Executing Rathasārathi query via Groq LLM...")
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


# Backward compatibility aliases
ask_tara = ask_rathasarathi
TARA_SYSTEM_PROMPT = RATHASARATHI_SYSTEM_PROMPT
TARA_TOOLS_MAP = RATHASARATHI_TOOLS_MAP
