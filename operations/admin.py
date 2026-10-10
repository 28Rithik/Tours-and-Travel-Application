from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline
from django.db import transaction
from django.urls import reverse
from django.utils.html import format_html, mark_safe
from .models import (
    Booking, Trip, TripCrewAssignment, TripJourney, TripHotel,
    BulkContract, BulkContractDay, TrafficFine,
    EmergencyIncidentAlert, VehicleTelematicsPing, DriverBehaviorLog, GeofenceZone,
    WhatsAppBotMessage, DriverHandoverSession, TripMilestoneEvent,
    TripItineraryDay,
)
from finance.models import TripExpense, FuelRecord, DriverSettlement, SupplierTripCost, Payment
from documents.models import CustomerDocument

@admin.register(TrafficFine)
class TrafficFineAdmin(ModelAdmin):
	list_display = ('challan_number', 'trip_link', 'vehicle', 'driver', 'date_of_offence', 'violation_badge', 'fine_amount_display', 'paid_by_badge', 'financial_responsibility_badge')
	list_filter = ('financial_responsibility', 'paid_by', 'violation_type', 'date_of_offence')
	list_select_related = ('trip', 'vehicle', 'driver')
	search_fields = ('challan_number', 'trip__trip_id', 'vehicle__registration_number', 'driver__name')
	autocomplete_fields = ['trip', 'vehicle', 'driver']
	date_hierarchy = 'date_of_offence'
	change_form_template = 'admin/operations/trafficfine/change_form.html'

	class Media:
		js = ('admin/js/traffic_fine_admin_v2.js',)

	@admin.display(description="Trip")
	def trip_link(self, obj):
		if obj.trip:
			url = reverse('admin:operations_trip_change', args=[obj.trip.pk])
			return format_html('<a href="{}" style="font-weight: 600; color: #38bdf8;">Trip #{}</a>', url, obj.trip.trip_id)
		return mark_safe('<span style="color: #94a3b8;">Direct (No Trip)</span>')

	@admin.display(description="Violation")
	def violation_badge(self, obj):
		text = obj.get_violation_type_display()
		if 'seatbelt' in obj.violation_type:
			return format_html('<span style="background: #fef3c7; color: #92400e; padding: 3px 8px; border-radius: 4px; font-weight: 500;">{}</span>', text)
		elif obj.violation_type == 'speeding':
			return format_html('<span style="background: #fee2e2; color: #991b1b; padding: 3px 8px; border-radius: 4px; font-weight: 500;">{}</span>', text)
		elif obj.violation_type in ['documents']:
			return format_html('<span style="background: #f3e8ff; color: #6b21a8; padding: 3px 8px; border-radius: 4px; font-weight: 500;">{}</span>', text)
		return format_html('<span style="font-weight: 500;">{}</span>', text)

	@admin.display(description="Fine Amount")
	def fine_amount_display(self, obj):
		return format_html('<span style="font-weight: bold; font-size: 1.05em;">₹{}</span>', obj.fine_amount)

	@admin.display(description="Paid Status")
	def paid_by_badge(self, obj):
		colors = {
			'unpaid': ('#b91c1c', '#fee2e2', '⏳ Unpaid'),
			'company': ('#047857', '#d1fae5', '🏢 Paid by Company'),
			'driver': ('#b45309', '#fef3c7', '🧑‍✈️ Paid by Driver'),
			'customer': ('#1d4ed8', '#dbeafe', '👤 Paid by Customer'),
		}
		fg, bg, label = colors.get(obj.paid_by, ('#4b5563', '#f3f4f6', obj.get_paid_by_display()))
		return format_html('<span style="background: {}; color: {}; padding: 2px 8px; border-radius: 4px; font-weight: 600; font-size: 11px;">{}</span>', bg, fg, label)

	@admin.display(description="Responsibility (Billing / Deduction)")
	def financial_responsibility_badge(self, obj):
		badges = {
			'customer': ('#1e40af', '#dbeafe', '#3b82f6', '👤 Bill to Customer (+ on Invoice)'),
			'driver': ('#9a3412', '#ffedd5', '#f97316', '🧑‍✈️ Deduct from Driver (Settlement)'),
			'supplier': ('#6b21a8', '#f3e8ff', '#a855f7', '🏢 Deduct from Supplier (Fleet Owner)'),
			'company': ('#374151', '#f3f4f6', '#9ca3af', '🏛️ Company Expense (Absorbed)'),
		}
		fg, bg, border, label = badges.get(obj.financial_responsibility, ('#374151', '#f3f4f6', '#d1d5db', obj.get_financial_responsibility_display()))
		return format_html('<span style="background: {}; color: {}; border: 1px solid {}; padding: 3px 10px; border-radius: 6px; font-weight: 600; font-size: 11px; white-space: nowrap;">{}</span>', bg, fg, border, label)

@admin.action(description="Convert selected Bookings to Trips")
def convert_to_trip(modeladmin, request, queryset):
	created_trips = []
	with transaction.atomic():
		for booking in queryset.select_for_update():
			if booking.status in ['pending', 'confirmed']:
				billing_m = 'fixed' if booking.billing_type == 'package' else ('km' if booking.billing_type == 'km' else 'day')
				trip = Trip.objects.create(
					booking=booking,
					party=booking.party,
					guest_name=booking.guest_name,
					package=booking.package,
					package_inventory=booking.package_inventory,
					vehicle=booking.package_inventory.assigned_vehicle if (booking.package_inventory and booking.package_inventory.assigned_vehicle) else None,
					driver=booking.package_inventory.assigned_driver if (booking.package_inventory and booking.package_inventory.assigned_driver) else None,
					start_date=booking.pickup_date,
					end_date=booking.drop_date or booking.pickup_date,
					start_time=booking.pickup_time,
					travel_pnr=booking.travel_pnr,
					pax_count=booking.pax_count,
					luggage_count=booking.luggage_count,
					billing_model=billing_m,
					fixed_amount=booking.quoted_price or 0,
					notes=booking.special_requirements or booking.notes,
					status='booked'
				)
				booking.status = 'dispatched'
				booking.save(update_fields=['status'])
				created_trips.append(trip.trip_id)
	modeladmin.message_user(request, f"Successfully converted {len(created_trips)} bookings to Trips ({', '.join(created_trips)}).")

class CustomerDocumentInline(TabularInline):
	model = CustomerDocument
	extra = 1

class BookingPaymentInline(TabularInline):
	model = Payment
	extra = 0
	verbose_name = "Advance / Payment Received"
	verbose_name_plural = "Advances / Payments Received"
	fields = ('date', 'amount', 'payment_type', 'payment_mode', 'collected_by', 'reference_number', 'notes')
	exclude = ('party', 'trip', 'contract_trip', 'statement')

