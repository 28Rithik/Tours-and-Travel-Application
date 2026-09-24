from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils import timezone
import datetime

from packages.models import (
    BoardingPoint as BaseBoardingPoint,
    TourPassengerManifest as BaseTourPassengerManifest,
    PackageHotelAllotment as BasePackageHotelAllotment,
)
from .models import (
    CollegeIVProxy,
    TourDepartureBatchProxy,
    BoardingPointProxy,
    PassengerManifestProxy,
    HotelAllotmentProxy,
    TourFeedbackProxy,
    SeasonalRateProxy,
    PackageAddonProxy,
    B2BMarginProxy,
)


# ==============================================================================
# Inlines
# ==============================================================================

class BoardingPointInline(admin.TabularInline):
    model = BaseBoardingPoint
    extra = 1
    fields = ('stop_order', 'stop_name', 'pickup_time', 'landmark', 'coordinator_phone')
    ordering = ('stop_order',)


class HotelAllotmentInline(admin.TabularInline):
    model = BasePackageHotelAllotment
    extra = 0
    fields = ('hotel_name', 'room_category', 'check_in_date', 'check_out_date', 'rooms_blocked', 'rooms_occupied', 'cost_per_room_night', 'status')


import csv
from django.http import HttpResponse


class PassengerManifestInline(admin.TabularInline):
    """Lightweight inline — shows only 10 rows to avoid page crash on large manifests."""
    model = BaseTourPassengerManifest
    extra = 0
    max_num = 0          # read-only: no new rows via inline
    can_delete = False
    show_change_link = True
    fields = ('passenger_name', 'category', 'gender', 'bus_assignment', 'seat_number', 'room_sharing_number', 'phone')
    readonly_fields = ('passenger_name', 'category', 'gender', 'bus_assignment', 'seat_number', 'room_sharing_number', 'phone')

    def get_queryset(self, request):
        """Only show first 10 — link to full manifest list page for rest."""
        return super().get_queryset(request).order_by('bus_assignment', 'seat_number')[:10]

    def has_add_permission(self, request, obj=None):
        return False




# ==============================================================================
# Bulk Actions
# ==============================================================================

@admin.action(description="✅ Mark selected IV Expeditions as Confirmed")
def mark_iv_confirmed(modeladmin, request, queryset):
    updated = queryset.update(status='confirmed')
    modeladmin.message_user(request, f"{updated} IV Expedition(s) marked as confirmed.")


@admin.action(description="📄 Mark Industry Permission as Approved")
def mark_permission_approved(modeladmin, request, queryset):
    updated = queryset.update(permission_status='approved')
    modeladmin.message_user(request, f"{updated} industry visit permission(s) approved.")


@admin.action(description="🟢 Open selected departure batches")
def mark_departure_open(modeladmin, request, queryset):
    updated = queryset.update(status='open')
    modeladmin.message_user(request, f"{updated} tour departure(s) opened.")


@admin.action(description="📤 Bulk Import Passenger Manifest from Excel/CSV")
def upload_manifest_redirect(modeladmin, request, queryset):
    from django.shortcuts import redirect
    return redirect('/packages/manifest/upload/')


@admin.action(description="📥 Download Manifest CSV Template")
def download_template_redirect(modeladmin, request, queryset):
    from django.shortcuts import redirect
    return redirect('/packages/manifest/template/download/')


@admin.action(description="📤 Bulk Import Student Manifest for selected College")
def upload_manifest_for_iv(modeladmin, request, queryset):
    from django.shortcuts import redirect
    iv = queryset.first()
    if iv:
        return redirect(f'/packages/manifest/upload/?iv_id={iv.id}')
    return redirect('/packages/manifest/upload/')


@admin.action(description="✅ Auto-Assign Bus, Seat & Room for selected IV Expedition")
def auto_assign_bus_seat_room_iv(modeladmin, request, queryset):
    """Auto-assigns Bus numbers, seat numbers and room allocations for all passengers
    in the selected College IV Expedition(s). Faculty go to Bus 01 (front).
    Male students fill remaining Bus 01 seats then overflow to Bus 02, 03...
    Female students get their own dedicated buses.
    Students are put in 4-sharing rooms; faculty get twin-sharing."""
    from packages.manifest_autoassign import auto_assign_for_expedition
    total_assigned = 0
    for iv in queryset:
        result = auto_assign_for_expedition(iv.id)
        if 'error' in result:
            modeladmin.message_user(request, f"❌ {iv}: {result['error']}", level='error')
        else:
            total_assigned += result['total_passengers']
            all_buses = ', '.join(result.get('mixed_buses', result.get('male_buses', [])))
            fac_per_bus = result.get('faculty_per_bus_approx', '~1')
            modeladmin.message_user(
                request,
                f"🎉 {result['expedition']}: {result['total_passengers']} passengers assigned across "
                f"{result.get('n_buses', '?')} buses ({all_buses})! "
                f"{result['faculty_assigned']} Faculty spread equally (~{fac_per_bus} per bus); "
                f"{result['male_students_assigned']} Boys + {result['female_students_assigned']} Girls "
                f"travel mixed. Rooms gender-separated (Boys: Room M101+, Girls: Room F201+)."
            )


