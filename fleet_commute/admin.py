from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline, StackedInline
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils import timezone
import datetime

from fleet_contracts.models import RouteStop as BaseRouteStop, NightSafetyEscortLog as BaseNightSafetyEscortLog
from .models import (
    CommuteRoute,
    RouteStop,
    CommuteShift,
    CommuterManifestProxy,
    DailyTripLog,
    NightSafetyEscort,
    CommuterBoardingPass,
    ESGCarbonMetric,
)


# ==============================================================================
# Inlines
# ==============================================================================

class RouteStopInline(TabularInline):
    model = BaseRouteStop
    extra = 1
    fields = ('stop_order', 'name', 'scheduled_offset_minutes', 'pickup_landmark', 'expected_passenger_count', 'is_active')
    ordering = ('stop_order',)


class NightSafetyEscortInline(StackedInline):
    model = BaseNightSafetyEscortLog
    extra = 0
    fields = (
        ('escort_guard_name', 'security_agency', 'guard_badge_number'),
        ('guard_contact_phone', 'female_passengers_count'),
        ('first_pickup_time', 'last_female_drop_time', 'last_drop_verification_status'),
        'safe_drop_confirmed_by', 'remarks'
    )


# ==============================================================================
# Bulk Actions
# ==============================================================================

@admin.action(description="✅ Mark selected trip logs as Completed")
def mark_trips_completed(modeladmin, request, queryset):
    updated = queryset.filter(status__in=['scheduled', 'en_route', 'delayed']).update(status='completed')
    modeladmin.message_user(request, f"{updated} trip log(s) marked as completed.")


@admin.action(description="❌ Mark selected trip logs as Cancelled")
def mark_trips_cancelled(modeladmin, request, queryset):
    updated = queryset.exclude(status='completed').update(status='cancelled')
    modeladmin.message_user(request, f"{updated} trip log(s) marked as cancelled.")


@admin.action(description="📞 Confirm Safe Drop verification via Call")
def mark_safe_drop_verified(modeladmin, request, queryset):
    updated = queryset.update(last_drop_verification_status='verified_call')
    modeladmin.message_user(request, f"{updated} escort record(s) verified.")


# ==============================================================================
# 1. Commute Route Admin
# ==============================================================================

@admin.register(CommuteRoute)
class CommuteRouteAdmin(ModelAdmin):
    list_display = (
        'name_display', 'contract_link', 'path_display',
        'distance_badge', 'stops_count', 'rate_display', 'is_active_badge'
    )
    list_filter = ('contract', 'is_active')
    search_fields = ('name', 'origin', 'destination', 'contract__name')
    inlines = [RouteStopInline]

    @admin.display(description='Route Name')
    def name_display(self, obj):
        return format_html(
            '<span class="font-semibold text-slate-900 dark:text-slate-100"><i class="fas fa-route mr-1 text-sky-600 dark:text-sky-400"></i>{}</span>',
            obj.name
        )

    @admin.display(description='Contract')
    def contract_link(self, obj):
        return format_html(
            '<a href="/admin/fleet_contracts/transportcontract/{}/change/" class="text-sky-700 dark:text-sky-400 font-medium hover:underline">'
            '<i class="fas fa-building mr-1"></i>{}'
            '</a>',
            obj.contract.id, obj.contract.name
        )

    @admin.display(description='Origin → Destination')
    def path_display(self, obj):
        if obj.origin or obj.destination:
            return format_html(
                '<span class="text-xs text-slate-700 dark:text-slate-300">{} <i class="fas fa-long-arrow-alt-right text-sky-600 mx-1"></i> {}</span>',
                obj.origin or 'Origin', obj.destination or 'Campus'
            )
        return mark_safe('<span style="color: #64748b;">—</span>')

    @admin.display(description='Distance')
    def distance_badge(self, obj):
        if not obj.distance_km:
            return mark_safe('<span style="color: #94a3b8;">—</span>')
        return format_html(
            '<span class="badge" style="background-color: #334155; color: #f8fafc; border: 1px solid #475569; padding: 4px 8px; font-size: 12px;">'
            '<i class="fas fa-tachometer-alt mr-1"></i>{} km'
            '</span>',
            obj.distance_km
        )

    @admin.display(description='Stops / Nodes')
    def stops_count(self, obj):
        count = obj.stops.count()
        return format_html(
            '<span class="badge" style="background-color: #0369a1; color: #fff; padding: 4px 8px; font-size: 11px;">'
            '<i class="fas fa-map-marker-alt mr-1"></i>{} Stops'
            '</span>',
            count
        )

    @admin.display(description='Rate Override')
    def rate_display(self, obj):
        if not obj.rate_override:
            return mark_safe('<span class="badge" style="background-color: #1e293b; color: #94a3b8; padding: 3px 6px; font-size: 11px;">Default</span>')
        return format_html(
            '<span style="color: #38bdf8; font-weight: 600;">₹{}</span>',
            f"{obj.rate_override:,.0f}"
        )

    @admin.display(description='Active')
    def is_active_badge(self, obj):
        if obj.is_active:
            return mark_safe('<span class="badge" style="background-color: #059669; color: #fff;">Active</span>')
        return mark_safe('<span class="badge" style="background-color: #64748b; color: #fff;">Inactive</span>')


