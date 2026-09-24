import datetime
from decimal import Decimal
import json
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count, Sum, Q, Avg

from core.models import Party, Client, Supplier, VehicleType
from crm.models import (
    Inquiry, InquiryFollowUp, Quotation, QuotationDay, QuotationItem,
    HotelMaster, MonumentEntranceMaster, ActivityMaster, GuideChargeMaster,
    PartnerProfile, PartyContactPerson, B2CCustomerProfile,
    SupplierProfile, SupplierContractedRate, SupplierServiceVoucher,
    DmcTask,
    FlightMaster, DmcDocument, TravelComplaint, SupplierPaymentRequisition,
    DmcInvoice,
)
from .analytics import get_dmc_executive_metrics


@login_required
def inquiry_pipeline_view(request):
    """
    Control Room Query Tracker 2.0 with SLA Turnaround Time (TAT) monitoring,
    priority classification, status funnels, and 1-click quotation links.
    """
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = today_start.replace(day=1)

    # Base Queryset
    inquiries = Inquiry.objects.select_related('party', 'vehicle_type', 'assigned_to').prefetch_related('follow_ups')

    # Status filter
    status_filter = request.GET.get('status')
    if status_filter:
        inquiries = inquiries.filter(status=status_filter)

    # Priority filter
    priority_filter = request.GET.get('priority')
    if priority_filter:
        inquiries = inquiries.filter(priority=priority_filter)

    # SLA Overdue filter
    sla_filter = request.GET.get('sla')
    if sla_filter == 'overdue':
        inquiries = inquiries.filter(status__in=['new', 'in_progress'], tat_deadline__lt=now)

    # Search query
    q = request.GET.get('q', '').strip()
    if q:
        inquiries = inquiries.filter(
            Q(inquiry_number__icontains=q) |
            Q(guest_name__icontains=q) |
            Q(guest_phone__icontains=q) |
            Q(destination__icontains=q) |
            Q(party__name__icontains=q)
        )

    # KPI Metrics
    all_inqs = Inquiry.objects.all()
    today_count = all_inqs.filter(created_at__gte=today_start).count()
    month_count = all_inqs.filter(created_at__gte=month_start).count()
    active_count = all_inqs.filter(status__in=['new', 'in_progress']).count()
    quoted_count = all_inqs.filter(status='quoted').count()
    won_count = all_inqs.filter(status='won').count()
    overdue_count = all_inqs.filter(status__in=['new', 'in_progress'], tat_deadline__lt=now).count()
    total_closed = won_count + all_inqs.filter(status='lost').count()
    win_rate = round((won_count / total_closed * 100), 1) if total_closed > 0 else 0.0

    context = {
        'inquiries': inquiries[:100],
        'today_count': today_count,
        'month_count': month_count,
        'active_count': active_count,
        'quoted_count': quoted_count,
        'won_count': won_count,
        'overdue_count': overdue_count,
        'win_rate': win_rate,
        'status_filter': status_filter,
        'priority_filter': priority_filter,
        'sla_filter': sla_filter,
        'search_query': q,
        'now': now,
    }
    return render(request, 'crm/inquiry_pipeline.html', context)


@login_required
def quotation_builder_view(request, quotation_id=None):
    """
    Interactive Day-by-Day Quotation Builder with live itemized costing,
    markup percentage calculator, and Master Data auto-complete.
    """
    quotation = None
    if quotation_id:
        quotation = get_object_or_404(Quotation.objects.prefetch_related('days__items', 'items'), id=quotation_id)

    inquiry_id = request.GET.get('inquiry_id')
    inquiry = None
    if inquiry_id:
        inquiry = get_object_or_404(Inquiry, id=inquiry_id)

    if request.method == 'POST':
        client_id = request.POST.get('party')
        party = get_object_or_404(Client, id=client_id)
        guest_name = request.POST.get('guest_name', party.name)
        guest_phone = request.POST.get('guest_phone', party.phone)
        guest_email = request.POST.get('guest_email', party.email)
        title = request.POST.get('title', 'Custom Tour Itinerary & Quotation')
        destination = request.POST.get('destination', 'Tamil Nadu Circuit')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        pax_count = int(request.POST.get('pax_count', 2))
        vtype_id = request.POST.get('vehicle_type')
        vtype = VehicleType.objects.filter(id=vtype_id).first() if vtype_id else None
        markup_pct = Decimal(str(request.POST.get('markup_percent', '15.00')))
        gst_rate = Decimal(str(request.POST.get('gst_rate', '5.00')))
        inclusions = request.POST.get('inclusions', '')
        exclusions = request.POST.get('exclusions', '')

        if not quotation:
            quotation = Quotation.objects.create(
                party=party,
                inquiry=inquiry,
                guest_name=guest_name,
                guest_phone=guest_phone,
                guest_email=guest_email,
                title=title,
                destination=destination,
                start_date=start_date,
                end_date=end_date,
                pax_count=pax_count,
                vehicle_type=vtype,
                markup_percent=markup_pct,
                gst_rate=gst_rate,
                inclusions=inclusions,
                exclusions=exclusions,
                created_by=request.user,
                status='draft'
            )
        else:
            quotation.party = party
            quotation.guest_name = guest_name
            quotation.guest_phone = guest_phone
            quotation.guest_email = guest_email
            quotation.title = title
            quotation.destination = destination
            quotation.start_date = start_date
            quotation.end_date = end_date
            quotation.pax_count = pax_count
            quotation.vehicle_type = vtype
            quotation.markup_percent = markup_pct
            quotation.gst_rate = gst_rate
            if inclusions:
                quotation.inclusions = inclusions
            if exclusions:
                quotation.exclusions = exclusions
            quotation.save()

        # Update Inquiry status if linked
        if inquiry:
            inquiry.status = 'quoted'
            inquiry.quoted_price = quotation.total_quoted_price
            inquiry.save(update_fields=['status', 'quoted_price'])

        messages.success(request, f"Quotation {quotation.quotation_number} saved successfully!")
        return redirect('crm:quotation_builder', quotation_id=quotation.id)

    clients = Client.objects.filter(is_active=True).order_by('name')
    vehicle_types = VehicleType.objects.all().order_by('name')
    hotels = HotelMaster.objects.filter(is_active=True).order_by('destination', 'name')
    monuments = MonumentEntranceMaster.objects.filter(is_active=True).order_by('destination', 'name')
    activities = ActivityMaster.objects.filter(is_active=True).order_by('destination', 'name')
    guides = GuideChargeMaster.objects.filter(is_active=True).order_by('destination', 'language')

    form_data = {
        'party_id': (quotation.party_id if quotation else None) or (inquiry.party_id if inquiry else None),
        'title': quotation.title if quotation else (f"Tour Itinerary: {inquiry.destination}" if inquiry else "Custom Nilgiris & Western Ghats Circuit"),
        'guest_name': quotation.guest_name if quotation else (inquiry.guest_name if inquiry else ''),
        'guest_phone': quotation.guest_phone if quotation else (inquiry.guest_phone if inquiry else ''),
        'guest_email': quotation.guest_email if quotation else (inquiry.guest_email if inquiry else ''),
        'destination': quotation.destination if quotation else (inquiry.destination if inquiry else 'Ooty & Coonoor'),
        'start_date': quotation.start_date if quotation else (inquiry.pickup_date if inquiry else None),
        'end_date': quotation.end_date if quotation else (inquiry.drop_date if inquiry else None),
        'pax_count': quotation.pax_count if quotation else (inquiry.adult_count if inquiry else 2),
        'vehicle_type_id': (quotation.vehicle_type_id if quotation else None) or (inquiry.vehicle_type_id if inquiry else None),
        'markup_percent': quotation.markup_percent if quotation else Decimal('15.00'),
    }

    context = {
        'quotation': quotation,
        'inquiry': inquiry,
        'form_data': form_data,
        'clients': clients,
        'vehicle_types': vehicle_types,
        'hotels': hotels,
        'monuments': monuments,
        'activities': activities,
        'guides': guides,
    }
    return render(request, 'crm/quotation_builder.html', context)


