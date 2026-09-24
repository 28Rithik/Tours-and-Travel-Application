from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import CustomerAccount
from documents.models import CustomerDocument
from operations.models import Booking
from packages.models import Package, PackageInventory
from payments_gateway.services import create_payment_link
from marketing.models import Coupon
from django.shortcuts import get_object_or_404

def portal_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            auth_login(request, user)
            return redirect('customer_portal:home')
        else:
            messages.error(request, 'Invalid username or password.')
    return render(request, 'customer_portal/login.html')

def portal_logout(request):
    auth_logout(request)
    return redirect('customer_portal:login')

@login_required(login_url='customer_portal:login')
def portal_home(request):
    return render(request, 'customer_portal/home.html')

@login_required(login_url='customer_portal:login')
def my_bookings(request):
    client = request.user.customer_profile.client_record
    bookings = Booking.objects.filter(party=client).order_by('-created_at')
    
    # Calculate balances for each booking
    for booking in bookings:
        total_paid = sum(payment.amount for payment in booking.payments.filter(status='captured'))
        booking.total_paid = total_paid
        booking.balance_due = max(float(booking.quoted_price or 0) - float(total_paid), 0)
        
        # Get invoice if available
        booking.invoice = booking.generated_statements.filter(status='paid').first()
        
    return render(request, 'customer_portal/bookings.html', {'bookings': bookings})

@login_required(login_url='customer_portal:login')
def portal_booking_detail(request, booking_id):
    client = request.user.customer_profile.client_record
    booking = get_object_or_404(Booking, id=booking_id, party=client)
    
    # Calculate balances
    total_paid = sum(payment.amount for payment in booking.payments.filter(status='captured'))
    balance_due = max(float(booking.quoted_price or 0) - float(total_paid), 0)
    
    invoice = booking.generated_statements.filter(status='paid').first()
    
    # Fetch itinerary if it's a package booking
    itinerary_days = []
    if booking.package:
        itinerary_days = booking.package.itinerary_days.all().order_by('day_number')
        
    return render(request, 'customer_portal/booking_detail.html', {
        'booking': booking,
        'total_paid': total_paid,
        'balance_due': balance_due,
        'invoice': invoice,
        'itinerary_days': itinerary_days
    })

@login_required(login_url='customer_portal:login')
def my_documents(request):
    try:
        account = request.user.customer_profile
        documents = account.client_record.documents.all()
    except Exception:
        documents = []
    return render(request, 'customer_portal/documents.html', {'documents': documents})

def package_list(request):
    packages = Package.objects.filter(is_active=True)
    return render(request, 'customer_portal/package_list.html', {'packages': packages})

def package_detail(request, package_id):
    package = get_object_or_404(Package, id=package_id)
    inventories = package.inventory.filter(status='open')
    return render(request, 'customer_portal/package_detail.html', {'package': package, 'inventories': inventories})

@login_required(login_url='customer_portal:login')
def checkout(request, inventory_id):
    inventory = get_object_or_404(PackageInventory, id=inventory_id)
    package = inventory.package
    
    if request.method == 'POST':
        client = request.user.customer_profile.client_record
        pax = request.POST.get('pax', 1)
        coupon_code = request.POST.get('coupon', '').strip()
        payment_plan = request.POST.get('payment_plan', 'full') # 'full' or 'advance'
        
        # Base price
        base_price = inventory.price_override or package.base_price
        total_price = float(base_price) * int(pax)
        
        # Apply coupon logic
        if coupon_code:
            try:
                coupon = Coupon.objects.get(code=coupon_code, is_active=True)
                if coupon.discount_percent:
                    total_price -= total_price * (float(coupon.discount_percent) / 100)
                elif coupon.flat_discount:
                    total_price -= float(coupon.flat_discount)
                coupon.used_count += 1
                coupon.save()
            except Coupon.DoesNotExist:
                messages.error(request, 'Invalid coupon code.')
                
        # Handle installments
        amount_to_pay = total_price
        if payment_plan == 'advance':
            amount_to_pay = total_price * 0.5 # 50% advance
        
        # Create pending booking
        from core.models import VehicleType
        import datetime
        from decimal import Decimal
        default_vtype = getattr(package, 'vehicle_type', None) or VehicleType.objects.first()
        client_phone = getattr(client, 'phone', '') or '9876543210'

        booking = Booking.objects.create(
            party=client,
            guest_name=client.name,
            guest_phone=client_phone,
            pickup_location='Self Arranged',
            destination=package.destination,
            pickup_date=inventory.departure_date,
            pickup_time=datetime.time(10, 0),
            journey_type='local',
            vehicle_type=default_vtype,
            pax_count=int(pax),
            billing_type='package',
            quoted_price=Decimal(str(total_price)),
            package=package,
            package_inventory=inventory,
            status='pending',
            gst_rate=Decimal('5.0')
        )
        
        if payment_plan == 'advance':
            from payments_gateway.models import InstallmentPlan
            InstallmentPlan.objects.create(
                booking=booking,
                total_amount=Decimal(str(total_price)),
                number_of_installments=2,
                is_active=True
            )
        
        # Handle Razorpay Link
        payment_response = create_payment_link(
            amount=amount_to_pay,
            reference_id=booking.booking_number,
            description=f"Booking for {package.name}",
            customer_name=client.name,
            customer_email=request.user.email,
            customer_contact=client_phone
        )
        
        # Redirect to payment URL
        if 'short_url' in payment_response:
            return redirect(payment_response['short_url'])
        else:
            messages.error(request, 'Payment link generation failed. Please try again later.')
            return redirect('customer_portal:home')

    upsells = package.upsells.all()
    return render(request, 'customer_portal/checkout.html', {'inventory': inventory, 'package': package, 'upsells': upsells})