# ==============================================================================
# 2. Route Stop Admin
# ==============================================================================

@admin.register(RouteStop)
class RouteStopAdmin(ModelAdmin):
    list_display = ('stop_order_badge', 'name', 'route_link', 'offset_display', 'expected_passenger_count', 'is_active')
    list_filter = ('route__contract', 'route', 'is_active')
    search_fields = ('name', 'pickup_landmark', 'route__name')
    ordering = ('route', 'stop_order')

    @admin.display(description='Seq #')
    def stop_order_badge(self, obj):
        return format_html(
            '<span class="badge" style="background-color: #0f766e; color: #fff; font-size: 12px; padding: 3px 8px;">'
            'Stop #{}'
            '</span>',
            obj.stop_order
        )

    @admin.display(description='Route')
    def route_link(self, obj):
        return format_html(
            '<a href="/admin/fleet_commute/commuteroute/{}/change/" style="color: #38bdf8; text-decoration: none;">{}</a>',
            obj.route.id, obj.route.name
        )

    @admin.display(description='Offset Time')
    def offset_display(self, obj):
        return format_html(
            '<span style="color: #fbbf24; font-weight: 600;"><i class="far fa-clock mr-1"></i>+{} mins</span>',
            obj.scheduled_offset_minutes
        )


# ==============================================================================
# 3. Commute Shift Admin
# ==============================================================================

@admin.register(CommuteShift)
class CommuteShiftAdmin(ModelAdmin):
    list_display = ('shift_label', 'route_display', 'direction_pill', 'timing_display', 'days_of_week', 'escort_pill')
    list_filter = ('direction', 'escort_guard_required', 'route__contract')
    search_fields = ('shift_name', 'route__name')

    @admin.display(description='Shift Title')
    def shift_label(self, obj):
        name = obj.shift_name or f"Shift @ {obj.timing.strftime('%I:%M %p')}"
        return format_html('<span class="font-semibold text-slate-900 dark:text-slate-100">{}</span>', name)

    @admin.display(description='Route')
    def route_display(self, obj):
        return format_html(
            '<span class="text-sky-700 dark:text-sky-300 font-medium">{}</span> <small class="text-xs text-slate-500 dark:text-slate-400">({})</small>',
            obj.route.name, obj.route.contract.name
        )

    @admin.display(description='Direction')
    def direction_pill(self, obj):
        if obj.direction == 'pickup':
            return mark_safe(
                '<span class="badge" style="background-color: #059669; color: #fff; padding: 4px 10px; font-size: 11px;">'
                '⬆️ Pickup (To Campus)'
                '</span>'
            )
        return mark_safe(
            '<span class="badge" style="background-color: #dc2626; color: #fff; padding: 4px 10px; font-size: 11px;">'
            '⬇️ Drop (From Campus)'
            '</span>'
        )

    @admin.display(description='Scheduled Time')
    def timing_display(self, obj):
        time_str = obj.timing.strftime('%I:%M %p')
        return format_html(
            '<span style="color: #38bdf8; font-weight: 700; font-size: 13px;">'
            '<i class="far fa-clock mr-1"></i>{}'
            '</span>',
            time_str
        )

    @admin.display(description='Security Escort')
    def escort_pill(self, obj):
        if obj.escort_guard_required:
            return mark_safe(
                '<span class="badge" style="background-color: #b91c1c; color: #fff; padding: 4px 8px; font-size: 11px;">'
                '<i class="fas fa-shield-alt mr-1"></i>Mandatory Escort'
                '</span>'
            )
        return mark_safe('<span style="color: #64748b; font-size: 11px;">Not Required</span>')