@login_required
def quotation_add_day_api(request, quotation_id):
    """AJAX endpoint to add an itinerary day to a quotation."""
    quotation = get_object_or_404(Quotation, id=quotation_id)
    if request.method == 'POST':
        day_num = quotation.days.count() + 1
        title = request.POST.get('title', f"Day {day_num}: Sightseeing & Leisure")
        dest = request.POST.get('overnight_destination', quotation.destination)
        desc = request.POST.get('description', '')
        hotel_id = request.POST.get('hotel')
        hotel = HotelMaster.objects.filter(id=hotel_id).first() if hotel_id else None
        meal_plan = request.POST.get('hotel_meal_plan', 'CP')

        day = QuotationDay.objects.create(
            quotation=quotation,
            day_number=day_num,
            title=title,
            overnight_destination=dest,
            description=desc,
            hotel=hotel,
            hotel_meal_plan=meal_plan
        )

        # Auto-create hotel cost item if hotel is selected
        if hotel:
            rate = getattr(hotel, f"{meal_plan.lower()}_rate", hotel.cp_rate) or Decimal('0.00')
            # 1 room per 2 pax
            rooms = max(1, (quotation.pax_count + 1) // 2)
            total_hotel_cost = rate * rooms
            QuotationItem.objects.create(
                quotation=quotation,
                day=day,
                category='hotel',
                item_name=f"{hotel.name} ({rooms}x {hotel.room_type} - {meal_plan})",
                quantity=rooms,
                unit_cost=rate,
                total_cost=total_hotel_cost
            )
            quotation.recalculate_totals()

        return JsonResponse({
            'status': 'success',
            'day_id': day.id,
            'day_number': day.day_number,
            'title': day.title,
            'net_cost': float(quotation.net_cost),
            'total_quoted_price': float(quotation.total_quoted_price),
        })
    return JsonResponse({'status': 'error', 'message': 'POST required'}, status=400)


@login_required
def quotation_add_item_api(request, quotation_id):
    """AJAX endpoint to add a cost item (transport, ticket, activity, guide) to a quotation."""
    quotation = get_object_or_404(Quotation, id=quotation_id)
    if request.method == 'POST':
        day_id = request.POST.get('day_id')
        day = quotation.days.filter(id=day_id).first() if day_id else None
        category = request.POST.get('category', 'other')
        item_name = request.POST.get('item_name', 'Sightseeing Service')
        qty = int(request.POST.get('quantity', 1))
        unit_cost = Decimal(str(request.POST.get('unit_cost', '0.00')))
        total_cost = unit_cost * qty

        item = QuotationItem.objects.create(
            quotation=quotation,
            day=day,
            category=category,
            item_name=item_name,
            quantity=qty,
            unit_cost=unit_cost,
            total_cost=total_cost
        )
        quotation.recalculate_totals()

        return JsonResponse({
            'status': 'success',
            'item_id': item.id,
            'item_name': item.item_name,
            'category': item.get_category_display(),
            'total_cost': float(item.total_cost),
            'net_cost': float(quotation.net_cost),
            'markup_amount': float(quotation.markup_amount),
            'total_quoted_price': float(quotation.total_quoted_price),
        })
    return JsonResponse({'status': 'error', 'message': 'POST required'}, status=400)


@login_required
def quotation_delete_item_api(request, item_id):
    """AJAX endpoint to delete an itemized cost line item."""
    item = get_object_or_404(QuotationItem, id=item_id)
    quotation = item.quotation
    item.delete()
    quotation.recalculate_totals()
    return JsonResponse({
        'status': 'success',
        'net_cost': float(quotation.net_cost),
        'markup_amount': float(quotation.markup_amount),
        'total_quoted_price': float(quotation.total_quoted_price),
    })


@login_required
def quotation_preview_view(request, quotation_id):
    """
    Client-ready, high-aesthetic proposal presentation view with interactive
    timeline, hotel specifications, itemized costing, and 1-click actions.
    """
    quotation = get_object_or_404(
        Quotation.objects.select_related('party', 'vehicle_type', 'booking', 'inquiry')
        .prefetch_related('days__items', 'days__hotel', 'items'),
        id=quotation_id
    )

    context = {
        'q': quotation,
        'days': quotation.days.all(),
        'items': quotation.items.all(),
        'today': timezone.now().date(),
    }
    return render(request, 'crm/quotation_client_preview.html', context)


@login_required
def quotation_send_to_client_action(request, quotation_id):
    """
    Marks quotation as 'sent' and automatically triggers WhatsApp / Email dispatch.
    """
    quotation = get_object_or_404(Quotation, id=quotation_id)
    quotation.status = 'sent'
    quotation.save(update_fields=['status'])
    messages.success(request, f"Quotation {quotation.quotation_number} marked as Sent! Customer dispatch triggered.")
    return redirect('crm:quotation_preview', quotation_id=quotation.id)


@login_required
def quotation_convert_to_booking_view(request, quotation_id):
    """
    1-Click Conversion: Converts accepted Quotation into a confirmed Booking.
    """
    quotation = get_object_or_404(Quotation, id=quotation_id)
    booking = quotation.convert_to_booking(user=request.user)
    messages.success(request, f"🎉 Quotation successfully converted to Booking {booking.booking_number}!")
    return redirect('booking-detail', booking_id=booking.id)


@login_required
def quotation_create_revision_view(request, quotation_id):
    """
    Generates a new revision version (e.g. V2, V3) during client negotiation.
    """
    quotation = get_object_or_404(Quotation, id=quotation_id)
    new_quote = quotation.create_revision()
    messages.success(request, f"New revision created: {new_quote.quotation_number} (v{new_quote.version}).")
    return redirect('crm:quotation_builder', quotation_id=new_quote.id)


@login_required
def api_master_data_lookup(request):
    """
    Fast JSON autocomplete endpoint for hotels, monuments, activities, and guides.
    """
    dest = request.GET.get('destination', '').strip()
    data = {'hotels': [], 'monuments': [], 'activities': [], 'guides': []}

    hotels = HotelMaster.objects.filter(is_active=True)
    monuments = MonumentEntranceMaster.objects.filter(is_active=True)
    activities = ActivityMaster.objects.filter(is_active=True)
    guides = GuideChargeMaster.objects.filter(is_active=True)

    if dest:
        hotels = hotels.filter(destination__icontains=dest)
        monuments = monuments.filter(destination__icontains=dest)
        activities = activities.filter(destination__icontains=dest)
        guides = guides.filter(destination__icontains=dest)

    for h in hotels[:20]:
        data['hotels'].append({
            'id': h.id,
            'name': h.name,
            'destination': h.destination,
            'star': h.get_star_category_display(),
            'room_type': h.room_type,
            'ep_rate': float(h.ep_rate),
            'cp_rate': float(h.cp_rate),
            'map_rate': float(h.map_rate),
            'ap_rate': float(h.ap_rate),
        })

    for m in monuments[:20]:
        data['monuments'].append({
            'id': m.id,
            'name': m.name,
            'destination': m.destination,
            'adult_rate': float(m.domestic_adult_rate),
            'child_rate': float(m.domestic_child_rate),
            'foreigner_rate': float(m.foreigner_adult_rate),
        })

    for a in activities[:20]:
        data['activities'].append({
            'id': a.id,
            'name': a.name,
            'destination': a.destination,
            'pricing_type': a.get_pricing_type_display(),
            'rate': float(a.standard_rate),
        })

    for g in guides[:20]:
        data['guides'].append({
            'id': g.id,
            'destination': g.destination,
            'language': g.get_language_display(),
            'half_day_rate': float(g.half_day_rate),
            'full_day_rate': float(g.full_day_rate),
        })

    flights = FlightMaster.objects.filter(is_active=True)
    if dest:
        flights = flights.filter(Q(origin_airport__icontains=dest) | Q(destination_airport__icontains=dest) | Q(airline__icontains=dest))
    data['flights'] = []
    for f in flights[:20]:
        data['flights'].append({
            'id': f.id,
            'airline': f.airline,
            'flight_number': f.flight_number,
            'origin': f.origin_airport,
            'destination': f.destination_airport,
            'departure_time': f.departure_time.strftime('%H:%M'),
            'arrival_time': f.arrival_time.strftime('%H:%M'),
            'operating_days': f.operating_days,
            'cabin_class': f.get_cabin_class_display(),
            'baggage_allowance': f.baggage_allowance,
        })

    return JsonResponse(data)


# ==============================================================================
# PHASE B: PARTNER, SUPPLIER & SERVICE VOUCHER VIEWS
# ==============================================================================

@login_required
def partner_management_view(request):
    """
    Control console for FTOs, B2B Travel Agencies, Corporate MNCs, and Retail B2C clients.
    """
    tab = request.GET.get('tab', 'partners')
    q = request.GET.get('q', '').strip()
    category = request.GET.get('category', '').strip()

    partners = PartnerProfile.objects.select_related('party').prefetch_related('party__contact_persons').order_by('-created_at')
    b2c_customers = B2CCustomerProfile.objects.select_related('party').order_by('-created_at')

    if q:
        partners = partners.filter(
            Q(party__name__icontains=q) |
            Q(trade_name__icontains=q) |
            Q(party__phone__icontains=q) |
            Q(party__email__icontains=q)
        )
        b2c_customers = b2c_customers.filter(
            Q(full_name__icontains=q) |
            Q(party__phone__icontains=q) |
            Q(party__email__icontains=q) |
            Q(passport_number__icontains=q)
        )

    if category:
        partners = partners.filter(category=category)

    # Metrics
    total_credit_exposure = partners.aggregate(tot=Sum('credit_limit'))['tot'] or Decimal('0.00')
    total_fto_count = partners.count()
    total_b2c_count = b2c_customers.count()
    vip_count = b2c_customers.filter(is_vip=True).count()

    # Handle quick creation via POST
    if request.method == 'POST':
        action_type = request.POST.get('action_type')
        if action_type == 'add_partner':
            name = request.POST.get('name')
            ptype = request.POST.get('party_type', 'travel_agency')
            phone = request.POST.get('phone', '')
            email = request.POST.get('email', '')
            cat = request.POST.get('category', 'silver')
            trade_name = request.POST.get('trade_name', '')
            credit_limit = Decimal(str(request.POST.get('credit_limit', '0.00')))
            gstin = request.POST.get('gstin', '')
            pan = request.POST.get('pan_number', '')

            party = Party.objects.create(
                name=name,
                party_type=ptype,
                phone=phone,
                email=email,
                gstin=gstin
            )
            PartnerProfile.objects.create(
                party=party,
                category=cat,
                trade_name=trade_name,
                credit_limit=credit_limit,
                pan_number=pan,
                bank_name=request.POST.get('bank_name', ''),
                bank_account_number=request.POST.get('bank_account_number', ''),
                bank_ifsc=request.POST.get('bank_ifsc', '')
            )
            # Add primary contact person if provided
            contact_name = request.POST.get('contact_name')
            if contact_name:
                PartyContactPerson.objects.create(
                    party=party,
                    name=contact_name,
                    designation=request.POST.get('contact_designation', 'Operations Manager'),
                    phone=request.POST.get('contact_phone', phone),
                    email=request.POST.get('contact_email', email),
                    is_primary=True
                )
            messages.success(request, f"Partner {name} ({cat.upper()}) added successfully!")
            return redirect('crm:partner_list')

        elif action_type == 'add_b2c':
            full_name = request.POST.get('full_name')
            phone = request.POST.get('phone', '')
            email = request.POST.get('email', '')
            nationality = request.POST.get('nationality', 'Indian')
            passport = request.POST.get('passport_number', '')
            city = request.POST.get('city', '')
            is_vip = request.POST.get('is_vip') == 'on'

            party = Party.objects.create(
                name=full_name,
                party_type='individual',
                phone=phone,
                email=email
            )
            B2CCustomerProfile.objects.create(
                party=party,
                full_name=full_name,
                alternate_phone=request.POST.get('alternate_phone', ''),
                nationality=nationality,
                passport_number=passport,
                city=city,
                is_vip=is_vip,
                facebook_url=request.POST.get('facebook_url', ''),
                instagram_handle=request.POST.get('instagram_handle', ''),
                linkedin_url=request.POST.get('linkedin_url', '')
            )
            messages.success(request, f"B2C Traveler {full_name} profile saved!")
            return redirect(f"{request.path}?tab=b2c")

    context = {
        'tab': tab,
        'q': q,
        'category': category,
        'partners': partners,
        'b2c_customers': b2c_customers,
        'total_fto_count': total_fto_count,
        'total_credit_exposure': total_credit_exposure,
        'total_b2c_count': total_b2c_count,
        'vip_count': vip_count,
        'category_choices': PartnerProfile.CATEGORY_CHOICES,
    }
    return render(request, 'crm/partner_management.html', context)


@login_required
def supplier_management_view(request):
    """
    Supplier Master Directory & Contracted Rate Tariffs for Hoteliers, Transporters,
    Sightseeing Vendors, and Guide Agencies.
    """
    stype = request.GET.get('type', '').strip()
    dest = request.GET.get('dest', '').strip()
    q = request.GET.get('q', '').strip()

    suppliers = SupplierProfile.objects.select_related('party').prefetch_related('contracted_rates', 'party__contact_persons').order_by('destination_city', 'party__name')

    if stype:
        suppliers = suppliers.filter(supplier_type=stype)
    if dest:
        suppliers = suppliers.filter(destination_city__icontains=dest)
    if q:
        suppliers = suppliers.filter(
            Q(party__name__icontains=q) |
            Q(trade_name__icontains=q) |
            Q(destination_city__icontains=q)
        )

    # Metrics
    total_suppliers = suppliers.count()
    preferred_count = suppliers.filter(is_preferred=True).count()
    total_rates_count = SupplierContractedRate.objects.filter(is_active=True).count()

    # Handle quick creation via POST
    if request.method == 'POST':
        action_type = request.POST.get('action_type')
        if action_type == 'add_supplier':
            name = request.POST.get('name')
            supplier_type = request.POST.get('supplier_type', 'hotelier')
            dest_city = request.POST.get('destination_city', 'Ooty')
            phone = request.POST.get('phone', '')
            email = request.POST.get('email', '')
            is_preferred = request.POST.get('is_preferred') == 'on'
            gstin = request.POST.get('gstin', '')

            party = Party.objects.create(
                name=name,
                party_type='supplier',
                phone=phone,
                email=email,
                gstin=gstin
            )
            SupplierProfile.objects.create(
                party=party,
                supplier_type=supplier_type,
                trade_name=request.POST.get('trade_name', name),
                destination_city=dest_city,
                is_preferred=is_preferred,
                bank_beneficiary_name=request.POST.get('bank_beneficiary_name', ''),
                bank_name=request.POST.get('bank_name', ''),
                bank_account_number=request.POST.get('bank_account_number', ''),
                bank_ifsc=request.POST.get('bank_ifsc', '')
            )
            messages.success(request, f"Supplier {name} ({supplier_type}) added successfully!")
            return redirect('crm:supplier_list')

        elif action_type == 'add_contracted_rate':
            supplier_id = request.POST.get('supplier_id')
            supplier = get_object_or_404(SupplierProfile, id=supplier_id)
            service_cat = request.POST.get('service_category', 'hotel_room')
            service_name = request.POST.get('service_name')
            room_type = request.POST.get('room_type', '')
            meal_plan = request.POST.get('meal_plan', 'CP')
            seasonality = request.POST.get('seasonality', 'regular')
            rack_rate = Decimal(str(request.POST.get('rack_rate', '0.00')))
            contracted_rate = Decimal(str(request.POST.get('contracted_buy_rate', '0.00')))

            SupplierContractedRate.objects.create(
                supplier=supplier,
                service_category=service_cat,
                service_name=service_name,
                room_type=room_type,
                meal_plan=meal_plan,
                seasonality=seasonality,
                rack_rate=rack_rate,
                contracted_buy_rate=contracted_rate,
                is_active=True
            )
            messages.success(request, f"Contracted rate for {service_name} saved with {supplier.party.name}!")
            return redirect('crm:supplier_list')

    context = {
        'suppliers': suppliers,
        'stype': stype,
        'dest': dest,
        'q': q,
        'total_suppliers': total_suppliers,
        'preferred_count': preferred_count,
        'total_rates_count': total_rates_count,
        'supplier_types': SupplierProfile.SUPPLIER_TYPES,
        'season_choices': SupplierContractedRate.SEASON_CHOICES,
    }
    return render(request, 'crm/supplier_management.html', context)


@login_required
def voucher_console_view(request):
    """
    Control Console for Supplier Service Vouchers & Purchase Orders (LPO).
    """
    status_filter = request.GET.get('status', '').strip()
    vtype_filter = request.GET.get('type', '').strip()

    vouchers = SupplierServiceVoucher.objects.select_related('supplier__party', 'quotation', 'booking').order_by('-created_at')

    if status_filter:
        vouchers = vouchers.filter(status=status_filter)
    if vtype_filter:
        vouchers = vouchers.filter(voucher_type=vtype_filter)

    # Metrics
    total_count = vouchers.count()
    confirmed_count = vouchers.filter(status='confirmed').count()
    issued_count = vouchers.filter(status='issued').count()
    draft_count = vouchers.filter(status='draft').count()
    total_payable = vouchers.filter(status__in=['issued', 'confirmed']).aggregate(tot=Sum('total_payable_to_supplier'))['tot'] or Decimal('0.00')

    suppliers = SupplierProfile.objects.select_related('party').order_by('destination_city', 'party__name')
    quotations = Quotation.objects.order_by('-created_at')[:30]

    context = {
        'vouchers': vouchers,
        'status_filter': status_filter,
        'vtype_filter': vtype_filter,
        'total_count': total_count,
        'confirmed_count': confirmed_count,
        'issued_count': issued_count,
        'draft_count': draft_count,
        'total_payable': total_payable,
        'suppliers': suppliers,
        'quotations': quotations,
        'voucher_types': SupplierServiceVoucher.VOUCHER_TYPES,
        'status_choices': SupplierServiceVoucher.STATUS_CHOICES,
    }
    return render(request, 'crm/voucher_console.html', context)


@login_required
def voucher_create_view(request):
    """
    Quick generator to issue a new service voucher from scratch or linked to a quotation.
    """
    if request.method == 'POST':
        supplier_id = request.POST.get('supplier')
        supplier = get_object_or_404(SupplierProfile, id=supplier_id)
        vtype = request.POST.get('voucher_type', 'hotel_reservation')
        quote_id = request.POST.get('quotation')
        quotation = Quotation.objects.filter(id=quote_id).first() if quote_id else None

        guest_name = request.POST.get('guest_name', quotation.guest_name if quotation else 'Lead Traveler')
        guest_phone = request.POST.get('guest_phone', quotation.guest_phone if quotation else '')
        pax_count = int(request.POST.get('pax_count', quotation.pax_count if quotation else 2))

        start_date = request.POST.get('service_date_start', str(quotation.start_date if quotation else timezone.now().date()))
        end_date = request.POST.get('service_date_end', str(quotation.end_date if quotation else timezone.now().date()))
        nights = int(request.POST.get('duration_nights', quotation.duration_nights if quotation else 1))

        hotel_room = request.POST.get('hotel_room_type', '')
        hotel_meal = request.POST.get('hotel_meal_plan', 'CP')
        room_count = int(request.POST.get('room_count', 1))

        vtype_name = request.POST.get('vehicle_type_name', '')
        pickup_loc = request.POST.get('pickup_location', '')
        drop_loc = request.POST.get('drop_location', '')

        unit_cost = Decimal(str(request.POST.get('contracted_unit_cost', '0.00')))
        total_payable = Decimal(str(request.POST.get('total_payable_to_supplier', '0.00')))
        if total_payable == 0 and unit_cost > 0:
            total_payable = unit_cost * room_count * nights

        voucher = SupplierServiceVoucher.objects.create(
            supplier=supplier,
            voucher_type=vtype,
            quotation=quotation,
            guest_name=guest_name,
            guest_phone=guest_phone,
            pax_count=pax_count,
            service_date_start=start_date,
            service_date_end=end_date,
            duration_nights=nights,
            hotel_room_type=hotel_room,
            hotel_meal_plan=hotel_meal,
            room_count=room_count,
            vehicle_type_name=vtype_name,
            pickup_location=pickup_loc,
            drop_location=drop_loc,
            contracted_unit_cost=unit_cost,
            total_payable_to_supplier=total_payable,
            special_instructions=request.POST.get('special_instructions', ''),
            created_by=request.user,
            status='draft'
        )
        messages.success(request, f"Service Voucher {voucher.voucher_number} generated as Draft!")
        return redirect('crm:voucher_detail', voucher_id=voucher.id)

    return redirect('crm:voucher_console')


@login_required
def voucher_detail_view(request, voucher_id):
    """
    Official DMC Service Voucher & Purchase Order Document Presentation.
    """
    voucher = get_object_or_404(
        SupplierServiceVoucher.objects.select_related('supplier__party', 'quotation', 'booking'),
        id=voucher_id
    )
    supplier_party = voucher.supplier.party
    primary_contact = supplier_party.contact_persons.filter(is_primary=True).first()

    context = {
        'v': voucher,
        'supplier': voucher.supplier,
        'party': supplier_party,
        'contact': primary_contact,
        'today': timezone.now().date(),
    }
    return render(request, 'crm/voucher_detail.html', context)


@login_required
def voucher_issue_action(request, voucher_id):
    """
    Marks a service voucher as 'issued' and fires WhatsApp / Email dispatch to the supplier.
    """
    voucher = get_object_or_404(SupplierServiceVoucher, id=voucher_id)
    voucher.status = 'issued'
    voucher.issued_at = timezone.now()
    voucher.save(update_fields=['status', 'issued_at'])
    messages.success(request, f"Voucher {voucher.voucher_number} successfully issued! Supplier notification triggered.")
    return redirect('crm:voucher_detail', voucher_id=voucher.id)


def supplier_extranet_voucher_view(request, token):
    """
    Public Supplier Extranet confirmation portal accessed via secure token link.
    Allows hoteliers, transporters, and vendors to review the reservation order and confirm.
    """
    voucher = get_object_or_404(
        SupplierServiceVoucher.objects.select_related('supplier__party', 'quotation'),
        confirmation_token=token
    )

    if request.method == 'POST':
        action = request.POST.get('action')
        ref_code = request.POST.get('confirmation_reference', '').strip()
        notes = request.POST.get('supplier_notes', '').strip()

        if action == 'confirm':
            voucher.status = 'confirmed'
            voucher.confirmed_at = timezone.now()
            voucher.confirmation_reference = ref_code or f"CONF-{timezone.now().strftime('%Y%m%d%H%M')}"
            voucher.supplier_notes = notes
            voucher.save(update_fields=['status', 'confirmed_at', 'confirmation_reference', 'supplier_notes'])
            messages.success(request, f"Thank you! Reservation {voucher.voucher_number} has been confirmed.")
        elif action == 'amend':
            voucher.status = 'amended'
            voucher.supplier_notes = notes
            voucher.save(update_fields=['status', 'supplier_notes'])
            messages.warning(request, f"Amendment request noted for {voucher.voucher_number}. Our operations desk will contact you.")

        return redirect('crm:supplier_extranet_voucher', token=token)

    context = {
        'v': voucher,
        'supplier': voucher.supplier,
        'party': voucher.supplier.party,
    }
    return render(request, 'crm/supplier_extranet_voucher.html', context)


# ==============================================================================
# PHASE C: EXECUTIVE DMC BUSINESS DASHBOARD & TO-DO ENGINE
# ==============================================================================

@login_required
def dmc_executive_dashboard_view(request):
    """
    Executive Business Dashboard showcasing:
    - Monthly & Today's Query Summary
    - To-Do List: Add/Assign tasks, set priority, live completion
    - Destination information: Top destination breakdown
    - Status-wise Query Report & SLA TAT alerts
    - Monthly Sales & Gross Margin Data
    - List of Top 5 FTOs / Corporate Accounts
    """
    metrics = get_dmc_executive_metrics()
    staff_users = User.objects.filter(is_active=True).order_by('first_name', 'username')
    priority_choices = DmcTask.PRIORITY_CHOICES

    context = {
        **metrics,
        'staff_users': staff_users,
        'priority_choices': priority_choices,
        'today': timezone.now().date(),
    }
    return render(request, 'crm/dashboard.html', context)


@login_required
def task_create_api(request):
    """
    POST endpoint to add and assign a new operational task in the DMC To-Do List.
    """
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        if not title:
            return JsonResponse({'status': 'error', 'message': 'Task title required'}, status=400)

        assigned_to_id = request.POST.get('assigned_to')
        assigned_user = User.objects.filter(id=assigned_to_id).first() if assigned_to_id else request.user
        priority = request.POST.get('priority', 'medium')
        due_date_str = request.POST.get('due_date')
        if due_date_str:
            if isinstance(due_date_str, str):
                try:
                    due_date = datetime.date.fromisoformat(due_date_str)
                except (ValueError, TypeError):
                    due_date = timezone.now().date()
            else:
                due_date = due_date_str
        else:
            due_date = timezone.now().date()
        desc = request.POST.get('description', '')
        inquiry_id = request.POST.get('related_inquiry')
        inquiry = Inquiry.objects.filter(id=inquiry_id).first() if inquiry_id else None

        task = DmcTask.objects.create(
            title=title,
            description=desc,
            assigned_to=assigned_user,
            created_by=request.user,
            priority=priority,
            due_date=due_date,
            related_inquiry=inquiry,
            status='pending'
        )

        return JsonResponse({
            'status': 'success',
            'task_id': task.id,
            'title': task.title,
            'assigned_name': task.assigned_to.get_full_name() or task.assigned_to.username,
            'priority': task.get_priority_display(),
            'due_date': str(task.due_date),
            'is_overdue': task.is_overdue
        })
    return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)