@admin.action(description="🚀 Dispatch selected Expeditions to Operations (Create Operational Trip)")
def dispatch_iv_to_operations_trip(modeladmin, request, queryset):
    """Converts selected confirmed College IV expeditions into operational Trips in Operations,
    linking them directly to the Trip Cash Desk and P&L ledger."""
    from operations.models import Trip
    from core.models import Party
    from decimal import Decimal

    created_trips = []
    for iv in queryset:
        if iv.linked_trip:
            created_trips.append(f"{iv.college_name} (Already Dispatched: {iv.linked_trip.trip_id})")
            continue

        party, _ = Party.objects.get_or_create(
            name=iv.college_name,
            defaults={
                'party_type': 'corporate',
                'phone': iv.faculty_incharge_phone,
                'billing_cycle': 'trip',
            }
        )

        paying_students = iv.student_count_male + iv.student_count_female
        rate_per_student = Decimal('0')
        flight_rate = Decimal('0')
        if iv.package:
            rate_per_student = iv.package.price_with_food or iv.package.base_price or Decimal('0')
            if iv.transit_mode == 'flight_coach':
                flight_rate = iv.package.flight_estimate_per_pax or Decimal('0')
            elif iv.transit_mode == 'train_coach':
                flight_rate = iv.package.train_estimate_per_pax or Decimal('0')

        total_revenue = (rate_per_student + flight_rate) * Decimal(paying_students)

        notes_summary = (
            f"Expedition: {iv.college_name} - {iv.department_and_batch}\n"
            f"Transit Mode: {iv.get_transit_mode_display()}\n"
            f"Convoy: {iv.bus_count} Buses | Tour Manager: {iv.tour_manager_assigned}\n"
            f"Onward: {iv.onward_transit_details}\n"
            f"Return: {iv.return_transit_details}\n"
            f"Destination Coach: {iv.destination_coach_partner}"
        )

        trip = Trip.objects.create(
            party=party,
            guest_name=f"{iv.college_name} ({iv.department_and_batch})",
            package=iv.package,
            pax_count=iv.total_pax,
            travel_pnr=iv.transit_pnr_or_booking_ref,
            start_date=iv.start_date,
            end_date=iv.end_date,
            days_count=max(1, (iv.end_date - iv.start_date).days + 1),
            billing_model='fixed',
            fixed_amount=total_revenue,
            partner_handover_notes=notes_summary,
            status='assigned' if iv.bus_count == 1 else 'booked'
        )
        iv.linked_trip = trip
        iv.status = 'on_tour'
        iv.save(update_fields=['linked_trip', 'status'])
        created_trips.append(f"{iv.college_name} -> {trip.trip_id}")

    modeladmin.message_user(
        request,
        f"🚀 Dispatched {len(created_trips)} expedition(s) to Operations: {', '.join(created_trips)}"
    )


@admin.action(description="🚀 Dispatch selected Batches to Operations (Create Operational Trip)")
def dispatch_batch_to_operations_trip(modeladmin, request, queryset):
    """Dispatches scheduled departure batches with vehicle and driver into live Operations Trips."""
    from operations.models import Trip
    from decimal import Decimal

    created_trips = []
    for batch in queryset:
        existing_trip = Trip.objects.filter(package_inventory=batch).first()
        if existing_trip:
            created_trips.append(f"Batch #{batch.id} (Already Dispatched: {existing_trip.trip_id})")
            continue

        package = batch.package
        fare = (batch.price_override or (package.base_price if package else 0)) * batch.booked_seats

        trip = Trip.objects.create(
            package=package,
            package_inventory=batch,
            vehicle=batch.assigned_vehicle,
            driver=batch.assigned_driver,
            guest_name=f"{package.name if package else 'Tour Departure'} (Batch #{batch.id})",
            pax_count=batch.booked_seats,
            start_date=batch.departure_date,
            end_date=batch.return_date or batch.departure_date,
            days_count=max(1, ((batch.return_date - batch.departure_date).days + 1)) if batch.return_date else 1,
            billing_model='fixed',
            fixed_amount=Decimal(fare or 0),
            status='assigned' if (batch.assigned_vehicle and batch.assigned_driver) else 'booked'
        )
        batch.status = 'departed'
        batch.save(update_fields=['status'])
        created_trips.append(f"Batch #{batch.id} -> {trip.trip_id}")

    modeladmin.message_user(
        request,
        f"🚀 Dispatched {len(created_trips)} batch(es) to Operations: {', '.join(created_trips)}"
    )


# ==============================================================================
# Export Actions: Bus-wise Manifest, Rooming List, WhatsApp Broadcast
# ==============================================================================

@admin.action(description="🚌 Export Bus-wise Manifest CSV (all selected expeditions)")
def export_buswise_manifest_csv(modeladmin, request, queryset):
    """Export a CSV grouped by Bus number — one section per bus, sorted by seat."""
    from packages.models import TourPassengerManifest
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="buswise_manifest.csv"'
    response.write('\ufeff')  # BOM for Excel

    writer = csv.writer(response)
    writer.writerow(['Bus', 'Seat #', 'Passenger Name', 'Category', 'Gender', 'Roll Number', 'Room', 'Phone', 'Emergency Contact'])

    iv_ids = queryset.values_list('id', flat=True)
    passengers = TourPassengerManifest.objects.filter(
        iv_expedition_id__in=iv_ids
    ).order_by('bus_assignment', 'seat_number', 'passenger_name')

    current_bus = None
    for p in passengers:
        if p.bus_assignment != current_bus:
            current_bus = p.bus_assignment
            writer.writerow([])  # blank row separator
            writer.writerow([f'=== {current_bus} ===', '', '', '', '', '', '', '', ''])
        writer.writerow([
            p.bus_assignment, p.seat_number, p.passenger_name,
            p.get_category_display(), p.get_gender_display(),
            p.roll_number, p.room_sharing_number, p.phone, p.emergency_contact
        ])

    writer.writerow([])
    writer.writerow([f'Total Passengers: {passengers.count()}'])
    return response


@admin.action(description="🏨 Export Hotel Rooming List CSV (all selected expeditions)")
def export_rooming_list_csv(modeladmin, request, queryset):
    """Export a hotel-ready rooming list grouped by room number."""
    from packages.models import TourPassengerManifest
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="hotel_rooming_list.csv"'
    response.write('\ufeff')

    writer = csv.writer(response)
    writer.writerow(['Room', 'Guest #', 'Name', 'Gender', 'Category', 'Age', 'Phone'])

    iv_ids = queryset.values_list('id', flat=True)
    passengers = TourPassengerManifest.objects.filter(
        iv_expedition_id__in=iv_ids
    ).order_by('room_sharing_number', 'passenger_name')

    current_room = None
    guest_num = 1
    for p in passengers:
        if not p.room_sharing_number:
            continue
        if p.room_sharing_number != current_room:
            current_room = p.room_sharing_number
            guest_num = 1
            writer.writerow([])
            writer.writerow([f'=== {current_room} ===', '', '', '', '', '', ''])
        writer.writerow([
            p.room_sharing_number, guest_num, p.passenger_name,
            p.get_gender_display(), p.get_category_display(),
            p.age or '—', p.phone
        ])
        guest_num += 1

    writer.writerow([])
    writer.writerow([f'Total Guests: {passengers.count()}'])
    return response


