import json
from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from django.utils import timezone
from django.db.models import Sum, Count, Q

from core.models import Party, Vehicle
from operations.models import Trip, TripHotel
from .models import OutsourcedTripSettlement, HotelConfirmationVoucher, HotelVoucherGuest
from .settlement_engine import calculate_and_create_settlement, approve_and_post_settlement_ledger, determine_tds_rate
from .voucher_service import create_hotel_voucher, generate_hotel_whatsapp_link


@staff_member_required
def admin_settlement_hub_view(request):
    """
    Control studio for outsourced fleet operators:
    Tracks all outsourced vehicle duties, manages buy-vs-sell margins,
    calculates Sec 194C TDS, fuel/advance deductions, and handles 1-click approvals.
    """
    settlements = OutsourcedTripSettlement.objects.select_related(
        'supplier', 'vehicle', 'trip', 'approved_by'
    ).order_by('-settlement_date', '-id')

    # Status filter
    status_filter = request.GET.get('status', '')
    if status_filter:
        settlements = settlements.filter(status=status_filter)

    # Supplier filter
    supplier_id = request.GET.get('supplier', '')
    if supplier_id:
        settlements = settlements.filter(supplier_id=supplier_id)

    # Aggregates / KPIs
    total_count = settlements.count()
    total_buy = settlements.aggregate(total=Sum('agreed_buy_rate'))['total'] or Decimal('0.00')
    total_tds = settlements.aggregate(total=Sum('tds_amount'))['total'] or Decimal('0.00')
    total_net = settlements.aggregate(total=Sum('net_payable_amount'))['total'] or Decimal('0.00')
    total_margin = settlements.aggregate(total=Sum('gross_margin_earned'))['total'] or Decimal('0.00')
    pending_count = settlements.filter(status__in=['draft', 'verified']).count()

    # Potential un-settled outsourced trips
    # Trips using outsourced vehicles that don't have a settlement record
    settled_trip_ids = settlements.values_list('trip_id', flat=True)
    unsettled_trips = Trip.objects.filter(
        vehicle__ownership_type='outsourced'
    ).exclude(
        id__in=settled_trip_ids
    ).select_related('vehicle', 'vehicle__owner_party', 'driver', 'booking').order_by('-start_date')[:15]

    suppliers_list = Party.objects.filter(party_type='supplier', is_active=True).order_by('name')
    outsourced_vehicles = Vehicle.objects.filter(ownership_type='outsourced').exclude(status='inactive').select_related('owner_party').order_by('registration_number')

    context = {
        'settlements': settlements[:50],
        'total_count': total_count,
        'total_buy': total_buy,
        'total_tds': total_tds,
        'total_net': total_net,
        'total_margin': total_margin,
        'pending_count': pending_count,
        'unsettled_trips': unsettled_trips,
        'suppliers_list': suppliers_list,
        'outsourced_vehicles': outsourced_vehicles,
        'selected_status': status_filter,
        'selected_supplier': supplier_id,
    }
    return render(request, 'suppliers/settlement_hub.html', context)


@staff_member_required
def admin_hotel_vouchers_hub_view(request):
    """
    Hotel Vouchers & Rooming Manifests Studio:
    Manages all hotel confirmations across multi-day tour packages.
    """
    vouchers = HotelConfirmationVoucher.objects.select_related(
        'trip', 'trip_hotel'
    ).prefetch_related('guest_manifest').order_by('-check_in_date', '-id')

    # Find TripHotel records needing vouchers
    vouchered_hotel_ids = vouchers.exclude(trip_hotel__isnull=True).values_list('trip_hotel_id', flat=True)
    pending_hotels = TripHotel.objects.exclude(
        id__in=vouchered_hotel_ids
    ).select_related('trip', 'trip__booking', 'trip__booking__party').order_by('check_in_date')[:20]

    # Metrics
    total_vouchers = vouchers.count()
    active_stays = vouchers.filter(status__in=['issued', 'confirmed', 'checked_in']).count()
    total_hotel_tariff = vouchers.aggregate(total=Sum('agreed_hotel_tariff'))['total'] or Decimal('0.00')

    context = {
        'vouchers': vouchers[:50],
        'pending_hotels': pending_hotels,
        'total_vouchers': total_vouchers,
        'active_stays': active_stays,
        'total_hotel_tariff': total_hotel_tariff,
    }
    return render(request, 'suppliers/hotel_vouchers_hub.html', context)