# ==============================================================================
# 4. Commuter & Student Manifest Admin
# ==============================================================================

@admin.register(CommuterManifestProxy)
class CommuterManifestAdmin(ModelAdmin):
    list_display = (
        'name_with_id', 'type_badge', 'gender_badge',
        'contract_link', 'boarding_stop_display', 'emergency_contact_display',
        'escort_flag_badge', 'is_active'
    )
    list_filter = ('commuter_type', 'gender', 'requires_night_escort', 'contract', 'is_active')
    search_fields = ('name', 'commuter_id', 'phone', 'emergency_contact_name', 'department_or_grade')

    fieldsets = (
        ('Commuter Identity', {
            'fields': ('contract', 'commuter_type', 'commuter_id', 'name', 'gender', 'department_or_grade')
        }),
        ('Travel & Boarding Node', {
            'fields': ('boarding_stop', 'requires_night_escort', 'is_active')
        }),
        ('Contact & Emergency Details', {
            'fields': ('phone', 'emergency_contact_name', 'emergency_contact_phone')
        }),
    )

    @admin.display(description='Commuter / Student')
    def name_with_id(self, obj):
        return format_html(
            '<span style="font-weight: 600; color: #f8fafc;">{}</span><br>'
            '<small style="color: #94a3b8;"><i class="fas fa-id-badge mr-1"></i>{}</small>',
            obj.name, obj.commuter_id
        )

    @admin.display(description='Category')
    def type_badge(self, obj):
        colors = {
            'employee': ('#3b82f6', 'fas fa-briefcase', 'Corporate / IT'),
            'student': ('#f59e0b', 'fas fa-user-graduate', 'Student'),
            'worker': ('#8b5cf6', 'fas fa-hard-hat', 'Factory Worker'),
            'staff': ('#10b981', 'fas fa-chalkboard-teacher', 'Staff / Faculty'),
        }
        color, icon, label = colors.get(obj.commuter_type, ('#64748b', 'fas fa-user', obj.commuter_type))
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
        elif obj.gender == 'male':
            return mark_safe('<span style="color: #60a5fa; font-weight: 600;"><i class="fas fa-male mr-1"></i>Male</span>')
        return mark_safe('<span style="color: #94a3b8;">Other</span>')

    @admin.display(description='Contract')
    def contract_link(self, obj):
        return format_html(
            '<a href="/admin/fleet_contracts/transportcontract/{}/change/" style="color: #93c5fd; text-decoration: none;">{}</a>',
            obj.contract.id, obj.contract.name
        )

    @admin.display(description='Boarding Stop')
    def boarding_stop_display(self, obj):
        if obj.boarding_stop:
            return format_html(
                '<span class="text-xs text-slate-800 dark:text-slate-200"><i class="fas fa-map-pin text-amber-500 mr-1"></i>{}</span>',
                obj.boarding_stop.name
            )
        return mark_safe('<span style="color: #64748b;">Not Set</span>')

    @admin.display(description='Emergency Contact')
    def emergency_contact_display(self, obj):
        if obj.emergency_contact_phone:
            return format_html(
                '<span class="text-xs text-slate-700 dark:text-slate-300"><i class="fas fa-phone-alt text-emerald-600 mr-1"></i>{}</span><br>'
                '<small class="text-xs text-slate-500 dark:text-slate-400">{}</small>',
                obj.emergency_contact_phone, obj.emergency_contact_name or 'Emergency'
            )
        return mark_safe('<span style="color: #64748b;">—</span>')

    @admin.display(description='Night Escort')
    def escort_flag_badge(self, obj):
        if obj.requires_night_escort:
            return mark_safe(
                '<span class="badge" style="background-color: #dc2626; color: #fff; padding: 4px 6px; font-size: 11px;">'
                '<i class="fas fa-shield-alt mr-1"></i>Escort Mandate'
                '</span>'
            )
        return mark_safe('<span style="color: #475569;">—</span>')


# ==============================================================================
# 5. Daily Trip Log Admin
# ==============================================================================

