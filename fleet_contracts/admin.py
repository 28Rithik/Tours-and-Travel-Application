import datetime
from decimal import Decimal
from django.contrib import admin, messages
from unfold.admin import ModelAdmin, TabularInline
from django.http import HttpResponse, HttpResponseRedirect
from django.utils import timezone
from django.utils.html import format_html, escape
from django.utils.safestring import mark_safe
from django.db.models import Sum, Count, Q
from django.urls import path

from .models import (
    TransportContract,
    Route,
    RouteStop,
    Shift,
    ContractFleetRoster,
    ContractTripLog,
    ContractSLAPenalty,
    ContractMonthlyInvoice,
    NightSafetyEscortLog,
    CommuterManifest,
)


# ==============================================================================
# Inlines
# ==============================================================================

class RouteInline(TabularInline):
    model = Route
    extra = 0
    fields = ('name', 'origin', 'destination', 'distance_km', 'rate_override', 'is_active')


class ContractFleetRosterInline(TabularInline):
    model = ContractFleetRoster
    extra = 0
    autocomplete_fields = ['primary_vehicle', 'primary_driver', 'standby_vehicle']
    fields = ('primary_vehicle', 'primary_driver', 'standby_vehicle', 'route', 'shift', 'start_date', 'is_active')


class ContractSLAPenaltyInline(TabularInline):
    model = ContractSLAPenalty
    extra = 0
    fields = ('date', 'penalty_type', 'penalty_amount', 'waived', 'description')


# ==============================================================================
# Bulk Actions
# ==============================================================================

@admin.action(description="✅ Activate selected contracts")
def activate_contracts(modeladmin, request, queryset):
    updated = queryset.filter(status='draft').update(status='active')
    modeladmin.message_user(request, f"{updated} contract(s) activated.")


@admin.action(description="🛡️ Waive selected SLA Penalties")
def waive_sla_penalties(modeladmin, request, queryset):
    updated = queryset.filter(waived=False).update(waived=True, waiver_reason="Waived by Operations Management")
    modeladmin.message_user(request, f"{updated} SLA penalty record(s) waived.")


@admin.action(description="💰 Mark selected Invoices as Paid")
def mark_invoices_paid(modeladmin, request, queryset):
    updated = queryset.exclude(status='paid').update(
        status='paid',
        payment_reference=f"NEFT/BULK/{timezone.now().strftime('%Y%m%d%H%M')}"
    )
    modeladmin.message_user(request, f"{updated} contract invoice(s) marked as paid.")


# ==============================================================================
# Custom Filters
# ==============================================================================

class ContractHealthFilter(admin.SimpleListFilter):
    title = 'Contract Health'
    parameter_name = 'contract_health'

    def lookups(self, request, model_admin):
        return [
            ('expired', '🔴 Expired'),
            ('expiring_soon', '🟡 Expiring in 30 Days'),
            ('active_healthy', '🟢 Active & Healthy'),
        ]

    def queryset(self, request, queryset):
        today = timezone.now().date()
        soon = today + datetime.timedelta(days=30)
        if self.value() == 'expired':
            return queryset.filter(status='active', end_date__lt=today)
        elif self.value() == 'expiring_soon':
            return queryset.filter(status='active', end_date__gte=today, end_date__lte=soon)
        elif self.value() == 'active_healthy':
            return queryset.filter(status='active', end_date__gt=soon)
        return queryset


# ==============================================================================
# 1. Transport Contract Admin
# ==============================================================================