@login_required
def task_toggle_status_api(request, task_id):
    """
    POST endpoint to toggle task between pending and completed.
    """
    task = get_object_or_404(DmcTask, id=task_id)
    if task.status == 'completed':
        task.status = 'pending'
        task.completed_at = None
    else:
        task.status = 'completed'
        task.completed_at = timezone.now()
    task.save(update_fields=['status', 'completed_at', 'updated_at'])

    return JsonResponse({
        'status': 'success',
        'task_id': task.id,
        'new_status': task.status,
        'is_completed': task.status == 'completed'
    })


# ==============================================================================
# PHASE D: ENTERPRISE DOCUMENT VAULT
# ==============================================================================

@login_required
def dmc_documents_view(request):
    """
    Enterprise Document Management Vault:
    Organize and retrieve brochures, itinerary templates, rate sheets, agreements, and customer KYC.
    """
    category_filter = request.GET.get('category')
    search_query = request.GET.get('q', '').strip()

    docs = DmcDocument.objects.select_related('uploaded_by', 'related_partner', 'related_supplier').all()
    if category_filter:
        docs = docs.filter(category=category_filter)
    if search_query:
        docs = docs.filter(Q(title__icontains=search_query) | Q(description__icontains=search_query))

    categories = DmcDocument.CATEGORY_CHOICES
    counts = {cat[0]: DmcDocument.objects.filter(category=cat[0]).count() for cat in categories}
    total_docs = DmcDocument.objects.count()

    context = {
        'documents': docs,
        'categories': categories,
        'category_counts': counts,
        'total_docs': total_docs,
        'selected_category': category_filter,
        'search_query': search_query,
    }
    return render(request, 'crm/documents_vault.html', context)