@admin.register(DailyTripLog)
class DailyTripLogAdmin(ModelAdmin):
    list_display = (
        'shift_display', 'date', 'vehicle_link', 'driver_link',
        'timing_execution_display', 'km_display', 'passenger_badge',
        'status_badge', 'escort_badge'
    )
    list_filter = ('status', 'date', 'is_replacement_vehicle', 'shift__route__contract')
    search_fields = ('shift__route__name', 'vehicle__registration_number', 'driver__name', 'delay_reason')
    date_hierarchy = 'date'
    actions = [mark_trips_completed, mark_trips_cancelled]
    inlines = [NightSafetyEscortInline]

    fieldsets = (
        ('Shift & Date', {
            'fields': ('shift', 'date', 'status')
        }),
        ('Vehicle & Driver Assignment', {
            'fields': (
                ('vehicle', 'driver'),
                ('is_replacement_vehicle', 'replaced_vehicle')
            )
        }),
        ('Schedule & Actual Timings', {
            'fields': (
                ('scheduled_departure_time', 'actual_departure_time', 'actual_arrival_time'),
                ('delay_minutes', 'delay_reason')
            )
        }),
        ('Kilometers & Allowances', {
            'fields': (
                ('opening_km', 'closing_km'),
                ('passenger_count', 'driver_bata', 'toll_parking_charges')
            )
        }),
    )

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name in ["vehicle", "replaced_vehicle"]:
            from core.models import Vehicle
            kwargs["queryset"] = Vehicle.objects.exclude(status__in=['maintenance', 'inactive'])
        elif db_field.name == "driver":
            from core.models import Driver
            kwargs["queryset"] = Driver.objects.filter(status='active')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    @admin.display(description='Shift / Route')
    def shift_display(self, obj):
        direction_icon = '⬆️' if obj.shift.direction == 'pickup' else '⬇️'
        time_str = obj.shift.timing.strftime('%I:%M %p')
        return format_html(
            '<span class="text-slate-800 dark:text-slate-100 font-medium">{} {}</span><br>'
            '<small class="text-xs text-slate-500 dark:text-slate-400"><i class="far fa-clock mr-1"></i>{}</small>',
            direction_icon, obj.shift.route.name, time_str
        )

    @admin.display(description='Vehicle')
    def vehicle_link(self, obj):
        if not obj.vehicle:
            return mark_safe('<span style="color: #f59e0b;">⚠️ Not Assigned</span>')
        reg_html = format_html(
            '<a href="/admin/core/vehicle/{}/change/" class="text-sky-700 dark:text-sky-400 font-semibold hover:underline">'
            '<i class="fas fa-bus mr-1"></i>{}'
            '</a>',
            obj.vehicle.id, obj.vehicle.registration_number
        )
        if obj.is_replacement_vehicle:
            return format_html(
                '{}<br><span class="badge" style="background-color: #d97706; color: #fff; font-size: 10px;">'
                '<i class="fas fa-exchange-alt mr-1"></i>Standby Backup</span>',
                reg_html
            )
        return reg_html

    @admin.display(description='Driver')
    def driver_link(self, obj):
        if not obj.driver:
            return mark_safe('<span style="color: #f59e0b;">⚠️ Not Assigned</span>')
        return format_html(
            '<a href="/admin/core_crew/driver/{}/change/" class="text-sky-700 dark:text-sky-400 font-medium hover:underline">'
            '<i class="fas fa-user-tie mr-1"></i>{}'
            '</a>',
            obj.driver.id, obj.driver.name
        )

    @admin.display(description='Timings & Delays')
    def timing_execution_display(self, obj):
        if obj.actual_departure_time:
            dep_str = obj.actual_departure_time.strftime('%I:%M %p')
            arr_str = obj.actual_arrival_time.strftime('%I:%M %p') if obj.actual_arrival_time else '—'
            html = f'<span class="text-xs text-slate-700 dark:text-slate-300">{dep_str} → {arr_str}</span>'
            if obj.delay_minutes > 0:
                html += f'<br><span class="badge" style="background-color: #ef4444; color: #fff; font-size: 10px;">+{obj.delay_minutes}m Late</span>'
            return mark_safe(html)
        return mark_safe('<span style="color: #64748b;">—</span>')

    @admin.display(description='KMs Run')
    def km_display(self, obj):
        if obj.opening_km is not None and obj.closing_km is not None:
            distance = obj.closing_km - obj.opening_km
            color = '#10b981' if distance > 0 else '#ef4444'
            return format_html(
                '<span style="color: {}; font-weight: 600;">{} km</span>'
                '<br><small style="color: #94a3b8;">({} → {})</small>',
                color, distance, f"{obj.opening_km:,}", f"{obj.closing_km:,}"
            )
        return mark_safe('<span style="color: #94a3b8;">—</span>')

    @admin.display(description='Pax')
    def passenger_badge(self, obj):
        return format_html(
            '<span class="badge" style="background-color: #334155; color: #f8fafc; border: 1px solid #475569; padding: 4px 7px; font-size: 12px;">'
            '<i class="fas fa-users mr-1"></i>{}'
            '</span>',
            obj.passenger_count
        )

    @admin.display(description='Status')
    def status_badge(self, obj):
        styles = {
            'scheduled': ('#3b82f6', 'fas fa-calendar', 'Scheduled'),
            'en_route': ('#0ea5e9', 'fas fa-spinner fa-spin', 'En Route'),
            'completed': ('#10b981', 'fas fa-check-circle', 'Completed'),
            'delayed': ('#f59e0b', 'fas fa-clock', 'Delayed'),
            'breakdown': ('#b91c1c', 'fas fa-exclamation-triangle', 'Breakdown'),
            'cancelled': ('#ef4444', 'fas fa-times-circle', 'Cancelled'),
        }
        color, icon, label = styles.get(obj.status, ('#64748b', 'fas fa-question', obj.status))
        return format_html(
            '<span class="badge" style="background-color: {}; color: #fff; padding: 4px 8px;">'
            '<i class="{} mr-1"></i>{}'
            '</span>',
            color, icon, label
        )

    @admin.display(description='Night Escort')
    def escort_badge(self, obj):
        count = obj.escort_logs.count()
        if count > 0:
            escort = obj.escort_logs.first()
            color = '#059669' if escort.last_drop_verification_status in ['verified_call', 'verified_sms', 'supervisor_signoff'] else '#d97706'
            return format_html(
                '<span class="badge" style="background-color: {}; color: #fff; padding: 3px 6px; font-size: 11px;">'
                '<i class="fas fa-user-shield mr-1"></i>{}'
                '</span>',
                color, escort.escort_guard_name
            )
        if obj.shift.escort_guard_required:
            return mark_safe('<span class="badge" style="background-color: #b91c1c; color: #fff;">⚠️ Missing Escort</span>')
        return mark_safe('<span style="color: #64748b;">—</span>')