@admin.action(description="📱 Generate WhatsApp Broadcast Message for selected IV")
def generate_whatsapp_message(modeladmin, request, queryset):
    """Generate a copy-paste WhatsApp trip confirmation message and show it as an admin message."""
    from packages.models import TourPassengerManifest
    iv = queryset.first()
    if not iv:
        modeladmin.message_user(request, "No expedition selected.", level='warning')
        return

    total_manifest = TourPassengerManifest.objects.filter(iv_expedition=iv).count()
    buses = sorted(set(
        TourPassengerManifest.objects.filter(iv_expedition=iv)
        .exclude(bus_assignment='').values_list('bus_assignment', flat=True)
    ))
    n_buses = len(buses) or iv.bus_count
    departure_str = iv.start_date.strftime('%d %b %Y') if iv.start_date else '—'

    msg = (
        f"🚌 *TRIP CONFIRMED — {iv.college_name}*\n"
        f"📚 {iv.department_and_batch}\n"
        f"📅 Departure: {departure_str}\n"
        f"🏁 Return: {iv.end_date.strftime('%d %b %Y') if iv.end_date else '—'}\n"
        f"👥 Total: {iv.total_pax} Passengers ({iv.student_count_male} Boys + {iv.student_count_female} Girls + {iv.faculty_count} Faculty)\n"
        f"🚌 {n_buses} Buses in Convoy\n"
        f"📋 Manifest Uploaded: {total_manifest}/{iv.total_pax} passengers\n"
        f"📞 Tour Manager: {iv.tour_manager_assigned}\n"
        f"☎️ Siva Gayathri Tours: +91 98425 33777 (Rithik CA) / +91 94381 71311\n\n"
        f"✅ Please carry your College ID. Report 30 minutes before departure.\n"
        f"*Siva Gayathri Tours & Travels — Coimbatore*"
    )
    modeladmin.message_user(
        request,
        f"📱 WhatsApp Message for {iv.college_name} (copy below):\n\n{msg}",
        level='success'
    )


# ==============================================================================
# 1. College IV Expedition Admin
# ==============================================================================

@admin.register(CollegeIVProxy)
class CollegeIVAdmin(admin.ModelAdmin):
    list_display = (
        'college_display', 'package_link', 'travel_dates_display',
        'headcount_badge', 'faculty_incharge_display',
        'permission_status_badge', 'event_badges', 'status_badge',
        'quick_actions'
    )
    list_filter = ('status', 'permission_status', 'has_dj_campfire', 'start_date')
    search_fields = ('college_name', 'department_and_batch', 'faculty_incharge_name', 'tour_manager_assigned')
    date_hierarchy = 'start_date'
    actions = [mark_iv_confirmed, mark_permission_approved, dispatch_iv_to_operations_trip, upload_manifest_for_iv, auto_assign_bus_seat_room_iv, export_buswise_manifest_csv, export_rooming_list_csv, generate_whatsapp_message, download_template_redirect]

    fieldsets = (
        ('Institution & Faculty In-Charge', {
            'fields': (
                ('college_name', 'department_and_batch'),
                ('faculty_incharge_name', 'faculty_incharge_phone'),
                'package'
            )
        }),
        ('Headcount & Complimentary Staff Ratio', {
            'fields': (
                ('student_count_male', 'student_count_female'),
                ('faculty_count', 'total_pax'),
            ),
            'description': 'Standard IV Ratio: Complimentary travel & stay for faculty members (e.g. 50 students + 2 faculty).'
        }),
        ('🚍 Tour Transit & Logistics', {
            'fields': (
                'transit_mode',
                ('onward_transit_details', 'return_transit_details'),
                ('transit_pnr_or_booking_ref', 'baggage_allowance'),
                ('reporting_terminal', 'destination_coach_partner'),
                ('destination_city', 'aadhaar_id_mandatory'),
                'linked_trip',
            ),
            'classes': ('grp-flybus-specs',),
            'description': 'Configure All-Road Coach, Flight (Fly-Bus), or Rail transit mode and logistics details.'
        }),
        ('Industrial Visit Permission & Documents', {
            'fields': (
                'industry_visit_targets',
                ('permission_status', 'permission_letter_file')
            )
        }),
        ('Convoy & Tour Execution', {
            'fields': (
                ('start_date', 'end_date'),
                ('bus_count', 'tour_manager_assigned', 'has_dj_campfire'),
                'status',
                'notes'
            )
        }),
    )

    readonly_fields = ('total_pax',)

    class Media:
        css = {
            'all': ('packages/css/package_admin_custom.css',)
        }
        js = ('packages/js/departures_iv_dynamic.js',)

    @admin.display(description='College & Department')
    def college_display(self, obj):
        return format_html(
            '<span style="font-weight: 700; color: #f8fafc;"><i class="fas fa-university mr-1" style="color: #f59e0b;"></i>{}</span><br>'
            '<small style="color: #94a3b8;"><i class="fas fa-graduation-cap mr-1"></i>{}</small>',
            obj.college_name, obj.department_and_batch
        )

    @admin.display(description='Tour Package')
    def package_link(self, obj):
        if obj.package:
            return format_html(
                '<a href="/admin/packages/package/{}/change/" style="color: #38bdf8; text-decoration: none; font-weight: 500;">'
                '{}'
                '</a>',
                obj.package.id, obj.package.name
            )
        return mark_safe('<span style="color: #64748b;">—</span>')

    @admin.display(description='Travel Period')
    def travel_dates_display(self, obj):
        return format_html(
            '<span style="color: #e2e8f0; font-size: 12px;"><i class="far fa-calendar-alt mr-1 text-info"></i>{} → {}</span>',
            obj.start_date.strftime('%d/%m/%y'), obj.end_date.strftime('%d/%m/%y')
        )

    @admin.display(description='Headcount')
    def headcount_badge(self, obj):
        return format_html(
            '<span class="badge" style="background-color: #0369a1; color: #fff; padding: 4px 8px; font-size: 11px;">'
            '<i class="fas fa-users mr-1"></i>{} Pax'
            '</span><br>'
            '<small style="color: #94a3b8;">({} Boys, {} Girls + {} Staff)</small>',
            obj.total_pax, obj.student_count_male, obj.student_count_female, obj.faculty_count
        )

    @admin.display(description='Faculty Contact')
    def faculty_incharge_display(self, obj):
        return format_html(
            '<span style="color: #cbd5e1; font-size: 12px;"><i class="fas fa-user-tie mr-1 text-warning"></i>{}</span><br>'
            '<small style="color: #94a3b8;"><i class="fas fa-phone mr-1"></i>{}</small>',
            obj.faculty_incharge_name, obj.faculty_incharge_phone
        )

    @admin.display(description='Industry Clearance')
    def permission_status_badge(self, obj):
        colors = {
            'pending': ('#d97706', 'fas fa-clock', 'Pending'),
            'letter_submitted': ('#0284c7', 'fas fa-envelope', 'Letter Sent'),
            'approved': ('#059669', 'fas fa-check-circle', 'Approved'),
            'completed': ('#10b981', 'fas fa-award', 'Completed'),
        }
        color, icon, label = colors.get(obj.permission_status, ('#64748b', 'fas fa-question', obj.permission_status))
        return format_html(
            '<span class="badge" style="background-color: {}; color: #fff; padding: 4px 8px;">'
            '<i class="{} mr-1"></i>{}'
            '</span>',
            color, icon, label
        )

    @admin.display(description='Features')
    def event_badges(self, obj):
        badges = []
        if obj.has_dj_campfire:
            badges.append('<span class="badge" style="background-color: #7c3aed; color: #fff; font-size: 10px;"><i class="fas fa-fire mr-1"></i>DJ Campfire</span>')
        badges.append(f'<span class="badge" style="background-color: #334155; color: #fff; font-size: 10px;"><i class="fas fa-bus mr-1"></i>{obj.bus_count} Bus</span>')
        return mark_safe(' '.join(badges))

    @admin.display(description='Status')
    def status_badge(self, obj):
        colors = {
            'inquiry': ('#64748b', 'Inquiry'),
            'letter_submitted': ('#0284c7', 'Letter Submitted'),
            'confirmed': ('#059669', 'Confirmed'),
            'on_tour': ('#f59e0b', 'On Tour'),
            'completed': ('#10b981', 'Completed'),
            'cancelled': ('#ef4444', 'Cancelled'),
        }
        color, label = colors.get(obj.status, ('#64748b', obj.status))
        return format_html(
            '<span class="badge" style="background-color: {}; color: #fff; padding: 4px 8px;">{}</span>',
            color, label
        )

    @admin.display(description='Quick Actions')
    def quick_actions(self, obj):
        from packages.models import TourPassengerManifest
        manifest_count = TourPassengerManifest.objects.filter(iv_expedition=obj).count()
        manifest_color = '#059669' if manifest_count > 0 else '#d97706'

        buttons = [
            f'<a href="/packages/manifest/upload/?iv_id={obj.id}" class="badge" '
            f'style="background-color: #0284c7; color: #fff; padding: 5px 8px; margin-right: 4px; text-decoration: none; border-radius: 4px;" '
            f'title="Import students roster from CSV">'
            f'<i class="fas fa-file-upload mr-1"></i>Import CSV</a>',

            f'<a href="/admin/package_tours/passengermanifestproxy/?iv_expedition__id__exact={obj.id}" class="badge" '
            f'style="background-color: {manifest_color}; color: #fff; padding: 5px 8px; margin-right: 4px; text-decoration: none; border-radius: 4px;" '
            f'title="View student passenger roster">'
            f'<i class="fas fa-users mr-1"></i>Roster ({manifest_count})</a>',
        ]
        if obj.linked_trip:
            buttons.append(
                f'<a href="/admin/operations/trip/{obj.linked_trip.id}/change/" class="badge" '
                f'style="background-color: #059669; color: #fff; padding: 5px 8px; margin-right: 4px; text-decoration: none; border-radius: 4px;" '
                f'title="View Live Operations Trip">'
                f'<i class="fas fa-route mr-1"></i>{obj.linked_trip.trip_id}</a>'
            )
            buttons.append(
                f'<a href="/admin/finance/driveradvance/add/?trip={obj.linked_trip.id}" class="badge" '
                f'style="background-color: #d97706; color: #fff; padding: 5px 8px; margin-right: 4px; text-decoration: none; border-radius: 4px;" '
                f'title="Cash Advance Desk">'
                f'<i class="fas fa-hand-holding-usd mr-1"></i>Cash Desk</a>'
            )
        if obj.package_id:
            buttons.append(
                f'<a href="/packages/quote/{obj.package_id}/" target="_blank" class="badge" '
                f'style="background-color: #7c3aed; color: #fff; padding: 5px 8px; margin-right: 4px; text-decoration: none; border-radius: 4px;" '
                f'title="Print Tour Proposal Quotation">'
                f'<i class="fas fa-file-pdf mr-1"></i>Proposal</a>'
            )
        buttons.append(
            f'<a href="/packages/manifest/{obj.id}/rooming-list/" target="_blank" class="badge" '
            f'style="background-color: #0d9488; color: #fff; padding: 5px 8px; text-decoration: none; border-radius: 4px;" '
            f'title="Print Rooming List & Coach Seating Manifest">'
            f'<i class="fas fa-bed mr-1"></i>Rooming List</a>'
        )
        return mark_safe(' '.join(buttons))