def hotel_voucher_print_view(request, voucher_id):
    """
    Printable, branded Hotel Confirmation Voucher with Rooming Manifest,
    Meal Plan, and Hotel check-in terms.
    """
    voucher = get_object_or_404(
        HotelConfirmationVoucher.objects.select_related('trip', 'trip__booking'),
        pk=voucher_id
    )
    guests = voucher.guest_manifest.all()
    context = {
        'voucher': voucher,
        'guests': guests,
        'now': timezone.now(),
    }
    return render(request, 'suppliers/hotel_voucher_print.html', context)


@staff_member_required
def outsourced_duty_slip_print_view(request, settlement_id):
    """
    Driver Duty Slip & Waybill print view for outsourced partner vehicles.
    """
    settlement = get_object_or_404(
        OutsourcedTripSettlement.objects.select_related('supplier', 'vehicle', 'trip', 'trip__booking'),
        pk=settlement_id
    )
    context = {
        'settlement': settlement,
        'trip': settlement.trip,
        'now': timezone.now(),
    }
    return render(request, 'suppliers/outsourced_duty_slip_print.html', context)


@staff_member_required
def outsourced_settlement_print_view(request, settlement_id):
    """
    Official Vendor Payment Clearance Voucher & Sec 194C TDS certificate.
    """
    settlement = get_object_or_404(
        OutsourcedTripSettlement.objects.select_related('supplier', 'vehicle', 'trip', 'approved_by'),
        pk=settlement_id
    )
    context = {
        'settlement': settlement,
        'now': timezone.now(),
    }
    return render(request, 'suppliers/outsourced_settlement_print.html', context)


# ──────────────────────────────────────────────────────────────────────────
# REST APIs FOR SETTLEMENTS & HOTEL VOUCHERS
# ──────────────────────────────────────────────────────────────────────────