# ==============================================================================
# 6. Night Safety & Escort Log Admin
# ==============================================================================

@admin.register(NightSafetyEscort)
class NightSafetyEscortAdmin(ModelAdmin):
    list_display = (
        'escort_guard_name', 'security_agency', 'trip_link',
        'female_passengers_badge', 'timing_span', 'verification_status_badge'
    )
    list_filter = ('last_drop_verification_status', 'security_agency')
    search_fields = ('escort_guard_name', 'guard_badge_number', 'security_agency', 'safe_drop_confirmed_by')
    actions = [mark_safe_drop_verified]

    @admin.display(description='Trip Log')
    def trip_link(self, obj):
        return format_html(
            '<a href="/admin/fleet_commute/dailytriplog/{}/change/" style="color: #38bdf8; text-decoration: none; font-weight: 500;">'
            'Trip #{} on {}'
            '</a>',
            obj.trip_log.id, obj.trip_log.id, obj.trip_log.date
        )

    @admin.display(description='Women Commuters')
    def female_passengers_badge(self, obj):
        return format_html(
            '<span class="badge" style="background-color: #ec4899; color: #fff; padding: 4px 8px; font-size: 12px;">'
            '<i class="fas fa-female mr-1"></i>{} Female Pax'
            '</span>',
            obj.female_passengers_count
        )

    @admin.display(description='Pickup → Last Drop')
    def timing_span(self, obj):
        p_str = obj.first_pickup_time.strftime('%I:%M %p') if obj.first_pickup_time else '—'
        d_str = obj.last_female_drop_time.strftime('%I:%M %p') if obj.last_female_drop_time else '—'
        return format_html(
            '<span class="text-xs text-slate-700 dark:text-slate-300"><i class="far fa-clock mr-1 text-sky-600"></i>{} → {}</span>',
            p_str, d_str
        )

    @admin.display(description='Safe Drop Status')
    def verification_status_badge(self, obj):
        colors = {
            'verified_call': ('#059669', 'fas fa-phone-alt', 'Verified Call'),
            'verified_sms': ('#0284c7', 'fas fa-sms', 'Verified SMS/OTP'),
            'supervisor_signoff': ('#7c3aed', 'fas fa-file-signature', 'Supervisor Signed'),
            'pending': ('#d97706', 'fas fa-hourglass-half', 'Pending'),
        }
        color, icon, label = colors.get(obj.last_drop_verification_status, ('#64748b', 'fas fa-question', obj.last_drop_verification_status))
        return format_html(
            '<span class="badge" style="background-color: {}; color: #fff; padding: 4px 8px;">'
            '<i class="{} mr-1"></i>{}'
            '</span>',
            color, icon, label
        )