# ==============================================================================
# 2. Tour Bus Departure Batches Admin
# ==============================================================================

@admin.register(TourDepartureBatchProxy)
class TourDepartureBatchAdmin(admin.ModelAdmin):
    list_display = (
        'package_display', 'departure_date_display', 'vehicle_badge',
        'driver_badge', 'seat_gauge', 'status_badge', 'quick_actions'
    )
    list_filter = ('status', 'departure_date', 'package')
    search_fields = ('package__name', 'assigned_vehicle__registration_number', 'assigned_driver__name')
    date_hierarchy = 'departure_date'
    actions = [mark_departure_open, dispatch_batch_to_operations_trip]
    inlines = [BoardingPointInline, PassengerManifestInline, HotelAllotmentInline]

    class Media:
        css = {
            'all': ('packages/css/package_admin_custom.css',)
        }
        js = ('packages/js/departures_iv_dynamic.js',)

    @admin.display(description='Tour Package')
    def package_display(self, obj):
        return format_html(
            '<span style="font-weight: 700; color: #f8fafc;"><i class="fas fa-map-marked-alt mr-1" style="color: #38bdf8;"></i>{}</span>',
            obj.package.name
        )

    @admin.display(description='Departure & Return')
    def departure_date_display(self, obj):
        ret_str = f" → {obj.return_date.strftime('%d/%m/%y')}" if obj.return_date else ""
        return format_html(
            '<span style="color: #cbd5e1; font-size: 12px;"><i class="far fa-calendar-check mr-1 text-success"></i>{}{}'
            '</span>',
            obj.departure_date.strftime('%d/%m/%y'), ret_str
        )

    @admin.display(description='Vehicle')
    def vehicle_badge(self, obj):
        if obj.assigned_vehicle:
            return format_html(
                '<span class="badge" style="background-color: #0284c7; color: #fff; padding: 4px 8px;">'
                '<i class="fas fa-bus mr-1"></i>{}'
                '</span>',
                obj.assigned_vehicle.registration_number
            )
        return mark_safe('<span style="color: #f59e0b;">⚠️ Unassigned</span>')

    @admin.display(description='Driver')
    def driver_badge(self, obj):
        if obj.assigned_driver:
            return format_html(
                '<span style="color: #93c5fd; font-weight: 500;"><i class="fas fa-user-tie mr-1"></i>{}</span>',
                obj.assigned_driver.name
            )
        return mark_safe('<span style="color: #64748b;">—</span>')

    @admin.display(description='Seat Availability')
    def seat_gauge(self, obj):
        color = '#059669' if obj.available_seats > 10 else ('#d97706' if obj.available_seats > 0 else '#dc2626')
        return format_html(
            '<span style="color: {}; font-weight: 700; font-size: 13px;">{} Free</span> '
            '<small style="color: #94a3b8;">({} Booked / {} Total)</small>',
            color, obj.available_seats, obj.booked_seats, obj.total_seats
        )

    @admin.display(description='Status')
    def status_badge(self, obj):
        colors = {
            'open': ('#059669', 'Open'),
            'fast_filling': ('#d97706', 'Fast Filling'),
            'sold_out': ('#dc2626', 'Sold Out'),
            'departed': ('#0284c7', 'Departed'),
            'completed': ('#10b981', 'Completed'),
            'cancelled': ('#ef4444', 'Cancelled'),
        }
        color, label = colors.get(obj.status, ('#64748b', obj.status))
        return format_html(
            '<span class="badge" style="background-color: {}; color: #fff; padding: 4px 8px;">{}</span>',
            color, label
        )

    @admin.display(description='Quick Actions')
    def quick_actions(self, obj):
        from operations.models import Trip
        trip = Trip.objects.filter(package_inventory=obj).first()
        buttons = [
            f'<a href="/admin/package_tours/passengermanifestproxy/?departure__id__exact={obj.id}" class="badge" '
            f'style="background-color: #0284c7; color: #fff; padding: 5px 8px; margin-right: 4px; text-decoration: none; border-radius: 4px;" '
            f'title="View passenger manifest for this departure batch">'
            f'<i class="fas fa-clipboard-list mr-1"></i>Manifest</a>',
        ]
        if trip:
            buttons.append(
                f'<a href="/admin/operations/trip/{trip.id}/change/" class="badge" '
                f'style="background-color: #059669; color: #fff; padding: 5px 8px; margin-right: 4px; text-decoration: none; border-radius: 4px;" '
                f'title="View Live Operations Trip">'
                f'<i class="fas fa-route mr-1"></i>{trip.trip_id}</a>'
            )
            buttons.append(
                f'<a href="/admin/finance/driveradvance/add/?trip={trip.id}" class="badge" '
                f'style="background-color: #d97706; color: #fff; padding: 5px 8px; margin-right: 4px; text-decoration: none; border-radius: 4px;" '
                f'title="Trip Cash Desk & Driver Advance">'
                f'<i class="fas fa-hand-holding-usd mr-1"></i>Cash Desk</a>'
            )
        if obj.package_id:
            buttons.append(
                f'<a href="/packages/quote/{obj.package_id}/" target="_blank" class="badge" '
                f'style="background-color: #059669; color: #fff; padding: 5px 8px; text-decoration: none; border-radius: 4px;" '
                f'title="Print Tour Proposal">'
                f'<i class="fas fa-file-pdf mr-1"></i>Proposal</a>'
            )
        return mark_safe(' '.join(buttons))