@csrf_exempt
@require_POST
def api_calculate_settlement(request):
    """
    REST API to calculate and persist an outsourced trip settlement.
    """
    if not request.user.is_authenticated or not request.user.is_staff:
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    try:
        data = json.loads(request.body)
        supplier_id = data.get('supplier_id')
        vehicle_id = data.get('vehicle_id')
        trip_id = data.get('trip_id')
        buy_rate = Decimal(str(data.get('agreed_buy_rate') or 0))

        if not supplier_id or not vehicle_id:
            return JsonResponse({'error': 'Supplier and Vehicle are required.'}, status=400)
        if buy_rate <= Decimal('0.00'):
            return JsonResponse({'error': 'Agreed buy rate must be greater than zero.'}, status=400)

        supplier = get_object_or_404(Party, pk=supplier_id)
        vehicle = get_object_or_404(Vehicle, pk=vehicle_id)
        trip = Trip.objects.filter(pk=trip_id).first() if trip_id else None

        settlement = calculate_and_create_settlement(
            supplier=supplier,
            vehicle=vehicle,
            agreed_buy_rate=buy_rate,
            trip=trip,
            toll_parking_allowance=Decimal(str(data.get('toll_parking_allowance') or 0)),
            driver_bata_payable=Decimal(str(data.get('driver_bata_payable') or 0)),
            advance_paid=Decimal(str(data.get('advance_paid') or 0)),
            fuel_deducted=Decimal(str(data.get('fuel_deducted') or 0)),
            damage_penalty=Decimal(str(data.get('damage_penalty') or 0)),
            pan_number=data.get('pan_number', ''),
            tds_applicable=data.get('tds_applicable', True),
            custom_tds_section=data.get('custom_tds_section'),
            driver_name=data.get('driver_name', ''),
            driver_phone=data.get('driver_phone', ''),
            odometer_start=data.get('odometer_start'),
            odometer_end=data.get('odometer_end'),
            duty_slip_number=data.get('duty_slip_number', ''),
            notes=data.get('notes', '')
        )

        return JsonResponse({
            'success': True,
            'settlement_id': settlement.id,
            'settlement_number': settlement.settlement_number,
            'gross_payable': float(settlement.gross_supplier_payable),
            'tds_amount': float(settlement.tds_amount),
            'tds_rate': float(settlement.tds_rate_percent),
            'net_payable': float(settlement.net_payable_amount),
            'gross_margin': float(settlement.gross_margin_earned),
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@csrf_exempt
@require_POST
def api_approve_settlement(request, settlement_id):
    """
    Approves settlement and triggers double-entry GL ledger posting.
    """
    if not request.user.is_authenticated or not request.user.is_staff:
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    try:
        settlement = get_object_or_404(OutsourcedTripSettlement, pk=settlement_id)
        settlement = approve_and_post_settlement_ledger(settlement, approved_by_user=request.user)

        return JsonResponse({
            'success': True,
            'settlement_id': settlement.id,
            'settlement_number': settlement.settlement_number,
            'status': settlement.status,
            'net_payable': float(settlement.net_payable_amount),
            'message': f"Settlement {settlement.settlement_number} approved and posted to Supplier Ledger."
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@csrf_exempt
@require_POST
def api_create_hotel_voucher(request):
    """
    REST API to create a hotel voucher from a trip and optional trip hotel.
    """
    if not request.user.is_authenticated or not request.user.is_staff:
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    try:
        data = json.loads(request.body)
        trip_id = data.get('trip_id')
        trip = get_object_or_404(Trip, pk=trip_id)

        trip_hotel_id = data.get('trip_hotel_id')
        trip_hotel = TripHotel.objects.filter(pk=trip_hotel_id).first() if trip_hotel_id else None

        voucher = create_hotel_voucher(
            trip=trip,
            trip_hotel=trip_hotel,
            hotel_name=data.get('hotel_name', ''),
            hotel_city=data.get('hotel_city', 'Coimbatore'),
            hotel_address=data.get('hotel_address', ''),
            hotel_phone=data.get('hotel_phone', ''),
            hotel_email=data.get('hotel_email', ''),
            reservation_contact=data.get('reservation_contact', ''),
            check_in_date=data.get('check_in_date'),
            check_out_date=data.get('check_out_date'),
            lead_guest_name=data.get('lead_guest_name', ''),
            lead_guest_phone=data.get('lead_guest_phone', ''),
            total_adults=int(data.get('total_adults', 2)),
            total_children=int(data.get('total_children', 0)),
            total_rooms=int(data.get('total_rooms', 1)),
            room_category=data.get('room_category', 'deluxe'),
            meal_plan=data.get('meal_plan', 'MAP'),
            agreed_tariff=Decimal(str(data.get('agreed_hotel_tariff') or 0)),
            advance_paid=Decimal(str(data.get('advance_paid_to_hotel') or 0)),
            billing_instruction=data.get('billing_instruction', 'bill_to_company'),
            special_requests=data.get('special_requests', '')
        )

        return JsonResponse({
            'success': True,
            'voucher_id': voucher.id,
            'voucher_number': voucher.voucher_number,
            'hotel_name': voucher.hotel_name,
            'print_url': f"/suppliers/hotel-voucher/{voucher.id}/print/",
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@require_GET
def api_hotel_voucher_whatsapp(request, voucher_id):
    """
    Returns WhatsApp click-to-chat URL and structured text for hotel reservations.
    """
    voucher = get_object_or_404(HotelConfirmationVoucher, pk=voucher_id)
    res = generate_hotel_whatsapp_link(voucher)

    # Mark timestamp
    voucher.whatsapp_dispatched_at = timezone.now()
    voucher.save(update_fields=['whatsapp_dispatched_at'])

    return JsonResponse({
        'success': True,
        'voucher_number': voucher.voucher_number,
        'whatsapp_url': res['whatsapp_url'],
        'message_text': res['message_text']
    })