@admin.register(CommuterBoardingPass)
class CommuterBoardingPassAdmin(ModelAdmin):
    list_display = (
        'commuter_link',
        'date',
        'otp_badge',
        'boarding_status_badge',
        'night_drop_badge',
        'ivr_status_badge',
        'pass_link',
    )
    list_filter = ('is_boarded', 'is_isolated_night_drop', 'ivr_status', 'date')
    search_fields = ('commuter__name', 'commuter__commuter_id', 'boarding_otp', 'pass_token')
    date_hierarchy = 'date'

    @admin.display(description='Commuter Passenger')
    def commuter_link(self, obj):
        return format_html(
            '<strong>{}</strong> <span style="color:#94a3b8;font-size:11px;">({})</span>',
            obj.commuter.name, obj.commuter.commuter_id
        )

    @admin.display(description='4-Digit OTP')
    def otp_badge(self, obj):
        return format_html(
            '<span style="font-family: monospace; font-weight: 800; background: #0284c7; color: #fff; padding: 2px 8px; border-radius: 6px; letter-spacing: 2px;">{}</span>',
            obj.boarding_otp
        )

    @admin.display(description='Boarding Status')
    def boarding_status_badge(self, obj):
        if obj.is_boarded:
            return format_html('<span style="color: #10b981; font-weight: 700;">✅ Boarded</span>')
        return format_html('<span style="color: #f59e0b; font-weight: 600;">⏳ Waiting</span>')

    @admin.display(description='Night Safety')
    def night_drop_badge(self, obj):
        if obj.is_isolated_night_drop:
            return format_html('<span style="background: rgba(239,68,68,0.2); color: #f87171; border: 1px solid rgba(239,68,68,0.4); padding: 2px 6px; border-radius: 4px; font-size: 11px; font-weight: 700;">⚠️ Isolated Drop</span>')
        return format_html('<span style="color: #94a3b8; font-size: 11px;">Normal</span>')

    @admin.display(description='IVR Drop Check')
    def ivr_status_badge(self, obj):
        colors = {
            'safe_confirmed': '#10b981',
            'sos_escalated': '#ef4444',
            'initiated': '#38bdf8',
            'pending': '#64748b'
        }
        color = colors.get(obj.ivr_status, '#64748b')
        return format_html('<span style="color: {}; font-weight: 700; font-size: 11px;">{}</span>', color, obj.get_ivr_status_display())

    @admin.display(description='Mobile Pass')
    def pass_link(self, obj):
        return format_html(
            '<a href="/commute/pass/{}/" target="_blank" style="color: #38bdf8; font-weight: 600; text-decoration: none;">📱 Open Pass &rarr;</a>',
            obj.pass_token
        )


@admin.register(ESGCarbonMetric)
class ESGCarbonMetricAdmin(ModelAdmin):
    list_display = ('date', 'vehicle', 'fuel_type', 'trip_km', 'co2_emitted_badge', 'co2_saved_badge', 'green_score_badge')
    list_filter = ('fuel_type', 'date')
    search_fields = ('vehicle__registration_number',)

    @admin.display(description='CO2 Emitted')
    def co2_emitted_badge(self, obj):
        return format_html('<span style="font-family: monospace; color: #f87171;">{} kg</span>', obj.co2_emitted_kg)

    @admin.display(description='CO2 Saved (Group Commute)')
    def co2_saved_badge(self, obj):
        return format_html('<span style="font-family: monospace; color: #10b981; font-weight: 700;">{} kg</span>', obj.co2_saved_kg)

    @admin.display(description='Green Score')
    def green_score_badge(self, obj):
        return format_html('<span style="background: rgba(16,185,129,0.15); color: #34d399; padding: 2px 8px; border-radius: 6px; font-weight: 700;">{} / 100</span>', obj.green_efficiency_score)