@login_required
def dmc_document_upload_api(request):
    """
    POST endpoint to upload a document to the DMC vault.
    """
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        category = request.POST.get('category', 'brochure')
        desc = request.POST.get('description', '').strip()
        doc_file = request.FILES.get('document_file')

        if not title:
            return JsonResponse({'status': 'error', 'message': 'Document title is required'}, status=400)
        if not doc_file:
            return JsonResponse({'status': 'error', 'message': 'Please attach a document file'}, status=400)

        inq_id = request.POST.get('related_inquiry')
        inq = Inquiry.objects.filter(id=inq_id).first() if inq_id else None

        partner_id = request.POST.get('related_partner')
        partner = PartnerProfile.objects.filter(id=partner_id).first() if partner_id else None

        doc = DmcDocument.objects.create(
            title=title,
            category=category,
            document_file=doc_file,
            description=desc,
            related_inquiry=inq,
            related_partner=partner,
            uploaded_by=request.user
        )

        return JsonResponse({
            'status': 'success',
            'document_id': doc.id,
            'title': doc.title,
            'category': doc.get_category_display(),
            'file_url': doc.document_file.url
        })
    return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)


# ==============================================================================
# PHASE D: COMPLAINT & SERVICE QUALITY MANAGEMENT
# ==============================================================================