@admin.register(Booking)
class BookingAdmin(ModelAdmin):
	list_display = ('booking_number', 'party', 'guest_name', 'pickup_date', 'journey_type', 'status_badge', 'quoted_price', 'advance_received', 'outstanding_balance', 'linked_trip', 'whatsapp_quote', 'quick_actions')
	list_filter = ('status', 'journey_type', 'pickup_date', 'billing_type')
	list_select_related = ('party', 'package', 'package_inventory')
	search_fields = ('booking_number', 'guest_name', 'guest_phone', 'party__name')
	date_hierarchy = 'pickup_date'
	autocomplete_fields = ['party', 'package', 'package_inventory']
	inlines = [CustomerDocumentInline, BookingPaymentInline]
	actions = [convert_to_trip]
	change_form_template = 'admin/operations/booking/change_form.html'

	class Media:
		js = ('admin/js/booking_form_v2.js',)
	
	fieldsets = (
		('Customer Details', {
			'fields': ('booking_number', 'party', 'guest_name', 'guest_phone')
		}),
		('Journey Details', {
			'fields': ('pickup_location', 'destination', 'pickup_date', 'drop_date', 'pickup_time', 'reporting_time', 'travel_pnr')
		}),
		('Vehicle Requirements', {
			'fields': ('journey_type', 'vehicle_type', 'pax_count', 'luggage_count', 'special_requirements')
		}),
		('Financial Agreement', {
			'fields': ('billing_type', 'quoted_price', 'payment_terms_override', 'expected_km', 'gst_rate')
		}),
		('Itinerary & Status', {
			'fields': ('package', 'package_inventory', 'plan_details', 'hotel_confirmation_status', 'hotel_paid_by', 'linked_trip', 'notes', 'status')
		}),
	)
	
	readonly_fields = ('booking_number', 'advance_received', 'outstanding_balance_display', 'linked_trip')

	@admin.display(description="Trip")
	def linked_trip(self, obj):
		trip = obj.trips.first()
		if trip:
			url = reverse('admin:operations_trip_change', args=[trip.pk])
			status_color = {'booked': '#6c757d', 'assigned': '#17a2b8', 'started': '#007bff', 'completed': '#28a745'}.get(trip.status, '#343a40')
			return format_html(
				'<a href="{}" class="badge" style="background:{}; color:#fff; padding:4px 8px; border-radius:4px; font-weight:bold; text-decoration:none;" title="View Trip Details">'
				'🚗 {} ({})'
				'</a>',
				url, status_color, trip.trip_id, trip.get_status_display()
			)
		return mark_safe('<span class="text-muted" style="font-size:11px;">Not converted</span>')

	@admin.display(description="Status")
	def status_badge(self, obj):
		colors = {'pending': '#ffc107', 'confirmed': '#28a745', 'completed': '#17a2b8', 'cancelled': '#dc3545'}
		color = colors.get(obj.status, '#6c757d')
		return format_html('<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 4px; font-weight: bold;">{}</span>', color, obj.get_status_display())

	@admin.display(description="Balance")
	def outstanding_balance(self, obj):
		if obj.quoted_price:
			balance = obj.quoted_price - obj.advance_received
			color = "red" if balance > 0 else "green"
			return format_html('<span style="color: {}; font-weight: bold;">₹{}</span>', color, balance)
		return "-"
		
	@admin.display(description="Outstanding Balance")
	def outstanding_balance_display(self, obj):
		return self.outstanding_balance(obj)

	@admin.display(description="Actions")
	def quick_actions(self, obj):
		buttons = []
		upi_studio_url = f"/admin/finance/payment-studio/?booking_id={obj.pk}"
		buttons.append(f'<a class="button" href="{upi_studio_url}" style="padding:4px 6px; background:#4f46e5; color:white; border-radius:3px; text-decoration:none; font-size:11px; font-weight:600;" title="Collect Payment via Dynamic UPI QR">⚡ UPI QR</a>')
		if obj.status in ['pending', 'confirmed'] and not obj.trips.exists():
			url = reverse('admin:booking-quick-convert', args=[obj.pk])
			buttons.append(f'<a class="button" href="{url}" style="padding:4px 6px; background:#0284c7; color:white; border-radius:3px; text-decoration:none; font-size:11px; font-weight:600;" title="Convert to Trip">▶️ Trip</a>')
		elif obj.trips.exists():
			trip = obj.trips.first()
			url = reverse('admin:operations_trip_change', args=[trip.pk])
			buttons.append(f'<a class="button" href="{url}" style="padding:4px 6px; background:#0f766e; color:white; border-radius:3px; text-decoration:none; font-size:11px; font-weight:600;" title="Open Trip">Trip #{trip.trip_id}</a>')
		return mark_safe('<div style="display:flex; gap:4px; align-items:center;">' + "".join(buttons) + '</div>')

		
	def get_urls(self):
		from django.urls import path
		urls = super().get_urls()
		custom_urls = [
			path('<int:booking_id>/quick-convert/', self.admin_site.admin_view(self.quick_convert), name='booking-quick-convert'),
		]
		return custom_urls + urls
		
	def quick_convert(self, request, booking_id):
		from django.shortcuts import get_object_or_404, redirect
		from django.contrib import messages
		booking = get_object_or_404(Booking, pk=booking_id)
		if booking.status in ['pending', 'confirmed'] and not booking.trips.exists():
			billing_m = 'fixed' if booking.billing_type == 'package' else ('km' if booking.billing_type == 'km' else 'day')
			trip = Trip.objects.create(
				booking=booking,
				party=booking.party,
				guest_name=booking.guest_name,
				package=booking.package,
				package_inventory=booking.package_inventory,
				vehicle=booking.package_inventory.assigned_vehicle if (booking.package_inventory and booking.package_inventory.assigned_vehicle) else None,
				driver=booking.package_inventory.assigned_driver if (booking.package_inventory and booking.package_inventory.assigned_driver) else None,
				start_date=booking.pickup_date,
				end_date=booking.drop_date or booking.pickup_date,
				start_time=booking.pickup_time,
				travel_pnr=booking.travel_pnr,
				pax_count=booking.pax_count,
				luggage_count=booking.luggage_count,
				billing_model=billing_m,
				fixed_amount=booking.quoted_price or 0,
				notes=booking.special_requirements or booking.notes,
				status='booked'
			)
			booking.status = 'dispatched'
			booking.save(update_fields=['status'])
			messages.success(request, f'Booking {booking.booking_number} converted to Trip {trip.trip_id} successfully.')
			return redirect('admin:operations_trip_change', trip.pk)
		elif booking.trips.exists():
			trip = booking.trips.first()
			messages.info(request, f'Booking {booking.booking_number} is already linked to Trip {trip.trip_id}.')
			return redirect('admin:operations_trip_change', trip.pk)
		else:
			messages.warning(request, f'Booking {booking.booking_number} cannot be converted.')
			return redirect('admin:operations_booking_changelist')

	def whatsapp_quote(self, obj):
		import urllib.parse
		if not obj.guest_phone:
			return "-"
		phone = obj.guest_phone.replace("+", "").replace(" ", "")
		msg = f"Travel Quote / Confirmation\nGuest: {obj.guest_name}\nDate: {obj.pickup_date}\nFrom: {obj.pickup_location}\nTo: {obj.destination}\n"
		if obj.quoted_price:
			msg += f"Price: Rs. {obj.quoted_price}\n"
		msg = urllib.parse.quote(msg)
		url = f"https://wa.me/91{phone}?text={msg}"
		return format_html('<a class="button" href="{}" target="_blank" style="background-color: #25D366; color: white; padding: 4px 8px; border-radius: 4px; text-decoration:none;">📲 WhatsApp</a>', url)
	whatsapp_quote.short_description = 'Message'

	def save_formset(self, request, form, formset, change):
		instances = formset.save(commit=False)
		for instance in instances:
			if isinstance(instance, CustomerDocument):
				instance.customer = form.instance.party
			elif isinstance(instance, Payment):
				instance.party = form.instance.party
			instance.save()
		formset.save_m2m()

	def get_search_results(self, request, queryset, search_term):
		queryset, use_distinct = super().get_search_results(request, queryset, search_term)
		if 'party_id' in request.GET and request.GET['party_id']:
			queryset = queryset.filter(party_id=request.GET['party_id'])
		return queryset, use_distinct


class TripJourneyInline(TabularInline):
	model = TripJourney
	extra = 0