# ==============================================================================
# 3. Boarding Points Admin
# ==============================================================================

@admin.register(BoardingPointProxy)
class BoardingPointAdmin(admin.ModelAdmin):
    list_display = ('stop_order_badge', 'stop_name', 'departure_link', 'pickup_time_display', 'landmark', 'coordinator_phone')
    list_filter = ('departure__package', 'departure')
    search_fields = ('stop_name', 'landmark', 'coordinator_phone')
    ordering = ('departure', 'stop_order')

    @admin.display(description='Order')
    def stop_order_badge(self, obj):
        return format_html(
            '<span class="badge" style="background-color: #0f766e; color: #fff; padding: 3px 8px;">Stop #{}</span>',
            obj.stop_order
        )

    @admin.display(description='Departure Batch')
    def departure_link(self, obj):
        return format_html(
            '<a href="/admin/package_tours/tourdeparturebatchproxy/{}/change/" style="color: #38bdf8; text-decoration: none;">'
            '{} ({})'
            '</a>',
            obj.departure.id, obj.departure.package.name, obj.departure.departure_date.strftime('%d/%m/%y')
        )

    @admin.display(description='Pickup Time')
    def pickup_time_display(self, obj):
        return format_html(
            '<span style="color: #fbbf24; font-weight: 700;"><i class="far fa-clock mr-1"></i>{}</span>',
            obj.pickup_time.strftime('%I:%M %p')
        )


# ==============================================================================
# 4. Tour Passenger Manifest & Rooming List Admin
# ==============================================================================


@admin.action(description="✅ Auto-Assign Bus, Seat & Room (from Manifest list)")
def auto_assign_bus_seat_room_manifest(modeladmin, request, queryset):
    """Auto-assigns Bus, Seat & Room for all passengers belonging to the same
    IV expedition as the selected passengers. Select any row from an expedition
    and the entire expedition will be re-assigned."""
    from packages.manifest_autoassign import auto_assign_for_expedition
    iv_ids = queryset.filter(iv_expedition__isnull=False).values_list('iv_expedition_id', flat=True).distinct()
    if not iv_ids:
        modeladmin.message_user(request, "⚠️ No College IV expedition found among selected passengers. Please filter by iv_expedition first.", level='warning')
        return
    for iv_id in iv_ids:
        result = auto_assign_for_expedition(iv_id)
        if 'error' in result:
            modeladmin.message_user(request, f"❌ {result['error']}", level='error')
        else:
            modeladmin.message_user(
                request,
                f"🎉 {result['expedition']}: {result['total_passengers']} passengers auto-assigned! "
                f"({result['male_students_assigned']} Boys + {result['female_students_assigned']} Girls + {result['faculty_assigned']} Faculty)"
            )