@login_required
def complaints_console_view(request):
    """
    DMC Complaint Management Console:
    Tracks lodging, investigation, resolution, and supplier performance impact.
    """
    status_filter = request.GET.get('status')
    category_filter = request.GET.get('category')

    complaints = TravelComplaint.objects.select_related('supplier_involved', 'assigned_to', 'related_booking').all()
    if status_filter:
        complaints = complaints.filter(status=status_filter)
    if category_filter:
        complaints = complaints.filter(category=category_filter)

    suppliers = SupplierProfile.objects.select_related('party').filter(party__is_active=True).order_by('party__name')

    status_counts = {st[0]: TravelComplaint.objects.filter(status=st[0]).count() for st in TravelComplaint.STATUS_CHOICES}
    total_complaints = TravelComplaint.objects.count()
    open_count = TravelComplaint.objects.filter(status__in=['lodged', 'under_investigation', 'supplier_escalated']).count()
    resolved_count = TravelComplaint.objects.filter(status='resolved').count()

    context = {
        'complaints': complaints,
        'suppliers': suppliers,
        'categories': TravelComplaint.CATEGORY_CHOICES,
        'statuses': TravelComplaint.STATUS_CHOICES,
        'status_counts': status_counts,
        'total_complaints': total_complaints,
        'open_count': open_count,
        'resolved_count': resolved_count,
        'selected_status': status_filter,
        'selected_category': category_filter,
    }
    return render(request, 'crm/complaints_console.html', context)