class TripCrewAssignmentInline(TabularInline):
	model = TripCrewAssignment
	extra = 0

	def formfield_for_foreignkey(self, db_field, request, **kwargs):
		if db_field.name == "driver":
			from core.models import Driver
			kwargs["queryset"] = Driver.objects.filter(status='active')
		elif db_field.name == "cleaner":
			from core.models import Cleaner
			kwargs["queryset"] = Cleaner.objects.filter(status='active')
		return super().formfield_for_foreignkey(db_field, request, **kwargs)

class TripExpenseInline(TabularInline):
	model = TripExpense
	extra = 0

class TripHotelInline(TabularInline):
	model = TripHotel
	extra = 0

class FuelRecordInline(TabularInline):
	model = FuelRecord
	exclude = ('vehicle',)
	extra = 0

class DriverSettlementInline(TabularInline):
	model = DriverSettlement
	exclude = ('driver',)
	extra = 0
	max_num = 1

class SupplierTripCostInline(TabularInline):
	model = SupplierTripCost
	extra = 0
	max_num = 1
	exclude = ('supplier', 'vehicle')

class TrafficFineInline(TabularInline):
	model = TrafficFine
	extra = 0
	fields = ('challan_number', 'date_of_offence', 'violation_type', 'fine_amount', 'paid_by', 'financial_responsibility', 'receipt_file', 'notes')

class TripMilestoneEventInline(TabularInline):
	model = TripMilestoneEvent
	extra = 0
	fields = ('milestone', 'milestone_index', 'timestamp', 'odometer_reading', 'passenger_pin_entered', 'is_pin_verified', 'location_name', 'notes')
	readonly_fields = ('timestamp',)

class TripItineraryDayInline(TabularInline):
	model = TripItineraryDay
	extra = 0
	fields = ('day_number', 'date', 'title', 'route_segment', 'hotel_name', 'hotel_booking_status', 'meals_included', 'is_active_today')
	ordering = ['day_number']

@admin.register(TripItineraryDay)
class TripItineraryDayAdmin(ModelAdmin):
	list_display = ('trip_link', 'day_number_badge', 'date', 'title', 'route_segment', 'hotel_name', 'hotel_status_badge', 'meals_included', 'is_active_today')
	list_filter = ('hotel_booking_status', 'is_active_today', 'date')
	search_fields = ('trip__trip_id', 'title', 'route_segment', 'sightseeing_spots', 'hotel_name')
	list_select_related = ('trip',)

	@admin.display(description="Trip")
	def trip_link(self, obj):
		url = reverse('admin:operations_trip_change', args=[obj.trip.pk])
		return format_html('<a href="{}" style="font-weight: 600; color: #38bdf8;">Trip #{}</a>', url, obj.trip.trip_id)

	@admin.display(description="Day")
	def day_number_badge(self, obj):
		return format_html('<span style="background: #e0e7ff; color: #4338ca; padding: 2px 8px; border-radius: 4px; font-weight: 700;">Day {}</span>', f"{obj.day_number:02d}")

	@admin.display(description="Hotel Status")
	def hotel_status_badge(self, obj):
		colors = {
			'pending': ('#b45309', '#fef3c7', '⏳ Pending'),
			'confirmed': ('#047857', '#d1fae5', '✅ Confirmed Voucher'),
			'checked_in': ('#1d4ed8', '#dbeafe', '🏨 Checked In'),
		}
		fg, bg, label = colors.get(obj.hotel_booking_status, ('#4b5563', '#f3f4f6', obj.get_hotel_booking_status_display()))
		return format_html('<span style="background: {}; color: {}; padding: 2px 8px; border-radius: 4px; font-weight: 600; font-size: 11px;">{}</span>', bg, fg, label)