@admin.register(TransportContract)
class TransportContractAdmin(ModelAdmin):
    autocomplete_fields = ['customer']
    list_display = (
        'name', 'category_badge', 'customer_link',
        'duration_display', 'committed_fleet_badge',
        'billing_model_badge', 'sla_penalties_summary', 'status_badge', 'quick_actions'
    )
    list_filter = (ContractHealthFilter, 'contract_category', 'status', 'billing_model', 'fuel_escalation_enabled')
    search_fields = ('name', 'customer__name', 'contact_person', 'contact_phone')
    inlines = [RouteInline, ContractFleetRosterInline, ContractSLAPenaltyInline]
    date_hierarchy = 'start_date'
    actions = [activate_contracts]
    change_list_template = 'admin/fleet_contracts/transportcontract/change_list.html'
    readonly_fields = ('contract_health_snapshot', 'contract_unit_economics_card')

    class Media:
        css = {
            'all': ('fleet_contracts/css/transport_contract_admin.css',)
        }
        js = (
            'fleet_contracts/js/transport_contract_dynamic.js',
        )

    fieldsets = (
        ('Step 1: Classification & Client Organization', {
            'fields': (
                ('contract_category', 'status'),
                ('name', 'customer'),
                ('contact_person', 'contact_phone'),
                'contract_health_snapshot',
            )
        }),
        ('Step 2: Operational & Compliance Specifications', {
            'fields': ('category_specifications',),
            'description': 'Vertical-specific operational rules, statutory compliance checklists, and SLA parameters dynamically adapted to the selected contract category.'
        }),
        ('Step 3: Term Duration & Credit Schedule', {
            'fields': (
                ('start_date', 'end_date'),
                'payment_credit_days'
            )
        }),
        ('Step 4: Dedicated Fleet Commitment & Spares', {
            'fields': (
                ('committed_vehicle_count', 'standby_vehicle_count'),
            )
        }),
        ('Step 5: Billing Structure & Commercial Rates', {
            'fields': (
                ('billing_model', 'billing_cycle'),
                ('default_rate', 'gst_rate'),
                'contract_unit_economics_card',
            )
        }),
        ('Step 6: Fuel Escalation Clause & SLA Caps', {
            'fields': (
                ('fuel_escalation_enabled', 'base_diesel_price', 'fuel_revision_factor'),
                'sla_penalty_cap_pct'
            )
        }),
        ('Step 7: Special Terms & Contractual Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        })
    )

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        total_contracts = TransportContract.objects.count()
        active_contracts = TransportContract.objects.filter(status='active').count()
        committed_buses = TransportContract.objects.filter(status='active').aggregate(s=Sum('committed_vehicle_count'))['s'] or 0
        standby_buses = TransportContract.objects.filter(status='active').aggregate(s=Sum('standby_vehicle_count'))['s'] or 0
        
        # Estimate monthly revenue run rate
        monthly_rev = Decimal('0')
        for c in TransportContract.objects.filter(status='active'):
            if c.billing_model == 'fixed_monthly':
                monthly_rev += c.default_rate
            elif c.billing_model == 'per_trip':
                monthly_rev += (c.default_rate * c.committed_vehicle_count * 44) # approx 44 trips/mo per vehicle
            else: # per_km
                monthly_rev += (c.default_rate * c.committed_vehicle_count * 2200) # approx 2200 km/mo
        
        active_penalties = ContractSLAPenalty.objects.filter(waived=False)
        sla_ded = active_penalties.aggregate(s=Sum('penalty_amount'))['s'] or Decimal('0')
        pen_count = active_penalties.count()

        extra_context['kpi_metrics'] = {
            'total_contracts': total_contracts,
            'active_contracts': active_contracts,
            'committed_buses': committed_buses,
            'standby_buses': standby_buses,
            'monthly_revenue': f"{monthly_rev:,.0f}",
            'sla_deductions': f"{sla_ded:,.0f}",
            'penalty_count': pen_count,
        }
        extra_context['category_counts'] = {
            'total': total_contracts,
            'corporate': TransportContract.objects.filter(contract_category='corporate').count(),
            'school': TransportContract.objects.filter(contract_category='school').count(),
            'factory': TransportContract.objects.filter(contract_category='factory').count(),
            'hospital': TransportContract.objects.filter(contract_category='hospital').count(),
            'government': TransportContract.objects.filter(contract_category='government').count(),
        }
        return super().changelist_view(request, extra_context=extra_context)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<int:contract_id>/summary/', self.admin_site.admin_view(self.view_printable_summary), name='contract_printable_summary'),
            path('<int:contract_id>/fuel-revision/', self.admin_site.admin_view(self.view_fuel_revision_letter), name='contract_fuel_revision_letter'),
        ]
        return custom_urls + urls

    def view_printable_summary(self, request, contract_id):
        contract = self.get_object(request, contract_id)
        if not contract:
            messages.error(request, "Contract not found.")
            return HttpResponseRedirect('/admin/fleet_contracts/transportcontract/')

        roster_items = contract.roster_allocations.all()
        roster_rows = "".join([
            f"<tr><td style='padding: 8px; border-bottom: 1px solid #ddd;'>{r.primary_vehicle.registration_number} ({r.primary_vehicle.vehicle_type.name if r.primary_vehicle.vehicle_type else 'Bus'})</td>"
            f"<td style='padding: 8px; border-bottom: 1px solid #ddd;'>{r.primary_driver.name} ({r.primary_driver.phone})</td>"
            f"<td style='padding: 8px; border-bottom: 1px solid #ddd;'>{r.standby_vehicle.registration_number if r.standby_vehicle else 'None'}</td>"
            f"<td style='padding: 8px; border-bottom: 1px solid #ddd;'>{r.route.name if r.route else 'General'}</td></tr>"
            for r in roster_items
        ]) or "<tr><td colspan='4' style='padding: 8px;'>No roster allocations configured yet.</td></tr>"

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Service Agreement Summary - {escape(contract.name)}</title>
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 40px; color: #1e293b; }}
                h1 {{ color: #0284c7; margin-bottom: 4px; }}
                .badge {{ background: #0284c7; color: #fff; padding: 3px 8px; border-radius: 4px; font-size: 12px; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 13.5px; }}
                th {{ background: #f1f5f9; padding: 10px; text-align: left; border-bottom: 2px solid #cbd5e1; }}
                .section {{ margin-top: 30px; }}
                .btn-print {{ background: #059669; color: #fff; padding: 8px 16px; border: none; border-radius: 4px; cursor: pointer; }}
            </style>
        </head>
        <body>
            <div style="display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 2px solid #0284c7; padding-bottom: 16px;">
                <div>
                    <h1>SIVAGAYATHIRI TOURS &amp; TRAVELS</h1>
                    <div style="font-size: 14px; color: #64748b;">Institutional Transport Operations &amp; Corporate ETS Division</div>
                </div>
                <button class="btn-print" onclick="window.print()">🖨️ Print Agreement</button>
            </div>

            <div class="section">
                <h2>{escape(contract.name)}</h2>
                <p><strong>Client Organization:</strong> {escape(contract.customer.name)} | <strong>Category:</strong> <span class="badge">{contract.get_contract_category_display()}</span></p>
                <p><strong>Term Period:</strong> {contract.start_date.strftime('%d %B %Y')} to {contract.end_date.strftime('%d %B %Y')} ({ (contract.end_date - contract.start_date).days } days)</p>
                <p><strong>Committed Dedicated Fleet:</strong> {contract.committed_vehicle_count} Primary Buses + {contract.standby_vehicle_count} Standby Spares</p>
                <p><strong>Billing Model:</strong> {contract.get_billing_model_display()} @ ₹{contract.default_rate:,.2f} | <strong>Credit Period:</strong> {contract.payment_credit_days} days</p>
            </div>

            <div class="section">
                <h3>Dedicated Fleet &amp; Crew Allocations</h3>
                <table>
                    <thead>
                        <tr><th>Primary Vehicle</th><th>Assigned Chauffeur</th><th>Standby Spare</th><th>Assigned Route</th></tr>
                    </thead>
                    <tbody>
                        {roster_rows}
                    </tbody>
                </table>
            </div>

            {self.render_category_spec_html(contract)}

            <div class="section" style="margin-top: 50px; display: flex; justify-content: space-between;">
                <div>__________________________<br><strong>For Sivagayathiri Travels</strong><br>Authorized Operations Head</div>
                <div>__________________________<br><strong>For {escape(contract.customer.name[:35])}</strong><br>Authorized Transport Signatory</div>
            </div>
        </body>
        </html>
        """
        return HttpResponse(html)

    def render_category_spec_html(self, contract):
        specs = contract.category_specifications or {}
        cat = contract.contract_category

        if cat == 'corporate':
            title = "🏢 Annexure B: Corporate ETS Statutory & Night Escort Charter"
            escort_val = "Mandatory Escort Guard (20:00 - 06:00)" if specs.get('night_escort_mandatory', True) else "Not Mandatory"
            rows = [
                ("Female Commuter Night Escort Protocol", escort_val),
                ("Night Escort Timing Window", specs.get('escort_timing_window', '20:00 - 06:00')),
                ("Safe Drop Verification Protocol", specs.get('safe_drop_confirmation', 'SMS / OTP Confirmation')),
                ("Maximum In-Transit Duration SLA", f"{specs.get('max_in_transit_minutes', 60)} Minutes per Commuter"),
                ("Pickup Window Arrival Margin", f"±{specs.get('pickup_grace_minutes', 10)} Minutes"),
                ("Live GPS Telematics Portal", specs.get('gps_telematics_portal', 'https://telematics.sivagayathiritravels.com/live/client-omr')),
                ("Shift Roster Modification Cutoff", f"{specs.get('roster_cutoff_hours', 4)} Hours prior to shift start"),
                ("SOS In-Cabin Panic Button", "Verified & Operational" if specs.get('panic_button_installed', True) else "Not Fitted"),
            ]
        elif cat == 'school':
            title = "🎒 Annexure B: Institutional Student Safety & RTO Regulatory Charter"
            gov_val = f"Verified (Strictly Capped at {specs.get('speed_limit_kmh', 40)} km/h)" if specs.get('speed_governor_certified', True) else "Uncertified"
            rows = [
                ("RTO Speed Governor Certification", gov_val),
                ("Designated Female Bus Attendant", f"{specs.get('female_attendant_name', 'Kavitha M.')} ({specs.get('female_attendant_phone', '+91 98401 23456')})"),
                ("Child Safety Grills & Emergency Doors", "Inspected & Approved" if specs.get('child_safety_grills_verified', True) else "Pending Inspection"),
                ("Parent Real-Time SMS/WhatsApp Gateway", "Active & Integrated" if specs.get('parent_alerts_enabled', True) else "Disabled"),
                ("Summer Vacation Fee Exemption", specs.get('vacation_excluded_months', 'May (0-Fee Vacation Pause)')),
                ("RTO Yellow Board PSV & Fitness", "Active Valid FC" if specs.get('yellow_board_rto_verified', True) else "Pending"),
                ("First Aid Kit & Fire Extinguisher", "In-Cabin Verified" if specs.get('first_aid_fire_extinguisher', True) else "Pending"),
            ]
        elif cat == 'factory':
            title = "🏭 Annexure B: Industrial Plant Shift Timetable & Punctuality Charter"
            rows = [
                ("Shift A (Morning Shift) Timetable", specs.get('shift_a_timing', '06:00 AM - 02:00 PM')),
                ("Shift B (Evening Shift) Timetable", specs.get('shift_b_timing', '02:00 PM - 10:00 PM')),
                ("Shift C (Night Shift) Timetable", specs.get('shift_c_timing', '10:00 PM - 06:00 AM')),
                ("Factory Gate Siren Arrival Cutoff", f"Arrival {specs.get('gate_siren_buffer_minutes', 15)} Minutes prior to shift siren"),
                ("Assembly Line Downtime Penalty Rate", f"₹{specs.get('assembly_downtime_penalty_rate', 5000):,}/hour delay"),
                ("Industrial Corridor Fastag Route", specs.get('highway_toll_allocation', 'Sriperumbudur - Oragadam Industrial Corridor Fastag')),
                ("Minimum Vehicle Passenger Capacity", f"{specs.get('min_bus_seating_capacity', 40)} Seater Heavy Bus"),
                ("Worker Union Safety Charter", "Complied & Signed" if specs.get('worker_union_safety_charter', True) else "Pending"),
            ]
        elif cat == 'hospital':
            title = "🏥 Annexure B: Healthcare Critical Staff Transit & Hygiene Protocol"
            rows = [
                ("24/7 On-Call Emergency Recall SLA", f"≤ {specs.get('emergency_recall_minutes', 30)} Minutes response time"),
                ("Vehicle Cabin Fumigation Protocol", specs.get('cabin_sanitization_protocol', 'Daily post-shift fumigation with hospital-grade disinfectant')),
                ("100% Climate Control / AC Uptime SLA", "Guaranteed Zero Breakdown Tolerance" if specs.get('ac_reliability_sla', True) else "Standard"),
                ("Doctor & Surgeon Priority Dispatch", "Active Emergency Dispatch Priority" if specs.get('doctor_priority_dispatch', True) else "Standard"),
                ("Hospital Emergency Transport Desk", specs.get('hospital_emergency_desk', 'Apollo Main Casualty Desk: 044-28290200')),
                ("24/7 Dual-Crew Shift Rotation", "Implemented (Zero Driver Fatigue Policy)" if specs.get('dual_crew_driver_rotation', True) else "Single Driver"),
            ]
        elif cat == 'government':
            title = "🏛️ Annexure B: Government & PSU VIP Protocol & Movement Standards"
            rows = [
                ("Driver Police Clearance & PSV Badge", "Verified by Special Branch Police" if specs.get('police_verification_verified', True) else "Pending"),
                ("Chauffeur Uniform & Badge Protocol", "Crisp White Safari Suit & Name Badge Mandatory" if specs.get('uniform_protocol_mandatory', True) else "Standard"),
                ("Official Movement Order / Indent Ref", specs.get('govt_movement_order_ref', 'TN-POL-SEC-2026/088')),
                ("Kilometre Reconciliation Policy", "Office-to-Office Actual Mileage (No Dead KM)" if specs.get('km_billing_clause') == 'office_to_office' else "Garage-to-Garage Mileage with 10 KM Buffer"),
                ("PSU Settlement & TDS Credit Terms", specs.get('psu_tds_credit_terms', '60 Days Credit with Form 16A TDS Certificate')),
                ("Authorized Protocol Officer", specs.get('protocol_officer_name', 'Thiru. S. Ramanathan, Deputy Protocol Officer')),
            ]
        else:
            title = "📋 Annexure B: Contractual Operational Specifications"
            rows = [(k.replace('_', ' ').title(), str(v)) for k, v in specs.items()] or [("Standard Terms", "Standard commercial transport terms apply.")]

        spec_rows = "".join([
            f"<tr><td style='padding: 8px 12px; border-bottom: 1px solid #cbd5e1; width: 45%; font-weight: 600; color: #334155; background: #f8fafc;'>{escape(str(k))}</td>"
            f"<td style='padding: 8px 12px; border-bottom: 1px solid #cbd5e1; color: #0f172a;'>{escape(str(v))}</td></tr>"
            for k, v in rows
        ])

        return f"""
        <div class="section" style="margin-top: 30px; page-break-inside: avoid;">
            <h3 style="color: #0284c7; border-bottom: 2px solid #0284c7; padding-bottom: 6px;">{escape(title)}</h3>
            <table style="width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 13px;">
                <tbody>
                    {spec_rows}
                </tbody>
            </table>
        </div>
        """

    @admin.display(description='Contract Vertical')
    def category_badge(self, obj):
        colors = {
            'corporate': ('#3b82f6', 'fas fa-building', 'Corporate ETS'),
            'school': ('#f59e0b', 'fas fa-graduation-cap', 'School Bus'),
            'factory': ('#8b5cf6', 'fas fa-industry', 'Factory Shift'),
            'hospital': ('#10b981', 'fas fa-hospital', 'Hospital Staff'),
            'government': ('#059669', 'fas fa-landmark', 'Government'),
            'other': ('#64748b', 'fas fa-file-contract', 'Bulk Contract'),
        }
        color, icon, label = colors.get(obj.contract_category, ('#64748b', 'fas fa-file-contract', obj.contract_category))
        return format_html(
            '<span class="badge" style="background-color: {}; color: #fff; padding: 4px 8px; font-size: 11px;">'
            '<i class="{} mr-1"></i>{}'
            '</span>',
            color, icon, label
        )

    @admin.display(description='Client')
    def customer_link(self, obj):
        return format_html(
            '<a href="/admin/core_partners/client/{}/change/" style="color: #38bdf8; font-weight: 600; text-decoration: none;">'
            '<i class="fas fa-building mr-1"></i>{}'
            '</a>',
            obj.customer.id, obj.customer.name
        )

    @admin.display(description='Contract Period')
    def duration_display(self, obj):
        today = timezone.now().date()
        total_days = (obj.end_date - obj.start_date).days
        remaining = (obj.end_date - today).days
        if remaining < 0:
            return format_html(
                '<span style="color: #ef4444; font-weight: 600;">{} → {}<br><small>({} days, Expired)</small></span>',
                obj.start_date.strftime('%d/%m/%y'), obj.end_date.strftime('%d/%m/%y'), total_days
            )
        elif remaining <= 30:
            return format_html(
                '<span style="color: #f59e0b; font-weight: 600;">{} → {}<br><small>({} days, 🔥 {}d left)</small></span>',
                obj.start_date.strftime('%d/%m/%y'), obj.end_date.strftime('%d/%m/%y'), total_days, remaining
            )
        return format_html(
            '<span style="color: #f1f5f9;">{} → {}<br><small style="color: #94a3b8;">({} days, {} remaining)</small></span>',
            obj.start_date.strftime('%d/%m/%y'), obj.end_date.strftime('%d/%m/%y'), total_days, remaining
        )

    @admin.display(description='Dedicated Fleet')
    def committed_fleet_badge(self, obj):
        standby_str = f" + {obj.standby_vehicle_count} Spare" if obj.standby_vehicle_count else ""
        return format_html(
            '<span class="badge" style="background-color: #0f766e; color: #fff; padding: 4px 8px; font-size: 11px;">'
            '<i class="fas fa-bus mr-1"></i>{} Dedicated{}'
            '</span>',
            obj.committed_vehicle_count, standby_str
        )

    @admin.display(description='Billing Rate')
    def billing_model_badge(self, obj):
        styles = {
            'per_trip': ('#0ea5e9', 'Per Trip'),
            'per_km': ('#a855f7', 'Per KM'),
            'fixed_monthly': ('#10b981', 'Fixed Monthly'),
        }
        color, label = styles.get(obj.billing_model, ('#64748b', obj.billing_model))
        rate_str = f"₹{obj.default_rate:,.0f}"
        fuel_badge = '<span class="badge badge-warning ml-1" style="font-size: 9px; background: #d97706; color: #fff; padding: 2px 4px; border-radius: 3px;">Fuel Esc.</span>' if obj.fuel_escalation_enabled else ''
        return format_html(
            '<span class="badge" style="background-color: {}; color: #fff; padding: 3px 6px; font-size: 11px;">{}</span>'
            '<br><span style="color: #38bdf8; font-weight: 600; font-size: 12px;">{}</span>{}',
            color, label, rate_str, mark_safe(fuel_badge)
        )

    @admin.display(description='SLA Deductions')
    def sla_penalties_summary(self, obj):
        active_penalties = obj.sla_penalties.filter(waived=False)
        total_penalties = sum(p.penalty_amount for p in active_penalties)
        if total_penalties > 0:
            return format_html(
                '<span style="color: #ef4444; font-weight: 700; font-size: 12px;">'
                '<i class="fas fa-exclamation-circle mr-1"></i>₹{}'
                '</span>',
                f"{total_penalties:,.0f}"
            )
        return mark_safe('<span style="color: #10b981; font-size: 11px;"><i class="fas fa-check mr-1"></i>Zero Penalties</span>')

    @admin.display(description='Status')
    def status_badge(self, obj):
        today = timezone.now().date()
        styles = {
            'draft': ('#64748b', 'fas fa-pencil-alt', 'Draft'),
            'active': ('#10b981', 'fas fa-check-circle', 'Active'),
            'completed': ('#3b82f6', 'fas fa-flag-checkered', 'Completed'),
            'cancelled': ('#ef4444', 'fas fa-times-circle', 'Cancelled'),
        }
        color, icon, label = styles.get(obj.status, styles['draft'])
        if obj.status == 'active' and obj.end_date < today:
            color, icon, label = '#ef4444', 'fas fa-exclamation-triangle', 'Expired!'
        elif obj.status == 'active' and (obj.end_date - today).days <= 30:
            color, icon, label = '#f59e0b', 'fas fa-clock', f'Expiring ({(obj.end_date - today).days}d)'
        return format_html(
            '<span class="badge" style="background-color: {}; color: #fff; padding: 4px 8px;">'
            '<i class="{} mr-1"></i>{}'
            '</span>',
            color, icon, label
        )

    @admin.display(description='Quick Actions')
    def quick_actions(self, obj):
        roster_url = f"/admin/fleet_contracts/contractfleetroster/?contract__id__exact={obj.id}"
        inv_url = f"/admin/fleet_contracts/contractmonthlyinvoice/?contract__id__exact={obj.id}"
        summary_url = f"/admin/fleet_contracts/transportcontract/{obj.id}/summary/"
        fuel_btn = ""
        if obj.fuel_escalation_enabled:
            fuel_url = f"/admin/fleet_contracts/transportcontract/{obj.id}/fuel-revision/"
            fuel_btn = f'<a href="{fuel_url}" target="_blank" title="Print Fuel Escalation & Rate Revision Letter" style="background: #d97706; color: #fff; padding: 4px 7px; border-radius: 4px; font-size: 11px; text-decoration: none;"><i class="fas fa-gas-pump"></i></a>'

        return format_html(
            '<div style="display: flex; gap: 5px; align-items: center;">'
            '<a href="{}" title="View Live Fleet Roster" style="background: #0284c7; color: #fff; padding: 4px 7px; border-radius: 4px; font-size: 11px; text-decoration: none;">'
            '<i class="fas fa-bus"></i>'
            '</a>'
            '<a href="{}" title="View Monthly Invoices" style="background: #10b981; color: #fff; padding: 4px 7px; border-radius: 4px; font-size: 11px; text-decoration: none;">'
            '<i class="fas fa-file-invoice"></i>'
            '</a>'
            '<a href="{}" target="_blank" title="Print Agreement Summary" style="background: #6366f1; color: #fff; padding: 4px 7px; border-radius: 4px; font-size: 11px; text-decoration: none;">'
            '<i class="fas fa-print"></i>'
            '</a>'
            '{}'
            '</div>',
            roster_url, inv_url, summary_url, mark_safe(fuel_btn)
        )

    @admin.display(description='Contract Health & Operations Snapshot')
    def contract_health_snapshot(self, obj):
        if not obj.pk:
            return mark_safe('<span style="color: #94a3b8;">Available after contract is saved.</span>')
        routes_count = obj.routes.count()
        roster_count = obj.roster_allocations.filter(is_active=True).count()
        penalties_sum = sum(p.penalty_amount for p in obj.sla_penalties.filter(waived=False))
        
        return format_html(
            '<div style="background: #0f172a; border-left: 4px solid #38bdf8; padding: 14px 18px; border-radius: 6px; margin-top: 6px;">'
            '<div style="font-weight: 700; color: #f8fafc; font-size: 13px; margin-bottom: 6px;"><i class="fas fa-tachometer-alt mr-1" style="color: #38bdf8;"></i> Real-Time Contract Operations Snapshot</div>'
            '<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; font-size: 12.5px; color: #cbd5e1;">'
            '<div><strong>Operating Routes:</strong> <span style="color: #93c5fd;">{} Routes</span></div>'
            '<div><strong>Rostered Fleet:</strong> <span style="color: #34d399;">{} Active Crews</span></div>'
            '<div><strong>Committed Quota:</strong> {} Buses ({} Standby)</div>'
            '<div><strong>Active SLA Penalties:</strong> <span style="color: #f87171;">₹{}</span></div>'
            '</div>'
            '</div>',
            routes_count, roster_count, obj.committed_vehicle_count, obj.standby_vehicle_count, f"{penalties_sum:,.0f}"
        )

    @admin.display(description='Operational P&L & Gross Margin Economics')
    def contract_unit_economics_card(self, obj):
        if not obj.pk:
            return mark_safe('<span style="color: #94a3b8;">Available after saving contract parameters.</span>')
        
        if obj.billing_model == 'fixed_monthly':
            monthly_rev = obj.default_rate
        elif obj.billing_model == 'per_trip':
            monthly_rev = obj.default_rate * obj.committed_vehicle_count * Decimal('44')
        else:
            monthly_rev = obj.default_rate * obj.committed_vehicle_count * Decimal('2200')

        buses = max(1, obj.committed_vehicle_count)
        est_km = buses * 2200
        diesel_rate = obj.base_diesel_price if obj.base_diesel_price and obj.base_diesel_price > 0 else Decimal('92.50')
        fuel_cost = round((Decimal(str(est_km)) / Decimal('4.5')) * diesel_rate, 2)
        driver_cost = Decimal(str(buses)) * Decimal('24000.00')
        maintenance_cost = Decimal(str(est_km)) * Decimal('3.20')
        compliance_emi_cost = Decimal(str(buses)) * Decimal('16000.00')
        total_opex = fuel_cost + driver_cost + maintenance_cost + compliance_emi_cost
        net_margin = monthly_rev - total_opex
        margin_pct = (net_margin / monthly_rev * Decimal('100')) if monthly_rev > 0 else Decimal('0')

        if margin_pct >= 20:
            badge_html = f'<span class="badge" style="background: #059669; color: #fff; padding: 4px 10px; font-size: 12px;"><i class="fas fa-arrow-trend-up mr-1"></i>High Profitability ({margin_pct:.1f}% Margin)</span>'
            border_color = '#059669'
        elif margin_pct >= 10:
            badge_html = f'<span class="badge" style="background: #d97706; color: #fff; padding: 4px 10px; font-size: 12px;"><i class="fas fa-check mr-1"></i>Standard Profitability ({margin_pct:.1f}% Margin)</span>'
            border_color = '#d97706'
        else:
            badge_html = f'<span class="badge" style="background: #dc2626; color: #fff; padding: 4px 10px; font-size: 12px;"><i class="fas fa-exclamation-triangle mr-1"></i>Low / Sub-Par Margin ({margin_pct:.1f}% Margin)</span>'
            border_color = '#dc2626'

        fuel_letter_link = ""
        if obj.fuel_escalation_enabled:
            fuel_letter_link = f'<a href="/admin/fleet_contracts/transportcontract/{obj.id}/fuel-revision/" target="_blank" class="btn btn-sm btn-warning" style="background: #d97706; color: #fff; padding: 4px 10px; border-radius: 4px; text-decoration: none; font-size: 11px; font-weight: 600; margin-right: 8px;"><i class="fas fa-gas-pump mr-1"></i>Print Fuel Revision Addendum</a>'

        return format_html(
            '<div style="background: #0f172a; border-left: 4px solid {}; padding: 16px 20px; border-radius: 8px; margin-top: 10px; border: 1px solid #334155;">'
            '<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; border-bottom: 1px solid #334155; padding-bottom: 8px;">'
            '<div style="font-weight: 700; color: #f8fafc; font-size: 13.5px;"><i class="fas fa-chart-pie mr-1" style="color: #38bdf8;"></i> Institutional Contract Unit Economics &amp; P&amp;L Analysis</div>'
            '<div>{} {}</div>'
            '</div>'
            '<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 14px; font-size: 12.5px; color: #cbd5e1;">'
            '<div><strong>Monthly Revenue:</strong><br><span style="color: #38bdf8; font-size: 15px; font-weight: 700;">₹{}</span></div>'
            '<div><strong>Est. Fuel Cost:</strong><br><span style="color: #fbbf24; font-size: 14px; font-weight: 600;">₹{}</span> (₹{}/L)</div>'
            '<div><strong>Driver Wages:</strong><br><span style="color: #cbd5e1; font-size: 14px; font-weight: 600;">₹{}</span> ({} Crews)</div>'
            '<div><strong>Maintenance &amp; Tyres:</strong><br><span style="color: #cbd5e1; font-size: 14px; font-weight: 600;">₹{}</span> (₹3.20/km)</div>'
            '<div><strong>Fleet Amortization:</strong><br><span style="color: #cbd5e1; font-size: 14px; font-weight: 600;">₹{}</span> ({} Buses)</div>'
            '<div style="background: #1e293b; padding: 8px 12px; border-radius: 6px;"><strong>Net Operating Margin:</strong><br><span style="color: #34d399; font-size: 16px; font-weight: 800;">₹{}</span> / mo</div>'
            '</div>'
            '</div>',
            border_color, mark_safe(fuel_letter_link), mark_safe(badge_html),
            f"{monthly_rev:,.0f}", f"{fuel_cost:,.0f}", diesel_rate, f"{driver_cost:,.0f}", buses, f"{maintenance_cost:,.0f}", f"{compliance_emi_cost:,.0f}", buses, f"{net_margin:,.0f}"
        )

    def view_fuel_revision_letter(self, request, contract_id):
        contract = self.get_object(request, contract_id)
        if not contract:
            messages.error(request, "Contract not found.")
            return HttpResponseRedirect('/admin/fleet_contracts/transportcontract/')

        base_diesel = contract.base_diesel_price or Decimal('92.50')
        current_market_diesel = Decimal('97.80')
        diff = current_market_diesel - base_diesel
        revision_factor = contract.fuel_revision_factor or Decimal('0.25')
        rate_diff = round(diff * revision_factor, 2)
        revised_rate = contract.default_rate + rate_diff

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Fuel Price Escalation Notice - {escape(contract.name)}</title>
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 40px; color: #1e293b; line-height: 1.6; }}
                h1 {{ color: #0284c7; margin: 0; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 16px; margin-bottom: 20px; font-size: 13.5px; }}
                th {{ background: #f1f5f9; padding: 10px; text-align: left; border-bottom: 2px solid #cbd5e1; }}
                td {{ padding: 10px; border-bottom: 1px solid #e2e8f0; }}
                .highlight-box {{ background: #f0fdf4; border-left: 4px solid #16a34a; padding: 16px; margin: 20px 0; border-radius: 4px; }}
            </style>
        </head>
        <body>
            <div style="display: flex; justify-content: space-between; border-bottom: 2px solid #0284c7; padding-bottom: 16px;">
                <div>
                    <h1>SIVAGAYATHIRI TOURS &amp; TRAVELS</h1>
                    <div style="font-size: 13px; color: #64748b;">Fleet Management &amp; Institutional Transport Division</div>
                    <div style="font-size: 13px; color: #64748b;">GSTIN: 33AAAFS1234F1Z5 • State: Tamil Nadu (33)</div>
                </div>
                <div style="text-align: right;">
                    <div style="font-size: 12px; color: #64748b;">REF: STT/COMM/FUEL-REV/{timezone.now().strftime('%Y%m')}/{contract.id:04d}</div>
                    <div style="font-size: 13px; font-weight: bold; color: #0f172a;">Date: {timezone.now().strftime('%d %B %Y')}</div>
                    <button onclick="window.print()" style="margin-top: 8px; background: #059669; color: #fff; padding: 6px 14px; border: none; border-radius: 4px; cursor: pointer;">🖨️ Print Addendum Notice</button>
                </div>
            </div>

            <div style="margin-top: 24px;">
                <strong>To:</strong><br>
                The Head of Administration &amp; Transport Logistics<br>
                <strong>{escape(contract.customer.name)}</strong><br>
                {escape(contract.customer.address or 'Chennai, Tamil Nadu')}<br>
                Attention: {escape(contract.contact_person or 'Procurement & Vendor Management Desk')}
            </div>

            <div style="margin-top: 20px; font-weight: bold; color: #0f172a; text-decoration: underline;">
                SUBJECT: Formal Tariff Revision Notice Pursuant to Fuel Escalation Clause in Master Service Agreement #{contract.id} ({escape(contract.name)})
            </div>

            <p>Dear Sir / Madam,</p>
            <p>
                In accordance with <strong>Clause 6 (Fuel Price Escalation &amp; De-escalation Mechanism)</strong> of our executed Institutional Transport Service Agreement dated {contract.start_date.strftime('%d/%m/%Y')}, commercial tariffs are subject to mutual adjustment linked to statutory diesel price variations in Chennai.
            </p>

            <table>
                <thead>
                    <tr><th>Parameter Description</th><th>Agreement Baseline</th><th>Current Statutory Rate</th><th>Variance (INR)</th></tr>
                </thead>
                <tbody>
                    <tr><td>Statutory Retail Diesel Price (IOCL/HPCL Chennai)</td><td>₹{base_diesel:,.2f} / Litre</td><td>₹{current_market_diesel:,.2f} / Litre</td><td style="color: #dc2626; font-weight: bold;">+ ₹{diff:,.2f} / L</td></tr>
                    <tr><td>Agreed Escalation Multiplier / Factor</td><td colspan="2">₹{revision_factor:,.4f} per ₹1.00 diesel change</td><td>—</td></tr>
                    <tr><td>Applicable Surcharge Adjustment</td><td colspan="2">Formula: (Current Diesel - Base Diesel) &times; Factor</td><td style="color: #16a34a; font-weight: bold;">+ ₹{rate_diff:,.2f}</td></tr>
                </tbody>
            </table>

            <div class="highlight-box">
                <strong style="color: #166534; font-size: 15px;">Revised Billing Tariff Applicable from Next Billing Cycle:</strong><br>
                • Prior Contract Base Rate: <strong>₹{contract.default_rate:,.2f} ({contract.get_billing_model_display()})</strong><br>
                • Revised Enforceable Rate: <strong style="color: #15803d; font-size: 17px;">₹{revised_rate:,.2f} ({contract.get_billing_model_display()})</strong><br>
                • Effective Date: <strong>1st of {timezone.now().strftime('%B %Y')}</strong>
            </div>

            <p>
                Please countersign and return a duplicate copy of this notification or acknowledge via return corporate email to confirm your billing records. All other terms, safety SLAs, and committed fleet quotas remain unchanged.
            </p>

            <div style="margin-top: 50px; display: flex; justify-content: space-between;">
                <div>
                    <strong>For Sivagayathiri Tours &amp; Travels</strong><br><br><br>
                    <span>Authorized Commercial Signatory</span><br>
                    <small style="color: #64748b;">General Manager - Institutional Contracts</small>
                </div>
                <div style="text-align: right;">
                    <strong>Acknowledged &amp; Confirmed For {escape(contract.customer.name)}</strong><br><br><br>
                    <span>Authorized Client Representative &amp; Stamp</span>
                </div>
            </div>
        </body>
        </html>
        """
        return HttpResponse(html)


# ==============================================================================
# 2. Contract Fleet Roster Admin
# ==============================================================================

@admin.register(ContractFleetRoster)
class ContractFleetRosterAdmin(ModelAdmin):
    autocomplete_fields = ['contract', 'primary_vehicle', 'primary_driver', 'standby_vehicle', 'route', 'shift']
    list_display = (
        'contract_link', 'primary_vehicle_badge', 'driver_badge',
        'standby_vehicle_badge', 'route_shift_display', 'date_range_display', 'is_active_badge', 'hot_swap_button'
    )
    list_filter = ('is_active', 'contract__contract_category', 'primary_vehicle__vehicle_type')
    search_fields = ('contract__name', 'primary_vehicle__registration_number', 'primary_driver__name', 'primary_driver__phone')
    readonly_fields = ('crew_compliance_snapshot',)

    fieldsets = (
        ('Step 1: Institutional Contract & Route Duty', {
            'fields': (
                ('contract', 'route', 'shift'),
            )
        }),
        ('Step 2: Dedicated Primary Crew Allocation', {
            'fields': (
                ('primary_vehicle', 'primary_driver'),
                'crew_compliance_snapshot',
            )
        }),
        ('Step 3: Standby Breakdown Backup Cover', {
            'fields': (
                'standby_vehicle',
            ),
            'description': 'Designated replacement bus stationed at the depot/campus for breakdown contingencies.'
        }),
        ('Step 4: Roster Period & Operational Status', {
            'fields': (
                ('start_date', 'end_date', 'is_active'),
                'notes',
            )
        }),
    )

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<int:roster_id>/hot-swap/', self.admin_site.admin_view(self.hot_swap_view), name='fleet_roster_hot_swap'),
        ]
        return custom_urls + urls

    def hot_swap_view(self, request, roster_id):
        roster = self.get_object(request, roster_id)
        if not roster:
            messages.error(request, "Roster record not found.")
            return HttpResponseRedirect('/admin/fleet_contracts/contractfleetroster/')
        if not roster.standby_vehicle:
            messages.warning(request, f"Cannot hot-swap: No standby vehicle allocated to roster #{roster.id} ({roster.contract.name}).")
            return HttpResponseRedirect('/admin/fleet_contracts/contractfleetroster/')
        
        old_primary = roster.primary_vehicle
        new_primary = roster.standby_vehicle
        roster.primary_vehicle = new_primary
        roster.standby_vehicle = old_primary
        timestamp_str = timezone.now().strftime('%d/%m/%Y %H:%M')
        swap_note = f"[⚡ Hot-Swap {timestamp_str}] Dispatched Standby {new_primary.registration_number} as Primary; moved {old_primary.registration_number} to Standby."
        roster.notes = f"{swap_note}\n{roster.notes}" if roster.notes else swap_note
        roster.save(update_fields=['primary_vehicle', 'standby_vehicle', 'notes'])
        messages.success(
            request,
            f"⚡ Hot-Swap Successful! {new_primary.registration_number} is now Primary vehicle. {old_primary.registration_number} moved to Standby for {roster.contract.name}."
        )
        return HttpResponseRedirect('/admin/fleet_contracts/contractfleetroster/')

    @admin.display(description='Contract')
    def contract_link(self, obj):
        return format_html(
            '<a href="/admin/fleet_contracts/transportcontract/{}/change/" style="color: #38bdf8; text-decoration: none; font-weight: 600;">'
            '<i class="fas fa-building mr-1"></i>{}'
            '</a>',
            obj.contract.id, obj.contract.name
        )

    @admin.display(description='Primary Vehicle')
    def primary_vehicle_badge(self, obj):
        vt = obj.primary_vehicle.vehicle_type.name if obj.primary_vehicle and obj.primary_vehicle.vehicle_type else 'Bus'
        cap = f"({obj.primary_vehicle.vehicle_type.seating_capacity} seats)" if obj.primary_vehicle and obj.primary_vehicle.vehicle_type and obj.primary_vehicle.vehicle_type.seating_capacity else ""
        return format_html(
            '<span class="badge" style="background-color: #0369a1; color: #fff; padding: 4px 8px; font-size: 11px;">'
            '<i class="fas fa-bus mr-1"></i>{}'
            '</span>'
            '<br><small style="color: #94a3b8; font-size: 11px;">{} {}</small>',
            obj.primary_vehicle.registration_number, vt, cap
        )

    @admin.display(description='Dedicated Driver')
    def driver_badge(self, obj):
        phone_str = f"<br><small style='color: #94a3b8;'><i class='fas fa-phone mr-1'></i>{obj.primary_driver.phone}</small>" if obj.primary_driver.phone else ""
        return format_html(
            '<span style="color: #93c5fd; font-weight: 600;"><i class="fas fa-user-tie mr-1"></i>{}</span>{}',
            obj.primary_driver.name, mark_safe(phone_str)
        )

    @admin.display(description='Standby Backup')
    def standby_vehicle_badge(self, obj):
        if obj.standby_vehicle:
            return format_html(
                '<span class="badge" style="background-color: #0f766e; color: #fff; padding: 4px 7px; font-size: 11px;">'
                '<i class="fas fa-shield-alt mr-1"></i>{}'
                '</span>',
                obj.standby_vehicle.registration_number
            )
        return mark_safe('<span class="badge" style="background: #334155; color: #f59e0b; padding: 3px 6px;">⚠️ No Standby</span>')

    @admin.display(description='Route & Shift')
    def route_shift_display(self, obj):
        route_name = obj.route.name if obj.route else 'General Assignment'
        shift_str = ""
        if obj.shift:
            dir_icon = '⬆️' if obj.shift.direction == 'pickup' else '⬇️'
            shift_str = f"<br><small style='color: #38bdf8;'>{dir_icon} {obj.shift.shift_name} ({obj.shift.timing.strftime('%I:%M %p')})</small>"
        return format_html('<span style="color: #cbd5e1; font-size: 12px; font-weight: 500;">{}</span>{}', route_name, mark_safe(shift_str))

    @admin.display(description='Effective Period')
    def date_range_display(self, obj):
        end_str = obj.end_date.strftime('%d/%m/%y') if obj.end_date else 'Ongoing'
        return format_html('<span style="color: #94a3b8; font-size: 12px;">{} → {}</span>', obj.start_date.strftime('%d/%m/%y'), end_str)

    @admin.display(description='Status')
    def is_active_badge(self, obj):
        if obj.is_active:
            return mark_safe('<span class="badge" style="background-color: #059669; color: #fff; padding: 4px 8px;">Active Duty</span>')
        return mark_safe('<span class="badge" style="background-color: #64748b; color: #fff; padding: 4px 8px;">Inactive</span>')

    @admin.display(description='Quick Actions')
    def hot_swap_button(self, obj):
        if obj.standby_vehicle and obj.is_active:
            url = f"/admin/fleet_contracts/contractfleetroster/{obj.id}/hot-swap/"
            return format_html(
                '<a href="{}" onclick="return confirm(\'Are you sure you want to hot-swap standby vehicle {} to primary duty?\');" '
                'style="background: #0284c7; color: #fff; padding: 4px 8px; border-radius: 4px; font-size: 11px; text-decoration: none; font-weight: 600; display: inline-block;">'
                '<i class="fas fa-exchange-alt mr-1"></i>Hot-Swap'
                '</a>',
                url, obj.standby_vehicle.registration_number
            )
        return mark_safe('<span style="color: #64748b; font-size: 11px;">—</span>')

    @admin.display(description='Driver & Vehicle Compliance Snapshot')
    def crew_compliance_snapshot(self, obj):
        if not obj.primary_vehicle or not obj.primary_driver:
            return mark_safe('<span style="color: #94a3b8;">Select vehicle and driver to view compliance.</span>')
        
        v = obj.primary_vehicle
        d = obj.primary_driver
        today = timezone.now().date()

        def _format_compliance(date_val, label):
            if not date_val:
                return f'<span style="color: #94a3b8;">{label}: Not Set</span>'
            days = (date_val - today).days
            if days < 0:
                return f'<span style="color: #f87171; font-weight: bold;">{label}: EXPIRED ({date_val.strftime("%d/%m/%Y")})</span>'
            elif days <= 30:
                return f'<span style="color: #fbbf24; font-weight: bold;">{label}: Expiring in {days}d ({date_val.strftime("%d/%m/%Y")})</span>'
            return f'<span style="color: #34d399;">{label}: Valid ({date_val.strftime("%d/%m/%Y")} - {days}d left)</span>'

        v_fc_html = _format_compliance(v.fc_expiry, 'Fitness Cert (FC)')
        v_ins_html = _format_compliance(v.insurance_expiry, 'Insurance')
        v_tax_html = _format_compliance(v.tax_expiry, 'Road Tax')
        v_prm_html = _format_compliance(v.permit_expiry, 'Permit')

        d_lic_tr = _format_compliance(d.license_validity_tr, 'License (Transport TR)')
        d_badge = f'<span style="color: #93c5fd;">Badge: {d.badge_number or "Verified Commercial"}</span>'

        return format_html(
            '<div style="background: #1e293b; padding: 14px 18px; border-radius: 8px; font-size: 12.5px; color: #cbd5e1; border: 1px solid #334155;">'
            '<strong style="color: #f8fafc; font-size: 13px;"><i class="fas fa-clipboard-check mr-1" style="color: #10b981;"></i> Pre-Flight Statutory Compliance Gate:</strong><br>'
            '<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 8px;">'
            '<div><strong>Bus {} Documents:</strong><br>• {}<br>• {}<br>• {}<br>• {}</div>'
            '<div><strong>Driver {} Credentials:</strong><br>• {}<br>• {}<br>• <span style="color: #34d399;">Police Verification: Complete</span></div>'
            '</div>'
            '</div>',
            v.registration_number, mark_safe(v_fc_html), mark_safe(v_ins_html), mark_safe(v_tax_html), mark_safe(v_prm_html),
            d.name, mark_safe(d_lic_tr), mark_safe(d_badge)
        )


# ==============================================================================
# 3. Contract SLA Penalty Admin
# ==============================================================================

@admin.register(ContractSLAPenalty)
class ContractSLAPenaltyAdmin(ModelAdmin):
    autocomplete_fields = ['contract', 'trip_log', 'applied_to_invoice']
    list_display = (
        'contract_link', 'date', 'penalty_type_badge', 'severity_badge',
        'amount_display', 'waiver_status_badge', 'trip_link', 'invoice_link', 'quick_waiver_toggle'
    )
    list_filter = ('penalty_type', 'waived', 'contract__contract_category', 'date')
    search_fields = ('contract__name', 'description', 'waiver_reason')
    actions = [waive_sla_penalties]
    change_list_template = 'admin/fleet_contracts/contractslapenalty/change_list.html'
    readonly_fields = ('trip_incident_inspection',)

    fieldsets = (
        ('Step 1: Incident Particulars & Infraction', {
            'fields': (
                ('contract', 'date'),
                ('penalty_type', 'trip_log'),
                'description',
                'trip_incident_inspection',
            )
        }),
        ('Step 2: Financial Deduction Details', {
            'fields': (
                'penalty_amount',
            )
        }),
        ('Step 3: Dispute & Operational Waiver Resolution', {
            'fields': (
                ('waived', 'waiver_reason'),
            ),
            'description': 'Check waived if client operations committee approved justification (e.g. VIP convoy route diversions).'
        }),
        ('Step 4: Monthly Invoice Settlement', {
            'fields': (
                'applied_to_invoice',
            )
        }),
    )

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        deductible_qs = ContractSLAPenalty.objects.filter(waived=False)
        waived_qs = ContractSLAPenalty.objects.filter(waived=True)
        
        deductible_amt = deductible_qs.aggregate(s=Sum('penalty_amount'))['s'] or Decimal('0')
        waived_amt = waived_qs.aggregate(s=Sum('penalty_amount'))['s'] or Decimal('0')
        delay_count = ContractSLAPenalty.objects.filter(penalty_type='late_arrival').count()
        safety_count = ContractSLAPenalty.objects.filter(penalty_type__in=['ac_failure', 'unauthorized_driver', 'escort_missing', 'speed_violation', 'breakdown_delay']).count()

        extra_context['sla_metrics'] = {
            'deductible_amount': f"{deductible_amt:,.0f}",
            'deductible_count': deductible_qs.count(),
            'waived_amount': f"{waived_amt:,.0f}",
            'waived_count': waived_qs.count(),
            'delay_count': delay_count,
            'safety_count': safety_count,
        }
        return super().changelist_view(request, extra_context=extra_context)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<int:penalty_id>/toggle-waiver/', self.admin_site.admin_view(self.toggle_waiver), name='penalty_toggle_waiver'),
            path('auto-ingest/', self.admin_site.admin_view(self.auto_ingest_penalties_view), name='contract_penalty_auto_ingest'),
        ]
        return custom_urls + urls

    def auto_ingest_penalties_view(self, request):
        from django.db.models import Q
        trips = ContractTripLog.objects.filter(
            Q(status__in=['delayed', 'breakdown']) | Q(delay_minutes__gt=15),
            sla_penalties__isnull=True
        ).select_related('shift__route__contract', 'vehicle', 'driver')

        ingested_count = 0
        total_pen_amt = Decimal('0')

        for trip in trips:
            contract = trip.shift.route.contract
            if trip.status == 'breakdown':
                p_type = 'breakdown_delay'
                amount = Decimal('3500.00')
                desc = f"Vehicle breakdown during service on route '{trip.shift.route.name}'. Vehicle: {trip.vehicle.registration_number if trip.vehicle else 'N/A'}."
            else:
                p_type = 'late_arrival'
                if trip.delay_minutes > 30:
                    amount = Decimal('2000.00')
                else:
                    amount = Decimal('1000.00')
                desc = f"Automated ingestion: Logged delay of {trip.delay_minutes} mins on route '{trip.shift.route.name}'. Driver: {trip.driver.name if trip.driver else 'Unassigned'}."

            ContractSLAPenalty.objects.create(
                contract=contract,
                trip_log=trip,
                date=trip.date,
                penalty_type=p_type,
                penalty_amount=amount,
                description=desc,
                waived=False
            )
            ingested_count += 1
            total_pen_amt += amount

        if ingested_count > 0:
            messages.success(
                request,
                f"⚡ Auto-Ingestion Complete! Ingested {ingested_count} SLA penalty drafts totaling ₹{total_pen_amt:,.2f} from completed delayed trip logs."
            )
        else:
            messages.info(request, "No unpenalized delayed trips or breakdowns found to ingest.")
        return HttpResponseRedirect('/admin/fleet_contracts/contractslapenalty/')

    def toggle_waiver(self, request, penalty_id):
        penalty = self.get_object(request, penalty_id)
        if penalty:
            penalty.waived = not penalty.waived
            if penalty.waived and not penalty.waiver_reason:
                penalty.waiver_reason = "Waived via 1-click Quick Toggle by Operations Supervisor"
            penalty.save(update_fields=['waived', 'waiver_reason'])
            messages.success(request, f"Updated waiver status for {penalty}.")
        return HttpResponseRedirect('/admin/fleet_contracts/contractslapenalty/')

    @admin.display(description='Contract')
    def contract_link(self, obj):
        return format_html(
            '<a href="/admin/fleet_contracts/transportcontract/{}/change/" style="color: #93c5fd; text-decoration: none; font-weight: 500;">{}</a>',
            obj.contract.id, obj.contract.name
        )

    @admin.display(description='Infraction')
    def penalty_type_badge(self, obj):
        return format_html(
            '<span style="color: #f8fafc; font-weight: 500; font-size: 12px;">{}</span>',
            obj.get_penalty_type_display()
        )

    @admin.display(description='Severity')
    def severity_badge(self, obj):
        if obj.penalty_type in ['missed_trip', 'escort_missing'] or obj.penalty_amount >= 3500:
            return mark_safe('<span class="badge" style="background: #dc2626; color: #fff; padding: 3px 6px;">🔴 High</span>')
        elif obj.penalty_type in ['ac_failure', 'unauthorized_driver', 'breakdown_delay']:
            return mark_safe('<span class="badge" style="background: #d97706; color: #fff; padding: 3px 6px;">🟡 Medium</span>')
        return mark_safe('<span class="badge" style="background: #0284c7; color: #fff; padding: 3px 6px;">🔵 Low</span>')

    @admin.display(description='Amount')
    def amount_display(self, obj):
        color = '#94a3b8' if obj.waived else '#ef4444'
        decoration = 'line-through' if obj.waived else 'none'
        return format_html(
            '<span style="color: {}; text-decoration: {}; font-weight: 700; font-size: 13px;">₹{}</span>',
            color, decoration, f"{obj.penalty_amount:,.0f}"
        )

    @admin.display(description='Waiver Status')
    def waiver_status_badge(self, obj):
        if obj.waived:
            return mark_safe(
                '<span class="badge" style="background-color: #059669; color: #fff; padding: 3px 6px;">'
                '<i class="fas fa-check mr-1"></i>Waived'
                '</span>'
            )
        return mark_safe(
            '<span class="badge" style="background-color: #dc2626; color: #fff; padding: 3px 6px;">'
            '<i class="fas fa-times mr-1"></i>Deductible'
            '</span>'
        )

    @admin.display(description='Trip Log')
    def trip_link(self, obj):
        if obj.trip_log:
            return format_html(
                '<span style="color: #cbd5e1; font-size: 11px;">Trip #{} ({}m delay)</span>',
                obj.trip_log.id, obj.trip_log.delay_minutes
            )
        return mark_safe('<span style="color: #64748b;">—</span>')

    @admin.display(description='Invoice Deducted')
    def invoice_link(self, obj):
        if obj.applied_to_invoice:
            return format_html(
                '<a href="/admin/fleet_contracts/contractmonthlyinvoice/{}/change/" style="color: #38bdf8; font-family: monospace; font-size: 11px;">{}</a>',
                obj.applied_to_invoice.id, obj.applied_to_invoice.invoice_number
            )
        return mark_safe('<span style="color: #94a3b8; font-size: 11px;">Pending Cycle</span>')

    @admin.display(description='Quick Toggle')
    def quick_waiver_toggle(self, obj):
        action_text = "Undo Waiver" if obj.waived else "Waive Deduction"
        bg_color = "#475569" if obj.waived else "#059669"
        url = f"/admin/fleet_contracts/contractslapenalty/{obj.id}/toggle-waiver/"
        return format_html(
            '<a href="{}" style="background: {}; color: #fff; padding: 3px 8px; border-radius: 4px; font-size: 11px; text-decoration: none;">{}</a>',
            url, bg_color, action_text
        )

    @admin.display(description='Trip Incident Inspection')
    def trip_incident_inspection(self, obj):
        if not obj.trip_log:
            return mark_safe('<span style="color: #94a3b8;">No trip log linked.</span>')
        tl = obj.trip_log
        v_str = tl.vehicle.registration_number if tl.vehicle else 'Not assigned'
        d_str = tl.driver.name if tl.driver else 'Not assigned'
        return format_html(
            '<div style="background: #1e293b; padding: 12px; border-radius: 6px; font-size: 12px; color: #cbd5e1; margin-top: 6px;">'
            '<strong style="color: #f8fafc;"><i class="fas fa-search mr-1" style="color: #f59e0b;"></i> Linked Trip Log Particulars:</strong><br>'
            '• <strong>Vehicle:</strong> {} | <strong>Driver:</strong> {}<br>'
            '• <strong>Odometer KM:</strong> {} → {} (Run: {} km)<br>'
            '• <strong>Logged Delay:</strong> <span style="color: #f87171; font-weight: bold;">{} mins</span> | <strong>Reason:</strong> {}'
            '</div>',
            v_str, d_str, tl.opening_km or 0, tl.closing_km or 0, (tl.closing_km or 0) - (tl.opening_km or 0),
            tl.delay_minutes, tl.delay_reason or 'None'
        )


# ==============================================================================
# 4. Contract Monthly Invoice Admin
# ==============================================================================

@admin.register(ContractMonthlyInvoice)
class ContractMonthlyInvoiceAdmin(ModelAdmin):
    autocomplete_fields = ['contract']
    list_display = (
        'invoice_number_badge', 'contract_link', 'billing_month_display',
        'trips_and_km_display', 'breakdown_display', 'grand_total_display', 'status_badge', 'invoice_quick_actions'
    )
    list_filter = ('status', 'billing_month', 'contract__contract_category')
    search_fields = ('invoice_number', 'contract__name', 'payment_reference')
    actions = [mark_invoices_paid]
    change_list_template = 'admin/fleet_contracts/contractmonthlyinvoice/change_list.html'
    readonly_fields = ('simulated_tax_invoice_preview',)

    fieldsets = (
        ('Step 1: Invoice Header & Period', {
            'fields': (
                ('contract', 'invoice_number'),
                ('billing_month', 'from_date', 'to_date'),
                ('status', 'due_date')
            )
        }),
        ('Step 2: Trip Volume & Distance Audit', {
            'fields': (
                ('total_trips_completed', 'total_kms_run'),
            )
        }),
        ('Step 3: Commercial Breakdown & SLA Deductions', {
            'fields': (
                ('base_contract_amount', 'extra_km_amount'),
                ('fuel_escalation_amount', 'toll_parking_amount'),
                ('sla_penalty_deduction', 'net_taxable_amount'),
                ('gst_rate', 'gst_amount', 'grand_total')
            )
        }),
        ('Step 4: Payment Settlement & Bank Reference', {
            'fields': ('payment_reference', 'notes')
        }),
        ('Step 5: Corporate Tax Invoice Preview', {
            'fields': ('simulated_tax_invoice_preview',),
            'description': 'Rendered legal tax invoice formatted for client accounts submission.'
        }),
    )

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        total_invoiced = ContractMonthlyInvoice.objects.aggregate(s=Sum('grand_total'))['s'] or Decimal('0')
        total_paid = ContractMonthlyInvoice.objects.filter(status='paid').aggregate(s=Sum('grand_total'))['s'] or Decimal('0')
        total_pending = ContractMonthlyInvoice.objects.filter(status__in=['generated', 'partially_paid', 'draft']).aggregate(s=Sum('grand_total'))['s'] or Decimal('0')
        total_pen = ContractMonthlyInvoice.objects.aggregate(s=Sum('sla_penalty_deduction'))['s'] or Decimal('0')
        
        extra_context['invoice_metrics'] = {
            'total_invoiced': f"{total_invoiced:,.0f}",
            'total_invoices': ContractMonthlyInvoice.objects.count(),
            'total_paid': f"{total_paid:,.0f}",
            'paid_count': ContractMonthlyInvoice.objects.filter(status='paid').count(),
            'total_pending': f"{total_pending:,.0f}",
            'pending_count': ContractMonthlyInvoice.objects.filter(status__in=['generated', 'partially_paid', 'draft']).count(),
            'total_sla_deductions': f"{total_pen:,.0f}",
        }
        return super().changelist_view(request, extra_context=extra_context)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('batch-generate/', self.admin_site.admin_view(self.batch_generate_invoices_view), name='contract_invoice_batch_generate'),
            path('<int:invoice_id>/print/', self.admin_site.admin_view(self.view_printable_invoice), name='contract_invoice_print'),
            path('<int:invoice_id>/mark-paid/', self.admin_site.admin_view(self.quick_mark_paid), name='contract_invoice_mark_paid'),
        ]
        return custom_urls + urls

    def batch_generate_invoices_view(self, request):
        import calendar
        from django.template.response import TemplateResponse
        from datetime import date

        active_contracts = TransportContract.objects.filter(status='active').select_related('customer')
        default_month = timezone.now().strftime('%Y-%m')

        if request.method == 'POST':
            month_str = request.POST.get('billing_month') or default_month
            try:
                year, month = map(int, month_str.split('-'))
            except ValueError:
                year, month = timezone.now().year, timezone.now().month

            from_date = date(year, month, 1)
            _, last_day = calendar.monthrange(year, month)
            to_date = date(year, month, last_day)

            auto_deduct_sla = request.POST.get('auto_deduct_sla') == '1'
            enforce_sla_cap = request.POST.get('enforce_sla_cap') == '1'
            include_fuel = request.POST.get('include_fuel_escalation') == '1'
            credit_policy = request.POST.get('credit_policy', 'contract_default')

            generated_count = 0
            skipped_count = 0
            total_billing = Decimal('0')
            total_penalties_deducted = Decimal('0')
            penalties_linked_count = 0

            existing_count = ContractMonthlyInvoice.objects.filter(billing_month=from_date).count()
            seq = existing_count + 1

            for contract in active_contracts:
                if ContractMonthlyInvoice.objects.filter(contract=contract, billing_month=from_date).exists():
                    skipped_count += 1
                    continue

                trips_qs = ContractTripLog.objects.filter(
                    shift__route__contract=contract,
                    date__range=(from_date, to_date),
                    status__in=['completed', 'delayed']
                )
                actual_trips = trips_qs.count()
                actual_km = Decimal('0')
                actual_toll = Decimal('0')
                for t in trips_qs:
                    if t.opening_km and t.closing_km and t.closing_km > t.opening_km:
                        actual_km += Decimal(str(t.closing_km - t.opening_km))
                    if t.toll_parking_charges:
                        actual_toll += t.toll_parking_charges

                buses = max(1, contract.committed_vehicle_count)
                if contract.billing_model == 'fixed_monthly':
                    base_amount = contract.default_rate
                    total_trips = actual_trips or (buses * 44)
                    total_kms = actual_km or Decimal(str(buses * 2200))
                    extra_km_amt = Decimal('0')
                elif contract.billing_model == 'per_trip':
                    total_trips = actual_trips or (buses * 44)
                    base_amount = Decimal(str(total_trips)) * contract.default_rate
                    total_kms = actual_km or Decimal(str(buses * 2200))
                    extra_km_amt = Decimal('0')
                else:
                    total_trips = actual_trips or (buses * 44)
                    total_kms = actual_km or Decimal(str(buses * 2200))
                    base_amount = total_kms * contract.default_rate
                    extra_km_amt = Decimal('0')

                fuel_amt = Decimal('0')
                if include_fuel and contract.fuel_escalation_enabled and contract.fuel_revision_factor:
                    fuel_amt = round(total_kms * contract.fuel_revision_factor * Decimal('2.0'), 2)

                sla_ded = Decimal('0')
                eligible_penalties = []
                if auto_deduct_sla:
                    pen_qs = ContractSLAPenalty.objects.filter(
                        contract=contract,
                        waived=False,
                        applied_to_invoice__isnull=True,
                        date__lte=to_date
                    )
                    raw_pen_sum = pen_qs.aggregate(s=Sum('penalty_amount'))['s'] or Decimal('0')
                    if enforce_sla_cap and contract.sla_penalty_cap_pct:
                        cap = round((base_amount * contract.sla_penalty_cap_pct) / Decimal('100'), 2)
                        sla_ded = min(raw_pen_sum, cap)
                    else:
                        sla_ded = raw_pen_sum
                    eligible_penalties = list(pen_qs)

                if credit_policy == 'net_45':
                    due_date = to_date + datetime.timedelta(days=45)
                elif credit_policy == 'net_60':
                    due_date = to_date + datetime.timedelta(days=60)
                elif credit_policy == 'net_30':
                    due_date = to_date + datetime.timedelta(days=30)
                else:
                    due_date = to_date + datetime.timedelta(days=contract.payment_credit_days or 30)

                cat_prefix = contract.contract_category[:3].upper() if contract.contract_category else 'COR'
                inv_number = f"INV-{cat_prefix}-{from_date.strftime('%Y%m')}-{seq:03d}"
                seq += 1

                invoice = ContractMonthlyInvoice(
                    contract=contract,
                    invoice_number=inv_number,
                    billing_month=from_date,
                    from_date=from_date,
                    to_date=to_date,
                    total_trips_completed=total_trips,
                    total_kms_run=total_kms,
                    base_contract_amount=base_amount,
                    extra_km_amount=extra_km_amt,
                    fuel_escalation_amount=fuel_amt,
                    toll_parking_amount=actual_toll,
                    sla_penalty_deduction=sla_ded,
                    gst_rate=contract.gst_rate or Decimal('5.00'),
                    status='draft',
                    due_date=due_date,
                    notes=f"Generated via 1-Click Batch Monthly Billing Run on {timezone.now().strftime('%d/%m/%Y %H:%M')}."
                )
                invoice.save()

                if eligible_penalties and sla_ded > 0:
                    for p in eligible_penalties:
                        p.applied_to_invoice = invoice
                        p.save(update_fields=['applied_to_invoice'])
                    total_penalties_deducted += sla_ded
                    penalties_linked_count += len(eligible_penalties)

                generated_count += 1
                total_billing += invoice.grand_total

            if generated_count > 0:
                messages.success(
                    request,
                    format_html(
                        '<strong><i class="fas fa-bolt mr-1"></i> Batch Billing Run Complete!</strong><br>'
                        '• Successfully created <strong>{} draft invoices</strong> totaling <strong>₹{}</strong> for {}.<br>'
                        '• Automatically linked and deducted <strong>{} SLA penalties</strong> (-₹{}).<br>'
                        '• Skipped {} contract(s) with pre-existing invoices for this month.',
                        generated_count, f"{total_billing:,.2f}", from_date.strftime('%B %Y'),
                        penalties_linked_count, f"{total_penalties_deducted:,.2f}", skipped_count
                    )
                )
            else:
                messages.info(
                    request,
                    f"No new invoices generated. All {skipped_count} active contracts already have invoices for {from_date.strftime('%B %Y')}."
                )
            return HttpResponseRedirect('/admin/fleet_contracts/contractmonthlyinvoice/')

        context = {
            **self.admin_site.each_context(request),
            'active_contracts': active_contracts,
            'default_month': default_month,
        }
        return TemplateResponse(request, 'admin/fleet_contracts/contractmonthlyinvoice/batch_generate.html', context)

    def quick_mark_paid(self, request, invoice_id):
        inv = self.get_object(request, invoice_id)
        if inv and inv.status != 'paid':
            inv.status = 'paid'
            inv.payment_reference = f"NEFT/QUICK/{timezone.now().strftime('%Y%m%d%H%M')}"
            inv.save(update_fields=['status', 'payment_reference'])
            messages.success(request, f"Invoice {inv.invoice_number} marked as Paid in Full.")
        return HttpResponseRedirect('/admin/fleet_contracts/contractmonthlyinvoice/')

    def view_printable_invoice(self, request, invoice_id):
        inv = self.get_object(request, invoice_id)
        if not inv:
            messages.error(request, "Invoice not found.")
            return HttpResponseRedirect('/admin/fleet_contracts/contractmonthlyinvoice/')

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Tax Invoice - {escape(inv.invoice_number)}</title>
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 40px; color: #1e293b; }}
                h1 {{ color: #0284c7; margin: 0; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 13.5px; }}
                th {{ background: #f1f5f9; padding: 10px; text-align: left; border-bottom: 2px solid #cbd5e1; }}
                td {{ padding: 10px; border-bottom: 1px solid #e2e8f0; }}
                .total-row {{ font-weight: bold; background: #f8fafc; font-size: 15px; }}
            </style>
        </head>
        <body>
            <div style="display: flex; justify-content: space-between; border-bottom: 2px solid #0284c7; padding-bottom: 16px;">
                <div>
                    <h1>SIVAGAYATHIRI TOURS &amp; TRAVELS</h1>
                    <div style="font-size: 13px; color: #64748b;">GSTIN: 33AAAFS1234F1Z5 • State: Tamil Nadu (33)</div>
                    <div style="font-size: 13px; color: #64748b;">100 Feet Road, Gandhipuram, Coimbatore - 641012</div>
                </div>
                <div style="text-align: right;">
                    <h2 style="margin: 0; color: #0f172a;">TAX INVOICE</h2>
                    <div style="font-size: 14px; font-weight: bold; color: #0284c7;">{escape(inv.invoice_number)}</div>
                    <div style="font-size: 13px; color: #64748b;">Date: {inv.from_date.strftime('%d/%m/%Y')}</div>
                    <button onclick="window.print()" style="margin-top: 8px; background: #059669; color: #fff; padding: 6px 14px; border: none; border-radius: 4px; cursor: pointer;">🖨️ Print Tax Invoice</button>
                </div>
            </div>

            <div style="margin-top: 24px; background: #f8fafc; padding: 16px; border-radius: 6px;">
                <strong>Billed To:</strong><br>
                <span style="font-size: 15px; font-weight: bold; color: #0f172a;">{escape(inv.contract.customer.name)}</span><br>
                <span style="font-size: 13px; color: #475569;">Agreement: {escape(inv.contract.name)} ({inv.contract.get_contract_category_display()})</span><br>
                <span style="font-size: 13px; color: #475569;">Billing Cycle: {inv.from_date.strftime('%d/%m/%Y')} to {inv.to_date.strftime('%d/%m/%Y')}</span>
            </div>

            <table>
                <thead>
                    <tr><th>Description of Service</th><th>Volume</th><th style="text-align: right;">Rate / Adjustment</th><th style="text-align: right;">Amount (INR)</th></tr>
                </thead>
                <tbody>
                    <tr><td>Base Retainer / Scheduled Commute Operations</td><td>{inv.total_trips_completed} Trips</td><td style="text-align: right;">Agreement Rate</td><td style="text-align: right;">₹{inv.base_contract_amount:,.2f}</td></tr>
                    <tr><td>Extra Kilometer Usage Over Plan</td><td>{inv.total_kms_run:,.0f} KM Run</td><td style="text-align: right;">Per KM</td><td style="text-align: right;">₹{inv.extra_km_amount:,.2f}</td></tr>
                    <tr><td>Fuel Price Escalation Clause Adjustment</td><td>Formula Based</td><td style="text-align: right;">Diesel Ref.</td><td style="text-align: right;">₹{inv.fuel_escalation_amount:,.2f}</td></tr>
                    <tr><td>Toll &amp; Municipal Parking Reimbursements</td><td>Actuals</td><td style="text-align: right;">FASTag Log</td><td style="text-align: right;">₹{inv.toll_parking_amount:,.2f}</td></tr>
                    <tr style="color: #dc2626;"><td>Less: Contractual SLA Penalties &amp; Delay Deductions</td><td>Infractions Log</td><td style="text-align: right;">Penalty Sched.</td><td style="text-align: right;">- ₹{inv.sla_penalty_deduction:,.2f}</td></tr>
                    <tr class="total-row"><td colspan="3">Net Taxable Amount</td><td style="text-align: right;">₹{inv.net_taxable_amount:,.2f}</td></tr>
                    <tr><td colspan="3">CGST @ 2.5%</td><td style="text-align: right;">₹{(inv.gst_amount / 2):,.2f}</td></tr>
                    <tr><td colspan="3">SGST @ 2.5%</td><td style="text-align: right;">₹{(inv.gst_amount / 2):,.2f}</td></tr>
                    <tr class="total-row" style="background: #e0f2fe; color: #0369a1;"><td colspan="3">TOTAL INVOICE PAYABLE</td><td style="text-align: right; font-size: 17px;">₹{inv.grand_total:,.2f}</td></tr>
                </tbody>
            </table>

            <div style="margin-top: 30px; font-size: 13px; color: #64748b;">
                <strong>Payment Instructions:</strong> Direct NEFT/RTGS to Sivagayathiri Tours &amp; Travels, Current A/C # 50200012345678, HDFC Bank, IFSC: HDFC0000123.<br>
                Due Date: {inv.due_date.strftime('%d/%m/%Y') if inv.due_date else 'Within credit period'}.
            </div>
        </body>
        </html>
        """
        return HttpResponse(html)

    @admin.display(description='Invoice #')
    def invoice_number_badge(self, obj):
        return format_html(
            '<span style="font-weight: 700; color: #38bdf8; font-family: monospace; font-size: 12.5px;">'
            '<i class="fas fa-file-invoice-dollar mr-1"></i>{}</span>',
            obj.invoice_number
        )

    @admin.display(description='Contract')
    def contract_link(self, obj):
        return format_html(
            '<a href="/admin/fleet_contracts/transportcontract/{}/change/" style="color: #93c5fd; text-decoration: none; font-weight: 500;">{}</a>',
            obj.contract.id, obj.contract.name
        )

    @admin.display(description='Billing Month')
    def billing_month_display(self, obj):
        return format_html(
            '<span style="color: #f1f5f9; font-weight: 600;">{}</span>',
            obj.billing_month.strftime('%B %Y')
        )

    @admin.display(description='Trips & KMs')
    def trips_and_km_display(self, obj):
        return format_html(
            '<span style="color: #cbd5e1; font-size: 12px;">{} Trips<br><small style="color: #94a3b8;">{} KMs</small></span>',
            obj.total_trips_completed, f"{obj.total_kms_run:,.0f}"
        )

    @admin.display(description='Deductions & Fuel')
    def breakdown_display(self, obj):
        fuel_str = f"+₹{obj.fuel_escalation_amount:,.0f} Fuel" if obj.fuel_escalation_amount > 0 else ""
        pen_str = f"-₹{obj.sla_penalty_deduction:,.0f} Penalties" if obj.sla_penalty_deduction > 0 else "0 Penalties"
        return format_html(
            '<span style="color: #94a3b8; font-size: 11px;">{}<br><span style="color: #ef4444; font-weight: 600;">{}</span></span>',
            fuel_str, pen_str
        )

    @admin.display(description='Grand Total (with GST)')
    def grand_total_display(self, obj):
        return format_html(
            '<span style="color: #10b981; font-weight: 700; font-size: 14px;">₹{}</span>',
            f"{obj.grand_total:,.2f}"
        )

    @admin.display(description='Status')
    def status_badge(self, obj):
        colors = {
            'draft': ('#64748b', 'Draft'),
            'generated': ('#0284c7', 'Sent to Client'),
            'paid': ('#059669', 'Paid in Full'),
            'partially_paid': ('#d97706', 'Partially Paid'),
            'disputed': ('#dc2626', 'Disputed'),
        }
        color, label = colors.get(obj.status, ('#64748b', obj.status))
        return format_html(
            '<span class="badge" style="background-color: {}; color: #fff; padding: 4px 8px;">{}</span>',
            color, label
        )

    @admin.display(description='Quick Actions')
    def invoice_quick_actions(self, obj):
        print_url = f"/admin/fleet_contracts/contractmonthlyinvoice/{obj.id}/print/"
        pay_btn = ""
        if obj.status != 'paid':
            pay_url = f"/admin/fleet_contracts/contractmonthlyinvoice/{obj.id}/mark-paid/"
            pay_btn = f'<a href="{pay_url}" title="Quick Mark as Paid" style="background: #059669; color: #fff; padding: 4px 7px; border-radius: 4px; font-size: 11px; text-decoration: none;"><i class="fas fa-check"></i></a>'

        return format_html(
            '<div style="display: flex; gap: 5px; align-items: center;">'
            '<a href="{}" target="_blank" title="Print Tax Invoice" style="background: #0284c7; color: #fff; padding: 4px 7px; border-radius: 4px; font-size: 11px; text-decoration: none;">'
            '<i class="fas fa-print"></i>'
            '</a>'
            '{}'
            '</div>',
            print_url, mark_safe(pay_btn)
        )

    @admin.display(description='Simulated Corporate Tax Invoice Preview')
    def simulated_tax_invoice_preview(self, obj):
        if not obj.pk:
            return mark_safe('<span style="color: #94a3b8;">Save invoice to generate preview.</span>')
        return format_html(
            '<div style="background: #0f172a; border: 1px solid #1e293b; border-radius: 8px; padding: 20px; max-width: 800px; color: #cbd5e1;">'
            '<div style="display: flex; justify-content: space-between; border-bottom: 1px solid #334155; padding-bottom: 12px; margin-bottom: 14px;">'
            '<div><strong style="color: #38bdf8; font-size: 16px;">SIVAGAYATHIRI TOURS &amp; TRAVELS</strong><br><small>Corporate Transit Operations Division • GSTIN: 33AAAFS1234F1Z5</small></div>'
            '<div style="text-align: right;"><span class="badge" style="background: #0284c7; color: #fff; padding: 4px 8px; font-size: 12px;">{}</span><br><small style="color: #94a3b8;">Period: {}</small></div>'
            '</div>'
            '<div style="margin-bottom: 14px; font-size: 12.5px;">'
            '<strong style="color: #f8fafc;">Billed Client:</strong> {}<br>'
            '<strong style="color: #f8fafc;">Contract:</strong> {}'
            '</div>'
            '<table style="width: 100%; border-collapse: collapse; font-size: 12.5px; margin-bottom: 14px;">'
            '<tr style="border-bottom: 1px solid #334155;"><td>Base Monthly Transit Retainer</td><td style="text-align: right; color: #f8fafc;">₹{}</td></tr>'
            '<tr style="border-bottom: 1px solid #334155;"><td>Extra KM Run Adjustment</td><td style="text-align: right; color: #f8fafc;">₹{}</td></tr>'
            '<tr style="border-bottom: 1px solid #334155;"><td>Fuel Price Escalation Clause</td><td style="text-align: right; color: #f8fafc;">₹{}</td></tr>'
            '<tr style="border-bottom: 1px solid #334155;"><td>FASTag Toll &amp; Parking Reimbursements</td><td style="text-align: right; color: #f8fafc;">₹{}</td></tr>'
            '<tr style="border-bottom: 1px solid #334155; color: #ef4444;"><td>Less: Contractual SLA Penalties Deducted</td><td style="text-align: right;">- ₹{}</td></tr>'
            '<tr style="border-bottom: 2px solid #38bdf8; font-weight: bold; color: #f8fafc;"><td>Net Taxable Billing</td><td style="text-align: right;">₹{}</td></tr>'
            '<tr><td>Goods &amp; Services Tax (GST @ 5%)</td><td style="text-align: right; color: #93c5fd;">₹{}</td></tr>'
            '<tr style="font-weight: bold; font-size: 15px; color: #10b981;"><td>GRAND TOTAL PAYABLE</td><td style="text-align: right;">₹{}</td></tr>'
            '</table>'
            '<div style="text-align: right;"><a href="/admin/fleet_contracts/contractmonthlyinvoice/{}/print/" target="_blank" class="btn btn-sm btn-info" style="background: #0284c7; color: #fff; padding: 6px 14px; text-decoration: none; border-radius: 4px; font-weight: 600;">🖨️ Open Full Printable Invoice</a></div>'
            '</div>',
            obj.invoice_number, obj.billing_month.strftime('%B %Y'), obj.contract.customer.name, obj.contract.name,
            f"{obj.base_contract_amount:,.2f}", f"{obj.extra_km_amount:,.2f}", f"{obj.fuel_escalation_amount:,.2f}", f"{obj.toll_parking_amount:,.2f}",
            f"{obj.sla_penalty_deduction:,.2f}", f"{obj.net_taxable_amount:,.2f}", f"{obj.gst_amount:,.2f}", f"{obj.grand_total:,.2f}", obj.id
        )


# ==============================================================================
# 5. Contract Daily Trip Logs Admin
# ==============================================================================

@admin.register(ContractTripLog)
class ContractTripLogAdmin(ModelAdmin):
    autocomplete_fields = ['shift', 'vehicle', 'driver', 'replaced_vehicle']
    list_display = (
        'date', 'shift_display', 'vehicle_badge', 'driver_badge',
        'status_badge', 'delay_badge', 'passenger_count_display', 'km_run_display'
    )
    list_filter = ('status', 'shift__route__contract', 'date', 'is_replacement_vehicle')
    search_fields = ('shift__route__name', 'vehicle__registration_number', 'driver__name', 'delay_reason')
    date_hierarchy = 'date'

    @admin.display(description='Route & Shift')
    def shift_display(self, obj):
        return format_html(
            '<span style="color: #38bdf8; font-weight: 600;">{}</span><br><small style="color: #94a3b8;">{} ({})</small>',
            obj.shift.route.name if obj.shift and obj.shift.route else 'Route',
            obj.shift.shift_name if obj.shift else 'Shift',
            obj.shift.timing.strftime('%I:%M %p') if obj.shift and obj.shift.timing else ''
        )

    @admin.display(description='Vehicle')
    def vehicle_badge(self, obj):
        if not obj.vehicle:
            return mark_safe('<span style="color: #64748b;">—</span>')
        rep = '<span class="badge" style="background: #d97706; color: #fff; font-size: 9px; margin-left: 4px;">Standby Rep.</span>' if obj.is_replacement_vehicle else ''
        return format_html(
            '<span style="color: #f8fafc; font-weight: 500;">{}</span>{}',
            obj.vehicle.registration_number, mark_safe(rep)
        )

    @admin.display(description='Driver')
    def driver_badge(self, obj):
        if not obj.driver:
            return mark_safe('<span style="color: #64748b;">—</span>')
        return format_html('<span style="color: #93c5fd;">{}</span>', obj.driver.name)

    @admin.display(description='Trip Status')
    def status_badge(self, obj):
        styles = {
            'completed': ('#059669', 'Completed'),
            'delayed': ('#d97706', 'Completed w/ Delay'),
            'breakdown': ('#dc2626', 'Breakdown'),
            'scheduled': ('#0284c7', 'Scheduled'),
            'en_route': ('#8b5cf6', 'En Route'),
            'cancelled': ('#64748b', 'Cancelled'),
        }
        color, label = styles.get(obj.status, ('#64748b', obj.status))
        return format_html('<span class="badge" style="background-color: {}; color: #fff; padding: 4px 8px;">{}</span>', color, label)

    @admin.display(description='Delay & Reason')
    def delay_badge(self, obj):
        if obj.delay_minutes > 0:
            return format_html(
                '<span style="color: #f87171; font-weight: 700;">+{} mins</span><br><small style="color: #94a3b8;">{}</small>',
                obj.delay_minutes, obj.delay_reason or 'Traffic'
            )
        return mark_safe('<span style="color: #10b981; font-size: 11px;">On Time</span>')

    @admin.display(description='Headcount')
    def passenger_count_display(self, obj):
        return format_html('<span style="color: #cbd5e1;">{} Pax</span>', obj.passenger_count)

    @admin.display(description='Odometer Run')
    def km_run_display(self, obj):
        if obj.opening_km is not None and obj.closing_km is not None:
            run = obj.closing_km - obj.opening_km
            return format_html('<span style="color: #cbd5e1;">{} km</span>', run)
        return mark_safe('<span style="color: #64748b;">—</span>')


# ==============================================================================
# 6. Night Safety & Escort Guard Logs Admin (Women Safety & Corporate ETS)
# ==============================================================================

@admin.register(NightSafetyEscortLog)
class NightSafetyEscortLogAdmin(ModelAdmin):
    autocomplete_fields = ['trip_log']
    list_display = (
        'trip_link', 'guard_badge', 'female_count_badge',
        'timing_display', 'verification_status_badge', 'confirmed_by_display', 'quick_verify_action'
    )
    list_filter = ('last_drop_verification_status', 'trip_log__shift__route__contract', 'trip_log__date')
    search_fields = ('escort_guard_name', 'guard_badge_number', 'security_agency', 'safe_drop_confirmed_by')

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<int:log_id>/quick-verify/', self.admin_site.admin_view(self.quick_verify_view), name='escort_log_quick_verify'),
        ]
        return custom_urls + urls

    def quick_verify_view(self, request, log_id):
        log = self.get_object(request, log_id)
        if log:
            log.last_drop_verification_status = 'verified_sms'
            log.safe_drop_confirmed_by = f"Supervisor Verified ({request.user.username})"
            log.save(update_fields=['last_drop_verification_status', 'safe_drop_confirmed_by'])
            messages.success(request, f"Night safety drop verified for {log.escort_guard_name} (Trip #{log.trip_log_id}).")
        return HttpResponseRedirect('/admin/fleet_contracts/nightsafetyescortlog/')

    @admin.display(description='Trip Particulars')
    def trip_link(self, obj):
        t = obj.trip_log
        return format_html(
            '<a href="/admin/fleet_contracts/contracttriplog/{}/change/" style="color: #38bdf8; font-weight: 600;">'
            'Trip #{} on {}'
            '</a><br><small style="color: #94a3b8;">{}</small>',
            t.id, t.id, t.date.strftime('%d/%m/%Y'), t.shift.route.name if t.shift and t.shift.route else 'Transit'
        )

    @admin.display(description='Security Guard')
    def guard_badge(self, obj):
        agency = f" ({obj.security_agency})" if obj.security_agency else ""
        return format_html(
            '<span style="color: #f8fafc; font-weight: 600;"><i class="fas fa-user-shield mr-1" style="color: #38bdf8;"></i>{}</span><br><small style="color: #94a3b8;">Badge: {}{}</small>',
            obj.escort_guard_name, obj.guard_badge_number or 'SIS-SEC', agency
        )

    @admin.display(description='Female Commuters')
    def female_count_badge(self, obj):
        return format_html(
            '<span class="badge" style="background: #be185d; color: #fff; padding: 4px 8px; font-size: 11px;">'
            '<i class="fas fa-female mr-1"></i>{} Female Drops'
            '</span>',
            obj.female_passengers_count
        )

    @admin.display(description='Escort Shift Hours')
    def timing_display(self, obj):
        t1 = obj.first_pickup_time.strftime('%I:%M %p') if obj.first_pickup_time else '20:00'
        t2 = obj.last_female_drop_time.strftime('%I:%M %p') if obj.last_female_drop_time else '05:30'
        return format_html('<span style="color: #cbd5e1; font-size: 12px;">{} → {}</span>', t1, t2)

    @admin.display(description='Safe-Drop Verification')
    def verification_status_badge(self, obj):
        styles = {
            'verified_sms': ('#059669', '📱 OTP Verified'),
            'verified_call': ('#0284c7', '📞 Call Verified'),
            'supervisor_signoff': ('#7c3aed', '✍️ Sign-off Done'),
            'pending': ('#dc2626', '⏳ Pending Verification'),
        }
        color, label = styles.get(obj.last_drop_verification_status, ('#64748b', obj.last_drop_verification_status))
        return format_html('<span class="badge" style="background-color: {}; color: #fff; padding: 4px 8px;">{}</span>', color, label)

    @admin.display(description='Confirmed By')
    def confirmed_by_display(self, obj):
        return format_html('<span style="color: #94a3b8; font-size: 12px;">{}</span>', obj.safe_drop_confirmed_by or '—')

    @admin.display(description='Action')
    def quick_verify_action(self, obj):
        if obj.last_drop_verification_status == 'pending':
            url = f"/admin/fleet_contracts/nightsafetyescortlog/{obj.id}/quick-verify/"
            return format_html(
                '<a href="{}" style="background: #059669; color: #fff; padding: 4px 8px; border-radius: 4px; font-size: 11px; text-decoration: none; font-weight: 600;">'
                '<i class="fas fa-check mr-1"></i>Verify OTP'
                '</a>',
                url
            )
        return mark_safe('<span style="color: #10b981; font-size: 11px;"><i class="fas fa-check-double mr-1"></i>Confirmed</span>')


# ==============================================================================
# 7. Commuter & Student Manifest Admin
# ==============================================================================

@admin.register(CommuterManifest)
class CommuterManifestAdmin(ModelAdmin):
    autocomplete_fields = ['contract', 'boarding_stop']
    list_display = (
        'name', 'commuter_id', 'contract_link', 'commuter_type_badge',
        'gender_badge', 'boarding_stop_display', 'night_escort_badge', 'contact_display'
    )
    list_filter = ('commuter_type', 'requires_night_escort', 'gender', 'contract')
    search_fields = ('name', 'commuter_id', 'phone', 'emergency_contact_phone', 'department_or_grade')

    @admin.display(description='Contract')
    def contract_link(self, obj):
        return format_html(
            '<a href="/admin/fleet_contracts/transportcontract/{}/change/" style="color: #38bdf8; text-decoration: none; font-weight: 500;">{}</a>',
            obj.contract.id, obj.contract.name
        )

    @admin.display(description='Commuter Type')
    def commuter_type_badge(self, obj):
        styles = {
            'employee': ('#0284c7', '🏢 Corporate Staff'),
            'student': ('#f59e0b', '🎒 Student'),
            'worker': ('#d97706', '🏭 Factory Worker'),
            'staff': ('#059669', '👨‍🏫 Faculty / Hospital'),
        }
        color, label = styles.get(obj.commuter_type, ('#64748b', obj.commuter_type))
        return format_html('<span class="badge" style="background-color: {}; color: #fff; padding: 3px 6px; font-size: 11px;">{}</span>', color, label)

    @admin.display(description='Gender')
    def gender_badge(self, obj):
        if obj.gender == 'female':
            return mark_safe('<span style="color: #f472b6; font-weight: 600;"><i class="fas fa-female mr-1"></i>Female</span>')
        return format_html('<span style="color: #93c5fd;">{}</span>', obj.get_gender_display())

    @admin.display(description='Boarding Stop')
    def boarding_stop_display(self, obj):
        if obj.boarding_stop:
            return format_html('<span style="color: #cbd5e1; font-size: 12px;">#{} {}</span>', obj.boarding_stop.stop_order, obj.boarding_stop.name)
        return mark_safe('<span style="color: #64748b;">—</span>')

    @admin.display(description='Night Escort Protocol')
    def night_escort_badge(self, obj):
        if obj.requires_night_escort:
            return mark_safe('<span class="badge" style="background: #be185d; color: #fff; padding: 3px 6px; font-size: 10px;">🛡️ Mandatory Escort</span>')
        return mark_safe('<span style="color: #64748b; font-size: 11px;">Standard</span>')

    @admin.display(description='Emergency Contact')
    def contact_display(self, obj):
        phone = obj.phone or obj.emergency_contact_phone or '—'
        dept = f"<br><small style='color: #94a3b8;'>{obj.department_or_grade}</small>" if obj.department_or_grade else ""
        return format_html('<span style="color: #cbd5e1; font-size: 12px;"><i class="fas fa-phone mr-1"></i>{}</span>{}', phone, mark_safe(dept))


# ==============================================================================
# Hidden Registration for Autocomplete & URL Backward Compatibility
# ==============================================================================

@admin.register(Route)
class RouteHiddenAdmin(ModelAdmin):
    search_fields = ('name',)
    def has_module_permission(self, request):
        return False


@admin.register(Shift)
class ShiftHiddenAdmin(ModelAdmin):
    search_fields = ('shift_name', 'route__name')
    def has_module_permission(self, request):
        return False


@admin.register(RouteStop)
class RouteStopHiddenAdmin(ModelAdmin):
    search_fields = ('name', 'pickup_landmark')
    def has_module_permission(self, request):
        return False