@login_required
def complaint_lodge_view(request):
    """
    POST action to lodge a new complaint.
    """
    if request.method == 'POST':
        c_name = request.POST.get('complainant_name', '').strip()
        c_phone = request.POST.get('complainant_phone', '').strip()
        c_type = request.POST.get('complainant_type', 'b2c_traveler')
        category = request.POST.get('category', 'hotel_quality')
        severity = request.POST.get('severity', 'medium')
        desc = request.POST.get('issue_description', '').strip()
        supplier_id = request.POST.get('supplier_involved')
        supplier = SupplierProfile.objects.filter(id=supplier_id).first() if supplier_id else None

        if not c_name or not desc:
            messages.error(request, 'Please provide complainant name and issue details.')
            return redirect('crm:complaint_list')

        complaint = TravelComplaint.objects.create(
            complainant_name=c_name,
            complainant_phone=c_phone,
            complainant_type=c_type,
            category=category,
            severity=severity,
            issue_description=desc,
            supplier_involved=supplier,
            assigned_to=request.user,
            status='lodged'
        )

        messages.success(request, f"Complaint #{complaint.complaint_number} lodged successfully.")
        return redirect('crm:complaint_list')
    return redirect('crm:complaint_list')


@login_required
def complaint_resolve_api(request, complaint_id):
    """
    POST API to update status, append root-cause remarks, and record supplier rating penalty.
    """
    complaint = get_object_or_404(TravelComplaint, id=complaint_id)
    if request.method == 'POST':
        new_status = request.POST.get('status', complaint.status)
        remarks = request.POST.get('investigation_remarks', '').strip()
        resolution = request.POST.get('resolution_notes', '').strip()
        rating = request.POST.get('supplier_rating')

        complaint.status = new_status
        if remarks:
            complaint.investigation_remarks = remarks
        if resolution:
            complaint.resolution_notes = resolution
        if rating and rating.isdigit():
            complaint.supplier_rating_awarded = int(rating)
        if new_status in ['resolved', 'closed'] and not complaint.resolved_at:
            complaint.resolved_at = timezone.now()

        complaint.save()

        return JsonResponse({
            'status': 'success',
            'complaint_number': complaint.complaint_number,
            'new_status': complaint.get_status_display(),
            'resolved_at': complaint.resolved_at.strftime('%d-%b-%Y') if complaint.resolved_at else None
        })
    return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)


# ==============================================================================
# PHASE D: SUPPLIER PAYMENT REQUISITIONS & CLIENT PENDING PAYMENTS
# ==============================================================================

@login_required
def payment_requisition_console_view(request):
    """
    Accounts Payable Console:
    Supplier Payment Requisitions tracking Cost-to-Company vs Cost-to-Client.
    """
    requisitions = SupplierPaymentRequisition.objects.select_related('supplier', 'related_voucher', 'requested_by').all()
    suppliers = SupplierProfile.objects.select_related('party').filter(party__is_active=True).order_by('party__name')

    total_requested = requisitions.aggregate(tot=Sum('amount_requested'))['tot'] or Decimal('0')
    total_cost_to_company = requisitions.aggregate(tot=Sum('cost_to_company'))['tot'] or Decimal('0')
    total_cost_to_client = requisitions.aggregate(tot=Sum('cost_to_client'))['tot'] or Decimal('0')
    total_margin = total_cost_to_client - total_cost_to_company

    context = {
        'requisitions': requisitions,
        'suppliers': suppliers,
        'total_requested': total_requested,
        'total_cost_to_company': total_cost_to_company,
        'total_cost_to_client': total_cost_to_client,
        'total_margin': total_margin,
        'statuses': SupplierPaymentRequisition.STATUS_CHOICES,
        'payment_types': SupplierPaymentRequisition.PAYMENT_TYPES,
    }
    return render(request, 'crm/payment_requisitions.html', context)


@login_required
def payment_requisition_create_view(request):
    """
    POST action to create a new accounts payable requisition for a supplier.
    """
    if request.method == 'POST':
        supplier_id = request.POST.get('supplier')
        amount = Decimal(request.POST.get('amount_requested', '0'))
        ptype = request.POST.get('payment_type', 'full')
        cost_company = Decimal(request.POST.get('cost_to_company', str(amount)))
        cost_client = Decimal(request.POST.get('cost_to_client', '0'))
        inv_no = request.POST.get('invoice_number', '').strip()
        inv_file = request.FILES.get('invoice_attachment')
        notes = request.POST.get('notes', '').strip()

        supplier = get_object_or_404(SupplierProfile, id=supplier_id)

        req = SupplierPaymentRequisition.objects.create(
            supplier=supplier,
            amount_requested=amount,
            payment_type=ptype,
            cost_to_company=cost_company,
            cost_to_client=cost_client,
            invoice_number=inv_no,
            invoice_attachment=inv_file,
            bank_account_number=supplier.bank_account_number,
            ifsc_code=supplier.bank_ifsc,
            bank_name=supplier.bank_name,
            notes=notes,
            requested_by=request.user,
            status='pending_approval'
        )

        messages.success(request, f"Payment Requisition #{req.requisition_number} submitted for finance approval.")
        return redirect('crm:requisition_list')
    return redirect('crm:requisition_list')