@admin.register(Trip)
class TripAdmin(ModelAdmin):
	actions = ['batch_mark_billed']
	list_display = ('trip_id', 'source_display', 'party', 'guest_name', 'vehicle_display', 'driver_display', 'status', 'itinerary_badge', 'milestone_badge', 'start_date', 'total_amount', 'display_net_profit', 'send_whatsapp_driver', 'quick_actions')
	list_editable = ('status',)
	list_filter = ('status', 'current_milestone', 'vehicle__ownership_type', 'driver__driver_type', 'billing_model', 'start_date')
	list_select_related = ('party', 'vehicle', 'driver', 'booking', 'package')
	search_fields = ('trip_id', 'booking__booking_number', 'guest_name', 'party__name', 'vehicle__registration_number', 'driver__name', 'bulk_contract_day__contract__name', 'pickup_pin')
	autocomplete_fields = ['booking', 'package', 'package_inventory', 'bulk_contract_day', 'party', 'vehicle', 'driver']
	date_hierarchy = 'start_date'

	@admin.display(description="Itinerary")
	def itinerary_badge(self, obj):
		count = obj.itinerary_days.count()
		builder_url = reverse('admin-trip-itinerary-builder', args=[obj.pk])
		if count > 0:
			return format_html('<a href="{}" target="_blank" style="background: rgba(99,102,241,0.15); border: 1px solid #6366f1; color: #818cf8; padding: 2px 8px; border-radius: 6px; font-weight: 700; font-size: 11px; text-decoration: none;">🗺️ {} Days</a>', builder_url, count)
		return format_html('<a href="{}" target="_blank" style="color: #94a3b8; font-size: 11px; text-decoration: none;">+ Add Days</a>', builder_url)

	@admin.display(description="7-Milestone Lifecycle", ordering='current_milestone')
	def milestone_badge(self, obj):
		icons = {
			'car_pickup': ('#38bdf8', '🚗 1. Car Pickup'),
			'driver_reached': ('#06b6d4', '📍 2. Driver Reached'),
			'guest_pickup': ('#a855f7', '🔢 3. Guest PIN OK'),
			'on_trip': ('#10b981', '🛣️ 4. On Trip'),
			'guest_drop': ('#f59e0b', '🏁 5. Guest Drop'),
			'expenses_photo': ('#ec4899', '🧾 6. Expenses Logged'),
			'car_drop': ('#64748b', '🅿️ 7. Car Drop / Closed'),
		}
		color, label = icons.get(obj.current_milestone, ('#94a3b8', obj.get_current_milestone_display()))
		lifecycle_url = reverse('trip-lifecycle-portal', args=[obj.pk])
		return format_html(
			'<a href="{}" target="_blank" style="background: rgba(255,255,255,0.06); border: 1px solid {}; color: {}; padding: 3px 8px; border-radius: 6px; font-weight: 700; font-size: 11px; text-decoration: none; display: inline-flex; align-items: center; gap: 4px;">{} ({}%)</a>',
			lifecycle_url, color, color, label, obj.milestone_progress_percent
		)

	@admin.display(description="7-Milestone Tour Cockpit")
	def lifecycle_portal_link(self, obj):
		if not obj or not getattr(obj, 'pk', None):
			return mark_safe('<span style="color: #94a3b8; font-size: 11px;">Available after saving trip</span>')
		url = reverse('trip-lifecycle-portal', args=[obj.pk])
		return format_html('<a href="{}" target="_blank" style="background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: white; padding: 6px 14px; border-radius: 8px; font-weight: 700; text-decoration: none;">🚀 Open 7-Milestone Tour Cockpit</a>', url)

	@admin.display(description="Day-by-Day Itinerary Builder & Guest Portal")
	def itinerary_builder_link(self, obj):
		if not obj or not getattr(obj, 'pk', None):
			return mark_safe('<span style="color: #94a3b8; font-size: 11px;">Available after saving trip</span>')
		url = reverse('admin-trip-itinerary-builder', args=[obj.pk])
		guest_url = obj.guest_itinerary_url
		return format_html(
			'<div style="display: flex; gap: 8px; align-items: center; flex-wrap: wrap;">'
			'<a href="{}" target="_blank" style="background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%); color: white; padding: 6px 14px; border-radius: 8px; font-weight: 700; text-decoration: none; font-size: 12px; display: inline-flex; align-items: center; gap: 6px;">🗺️ Open Day-by-Day Itinerary Builder</a>'
			'<a href="{}" target="_blank" style="background: rgba(99,102,241,0.12); border: 1px solid #6366f1; color: #818cf8; padding: 6px 12px; border-radius: 8px; font-weight: 600; text-decoration: none; font-size: 12px;">📱 Live Guest Experience Portal</a>'
			'</div>',
			url, guest_url
		)
	list_select_related = ('party', 'vehicle', 'driver', 'booking', 'package')
	search_fields = ('trip_id', 'booking__booking_number', 'guest_name', 'party__name', 'vehicle__registration_number', 'driver__name', 'bulk_contract_day__contract__name')
	autocomplete_fields = ['booking', 'package', 'package_inventory', 'bulk_contract_day', 'party', 'vehicle', 'driver']
	date_hierarchy = 'start_date'

	@admin.display(description="Source")
	def source_display(self, obj):
		if obj.booking:
			url = reverse('admin:operations_booking_change', args=[obj.booking.pk])
			return format_html('<a href="{}" style="color: #60a5fa; font-weight: 600;">Booking #{}</a>', url, obj.booking.booking_number)
		elif obj.bulk_contract_day:
			url = reverse('admin:operations_bulkcontractday_change', args=[obj.bulk_contract_day.pk])
			return format_html('<a href="{}" style="color: #c084fc; font-weight: 600;">Bulk: {}</a>', url, obj.bulk_contract_day.contract.name)
		return mark_safe('<span class="text-muted">Direct</span>')

	def get_urls(self):
		from django.urls import path
		urls = super().get_urls()
		custom_urls = [
			path('<int:trip_id>/quick-start/', self.admin_site.admin_view(self.quick_start_trip), name='trip-quick-start'),
			path('<int:trip_id>/quick-end/', self.admin_site.admin_view(self.quick_end_trip), name='trip-quick-end'),
		]
		return custom_urls + urls

	def quick_start_trip(self, request, trip_id):
		from django.shortcuts import get_object_or_404, redirect
		from django.utils import timezone
		from django.contrib import messages
		trip = get_object_or_404(Trip, pk=trip_id)
		if trip.status in ['booked', 'assigned']:
			trip.status = 'started'
			if not trip.start_time:
				trip.start_time = timezone.localtime().time()
			trip.save(update_fields=['status', 'start_time'])
			messages.success(request, f'Trip {trip.trip_id} started successfully.')
		else:
			messages.warning(request, f'Trip {trip.trip_id} cannot be started from its current status.')
		return redirect('admin:operations_trip_changelist')

	def quick_end_trip(self, request, trip_id):
		from django.shortcuts import get_object_or_404, redirect
		from django.utils import timezone
		from django.contrib import messages
		trip = get_object_or_404(Trip, pk=trip_id)
		if trip.status == 'started':
			trip.status = 'completed'
			if not trip.end_time:
				trip.end_time = timezone.localtime().time()
			trip.save(update_fields=['status', 'end_time'])
			messages.success(request, f'Trip {trip.trip_id} ended successfully.')
		else:
			messages.warning(request, f'Trip {trip.trip_id} must be in "started" status to end.')
		return redirect('admin:operations_trip_changelist')

	class Media:
		js = ('admin/js/trip_admin_v2.js',)
	
	change_form_template = 'admin/operations/trip/change_form.html'
	inlines = [TripItineraryDayInline, TripMilestoneEventInline, TripCrewAssignmentInline, TripHotelInline, TripJourneyInline, TrafficFineInline, FuelRecordInline, TripExpenseInline, DriverSettlementInline, SupplierTripCostInline]
	
	fieldsets = (
		('Booking / Contract Information', {
			'fields': ('trip_id', 'print_duty_slip', 'booking', 'package', 'package_inventory', 'bulk_contract_day', 'party', 'guest_name', 'travel_pnr', 'pax_count', 'luggage_count')
		}),
		('Multi-Day Tour Itinerary & Guest Portal', {
			'fields': ('itinerary_builder_link',),
			'description': 'Configure day-by-day sightseeing spots, route segments, and hotel stays, or share the mobile live guest companion portal'
		}),
		('7-Milestone Tour Lifecycle', {
			'fields': ('current_milestone', 'pickup_pin', 'is_pin_verified', 'lifecycle_portal_link'),
			'description': 'Real-time tour operational progression from depot departure through to guest drop & closing odometer'
		}),
		('Trip Execution', {
			'fields': ('vehicle', 'driver', 'status')
		}),
		('Schedule', {
			'fields': ('start_date', 'end_date', 'start_time', 'end_time')
		}),
		('Odometer Reading', {
			'fields': ('opening_km', 'closing_km', 'total_distance', 'extra_km')
		}),
		('Billing & Rates', {
			'fields': ('billing_model', 'day_rate', 'km_rate', 'fixed_amount', 'days_count', 'driver_bata', 'customer_billable_fines_display', 'total_bill_amount_display', 'commission')
		}),
		('Logistics', {
			'fields': ('partner_handover_notes', 'notes', 'whatsapp_dispatch_link', 'whatsapp_bill_link')
		}),
	)
	
	readonly_fields = ('trip_id', 'print_duty_slip', 'itinerary_builder_link', 'lifecycle_portal_link', 'total_distance', 'extra_km', 'customer_billable_fines_display', 'total_bill_amount_display', 'received_amount', 'total_supplier_cost', 'total_fuel_cost', 'company_paid_expenses', 'net_profit', 'whatsapp_dispatch_link', 'whatsapp_bill_link')

	@admin.display(description="Passenger Fines (Billable)")
	def customer_billable_fines_display(self, obj):
		if obj.customer_billable_fines > 0:
			return format_html('<span style="color: #dc2626; font-weight: bold; background: #fee2e2; padding: 2px 8px; border-radius: 4px;">+ ₹{} (Added to Customer Bill)</span>', obj.customer_billable_fines)
		return mark_safe('<span style="color: #6b7280;">₹0.00</span>')

	@admin.display(description="Total Bill (with Fines & Taxes)")
	def total_bill_amount_display(self, obj):
		return format_html('<span style="color: #16a34a; font-weight: bold; font-size: 1.1em;">₹{}</span>', obj.total_amount)
	
	def whatsapp_dispatch_link(self, obj):
		from urllib.parse import quote
		if not obj.booking or not obj.booking.guest_phone:
			return "-"
		phone = obj.booking.guest_phone.replace("+", "").replace(" ", "")
		text = quote(obj.customer_confirmation_message)
		url = f"https://wa.me/{phone}?text={text}"
		return format_html('<a class="button" href="{}" target="_blank" style="background-color: #25D366; color: white; padding: 5px 10px; border-radius: 4px;">Send Dispatch</a>', url)
	whatsapp_dispatch_link.short_description = 'WhatsApp Dispatch'

	def whatsapp_bill_link(self, obj):
		from urllib.parse import quote
		if not obj.booking or not obj.booking.guest_phone:
			return "-"
		phone = obj.booking.guest_phone.replace("+", "").replace(" ", "")
		text = quote(obj.final_bill_message)
		url = f"https://wa.me/{phone}?text={text}"
		return format_html('<a class="button" href="{}" target="_blank" style="background-color: #25D366; color: white; padding: 5px 10px; border-radius: 4px;">Send Bill</a>', url)
	whatsapp_bill_link.short_description = 'WhatsApp Bill'
	
	@admin.display(description="Net Profit")
	def display_net_profit(self, obj):
		color = "green" if obj.net_profit >= 0 else "red"
		return format_html('<span style="color: {}; font-weight: bold;">₹{}</span>', color, obj.net_profit)

	@admin.display(description="Total Distance")
	def total_distance(self, obj):
		if obj.used_km:
			return f"{obj.used_km} KM"
		return "-"

	@admin.display(description="Extra KMs")
	def extra_km(self, obj):
		if obj.extra_km and obj.extra_km > 0:
			return format_html('<span style="color: red; font-weight: bold;">{} KM</span>', obj.extra_km)
		return "0 KM"
		
	@admin.display(description="Vehicle")
	def vehicle_display(self, obj):
		if not obj.vehicle:
			return "-"
		badge_color = "#17a2b8" if obj.vehicle.ownership_type == 'owned' else "#fd7e14"
		badge_text = "Own" if obj.vehicle.ownership_type == 'owned' else "Supplier"
		return format_html('{} <span style="background-color:{}; color:white; padding:2px 4px; border-radius:3px; font-size:10px; margin-left:4px;">{}</span>', obj.vehicle, badge_color, badge_text)
		
	@admin.display(description="Driver")
	def driver_display(self, obj):
		if not obj.driver:
			return "-"
		if obj.driver.driver_type == 'owned':
			badge_color = "#17a2b8"
			badge_text = "Own"
		elif obj.driver.driver_type == 'supplier':
			badge_color = "#fd7e14"
			badge_text = "Supplier"
		else:
			badge_color = "#6c757d"
			badge_text = "Temp"
		return format_html('{} <span style="background-color:{}; color:white; padding:2px 4px; border-radius:3px; font-size:10px; margin-left:4px;">{}</span>', obj.driver, badge_color, badge_text)

	def print_duty_slip(self, obj):
		if obj.pk:
			url = reverse('trip-sheet', args=[obj.pk])
			return format_html('<a class="button" href="{}" target="_blank" style="padding:10px; background:#4CAF50; color:white; font-weight:bold; border-radius:4px; text-decoration:none;">🖨️ Print Duty Slip</a>', url)
		return "-"
	print_duty_slip.short_description = "Duty Slip"

	def send_whatsapp_driver(self, obj):
		from django.utils.safestring import mark_safe
		import urllib.parse
		
		buttons = []
		msg = f"New Trip Assignment\nGuest: {obj.guest_name}\nDate: {obj.start_date}"
		if obj.booking and obj.booking.pickup_location:
			msg += f"\nPickup: {obj.booking.pickup_location}"
		encoded_msg = urllib.parse.quote(msg)
		
		if obj.driver and obj.driver.phone:
			driver_url = f"https://wa.me/91{obj.driver.phone}?text={encoded_msg}"
			buttons.append(f'<a class="button" href="{driver_url}" target="_blank" style="padding:4px; background:#25D366; color:white; border-radius:3px; text-decoration:none;" title="Send to Driver">📲 Driver</a>')
			
		if obj.vehicle and obj.vehicle.ownership_type == 'outsourced' and obj.vehicle.owner_party and obj.vehicle.owner_party.phone:
			supplier_url = f"https://wa.me/91{obj.vehicle.owner_party.phone}?text={encoded_msg}"
			buttons.append(f'<a class="button" href="{supplier_url}" target="_blank" style="padding:4px; background:#128C7E; color:white; border-radius:3px; text-decoration:none;" title="Send to Supplier">📲 Supplier</a>')
			
		if buttons:
			return mark_safe("&nbsp;".join(buttons))
		return "-"
	send_whatsapp_driver.short_description = "WhatsApp"
	
	def quick_actions(self, obj):
		from django.urls import reverse
		from django.utils.safestring import mark_safe
		buttons = []
		if obj.status in ['booked', 'assigned', 'driver_confirmed']:
			url = reverse('admin:trip-quick-start', args=[obj.pk])
			buttons.append(f'<a class="button" href="{url}" style="padding:4px; background:#28a745; color:white; border-radius:3px; text-decoration:none;" title="Start Trip">▶️ Start</a>')
		elif obj.status == 'started':
			url = reverse('admin:trip-quick-end', args=[obj.pk])
			buttons.append(f'<a class="button" href="{url}" style="padding:4px; background:#dc3545; color:white; border-radius:3px; text-decoration:none;" title="End Trip">⏹️ End</a>')
		return mark_safe("&nbsp;".join(buttons))
	quick_actions.short_description = "Actions"

	@admin.action(description="Mark Selected Trips as Billed & Generate Invoice")
	def batch_mark_billed(self, request, queryset):
		from statements.services import generate_invoice_for_booking
		updated = 0
		invoices = 0
		for trip in queryset:
			if trip.status == 'completed':
				trip.status = 'billed'
				trip.save(update_fields=['status'])
				updated += 1
				if trip.booking_id:
					try:
						generate_invoice_for_booking(trip.booking)
						invoices += 1
					except Exception:
						pass
		self.message_user(request, f"Successfully marked {updated} trips as Billed and queued {invoices} invoices.")

	def save_formset(self, request, form, formset, change):
		instances = formset.save(commit=False)
		for instance in instances:
			# Auto-fill the hidden fields for inlines
			if isinstance(instance, FuelRecord):
				instance.vehicle = form.instance.vehicle
			elif isinstance(instance, DriverSettlement):
				instance.driver = form.instance.driver
			elif isinstance(instance, SupplierTripCost):
				if form.instance.vehicle and form.instance.vehicle.ownership_type == 'outsourced':
					instance.vehicle = form.instance.vehicle
					instance.supplier = form.instance.vehicle.owner_party
			instance.save()
		formset.save_m2m()
	
	def formfield_for_foreignkey(self, db_field, request, **kwargs):
		if db_field.name == "vehicle":
			from core.models import Vehicle
			kwargs["queryset"] = Vehicle.objects.exclude(status__in=['maintenance', 'inactive'])
		elif db_field.name == "driver":
			from core.models import Driver
			kwargs["queryset"] = Driver.objects.filter(status='active')
		return super().formfield_for_foreignkey(db_field, request, **kwargs)

	def get_search_results(self, request, queryset, search_term):
		queryset, use_distinct = super().get_search_results(request, queryset, search_term)
		if 'party_id' in request.GET and request.GET['party_id']:
			queryset = queryset.filter(party_id=request.GET['party_id'])
		return queryset, use_distinct

