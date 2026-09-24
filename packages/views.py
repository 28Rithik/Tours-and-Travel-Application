from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Package, CollegeIVExpedition, TourPassengerManifest


@login_required
def generate_tour_quotation(request, package_id):
    """
    Renders the official 5-page tour proposal quotation format for Siva Gayathri Tours and Travels.
    Ready for viewing and printing/saving as PDF.
    """
    package = get_object_or_404(Package, pk=package_id)
    itinerary_days = package.itinerary_days.all().order_by('day_number')

    # Parse inclusions, exclusions, and terms line by line
    inclusions_list = [line.strip() for line in package.inclusions.splitlines() if line.strip()]
    exclusions_list = [line.strip() for line in package.exclusions.splitlines() if line.strip()]
    terms_list = [line.strip() for line in package.terms_and_conditions.splitlines() if line.strip()]

    # Parse contact persons
    contacts_list = [c.strip() for c in package.contact_persons_footer.split(',') if c.strip()]

    # Fetch vehicle tariffs (4 to 60 seats), devotional slots, international docs, addons, and seasonal rates
    vehicle_tariffs = package.vehicle_tariffs.all().order_by('package_rate')
    temple_slots = package.temple_slots.all()
    intl_documents = package.intl_documents.all()
    addons = package.addons.filter(is_active=True)
    seasonal_rates = package.seasonal_rates.filter(is_active=True)

    context = {
        'package': package,
        'itinerary_days': itinerary_days,
        'inclusions_list': inclusions_list,
        'exclusions_list': exclusions_list,
        'terms_list': terms_list,
        'contacts_list': contacts_list,
        'vehicle_tariffs': vehicle_tariffs,
        'temple_slots': temple_slots,
        'intl_documents': intl_documents,
        'addons': addons,
        'seasonal_rates': seasonal_rates,
        'travel_date': request.GET.get('travel_date', 'FEB 2025'),
        'is_modal_preview': request.GET.get('modal') == '1',
    }
    return render(request, 'packages/quotation_proposal.html', context)


@login_required
def preview_tour_quotation(request):
    """
    Renders live preview of a tour proposal quotation from either an existing package ID
    or dynamic draft parameters submitted from the package form.
    """
    package_id = request.GET.get('package_id')
    if package_id and package_id.isdigit():
        return generate_tour_quotation(request, int(package_id))

    from decimal import Decimal
    from .models import Package, ItineraryDay

    name = request.GET.get('name', '4 NIGHTS 5 DAYS KERALA COLLEGE IV EXPEDITION')
    destination = request.GET.get('destination', 'Kochi, Alleppey, Vagamon (Kerala)')
    category = request.GET.get('category', 'college_iv')
    try:
        nights = int(request.GET.get('nights', 4))
    except (ValueError, TypeError):
        nights = 4
    try:
        days = int(request.GET.get('days', 5))
    except (ValueError, TypeError):
        days = 5

    def parse_dec(val, default):
        try:
            return Decimal(str(val))
        except:
            return Decimal(str(default))

    base_price = parse_dec(request.GET.get('base_price'), 4800)
    price_with_food = parse_dec(request.GET.get('price_with_food'), 6850)
    price_without_food = parse_dec(request.GET.get('price_without_food'), 4750)

    inclusions_text = request.GET.get('inclusions', '').strip() or Package._meta.get_field('inclusions').default
    exclusions_text = request.GET.get('exclusions', '').strip() or Package._meta.get_field('exclusions').default
    terms_text = request.GET.get('terms', '').strip() or Package._meta.get_field('terms_and_conditions').default
    contacts_text = request.GET.get('contacts', '').strip() or Package._meta.get_field('contact_persons_footer').default

    mock_package = Package(
        name=name,
        destination=destination,
        category=category,
        duration_nights=nights,
        duration_days=days,
        base_price=base_price,
        price_with_food=price_with_food,
        price_without_food=price_without_food,
        meal_plan=request.GET.get('meal_plan', 'AP'),
        room_sharing_type=request.GET.get('room_sharing', '4_sharing'),
        inclusions=inclusions_text,
        exclusions=exclusions_text,
        terms_and_conditions=terms_text,
        contact_persons_footer=contacts_text,
        has_campfire_dj=True,
        has_jeep_safari=True,
    )

    inclusions_list = [l.strip() for l in inclusions_text.splitlines() if l.strip()]
    exclusions_list = [l.strip() for l in exclusions_text.splitlines() if l.strip()]
    terms_list = [l.strip() for l in terms_text.splitlines() if l.strip()]
    contacts_list = [c.strip() for c in contacts_text.split(',') if c.strip()]

    latest_pkg = Package.objects.filter(itinerary_days__isnull=False).distinct().first()
    itinerary_days = latest_pkg.itinerary_days.all().order_by('day_number') if latest_pkg else []
    vehicle_tariffs = latest_pkg.vehicle_tariffs.all().order_by('package_rate') if latest_pkg else []

    context = {
        'package': mock_package,
        'itinerary_days': itinerary_days,
        'inclusions_list': inclusions_list,
        'exclusions_list': exclusions_list,
        'terms_list': terms_list,
        'contacts_list': contacts_list,
        'vehicle_tariffs': vehicle_tariffs,
        'temple_slots': [],
        'intl_documents': [],
        'travel_date': request.GET.get('travel_date', 'CURRENT DATE'),
        'is_modal_preview': request.GET.get('modal') == '1',
    }
    return render(request, 'packages/quotation_proposal.html', context)



