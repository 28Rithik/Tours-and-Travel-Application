"""
TravelERP Interactive Developer API Catalog & Documentation Portal.

Provides interactive REST API exploration, schema inspection, and curl code generators
for internal developers, mobile apps, and integration partners.
"""

from typing import Any, Dict, List
from django.http import HttpRequest, JsonResponse, HttpResponse
from django.shortcuts import render


API_CATALOG: List[Dict[str, Any]] = [
    # ── AI Copilot & Automation ──
    {
        "category": "AI Copilot & Automation",
        "name": "Rathasārathi Operations Copilot Chat",
        "method": "POST",
        "path": "/api/rathasarathi/chat/",
        "rate_limit": "20 req / min (IP)",
        "auth_required": "Admin / Dispatcher",
        "description": "Send natural language queries to Rathasārathi AI (powered by Groq Llama 3) for fleet allocation, route ETA estimates, driver checks, and booking insights.",
        "request_sample": '{\n  "message": "Which vehicles are available in Coimbatore depot for an outstation trip tomorrow?"\n}',
        "response_sample": '{\n  "response": "Found 3 available vehicles in Coimbatore: TN-38-AB-1234 (Innova), TN-38-CD-5678 (Tempo Traveller)...",\n  "status": "success"\n}',
    },
    {
        "category": "AI Copilot & Automation",
        "name": "Rathasārathi Quick KPI Metrics",
        "method": "GET",
        "path": "/api/rathasarathi/quick-stats/",
        "rate_limit": "60 req / min (IP)",
        "auth_required": "Authenticated",
        "description": "Returns operational KPIs (active dispatches, fleet utilization, overdue vouchers) for the AI assistant badge and status widgets.",
        "request_sample": "{}",
        "response_sample": '{\n  "active_trips": 12,\n  "available_vehicles": 28,\n  "pending_allocations": 3\n}',
    },

    # ── Real-Time Fleet & Telematics ──
    {
        "category": "Fleet & Telematics",
        "name": "GPS Telematics Ping Ingest",
        "method": "POST",
        "path": "/api/telematics/ping/",
        "rate_limit": "120 req / min (IP)",
        "auth_required": "Device Token / API Key",
        "description": "High-throughput telemetry ingestion endpoint for OBD-II and GPS hardware pings (lat, lng, speed, fuel, odometer, ignition status).",
        "request_sample": '{\n  "device_id": "GPS-TN38-9901",\n  "latitude": 11.0168,\n  "longitude": 76.9558,\n  "speed": 62.5,\n  "fuel_level": 78,\n  "ignition": true,\n  "odometer": 142500\n}',
        "response_sample": '{\n  "status": "acknowledged",\n  "geofence_status": "inside_permitted_zone",\n  "server_time": "2026-10-28T07:00:00Z"\n}',
    },
    {
        "category": "Fleet & Telematics",
        "name": "Live Fleet Feed & Radar Status",
        "method": "GET",
        "path": "/api/fleet/live-feed/",
        "rate_limit": "60 req / min (IP)",
        "auth_required": "Staff / Manager",
        "description": "Returns near real-time GPS locations, ignition states, and trip assignments for all vehicles scoped by depot.",
        "request_sample": "{}",
        "response_sample": '{\n  "vehicles": [\n    {\n      "id": 14,\n      "reg_no": "TN-38-AB-1001",\n      "lat": 11.025,\n      "lng": 76.962,\n      "status": "in_transit",\n      "driver": "K. Murugan"\n    }\n  ]\n}',
    },
    {
        "category": "Fleet & Telematics",
        "name": "Smart Dispatch Recommendations",
        "method": "GET",
        "path": "/api/operations/smart-dispatch/<trip_id>/",
        "rate_limit": "30 req / min (IP)",
        "auth_required": "Staff / Manager",
        "description": "Calculates best vehicle-driver match based on depot proximity, driver rest-hours compliance, vehicle fitness expiry, and passenger capacity.",
        "request_sample": "{}",
        "response_sample": '{\n  "recommended": [\n    {\n      "vehicle_id": 4,\n      "driver_id": 12,\n      "score": 96.4,\n      "rationale": "Closest to pickup (3.2 km), driver rest period > 12h"\n    }\n  ]\n}',
    },

    # ── Financials & Payment Gateway ──
    {
        "category": "Payments & Financials",
        "name": "Dynamic UPI QR Code Generation",
        "method": "POST",
        "path": "/api/payments/dynamic-upi/generate/",
        "rate_limit": "20 req / min (IP)",
        "auth_required": "Authenticated",
        "description": "Generates NPCI-compliant dynamic UPI intent strings and base64 QR codes with embedded trip ID and merchant transaction reference.",
        "request_sample": '{\n  "trip_id": 1042,\n  "amount": 3500.00,\n  "remarks": "Trip Advance Payment"\n}',
        "response_sample": '{\n  "success": true,\n  "upi_string": "upi://pay?pa=travelerp@hdfcbank&pn=Sivagayathiri&am=3500.00&tr=TRIP1042_TXN123",\n  "qr_base64": "data:image/png;base64,iVBORw0KGgo...",\n  "transaction_id": "TXN_UPI_99214"\n}',
    },
    {
        "category": "Payments & Financials",
        "name": "Direct UPI Payment Confirmation",
        "method": "POST",
        "path": "/api/payments/direct-upi/confirm/",
        "rate_limit": "20 req / min (IP)",
        "auth_required": "Staff / Accountant",
        "description": "Verifies bank reference (UTR) against payment ledger and updates Trip/Booking payment status to confirmed.",
        "request_sample": '{\n  "transaction_id": "TXN_UPI_99214",\n  "utr_number": "629901458921",\n  "collected_by": "Driver Mobile Wallet"\n}',
        "response_sample": '{\n  "success": true,\n  "payment_id": 401,\n  "new_balance": 0.00,\n  "receipt_number": "REC-2026-0812"\n}',
    },
    {
        "category": "Payments & Financials",
        "name": "Corporate GST Invoice & NIC E-Way Bill",
        "method": "POST",
        "path": "/api/finance/generate-invoice-ewaybill/",
        "rate_limit": "20 req / min (IP)",
        "auth_required": "Finance User",
        "description": "Generates GST-compliant B2B tax invoice with SAC 9964 calculation, CGST/SGST/IGST breakdown, and creates NIC E-Way bill JSON payload.",
        "request_sample": '{\n  "party_id": 5,\n  "trip_ids": [101, 102],\n  "gstin": "33AAACA1234A1Z5"\n}',
        "response_sample": '{\n  "invoice_id": 89,\n  "invoice_number": "INV/2026/0412",\n  "total_amount": 18900.00,\n  "tax_amount": 900.00,\n  "eway_bill_ready": true\n}',
    },

    # ── WhatsApp Bot & Guest Alerts ──
    {
        "category": "WhatsApp & Communications",
        "name": "WhatsApp Webhook Handler",
        "method": "POST",
        "path": "/api/whatsapp/webhook/",
        "rate_limit": "60 req / min (IP)",
        "auth_required": "Meta Webhook Secret",
        "description": "Receives inbound customer messages and interactive button responses (trip confirmation, OTP verification, driver rating).",
        "request_sample": '{\n  "object": "whatsapp_business_account",\n  "entry": [{ "changes": [{ "value": { "messages": [...] } }] }]\n}',
        "response_sample": '{\n  "status": "processed"\n}',
    },
    {
        "category": "WhatsApp & Communications",
        "name": "Dispatch Trip Sheet via WhatsApp",
        "method": "POST",
        "path": "/api/whatsapp/trip/<trip_id>/dispatch/",
        "rate_limit": "30 req / min (IP)",
        "auth_required": "Staff / Dispatcher",
        "description": "Sends interactive WhatsApp message to driver with trip reporting details, customer contact, and digital handover activation button.",
        "request_sample": '{\n  "recipient_type": "driver"\n}',
        "response_sample": '{\n  "status": "sent",\n  "whatsapp_message_id": "wamid.HBgLMj..."\n}',
    },

    # ── Tour Lifecycle & Milestone APIs ──
    {
        "category": "Tour Lifecycle & Execution",
        "name": "Advance Trip Milestone",
        "method": "POST",
        "path": "/api/trip/<trip_id>/milestone/advance/",
        "rate_limit": "30 req / min (IP)",
        "auth_required": "Driver / Staff",
        "description": "Advances the 7-milestone tour progression (Handover -> Boarding -> In-Transit -> Sightseeing -> Halt -> Return -> Settlement).",
        "request_sample": '{\n  "milestone": "boarding_completed",\n  "odometer_reading": 142512,\n  "gps_lat": 11.018,\n  "gps_lng": 76.958\n}',
        "response_sample": '{\n  "status": "success",\n  "current_milestone": "in_transit",\n  "timestamp": "2026-10-28T07:15:00Z"\n}',
    },
    {
        "category": "Tour Lifecycle & Execution",
        "name": "Digital Passenger Signature Capture",
        "method": "POST",
        "path": "/api/trip/<trip_id>/signature/",
        "rate_limit": "20 req / min (IP)",
        "auth_required": "Driver / Passenger Portal",
        "description": "Captures customer digital signature acknowledging start/completion odometer, duty hours, and toll/parking charges.",
        "request_sample": '{\n  "signature_base64": "data:image/png;base64,iVBORw0KGgo...",\n  "signer_name": "R. Sundaram",\n  "rating": 5\n}',
        "response_sample": '{\n  "status": "saved",\n  "signed_at": "2026-10-28T07:20:00Z"\n}',
    },

    # ── GIS & Spatial Radar ──
    {
        "category": "GIS & Navigation",
        "name": "Spatial Nearest Vehicles",
        "method": "GET",
        "path": "/api/gis/nearest-vehicles/?lat=<lat>&lng=<lng>&radius_km=<radius>",
        "rate_limit": "60 req / min (IP)",
        "auth_required": "Authenticated",
        "description": "PostGIS spatial query locating the closest active vehicles within a given radius (km) of a pickup coordinate.",
        "request_sample": "{}",
        "response_sample": '{\n  "vehicles": [\n    {\n      "id": 8,\n      "reg_no": "TN-38-EF-9090",\n      "distance_km": 1.4,\n      "eta_minutes": 4\n    }\n  ]\n}',
    },
]


def api_docs_view(request: HttpRequest) -> HttpResponse:
    """
    Renders the modern, interactive TravelERP Developer API Directory & Catalog.
    """
    # Group catalog endpoints by category
    categories: Dict[str, List[Dict[str, Any]]] = {}
    for item in API_CATALOG:
        cat = item.get("category", "General")
        categories.setdefault(cat, []).append(item)

    return render(
        request,
        "core/api_docs.html",
        {
            "categories": categories,
            "total_endpoints": len(API_CATALOG),
            "catalog_json": API_CATALOG,
        },
    )


def api_schema_json_view(request: HttpRequest) -> JsonResponse:
    """
    Returns machine-readable JSON OpenAPI / API directory specification.
    """
    return JsonResponse(
        {
            "openapi": "3.0.3",
            "info": {
                "title": "TravelERP Enterprise REST API",
                "version": "2.4.0",
                "description": "Comprehensive REST APIs for Sivagayathiri Travels ERP: Fleet, Telematics, Payments, AI, GIS, and Lifecycle.",
            },
            "endpoints": API_CATALOG,
        },
        json_dumps_params={"indent": 2},
    )