from .models import Booking, Trip, TripCrewAssignment, TripJourney, TripHotel, BulkContract, BulkContractDay, TrafficFine, ContractVehicleRate, ContractDayRequirement

class ContractVehicleRateInline(TabularInline):
	model = ContractVehicleRate
	extra = 1

class ContractDayRequirementInline(TabularInline):
	model = ContractDayRequirement
	extra = 1

class BulkContractDayInline(TabularInline):
	model = BulkContractDay
	extra = 0

class BulkContractTripInline(TabularInline):
	model = Trip
	extra = 0
	fk_name = 'bulk_contract_day'
	fields = ('vehicle', 'driver', 'status', 'start_time', 'end_time', 'opening_km', 'closing_km')

	def get_formset(self, request, obj=None, **kwargs):
		request._parent_obj = obj
		return super().get_formset(request, obj, **kwargs)

	def formfield_for_foreignkey(self, db_field, request, **kwargs):
		if db_field.name == "vehicle":
			from core.models import Vehicle
			kwargs["queryset"] = Vehicle.objects.exclude(status__in=['maintenance', 'inactive'])
		elif db_field.name == "driver":
			from core.models import Driver
			kwargs["queryset"] = Driver.objects.filter(status='active')
		return super().formfield_for_foreignkey(db_field, request, **kwargs)

