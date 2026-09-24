from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages

from core.models import Vehicle
from maintenance.services import check_compliance_expiries, check_preventive_maintenance_due
from maintenance.models import ServiceReminder, DefectTicket


@login_required
def compliance_and_maintenance_dashboard(request):
    """
    Control room dashboard for RTO document compliance, upcoming expirations,
    preventive maintenance schedules, and tyre/battery wear alerts.
    """
    threshold = int(request.GET.get('threshold', 30))
    compliance_data = check_compliance_expiries(threshold_days=threshold)
    maintenance_data = check_preventive_maintenance_due()

    open_defect_tickets = DefectTicket.objects.filter(status__in=['open', 'in_progress']).select_related('vehicle').order_by('-date_reported')

    context = {
        'threshold': threshold,
        'compliance': compliance_data,
        'maintenance': maintenance_data,
        'defect_tickets': open_defect_tickets,
        'expired_count': len(compliance_data['expired']),
        'critical_count': len(compliance_data['critical']),
        'warning_count': len(compliance_data['warning']),
        'services_due_count': len(maintenance_data['services_due']),
        'assets_due_count': len(maintenance_data['assets_due']),
    }
    return render(request, 'maintenance/compliance_dashboard.html', context)


@login_required
def api_compliance_summary(request):
    """JSON API endpoint returning real-time compliance health & alert counts."""
    data = check_compliance_expiries(threshold_days=30)
    return JsonResponse({
        'compliance_rate': data['compliance_rate'],
        'expired_count': len(data['expired']),
        'critical_count': len(data['critical']),
        'warning_count': len(data['warning']),
        'total_vehicles': data['total_vehicles_scanned'],
    })


@login_required
def api_send_renewal_warnings(request):
    """Triggers on-demand broadcast of RTO document expiry warnings & oil/tyre maintenance alerts."""
    from maintenance.services import send_compliance_renewal_warnings_alert
    result = send_compliance_renewal_warnings_alert()
    return JsonResponse(result)