@admin.register(PassengerManifestProxy)
class PassengerManifestAdmin(admin.ModelAdmin):
    list_display = (
        'passenger_name', 'roll_number_display', 'category_badge', 'gender_badge',
        'bus_badge', 'seat_badge', 'room_badge', 'aadhaar_display', 'contact_display'
    )
    list_filter = ('category', 'gender', 'bus_assignment', 'iv_expedition', 'departure')
    search_fields = ('passenger_name', 'roll_number', 'aadhaar_number', 'bus_assignment', 'seat_number', 'room_sharing_number', 'phone', 'emergency_contact')
    actions = [upload_manifest_redirect, download_template_redirect, auto_assign_bus_seat_room_manifest, export_buswise_manifest_csv, export_rooming_list_csv]
    list_per_page = 50
    show_full_result_count = True

    fieldsets = (
        ('Passenger Profile & Category', {
            'fields': (
                ('passenger_name', 'roll_number'),
                ('category', 'gender'),
                ('age', 'phone'),
            )
        }),
        ('Tour Convoy, Seat & Rooming', {
            'fields': (
                ('bus_assignment', 'seat_number'),
                'room_sharing_number',
                ('iv_expedition', 'departure', 'boarding_point'),
            )
        }),
        ('✈️ Flight & High-Speed Rail Security Check-in', {
            'fields': (
                ('aadhaar_number', 'ticket_or_pnr_status'),
            ),
            'classes': ('grp-flybus-specs',),
            'description': 'Mandatory Aadhaar / Govt Photo ID & Group Airline Ticket PNR status for domestic flights.'
        }),
        ('✈️ International Travel Documents (Passport & Visa)', {
            'fields': (
                ('passport_number', 'passport_expiry_date'),
                'visa_number',
            ),
            'classes': ('grp-international-specs',),
            'description': 'Applicable for International Tours (Requires min 6 months validity from departure date).'
        }),
        ('Special Care & Emergency Contact', {
            'fields': (
                'senior_assistance_needed',
                'emergency_contact',
            )
        }),
    )

    class Media:
        css = {
            'all': ('packages/css/package_admin_custom.css',)
        }
        js = ('packages/js/manifest_dynamic_form.js',)

    @admin.display(description='Roll # / ID')
    def roll_number_display(self, obj):
        if obj.roll_number:
            return format_html('<span style="font-family: monospace; color: #38bdf8; font-weight: 600;">{}</span>', obj.roll_number)
        return mark_safe('<span style="color: #64748b;">—</span>')

    @admin.display(description='Bus')
    def bus_badge(self, obj):
        if obj.bus_assignment:
            return format_html(
                '<span class="badge" style="background-color: #0284c7; color: #fff; padding: 4px 8px; font-size: 11px;">'
                '<i class="fas fa-bus mr-1"></i>{}</span>',
                obj.bus_assignment
            )
        return mark_safe('<span style="color: #64748b;">—</span>')

    @admin.display(description='Category')
    def category_badge(self, obj):
        colors = {
            'student': ('#3b82f6', 'fas fa-user-graduate', 'Student'),
            'faculty': ('#059669', 'fas fa-chalkboard-teacher', 'Faculty (Free)'),
            'adult': ('#0284c7', 'fas fa-user', 'Adult'),
            'child': ('#f59e0b', 'fas fa-child', 'Child'),
            'senior': ('#8b5cf6', 'fas fa-blind', 'Senior'),
        }
        color, icon, label = colors.get(obj.category, ('#64748b', 'fas fa-user', obj.category))
        return format_html(
            '<span class="badge" style="background-color: {}; color: #fff; padding: 4px 8px; font-size: 11px;">'
            '<i class="{} mr-1"></i>{}'
            '</span>',
            color, icon, label
        )

    @admin.display(description='Gender')
    def gender_badge(self, obj):
        if obj.gender == 'female':
            return mark_safe('<span style="color: #ec4899; font-weight: 600;"><i class="fas fa-female mr-1"></i>Female</span>')
        return mark_safe('<span style="color: #60a5fa; font-weight: 600;"><i class="fas fa-male mr-1"></i>Male</span>')

    @admin.display(description='Seat #')
    def seat_badge(self, obj):
        if obj.seat_number:
            return format_html(
                '<span class="badge" style="background-color: #334155; color: #f8fafc; border: 1px solid #475569; padding: 4px 8px;">'
                '<i class="fas fa-chair mr-1 text-warning"></i>{}'
                '</span>',
                obj.seat_number
            )
        return mark_safe('<span style="color: #64748b;">Unassigned</span>')

    @admin.display(description='Room Allocation')
    def room_badge(self, obj):
        if obj.room_sharing_number:
            return format_html(
                '<span style="color: #f1f5f9; font-size: 12px;"><i class="fas fa-bed mr-1 text-info"></i>{}</span>',
                obj.room_sharing_number
            )
        return mark_safe('<span style="color: #64748b;">—</span>')

    @admin.display(description='Boarding Stop')
    def boarding_point_display(self, obj):
        if obj.boarding_point:
            return format_html(
                '<span style="color: #cbd5e1; font-size: 12px;"><i class="fas fa-map-pin mr-1 text-danger"></i>{}</span>',
                obj.boarding_point.stop_name
            )
        return mark_safe('<span style="color: #64748b;">—</span>')

    @admin.display(description='Tour Batch')
    def departure_display(self, obj):
        return format_html(
            '<span style="color: #93c5fd; font-size: 12px;">{} ({})</span>',
            obj.departure.package.name, obj.departure.departure_date.strftime('%d/%m/%y')
        )

    @admin.display(description='Aadhaar / PNR')
    def aadhaar_display(self, obj):
        if obj.aadhaar_number:
            status_dot = "🟢" if obj.ticket_or_pnr_status == 'Confirmed' else "🟡"
            return format_html(
                '<span style="font-family: monospace; font-size: 11px; color: #cbd5e1;">'
                '<i class="fas fa-id-card text-info mr-1"></i>{}</span><br>'
                '<small style="color: #94a3b8;">{} {}</small>',
                obj.aadhaar_number, status_dot, obj.ticket_or_pnr_status or ''
            )
        return mark_safe('<span style="color: #64748b;">—</span>')

    @admin.display(description='Contact')
    def contact_display(self, obj):
        if obj.phone:
            return format_html(
                '<span style="color: #f1f5f9; font-size: 12px;"><i class="fas fa-phone mr-1 text-success"></i>{}</span>',
                obj.phone
            )
        return mark_safe('<span style="color: #64748b;">—</span>')


# ==============================================================================
# 5. Hotel Room Block Allotments Admin
# ==============================================================================