@admin.action(description="Auto-Generate Operating Days")
def generate_operating_days(modeladmin, request, queryset):
	from datetime import timedelta
	created_count = 0
	skipped_count = 0
	for contract in queryset:
		current_date = contract.start_date
		while current_date <= contract.end_date:
			obj, created = BulkContractDay.objects.get_or_create(
				contract=contract,
				date=current_date,
				defaults={}
			)
			if created:
				created_count += 1
			else:
				skipped_count += 1
			current_date += timedelta(days=1)
	modeladmin.message_user(request, f'Generated {created_count} new operating days (skipped {skipped_count} existing days).')

@admin.action(description="Clone Contract (Shift forward 1 month)")
def clone_contract_shifted(modeladmin, request, queryset):
	from dateutil.relativedelta import relativedelta
	count = 0
	for contract in queryset:
		days = list(contract.days.all())
		rates = list(contract.vehicle_rates.all())
		contract.pk = None
		contract.name = f"{contract.name} (Renewed)"
		contract.start_date = contract.start_date + relativedelta(months=1)
		contract.end_date = contract.end_date + relativedelta(months=1)
		contract.status = 'draft'
		contract.save()
		
		for rate in rates:
			rate.pk = None
			rate.contract = contract
			rate.save()
		
		for day in days:
			old_day_pk = day.pk
			reqs = list(ContractDayRequirement.objects.filter(contract_day_id=old_day_pk))
			day.pk = None
			day.contract = contract
			day.date = day.date + relativedelta(months=1)
			day.save()
			
			for req in reqs:
				req.pk = None
				req.contract_day = day
				req.save()
		count += 1
	modeladmin.message_user(request, f"Successfully cloned and shifted {count} contracts.")

@admin.action(description="Generate Scheduled Trips from Vehicle Requirements")
def generate_trips_from_requirements(modeladmin, request, queryset):
	total_created = 0
	for day in queryset:
		reqs = day.requirements.all()
		for req in reqs:
			v_type = req.vehicle_type
			rate_obj = day.contract.vehicle_rates.filter(vehicle_type=v_type).first()
			agreed_rate = rate_obj.agreed_day_rate if rate_obj else 0
			existing_count = day.trips.filter(vehicle__vehicle_type=v_type).count()
			needed = max(0, req.quantity - existing_count)
			for _ in range(needed):
				Trip.objects.create(
					bulk_contract_day=day,
					party=day.contract.customer,
					guest_name=f"{day.contract.name} ({v_type.name if v_type else 'Vehicle'})",
					start_date=day.date,
					end_date=day.date,
					billing_model='day',
					day_rate=agreed_rate,
					status='booked'
				)
				total_created += 1
	modeladmin.message_user(request, f"Successfully generated {total_created} trips from vehicle requirements.")

@admin.register(BulkContract)
class BulkContractAdmin(ModelAdmin):
	list_display = ('name', 'contract_type', 'customer', 'start_date', 'end_date', 'days_count_display', 'trips_count_display', 'status', 'billing_model')
	list_filter = ('status', 'contract_type', 'billing_model', 'start_date')
	search_fields = ('name', 'customer__name')
	inlines = [ContractVehicleRateInline, BulkContractDayInline]
	actions = [generate_operating_days, clone_contract_shifted]

	@admin.display(description='Operating Days')
	def days_count_display(self, obj):
		return obj.days.count()

	@admin.display(description='Total Trips')
	def trips_count_display(self, obj):
		return sum(day.trips.count() for day in obj.days.all())

	class Media:
		js = ('admin/js/bulk_contract_vehicle_rates.js',)

@admin.register(BulkContractDay)
class BulkContractDayAdmin(ModelAdmin):
	list_display = ('contract', 'date', 'requirements_summary', 'assignment_count')
	list_filter = ('date', 'contract__contract_type')
	search_fields = ('contract__name', 'contract__customer__name')
	inlines = [ContractDayRequirementInline, BulkContractTripInline]
	actions = [generate_trips_from_requirements]
	change_form_template = 'admin/operations/bulkcontractday/change_form.html'

	class Media:
		js = ('admin/js/bulk_contract_day_admin.js',)

	@admin.display(description='Requirements')
	def requirements_summary(self, obj):
		reqs = [f"{r.quantity}x {r.vehicle_type.name if r.vehicle_type else 'Vehicle'}" for r in obj.requirements.all()]
		return ", ".join(reqs) if reqs else "-"

	@admin.display(description='Assigned Trips')
	def assignment_count(self, obj):
		return obj.trips.count()


# ==============================================================================
# TELEMATICS, EMERGENCY RESPONSE & DRIVER BEHAVIOR ADMINS
# ==============================================================================

@admin.register(EmergencyIncidentAlert)
class EmergencyIncidentAlertAdmin(ModelAdmin):
	list_display = (
		'incident_id',
		'severity_badge',
		'incident_type_display',
		'vehicle_link',
		'driver_name',
		'reported_at',
		'status_badge',
		'standby_replacement_status',
		'map_link',
	)
	list_filter = ('status', 'severity', 'incident_type', 'passengers_safety_status')
	search_fields = ('incident_id', 'vehicle__registration_number', 'driver__name', 'description', 'location_address')
	readonly_fields = ('incident_id', 'reported_at')
	autocomplete_fields = ['vehicle', 'driver', 'standby_vehicle', 'standby_driver']
	date_hierarchy = 'reported_at'

	fieldsets = (
		("Incident Distress Overview", {
			"fields": (
				"incident_id",
				("incident_type", "severity", "status"),
				("vehicle", "driver"),
				("trip", "contract_trip"),
				"reported_at",
			)
		}),
		("Location & Passenger Safety", {
			"fields": (
				("latitude", "longitude"),
				"location_address",
				("passenger_count", "passengers_safety_status"),
				"description",
			)
		}),
		("Standby / Replacement Vehicle Dispatch", {
			"fields": (
				("standby_vehicle", "standby_driver"),
				("standby_dispatched_at", "standby_eta_minutes"),
				"resolution_notes",
				"resolved_at",
			)
		}),
	)

	@admin.display(description="Severity", ordering='severity')
	def severity_badge(self, obj):
		colors = {
			'critical': ('#dc2626', '#fee2e2', '🚨 CRITICAL'),
			'high': ('#ea580c', '#ffedd5', '⚠️ HIGH'),
			'medium': ('#d97706', '#fef3c7', '⚡ MEDIUM'),
			'low': ('#2563eb', '#dbeafe', 'ℹ️ LOW'),
		}
		fg, bg, label = colors.get(obj.severity, ('#4b5563', '#f3f4f6', obj.severity))
		return format_html('<span style="background:{}; color:{}; padding:3px 8px; border-radius:12px; font-weight:700; font-size:11px;">{}</span>', bg, fg, label)

	@admin.display(description="Type")
	def incident_type_display(self, obj):
		return obj.get_incident_type_display()

	@admin.display(description="Vehicle", ordering='vehicle__registration_number')
	def vehicle_link(self, obj):
		return format_html('<a href="/admin/core/vehicle/{}/change/" style="font-weight:700; color:#38bdf8;">🚗 {}</a>', obj.vehicle.pk, obj.vehicle.registration_number)

	@admin.display(description="Driver", ordering='driver__name')
	def driver_name(self, obj):
		return obj.driver.name if obj.driver else "-"

	@admin.display(description="Status", ordering='status')
	def status_badge(self, obj):
		styles = {
			'reported': ('#ef4444', '#fff', '🔴 NEW SOS'),
			'acknowledged': ('#f59e0b', '#000', '🟡 ACKNOWLEDGED'),
			'standby_dispatched': ('#3b82f6', '#fff', '🔵 STANDBY EN ROUTE'),
			'resolved': ('#10b981', '#fff', '🟢 RESOLVED'),
			'closed': ('#64748b', '#fff', '⚪ CLOSED'),
		}
		bg, fg, label = styles.get(obj.status, ('#64748b', '#fff', obj.status))
		return format_html('<span style="background:{}; color:{}; padding:3px 9px; border-radius:12px; font-weight:700; font-size:11px;">{}</span>', bg, fg, label)

	@admin.display(description="Standby Replacement")
	def standby_replacement_status(self, obj):
		if obj.standby_vehicle:
			return format_html('<span style="color:#38bdf8; font-weight:600;">🔄 {} (Dispatched)</span>', obj.standby_vehicle.registration_number)
		return mark_safe('<span style="color:#94a3b8;">None</span>')

	@admin.display(description="GPS Map")
	def map_link(self, obj):
		if obj.latitude and obj.longitude:
			url = f"https://www.google.com/maps?q={obj.latitude},{obj.longitude}"
			return format_html('<a href="{}" target="_blank" style="background:#0284c7; color:#fff; padding:2px 8px; border-radius:4px; font-size:11px; text-decoration:none;">📍 Map View</a>', url)
		return "-"