from django.http import JsonResponse
from core.models import Vehicle


@login_required
def api_package_info(request, package_id):
    """Returns metadata for dynamic form calculations (duration, price, category)."""
    try:
        package = Package.objects.get(pk=package_id)
        return JsonResponse({
            'success': True,
            'id': package.id,
            'name': package.name,
            'duration_days': package.duration_days,
            'duration_nights': package.duration_nights,
            'base_price': float(package.base_price or 0),
            'price_with_food': float(package.price_with_food or 0),
            'price_without_food': float(package.price_without_food or 0),
            'pricing_type': package.pricing_type,
            'category': package.category,
            'transit_mode': package.transit_mode,
            'flight_estimate_per_pax': float(package.flight_estimate_per_pax or 0),
            'train_estimate_per_pax': float(package.train_estimate_per_pax or 0),
        })
    except Package.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Package not found'}, status=404)


@login_required
def api_template_info(request, template_id):
    """Returns PackageTemplate metadata for 1-click package form auto-fill."""
    from .models import PackageTemplate
    try:
        tmpl = PackageTemplate.objects.get(pk=template_id)
        return JsonResponse({
            'success': True,
            'id': tmpl.id,
            'name': tmpl.name,
            'destination': tmpl.destination,
            'category': tmpl.category,
            'duration_days': tmpl.duration_days,
            'duration_nights': tmpl.duration_nights,
            'base_price': float(tmpl.base_price or 0),
            'description': tmpl.description or '',
        })
    except PackageTemplate.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Template not found'}, status=404)


@login_required
def api_vehicle_info(request, vehicle_id):
    """Returns seating capacity and default driver for dynamic fleet sync."""
    try:
        vehicle = Vehicle.objects.select_related('default_driver').get(pk=vehicle_id)
        return JsonResponse({
            'success': True,
            'id': vehicle.id,
            'registration_number': vehicle.registration_number,
            'seating_capacity': vehicle.seating_capacity or 4,
            'model': vehicle.model or '',
            'default_driver_id': vehicle.default_driver.id if vehicle.default_driver else None,
            'default_driver_name': vehicle.default_driver.name if vehicle.default_driver else '',
        })
    except Vehicle.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Vehicle not found'}, status=404)


@login_required
def generate_tour_voucher(request, package_id):
    """
    Renders an official confirmed Tour Service & Accommodation Voucher for Siva Gayathri Tours.
    Includes confirmed hotel blocks, transport specs, day-wise program highlights, and operational advisory.
    """
    package = get_object_or_404(Package, pk=package_id)
    itinerary_days = package.itinerary_days.all().order_by('day_number')
    hotel_allotments = package.hotel_allotments.all()
    addons = package.addons.filter(is_active=True)

    voucher_no = f"SGT-VCH-{package.id:04d}-2025"
    guest_name = request.GET.get('guest_name', 'Valued Corporate / Student Group')

    context = {
        'package': package,
        'voucher_no': voucher_no,
        'guest_name': guest_name,
        'itinerary_days': itinerary_days,
        'hotel_allotments': hotel_allotments,
        'addons': addons,
    }
    return render(request, 'packages/tour_service_voucher.html', context)


@login_required
def view_rooming_list(request, expedition_id):
    """
    Renders clean, printable Rooming List & Coach Seating Manifest for a College IV Expedition.
    Used by Tour Managers, Hotel Reception, and Coach Drivers.
    """
    expedition = get_object_or_404(CollegeIVExpedition, pk=expedition_id)
    passengers = TourPassengerManifest.objects.filter(iv_expedition=expedition).order_by('bus_assignment', 'seat_number', 'roll_number')

    context = {
        'expedition': expedition,
        'passengers': passengers,
    }
    return render(request, 'packages/manifest_rooming_list.html', context)