@admin.register(HotelAllotmentProxy)
class HotelAllotmentAdmin(admin.ModelAdmin):
    list_display = ('hotel_name', 'package_link', 'room_category_badge', 'date_range_display', 'occupancy_gauge', 'cost_display', 'status_badge')
    list_filter = ('room_category', 'status', 'package')
    search_fields = ('hotel_name', 'package__name', 'confirmation_voucher_no')

    @admin.display(description='Tour Package')
    def package_link(self, obj):
        return format_html(
            '<a href="/admin/packages/package/{}/change/" style="color: #38bdf8; text-decoration: none; font-weight: 500;">{}</a>',
            obj.package.id, obj.package.name
        )

    @admin.display(description='Room Category')
    def room_category_badge(self, obj):
        return format_html(
            '<span class="badge" style="background-color: #334155; color: #f8fafc; border: 1px solid #475569; padding: 4px 8px;">'
            '<i class="fas fa-bed mr-1 text-warning"></i>{}</span>',
            obj.get_room_category_display()
        )

    @admin.display(description='Stay Period')
    def date_range_display(self, obj):
        return format_html(
            '<span style="color: #cbd5e1; font-size: 12px;">{} → {} ({}N)</span>',
            obj.check_in_date.strftime('%d/%m/%y'), obj.check_out_date.strftime('%d/%m/%y'), obj.nights_count
        )

    @admin.display(description='Room Occupancy')
    def occupancy_gauge(self, obj):
        color = '#10b981' if obj.occupancy_rate >= 80 else ('#f59e0b' if obj.occupancy_rate >= 50 else '#38bdf8')
        return format_html(
            '<span style="color: {}; font-weight: 700; font-size: 13px;">{}/{} Rooms ({}%)</span><br>'
            '<small style="color: #94a3b8;">{} Available</small>',
            color, obj.rooms_occupied, obj.rooms_blocked, f"{obj.occupancy_rate:.0f}", obj.rooms_available
        )

    @admin.display(description='Rate & Total Cost')
    def cost_display(self, obj):
        return format_html(
            '<span style="color: #f1f5f9; font-weight: 600;">₹{} / night</span><br>'
            '<small style="color: #94a3b8;">Total: ₹{}</small>',
            f"{obj.cost_per_room_night:,.0f}", f"{obj.total_cost:,.0f}"
        )

    @admin.display(description='Status')
    def status_badge(self, obj):
        colors = {
            'blocked': ('#d97706', 'Tentative Block'),
            'confirmed': ('#059669', 'Confirmed'),
            'partially_released': ('#f59e0b', 'Partially Released'),
            'billed': ('#0284c7', 'Billed'),
            'cancelled': ('#ef4444', 'Cancelled'),
        }
        color, label = colors.get(obj.status, ('#64748b', obj.status))
        return format_html('<span class="badge" style="background-color: {}; color: #fff; padding: 4px 8px;">{}</span>', color, label)


# ==============================================================================
# 6. Customer Reviews & Quality NPS Governance Admin
# ==============================================================================

@admin.register(TourFeedbackProxy)
class TourFeedbackProxyAdmin(admin.ModelAdmin):
    list_display = (
        'guest_name_display', 'package_link', 'trip_date',
        'star_rating_display', 'dimension_scores_display', 'nps_badge',
        'flag_status_badge', 'verified_badge'
    )
    list_filter = ('overall_rating', 'flag_status', 'is_verified', 'trip_date', 'package')
    search_fields = ('guest_name', 'guest_phone', 'customer_review_text', 'package__name')
    date_hierarchy = 'trip_date'
    actions = ['mark_feedback_verified', 'resolve_quality_complaint']

    @admin.action(description="✅ Mark selected feedback as Verified")
    def mark_feedback_verified(self, request, queryset):
        queryset.update(is_verified=True)
        self.message_user(request, f"{queryset.count()} review(s) marked as verified.")

    @admin.action(description="🎉 Mark complaints as Resolved by Management")
    def resolve_quality_complaint(self, request, queryset):
        queryset.update(flag_status='resolved')
        self.message_user(request, f"{queryset.count()} complaint(s) marked as resolved.")

    @admin.display(description='Customer')
    def guest_name_display(self, obj):
        phone_str = f"<br><small style='color: #94a3b8;'>{obj.guest_phone}</small>" if obj.guest_phone else ""
        return format_html(
            '<span style="font-weight: 700; color: #f8fafc;"><i class="fas fa-user-check text-success mr-1"></i>{}</span>{}',
            obj.guest_name, mark_safe(phone_str)
        )

    @admin.display(description='Tour Package')
    def package_link(self, obj):
        return format_html(
            '<a href="/admin/packages/package/{}/change/" style="color: #38bdf8; text-decoration: none; font-weight: 500;">{}</a>',
            obj.package.id, obj.package.name
        )

    @admin.display(description='Overall Rating')
    def star_rating_display(self, obj):
        stars = "★" * obj.overall_rating + "☆" * (5 - obj.overall_rating)
        color = '#fbbf24' if obj.overall_rating >= 4 else ('#f59e0b' if obj.overall_rating == 3 else '#ef4444')
        return format_html(
            '<span style="color: {}; font-size: 14px; font-weight: 700;">{}</span> '
            '<small style="color: #94a3b8;">({}/5)</small>',
            color, stars, obj.overall_rating
        )

    @admin.display(description='5D Quality Scores')
    def dimension_scores_display(self, obj):
        return format_html(
            '<small style="color: #cbd5e1;">Coach: <b>{}★</b> | Hotel: <b>{}★</b> | Food: <b>{}★</b> | Route: <b>{}★</b></small>',
            obj.coach_driver_rating, obj.hotel_rating, obj.food_rating, obj.schedule_rating
        )

    @admin.display(description='NPS Score')
    def nps_badge(self, obj):
        colors = {
            'Promoter 🟢': '#059669',
            'Passive 🟡': '#d97706',
            'Detractor 🔴': '#dc2626',
        }
        cat = obj.nps_category
        return format_html(
            '<span class="badge" style="background-color: {}; color: #fff; padding: 4px 8px;">NPS {} ({})</span>',
            colors.get(cat, '#334155'), obj.nps_score, cat
        )

    @admin.display(description='Quality Status')
    def flag_status_badge(self, obj):
        colors = {
            'positive': ('#059669', 'Positive'),
            'neutral': ('#64748b', 'Neutral'),
            'escalated_complaint': ('#dc2626', 'Escalated Complaint'),
            'resolved': ('#10b981', 'Resolved'),
        }
        color, label = colors.get(obj.flag_status, ('#64748b', obj.flag_status))
        return format_html(
            '<span class="badge" style="background-color: {}; color: #fff; padding: 4px 8px;">{}</span>',
            color, label
        )

    @admin.display(description='Verified')
    def verified_badge(self, obj):
        if obj.is_verified:
            return mark_safe('<span style="color: #10b981;"><i class="fas fa-check-circle"></i> Verified</span>')
        return mark_safe('<span style="color: #94a3b8;">Unverified</span>')


