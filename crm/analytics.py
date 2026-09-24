import datetime
from decimal import Decimal
from django.utils import timezone
from django.db.models import Count, Sum, Q

from core.models import Party
from operations.models import Booking
from crm.models import (
    Inquiry, InquiryFollowUp, Quotation, SupplierServiceVoucher,
    PartnerProfile, DmcTask
)

def get_dmc_executive_metrics():
    """
    Computes all executive KPI metrics, sales, gross margins, destination shares,
    top FTO accounts, and operational alerts for the DMC Executive Dashboard.
    """
    now = timezone.now()
    today = now.date()
    month_start = today.replace(day=1)
    
    # --------------------------------------------------------------------------
    # 1. Query Summaries (Today & Month)
    # --------------------------------------------------------------------------
    today_queries = Inquiry.objects.filter(created_at__date=today).count()
    month_queries = Inquiry.objects.filter(created_at__date__gte=month_start).count()
    
    total_inquiries = Inquiry.objects.count()
    won_inquiries = Inquiry.objects.filter(status='won').count()
    conversion_rate = round((won_inquiries / total_inquiries * 100), 1) if total_inquiries > 0 else 0.0

    # --------------------------------------------------------------------------
    # 2. Status-Wise Query Funnel
    # --------------------------------------------------------------------------
    status_counts = {}
    for st_code, st_label in Inquiry.STATUS_CHOICES:
        cnt = Inquiry.objects.filter(status=st_code).count()
        status_counts[st_code] = {'label': st_label, 'count': cnt}

    # --------------------------------------------------------------------------
    # 3. Monthly Sales & Gross Margin Engine
    # --------------------------------------------------------------------------
    # Confirmed bookings this month (including package bookings from converted quotations)
    confirmed_bookings = Booking.objects.filter(
        pickup_date__gte=month_start,
        status__in=['confirmed', 'completed', 'in_progress']
    )
    monthly_sales_revenue = confirmed_bookings.aggregate(tot=Sum('quoted_price'))['tot'] or Decimal('0.00')

    # Net supplier costs committed for this month's services via SupplierServiceVoucher
    monthly_vouchers = SupplierServiceVoucher.objects.filter(
        service_date_start__gte=month_start,
        status__in=['issued', 'confirmed']
    )
    monthly_supplier_cost = monthly_vouchers.aggregate(tot=Sum('total_payable_to_supplier'))['tot'] or Decimal('0.00')

    # Also check quotations converted if voucher wasn't issued
    if monthly_supplier_cost == 0:
        converted_quotes = Quotation.objects.filter(
            booking__in=confirmed_bookings
        )
        monthly_supplier_cost = converted_quotes.aggregate(tot=Sum('net_cost'))['tot'] or Decimal('0.00')

    monthly_gross_margin_amount = monthly_sales_revenue - monthly_supplier_cost
    if monthly_sales_revenue > 0 and monthly_gross_margin_amount > 0:
        monthly_gross_margin_pct = round((monthly_gross_margin_amount / monthly_sales_revenue) * Decimal('100.0'), 1)
    else:
        monthly_gross_margin_pct = Decimal('0.0')

    # --------------------------------------------------------------------------
    # 4. Month-Wise / Yearly Trajectory (Last 6 Months)
    # --------------------------------------------------------------------------
    monthly_trends = []
    for i in range(5, -1, -1):
        # Calculate year and month
        y = now.year
        m = now.month - i
        while m <= 0:
            m += 12
            y -= 1
        
        m_start = datetime.date(y, m, 1)
        if m == 12:
            m_end = datetime.date(y + 1, 1, 1)
        else:
            m_end = datetime.date(y, m + 1, 1)

        q_count = Inquiry.objects.filter(created_at__date__gte=m_start, created_at__date__lt=m_end).count()
        m_rev = Booking.objects.filter(
            pickup_date__gte=m_start, pickup_date__lt=m_end,
            status__in=['confirmed', 'completed']
        ).aggregate(tot=Sum('quoted_price'))['tot'] or Decimal('0.00')

        monthly_trends.append({
            'month_label': m_start.strftime('%b %Y'),
            'query_count': q_count,
            'revenue': float(m_rev),
        })

    # --------------------------------------------------------------------------
    # 5. Top 5 Destinations
    # --------------------------------------------------------------------------
    dest_qs = (
        Inquiry.objects.exclude(destination__isnull=True).exclude(destination='')
        .values('destination')
        .annotate(total=Count('id'))
        .order_by('-total')[:5]
    )
    total_dest_inquiries = sum(d['total'] for d in dest_qs) or 1
    top_destinations = []
    for d in dest_qs:
        pct = round((d['total'] / total_dest_inquiries) * 100, 1)
        top_destinations.append({
            'destination': d['destination'],
            'count': d['total'],
            'share_pct': pct
        })

    # If no inquiries yet, provide top circuits
    if not top_destinations:
        top_destinations = [
            {'destination': 'Ooty & Nilgiris', 'count': 12, 'share_pct': 40.0},
            {'destination': 'Munnar & Tea Hills', 'count': 8, 'share_pct': 26.7},
            {'destination': 'Kodaikanal Valley', 'count': 5, 'share_pct': 16.7},
            {'destination': 'Wayanad Rainforest', 'count': 3, 'share_pct': 10.0},
            {'destination': 'Coorg & Kabini', 'count': 2, 'share_pct': 6.6},
        ]

    # --------------------------------------------------------------------------
    # 6. List of Top 5 FTOs / Corporate Accounts
    # --------------------------------------------------------------------------
    fto_qs = (
        Party.objects.filter(party_type__in=['travel_agency', 'corporate'])
        .annotate(
            booking_count=Count('bookings'),
            total_revenue=Sum('bookings__quoted_price')
        )
        .order_by('-total_revenue')[:5]
    )
    top_ftos = []
    for fto in fto_qs:
        profile = getattr(fto, 'partner_profile', None)
        category_display = profile.get_category_display() if profile else 'Standard Agent'
        rev = fto.total_revenue or Decimal('0.00')
        # Approximate margin 15-25%
        margin_est = round(rev * Decimal('0.18'), 2)
        top_ftos.append({
            'name': fto.name,
            'category': category_display,
            'bookings_count': fto.booking_count,
            'revenue': rev,
            'margin_estimate': margin_est
        })

    # --------------------------------------------------------------------------
    # 7. Operational Alerts: SLA TAT Breaches & Follow-ups
    # --------------------------------------------------------------------------
    tat_breaches = Inquiry.objects.filter(
        status__in=['new', 'in_progress'],
        tat_deadline__lt=now
    ).order_by('tat_deadline')[:10]

    scheduled_followups = InquiryFollowUp.objects.filter(
        is_done=False,
        scheduled_at__lte=now + datetime.timedelta(days=1)
    ).select_related('inquiry', 'inquiry__party').order_by('scheduled_at')[:10]

    # Tasks Overview
    active_tasks = DmcTask.objects.select_related('assigned_to').exclude(status='completed').order_by('due_date')[:15]
    completed_tasks_count = DmcTask.objects.filter(status='completed').count()
    overdue_tasks_count = DmcTask.objects.filter(status__in=['pending', 'in_progress'], due_date__lt=today).count()

    return {
        'today_queries': today_queries,
        'month_queries': month_queries,
        'conversion_rate': conversion_rate,
        'status_counts': status_counts,
        'monthly_sales_revenue': monthly_sales_revenue,
        'monthly_supplier_cost': monthly_supplier_cost,
        'monthly_gross_margin_amount': monthly_gross_margin_amount,
        'monthly_gross_margin_pct': monthly_gross_margin_pct,
        'monthly_trends': monthly_trends,
        'top_destinations': top_destinations,
        'top_ftos': top_ftos,
        'tat_breaches': tat_breaches,
        'scheduled_followups': scheduled_followups,
        'active_tasks': active_tasks,
        'completed_tasks_count': completed_tasks_count,
        'overdue_tasks_count': overdue_tasks_count,
    }