@admin.register(VehicleTelematicsPing)
class VehicleTelematicsPingAdmin(ModelAdmin):
	list_display = ('vehicle', 'timestamp', 'speed_kmh', 'ignition_display', 'fuel_display', 'coordinates_display', 'trip_link')
	list_filter = ('ignition_on', 'vehicle')
	search_fields = ('vehicle__registration_number', 'vehicle__gps_imei')
	date_hierarchy = 'timestamp'
	readonly_fields = [f.name for f in VehicleTelematicsPing._meta.fields]

	def has_add_permission(self, request):
		return False  # Telemetry pings are ingested automatically

	@admin.display(description="Ignition")
	def ignition_display(self, obj):
		return mark_safe('🟢 ON' if obj.ignition_on else '⚪ OFF')

	@admin.display(description="Fuel")
	def fuel_display(self, obj):
		return f"{obj.fuel_level_pct:.1f}%" if obj.fuel_level_pct is not None else "-"

	@admin.display(description="Coordinates")
	def coordinates_display(self, obj):
		url = f"https://www.google.com/maps?q={obj.latitude},{obj.longitude}"
		return format_html('<a href="{}" target="_blank">{}, {} 📍</a>', url, f"{obj.latitude:.4f}", f"{obj.longitude:.4f}")

	@admin.display(description="Trip")
	def trip_link(self, obj):
		if obj.trip:
			return format_html('<a href="/trips/{}/">Trip #{}</a>', obj.trip.pk, obj.trip.trip_id)
		return "-"


@admin.register(DriverBehaviorLog)
class DriverBehaviorLogAdmin(ModelAdmin):
	list_display = ('timestamp', 'vehicle', 'driver', 'event_badge', 'severity_badge', 'speed_comparison', 'penalty_points', 'trip_link')
	list_filter = ('event_type', 'severity', 'vehicle')
	search_fields = ('vehicle__registration_number', 'driver__name', 'location_address')
	date_hierarchy = 'timestamp'

	@admin.display(description="Event Type", ordering='event_type')
	def event_badge(self, obj):
		labels = {
			'overspeeding': '⚡ Overspeeding',
			'harsh_braking': '🛑 Harsh Braking',
			'harsh_acceleration': '🚀 Harsh Acceleration',
			'excessive_idling': '⏱️ Idle > 15m',
			'sharp_cornering': '🔄 Sharp Turn',
			'geofence_breach': '🚧 Geofence Breach',
		}
		return labels.get(obj.event_type, obj.get_event_type_display())

	@admin.display(description="Severity", ordering='severity')
	def severity_badge(self, obj):
		colors = {
			'critical': ('#dc2626', '#fee2e2'),
			'high': ('#ea580c', '#ffedd5'),
			'medium': ('#d97706', '#fef3c7'),
			'low': ('#2563eb', '#dbeafe'),
		}
		fg, bg = colors.get(obj.severity, ('#4b5563', '#f3f4f6'))
		return format_html('<span style="background:{}; color:{}; padding:2px 8px; border-radius:10px; font-weight:700; font-size:11px;">{}</span>', bg, fg, obj.severity.upper())

	@admin.display(description="Speed vs Limit")
	def speed_comparison(self, obj):
		if obj.event_type == 'overspeeding':
			return format_html('<span style="color:#ef4444; font-weight:700;">{} km/h</span> (Limit: {})', obj.recorded_speed_kmh, obj.speed_limit_kmh)
		return f"{obj.recorded_speed_kmh} km/h"

	@admin.display(description="Trip")
	def trip_link(self, obj):
		if obj.trip:
			return format_html('<a href="/trips/{}/">Trip #{}</a>', obj.trip.pk, obj.trip.trip_id)
		return "-"


@admin.register(GeofenceZone)
class GeofenceZoneAdmin(ModelAdmin):
	list_display = ('name', 'zone_type_badge', 'coordinates_display', 'radius_display', 'speed_limit_display', 'is_active')
	list_filter = ('zone_type', 'is_active')
	search_fields = ('name',)

	@admin.display(description="Zone Type", ordering='zone_type')
	def zone_type_badge(self, obj):
		return format_html('<span style="font-weight:600;">🏷️ {}</span>', obj.get_zone_type_display())

	@admin.display(description="Center Coordinates")
	def coordinates_display(self, obj):
		url = f"https://www.google.com/maps?q={obj.latitude},{obj.longitude}"
		return format_html('<a href="{}" target="_blank">{}, {} 📍</a>', url, f"{obj.latitude:.4f}", f"{obj.longitude:.4f}")

	@admin.display(description="Radius")
	def radius_display(self, obj):
		return f"{obj.radius_meters:,} meters"

	@admin.display(description="Speed Limit")
	def speed_limit_display(self, obj):
		return f"{obj.speed_limit_kmh} km/h"