# ==============================================================================
# 7. Seasonal Pricing & Peak Tariffs Admin
# ==============================================================================

@admin.register(SeasonalRateProxy)
class SeasonalRateProxyAdmin(admin.ModelAdmin):
    list_display = ('season_name', 'package_link', 'season_type_badge', 'date_range_display', 'surge_badge', 'override_prices_display', 'is_active')
    list_filter = ('season_type', 'is_active', 'package')
    search_fields = ('season_name', 'package__name')

    @admin.display(description='Tour Package')
    def package_link(self, obj):
        return format_html(
            '<a href="/admin/packages/package/{}/change/" style="color: #38bdf8; text-decoration: none; font-weight: 500;">{}</a>',
            obj.package.id, obj.package.name
        )

    @admin.display(description='Season Type')
    def season_type_badge(self, obj):
        colors = {
            'peak': ('#ef4444', 'fas fa-fire', 'Peak Season'),
            'festival': ('#f59e0b', 'fas fa-calendar-star', 'Festival'),
            'weekend': ('#3b82f6', 'fas fa-umbrella-beach', 'Weekend'),
            'off_peak': ('#06b6d4', 'fas fa-snowflake', 'Off-Peak'),
        }
        color, icon, label = colors.get(obj.season_type, ('#64748b', 'fas fa-tag', obj.season_type))
        return format_html(
            '<span class="badge" style="background-color: {}; color: #fff; padding: 4px 8px;">'
            '<i class="{} mr-1"></i>{}</span>',
            color, icon, label
        )

    @admin.display(description='Date Range')
    def date_range_display(self, obj):
        return format_html(
            '<span style="color: #e2e8f0; font-size: 12px;"><i class="far fa-calendar-alt text-info mr-1"></i>{} → {}</span>',
            obj.start_date.strftime('%d/%m/%y'), obj.end_date.strftime('%d/%m/%y')
        )

    @admin.display(description='Surge Multiplier')
    def surge_badge(self, obj):
        sign = "+" if obj.surge_percentage >= 0 else ""
        color = '#ef4444' if obj.surge_percentage > 0 else ('#10b981' if obj.surge_percentage < 0 else '#64748b')
        return format_html(
            '<span class="badge" style="background-color: {}; color: #fff; padding: 4px 8px; font-weight: 700;">{}{}%</span>',
            color, sign, obj.surge_percentage
        )

    @admin.display(description='Price Overrides')
    def override_prices_display(self, obj):
        if obj.price_with_food_override:
            return format_html('<span style="color: #10b981; font-weight: 600;">₹{} (Food)</span>', f"{obj.price_with_food_override:,.0f}")
        return mark_safe('<span style="color: #64748b;">Formula Multiplier</span>')


# ==============================================================================
# 8. Experience & Safari Add-Ons Admin
# ==============================================================================

@admin.register(PackageAddonProxy)
class PackageAddonProxyAdmin(admin.ModelAdmin):
    list_display = ('title', 'package_link', 'category_badge', 'pricing_unit', 'cost_price_display', 'selling_price_display', 'margin_badge', 'is_mandatory_inclusion', 'is_active')
    list_filter = ('category', 'pricing_unit', 'is_mandatory_inclusion', 'is_active', 'package')
    search_fields = ('title', 'package__name')

    @admin.display(description='Tour Package')
    def package_link(self, obj):
        return format_html(
            '<a href="/admin/packages/package/{}/change/" style="color: #38bdf8; text-decoration: none; font-weight: 500;">{}</a>',
            obj.package.id, obj.package.name
        )

    @admin.display(description='Category')
    def category_badge(self, obj):
        return format_html('<span class="badge" style="background-color: #0369a1; color: #fff; padding: 4px 8px;">{}</span>', obj.get_category_display())

    @admin.display(description='Procurement Cost')
    def cost_price_display(self, obj):
        return format_html('<span style="color: #f87171;">₹{}</span>', f"{(obj.cost_price or 0):,.0f}")

    @admin.display(description='Selling Rate')
    def selling_price_display(self, obj):
        return format_html('<span style="color: #38bdf8; font-weight: 700;">₹{}</span>', f"{(obj.selling_price or 0):,.0f}")

    @admin.display(description='Margin')
    def margin_badge(self, obj):
        return format_html(
            '<span class="badge" style="background-color: #059669; color: #fff; padding: 4px 8px;">'
            '+₹{} ({}%)</span>',
            f"{obj.margin_per_unit:,.0f}", f"{obj.margin_percentage:.1f}"
        )


# ==============================================================================
# 9. B2B Reseller Tiers & Margins Admin
# ==============================================================================

@admin.register(B2BMarginProxy)
class B2BMarginProxyAdmin(admin.ModelAdmin):
    list_display = ('tier_name_badge', 'package_link', 'commission_display', 'b2b_net_rates_display', 'is_active')
    list_filter = ('tier_name', 'is_active', 'package')
    search_fields = ('package__name',)

    @admin.display(description='B2B Partner Tier')
    def tier_name_badge(self, obj):
        return format_html('<span class="badge" style="background-color: #475569; color: #fff; padding: 4px 8px;">{}</span>', obj.get_tier_name_display())

    @admin.display(description='Tour Package')
    def package_link(self, obj):
        return format_html(
            '<a href="/admin/packages/package/{}/change/" style="color: #38bdf8; text-decoration: none;">{}</a>',
            obj.package.id, obj.package.name
        )

    @admin.display(description='Commission / Discount')
    def commission_display(self, obj):
        if obj.fixed_discount_per_pax > 0:
            return format_html('<span style="color: #10b981; font-weight: 700;">Flat ₹{} Off/pax</span>', f"{obj.fixed_discount_per_pax:,.0f}")
        return format_html('<span style="color: #10b981; font-weight: 700;">{}% Commission</span>', obj.commission_percent)

    @admin.display(description='B2B Net Buying Price')
    def b2b_net_rates_display(self, obj):
        return format_html(
            '<span style="color: #38bdf8; font-weight: 600;">₹{} (With Food)</span> | '
            '<span style="color: #94a3b8;">₹{} (No Food)</span>',
            f"{obj.net_b2b_rate_with_food:,.0f}", f"{obj.net_b2b_rate_without_food:,.0f}"
        )