@login_required
def payment_requisition_status_api(request, req_id):
    """
    POST API to approve, disburse, or reject a supplier payment requisition.
    """
    req = get_object_or_404(SupplierPaymentRequisition, id=req_id)
    if request.method == 'POST':
        action = request.POST.get('action')
        utr = request.POST.get('transaction_reference', '').strip()

        if action == 'approve':
            req.status = 'approved'
        elif action == 'disburse':
            req.status = 'disbursed'
            req.disbursed_at = timezone.now()
            if utr:
                req.transaction_reference = utr
        elif action == 'reject':
            req.status = 'rejected'
        req.save()

        return JsonResponse({
            'status': 'success',
            'requisition_number': req.requisition_number,
            'new_status': req.get_status_display(),
            'status_code': req.status
        })
    return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)


@login_required
def client_pending_payments_report_view(request):
    """
    Client Pending Payment Aging Report:
    Lists confirmed bookings with unpaid balances, organized by aging brackets
    (0-30 days, 31-60 days, 61-90 days, >90 days overdue).
    """
    now = timezone.now().date()
    from finance.models import Payment
    from operations.models import Booking

    confirmed_bookings = Booking.objects.filter(status__in=['confirmed', 'completed']).select_related('party')
    
    pending_items = []
    total_receivable = Decimal('0')
    bracket_current = Decimal('0')  # 0-30 days
    bracket_30_60 = Decimal('0')    # 31-60 days
    bracket_60_90 = Decimal('0')    # 61-90 days
    bracket_over_90 = Decimal('0')  # >90 days

    for b in confirmed_bookings:
        booking_price = b.quoted_price or Decimal('0.00')
        paid = Payment.objects.filter(booking=b, payment_type='customer_receipt').aggregate(tot=Sum('amount'))['tot'] or Decimal('0.00')
        balance = booking_price - paid
        if balance > Decimal('0'):
            days_overdue = (now - b.pickup_date).days if b.pickup_date and b.pickup_date < now else 0
            
            if days_overdue <= 30:
                aging_bracket = 'Current (0-30d)'
                bracket_current += balance
            elif days_overdue <= 60:
                aging_bracket = '31-60 Days'
                bracket_30_60 += balance
            elif days_overdue <= 90:
                aging_bracket = '61-90 Days'
                bracket_60_90 += balance
            else:
                aging_bracket = '>90 Days Critical'
                bracket_over_90 += balance

            total_receivable += balance
            pending_items.append({
                'booking': b,
                'client_name': b.guest_name or (b.party.name if b.party else "Client"),
                'client_phone': b.guest_phone or (b.party.phone if b.party else ""),
                'total_amount': b.quoted_price,
                'paid_amount': paid,
                'balance': balance,
                'pickup_date': b.pickup_date,
                'days_overdue': days_overdue,
                'aging_bracket': aging_bracket,
            })

    pending_items.sort(key=lambda x: x['balance'], reverse=True)

    context = {
        'pending_items': pending_items,
        'total_receivable': total_receivable,
        'bracket_current': bracket_current,
        'bracket_30_60': bracket_30_60,
        'bracket_60_90': bracket_60_90,
        'bracket_over_90': bracket_over_90,
        'total_overdue_accounts': len(pending_items),
    }
    return render(request, 'crm/client_pending_payments.html', context)


@login_required
def send_client_payment_reminder_api(request):
    """
    POST API to send an automated payment balance reminder to client via WhatsApp.
    """
    if request.method == 'POST':
        from operations.models import Booking
        from finance.models import Payment

        booking_id = request.POST.get('booking_id')
        booking = get_object_or_404(Booking, id=booking_id)

        phone = booking.guest_phone or (booking.party.phone if booking.party else None)
        if not phone:
            return JsonResponse({'status': 'error', 'message': 'No customer phone on file'}, status=400)

        booking_price = booking.quoted_price or Decimal('0.00')
        paid = Payment.objects.filter(booking=booking, payment_type='customer_receipt').aggregate(tot=Sum('amount'))['tot'] or Decimal('0.00')
        balance = booking_price - paid

        from integrations.communication import send_whatsapp_message
        msg = (
            f"Namaste {booking.guest_name}! 🙏\n\n"
            f"This is a gentle payment reminder from Sivagayathiri Travels regarding your tour booking *{booking.booking_number}* for *{booking.destination}*.\n\n"
            f"• *Total Booking Value:* ₹{booking_price:,.2f}\n"
            f"• *Amount Received:* ₹{paid:,.2f}\n"
            f"• *Outstanding Balance Due:* *₹{balance:,.2f}*\n\n"
            f"Please arrange settlement via UPI or bank transfer at your earliest convenience. Let us know if you need an updated payment receipt or invoice copy.\n\n"
            f"Thank you!"
        )

        result = send_whatsapp_message(phone, msg)
        return JsonResponse({
            'status': 'success',
            'booking_number': booking.booking_number,
            'balance': float(balance),
            'dispatched_to': phone
        })
    return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)


# ==============================================================================
# PHASE E: PROFORMA & TAX INVOICING SUITE
# ==============================================================================

@login_required
def dmc_invoice_console_view(request):
    """
    Console for Proforma and Tax Invoices with billing status, tax breakdowns,
    and client collections tracking.
    """
    invoices = DmcInvoice.objects.select_related('party', 'booking', 'quotation').order_by('-invoice_date', '-id')
    
    itype = request.GET.get('type')
    status_filter = request.GET.get('status')
    if itype:
        invoices = invoices.filter(invoice_type=itype)
    if status_filter:
        invoices = invoices.filter(status=status_filter)

    total_billed = invoices.aggregate(tot=Sum('total_invoice_amount'))['tot'] or Decimal('0.00')
    total_tax = invoices.aggregate(tot=Sum('total_tax_amount'))['tot'] or Decimal('0.00')
    total_received = invoices.aggregate(tot=Sum('paid_amount'))['tot'] or Decimal('0.00')
    total_balance = invoices.aggregate(tot=Sum('balance_due'))['tot'] or Decimal('0.00')

    parties = Party.objects.filter(is_active=True).order_by('name')
    from operations.models import Booking
    recent_bookings = Booking.objects.order_by('-booking_date')[:30]
    recent_quotes = Quotation.objects.order_by('-created_at')[:30]

    context = {
        'invoices': invoices,
        'selected_type': itype,
        'selected_status': status_filter,
        'total_billed': total_billed,
        'total_tax': total_tax,
        'total_received': total_received,
        'total_balance': total_balance,
        'invoice_count': invoices.count(),
        'parties': parties,
        'bookings': recent_bookings,
        'quotations': recent_quotes,
        'invoice_types': DmcInvoice.INVOICE_TYPES,
        'statuses': DmcInvoice.STATUS_CHOICES,
        'tax_regimes': DmcInvoice.TAX_REGIMES,
    }
    return render(request, 'crm/invoice_console.html', context)