@admin.register(WhatsAppBotMessage)
class WhatsAppBotMessageAdmin(ModelAdmin):
	list_display = ('created_at_fmt', 'direction_badge', 'intent_badge', 'sender_phone', 'recipient_phone', 'short_body', 'status_badge', 'trip_link')
	list_filter = ('message_direction', 'intent', 'status', 'created_at')
	search_fields = ('sender_phone', 'recipient_phone', 'message_body', 'trip__trip_id')
	autocomplete_fields = ['trip', 'driver']
	readonly_fields = ('created_at',)
	date_hierarchy = 'created_at'

	@admin.display(description="Timestamp", ordering='created_at')
	def created_at_fmt(self, obj):
		return obj.created_at.strftime('%Y-%m-%d %H:%M:%S')

	@admin.display(description="Direction", ordering='message_direction')
	def direction_badge(self, obj):
		if obj.message_direction == 'inbound':
			return mark_safe('<span style="background: rgba(56, 189, 248, 0.15); color: #38bdf8; padding: 2px 8px; border-radius: 4px; font-weight: 700;">📥 Inbound</span>')
		return mark_safe('<span style="background: rgba(37, 211, 102, 0.15); color: #25d366; padding: 2px 8px; border-radius: 4px; font-weight: 700;">📤 Outbound</span>')

	@admin.display(description="Intent", ordering='intent')
	def intent_badge(self, obj):
		colors = {
			'dispatch_alert': ('#25d366', '🚖 Dispatch Sheet'),
			'driver_briefing': ('#38bdf8', '📋 Driver Briefing'),
			'start_handover': ('#10b981', '🟢 Start Handover'),
			'end_handover': ('#6366f1', '🏁 End Handover'),
			'sos_trigger': ('#ef4444', '🚨 SOS Emergency'),
			'trip_status': ('#f59e0b', '🛰️ Trip Status'),
			'payment_upi': ('#ec4899', '💳 UPI Payment'),
			'general_query': ('#94a3b8', '💬 General Chat'),
		}
		color, label = colors.get(obj.intent, ('#94a3b8', obj.get_intent_display()))
		return format_html('<span style="color: {}; font-weight: 700;">{}</span>', color, label)

	@admin.display(description="Message Body")
	def short_body(self, obj):
		text = obj.message_body or ""
		if len(text) > 60:
			return f"{text[:60]}..."
		return text

	@admin.display(description="Status", ordering='status')
	def status_badge(self, obj):
		colors = {
			'sent': '#10b981',
			'delivered': '#059669',
			'received': '#38bdf8',
			'failed': '#ef4444',
			'simulated': '#f59e0b',
		}
		c = colors.get(obj.status, '#94a3b8')
		return format_html('<span style="color: {}; font-weight: 600;">{}</span>', c, obj.get_status_display())

	@admin.display(description="Trip")
	def trip_link(self, obj):
		if obj.trip:
			url = reverse('admin:operations_trip_change', args=[obj.trip.pk])
			return format_html('<a href="{}" style="color: #38bdf8; font-weight: 600;">#{}</a>', url, obj.trip.trip_id)
		return "-"


@admin.register(DriverHandoverSession)
class DriverHandoverSessionAdmin(ModelAdmin):
	list_display = ('trip_link', 'session_type_badge', 'driver', 'vehicle', 'odometer_display', 'fuel_badge', 'photo_thumb', 'status_badge', 'created_at_fmt', 'verified_by')
	list_filter = ('session_type', 'status', 'created_at')
	search_fields = ('trip__trip_id', 'driver__name', 'vehicle__registration_number')
	autocomplete_fields = ['trip', 'driver', 'vehicle']
	readonly_fields = ('created_at', 'verified_at')
	date_hierarchy = 'created_at'

	@admin.display(description="Trip")
	def trip_link(self, obj):
		url = reverse('admin:operations_trip_change', args=[obj.trip.pk])
		return format_html('<a href="{}" style="color: #38bdf8; font-weight: 700;">#{}</a>', url, obj.trip.trip_id)

	@admin.display(description="Session Type", ordering='session_type')
	def session_type_badge(self, obj):
		if obj.session_type == 'start':
			return mark_safe('<span style="background: rgba(16, 185, 129, 0.15); color: #10b981; padding: 2px 8px; border-radius: 4px; font-weight: 700;">🟢 Start Duty</span>')
		return mark_safe('<span style="background: rgba(59, 130, 246, 0.15); color: #3b82f6; padding: 2px 8px; border-radius: 4px; font-weight: 700;">🏁 End Duty</span>')

	@admin.display(description="Odometer Reading")
	def odometer_display(self, obj):
		return format_html('<span style="font-family: monospace; font-weight: 700; color: #fff;">{} KM</span>', obj.odometer_reading)

	@admin.display(description="Fuel Level")
	def fuel_badge(self, obj):
		return format_html('<span style="font-weight: 600; color: #fbbf24;">⛽ {}%</span>', obj.fuel_level_percent)

	@admin.display(description="Odometer Photo")
	def photo_thumb(self, obj):
		if obj.odometer_photo:
			return format_html('<a href="{}" target="_blank"><img src="{}" style="width: 36px; height: 36px; object-fit: cover; border-radius: 6px; border: 1px solid rgba(255,255,255,0.2);"></a>', obj.odometer_photo.url, obj.odometer_photo.url)
		return mark_safe('<span style="color: #64748b;">No photo</span>')

	@admin.display(description="Audit Status", ordering='status')
	def status_badge(self, obj):
		colors = {
			'approved': ('rgba(16, 185, 129, 0.2)', '#10b981', '✓ Approved'),
			'submitted': ('rgba(245, 158, 11, 0.2)', '#fbbf24', '⏳ Submitted'),
			'flagged': ('rgba(239, 68, 68, 0.2)', '#f87171', '✕ Flagged'),
		}
		bg, fg, label = colors.get(obj.status, ('rgba(255,255,255,0.1)', '#fff', obj.get_status_display()))
		return format_html('<span style="background: {}; color: {}; padding: 2px 8px; border-radius: 4px; font-weight: 700; font-size: 11px;">{}</span>', bg, fg, label)

	@admin.display(description="Timestamp", ordering='created_at')
	def created_at_fmt(self, obj):
		return obj.created_at.strftime('%Y-%m-%d %H:%M')


@admin.register(TripMilestoneEvent)
class TripMilestoneEventAdmin(ModelAdmin):
	list_display = ('trip_link', 'milestone_step_badge', 'timestamp_fmt', 'odometer_display', 'pin_badge', 'location_name', 'actor_driver')
	list_filter = ('milestone', 'is_pin_verified', 'timestamp')
	search_fields = ('trip__trip_id', 'location_name', 'actor_driver__name', 'passenger_pin_entered')
	autocomplete_fields = ['trip', 'actor_driver']
	readonly_fields = ('timestamp',)
	date_hierarchy = 'timestamp'

	@admin.display(description="Trip")
	def trip_link(self, obj):
		url = reverse('admin:operations_trip_change', args=[obj.trip.pk])
		return format_html('<a href="{}" style="color: #38bdf8; font-weight: 700;">#{}</a>', url, obj.trip.trip_id)

	@admin.display(description="Milestone", ordering='milestone_index')
	def milestone_step_badge(self, obj):
		icons = {
			'car_pickup': ('#38bdf8', '🚗 1. Car Pickup'),
			'driver_reached': ('#06b6d4', '📍 2. Driver Reached'),
			'guest_pickup': ('#a855f7', '🔢 3. Guest Pickup'),
			'on_trip': ('#10b981', '🛣️ 4. On Trip'),
			'guest_drop': ('#f59e0b', '🏁 5. Guest Drop'),
			'expenses_photo': ('#ec4899', '🧾 6. Expenses Photo'),
			'car_drop': ('#64748b', '🅿️ 7. Car Drop'),
		}
		color, label = icons.get(obj.milestone, ('#94a3b8', obj.get_milestone_display()))
		return format_html('<span style="background: rgba(255,255,255,0.08); border: 1px solid {}; color: {}; padding: 2px 8px; border-radius: 4px; font-weight: 700; font-size: 11px;">{}</span>', color, color, label)

	@admin.display(description="Odometer")
	def odometer_display(self, obj):
		if obj.odometer_reading:
			return f"{obj.odometer_reading} KM"
		return "-"

	@admin.display(description="PIN Verified")
	def pin_badge(self, obj):
		if obj.milestone == 'guest_pickup':
			if obj.is_pin_verified:
				return format_html('<span style="color: #10b981; font-weight: 700;">✓ Verified ({})</span>', obj.passenger_pin_entered)
			return format_html('<span style="color: #ef4444; font-weight: 700;">✕ Invalid</span>')
		return "-"

	@admin.display(description="Timestamp", ordering='timestamp')
	def timestamp_fmt(self, obj):
		return obj.timestamp.strftime('%Y-%m-%d %H:%M')