@login_required
def dmc_invoice_create_view(request):
    """
    POST action to create Proforma or Tax Invoice from Quotation, Booking, or Party.
    """
    if request.method == 'POST':
        itype = request.POST.get('invoice_type', 'tax_invoice')
        party_id = request.POST.get('party')
        party = get_object_or_404(Party, id=party_id)
        
        booking_id = request.POST.get('booking')
        from operations.models import Booking
        booking = Booking.objects.filter(id=booking_id).first() if booking_id else None

        quote_id = request.POST.get('quotation')
        quotation = Quotation.objects.filter(id=quote_id).first() if quote_id else None

        b_name = request.POST.get('billing_name') or party.name
        b_addr = request.POST.get('billing_address') or (party.address or "")
        gstin = request.POST.get('client_gstin') or (party.gstin or "")
        pan = request.POST.get('client_pan') or ""
        pos = request.POST.get('place_of_supply', 'Tamil Nadu (33)')

        taxable = Decimal(request.POST.get('taxable_amount', '0.00'))
        tax_regime = request.POST.get('tax_regime', 'intra_state')
        gst_rate = Decimal(request.POST.get('gst_rate', '5.00'))
        paid = Decimal(request.POST.get('paid_amount', '0.00'))
        
        desc = request.POST.get('description_of_service', 'Tour Package & Ground Handling Operations')
        due_date_str = request.POST.get('due_date')
        due_date = None
        if due_date_str:
            try:
                due_date = datetime.date.fromisoformat(due_date_str)
            except Exception:
                due_date = None

        inv = DmcInvoice.objects.create(
            invoice_type=itype,
            party=party,
            booking=booking,
            quotation=quotation,
            billing_name=b_name,
            billing_address=b_addr,
            client_gstin=gstin,
            client_pan=pan,
            place_of_supply=pos,
            description_of_service=desc,
            taxable_amount=taxable,
            tax_regime=tax_regime,
            gst_rate=gst_rate,
            paid_amount=paid,
            due_date=due_date,
            created_by=request.user,
            status='issued'
        )

        messages.success(request, f"Invoice {inv.invoice_number} ({inv.get_invoice_type_display()}) generated successfully.")
        return redirect('crm:invoice_detail', invoice_id=inv.id)
    return redirect('crm:invoice_console')


@login_required
def dmc_invoice_detail_view(request, invoice_id):
    """
    Printable, official letterhead view with terms, QR, tax breakdowns,
    and download / print actions.
    """
    invoice = get_object_or_404(DmcInvoice.objects.select_related('party', 'booking', 'quotation'), id=invoice_id)
    context = {
        'inv': invoice,
        'today': timezone.now().date(),
    }
    return render(request, 'crm/invoice_detail.html', context)


@login_required
def dmc_invoice_dispatch_api(request, invoice_id):
    """
    POST API to send invoice link and summary to client via WhatsApp / Email.
    """
    if request.method == 'POST':
        invoice = get_object_or_404(DmcInvoice, id=invoice_id)
        phone = invoice.party.phone or (invoice.booking.guest_phone if invoice.booking else "")
        if not phone:
            return JsonResponse({'status': 'error', 'message': 'No customer phone on file'}, status=400)

        from integrations.communication import send_whatsapp_message
        host = request.get_host()
        url = f"http://{host}/crm/invoices/{invoice.id}/"
        msg = (
            f"Namaste {invoice.billing_name}! 🙏\n\n"
            f"Please find your *{invoice.get_invoice_type_display()}* *{invoice.invoice_number}* from Sivagayathiri Travels.\n\n"
            f"• *Invoice Date:* {invoice.invoice_date.strftime('%d-%b-%Y')}\n"
            f"• *Taxable Amount:* ₹{invoice.taxable_amount:,.2f}\n"
            f"• *GST ({invoice.gst_rate}%):* ₹{invoice.total_tax_amount:,.2f}\n"
            f"• *Total Amount:* *₹{invoice.total_invoice_amount:,.2f}*\n"
            f"• *Balance Due:* *₹{invoice.balance_due:,.2f}*\n\n"
            f"📄 View & Download your Tax Invoice:\n{url}\n\n"
            f"Thank you for traveling with us!"
        )

        send_whatsapp_message(phone, msg)
        invoice.status = 'issued'
        invoice.save(update_fields=['status'])

        return JsonResponse({
            'status': 'success',
            'invoice_number': invoice.invoice_number,
            'dispatched_to': phone
        })
    return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)


# ==============================================================================
# PHASE E: DMC COMPREHENSIVE REPORTS & ANALYTICS HUB
# ==============================================================================

@login_required
def dmc_reports_hub_view(request):
    """
    Unified DMC Executive Reports Center:
    - Quotation Performance & Win Rates
    - Customer & B2B Partner Volume
    - Destination & Description-wise Turnover
    - Outstanding Balances Breakdown
    - CSV Export capability
    """
    from operations.models import Booking
    from finance.models import Payment

    bookings = Booking.objects.select_related('party').all()
    quotations = Quotation.objects.all()

    # Destination-wise analytics
    dest_stats = {}
    for b in bookings:
        dest = b.destination or "Custom South Circuit"
        price = b.quoted_price or Decimal('0.00')
        if dest not in dest_stats:
            dest_stats[dest] = {'count': 0, 'revenue': Decimal('0.00'), 'pax': 0}
        dest_stats[dest]['count'] += 1
        dest_stats[dest]['revenue'] += price
        dest_stats[dest]['pax'] += (b.pax_count or 2)

    dest_list = [{'dest': k, **v} for k, v in dest_stats.items()]
    dest_list.sort(key=lambda x: x['revenue'], reverse=True)

    # Quotation metrics
    total_quotes = quotations.count()
    won_quotes = quotations.filter(status='converted').count()
    sent_quotes = quotations.filter(status__in=['sent', 'approved']).count()
    win_rate = round((won_quotes / total_quotes * 100), 1) if total_quotes > 0 else 0
    avg_quote_val = quotations.aggregate(avg=Avg('total_quoted_price'))['avg'] or Decimal('0.00')

    # Top customer accounts
    top_parties = Party.objects.annotate(
        booking_count=Count('bookings'),
        total_spent=Sum('bookings__quoted_price')
    ).filter(total_spent__gt=0).order_by('-total_spent')[:10]

    # Export to CSV action
    if request.GET.get('export') == 'destinations_csv':
        import csv
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="dmc_destination_report.csv"'
        writer = csv.writer(response)
        writer.writerow(['Destination', 'Total Bookings', 'Total Passengers', 'Gross Revenue (INR)'])
        for item in dest_list:
            writer.writerow([item['dest'], item['count'], item['pax'], float(item['revenue'])])
        return response

    context = {
        'dest_list': dest_list[:12],
        'total_quotes': total_quotes,
        'won_quotes': won_quotes,
        'sent_quotes': sent_quotes,
        'win_rate': win_rate,
        'avg_quote_val': avg_quote_val,
        'top_parties': top_parties,
        'total_bookings': bookings.count(),
        'total_turnover': bookings.aggregate(tot=Sum('quoted_price'))['tot'] or Decimal('0.00'),
    }
    return render(request, 'crm/reports_hub.html', context)

