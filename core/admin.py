from decimal import Decimal
from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline
from django.db.models import Prefetch, Q
from django.utils import timezone
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from datetime import timedelta

from .models import (
	Cleaner,
	CleanerEmploymentPeriod,
	Client,
	Driver,
	DriverEmploymentPeriod,
	LicenseClass,
	Party,
	RateCard,
	Supplier,
	Vehicle,
	VehiclePhoto,
	VehicleType,
)


def format_phone_display(phone_raw):
	if not phone_raw:
		return mark_safe('<span class="text-muted">—</span>')
	digits = ''.join(c for c in phone_raw if c.isdigit())
	wa_num = digits if len(digits) > 10 else f"91{digits}"
	return format_html(
		'<div style="display:inline-flex; align-items:center; gap:6px;">'
		'<span>{}</span>'
		'<a href="https://wa.me/{}" target="_blank" title="Chat on WhatsApp" style="color:#22c55e; font-size:14px;"><i class="fab fa-whatsapp"></i></a>'
		'<a href="tel:{}" title="Call" style="color:#3b82f6; font-size:13px;"><i class="fas fa-phone-alt"></i></a>'
		'</div>',
		phone_raw, wa_num, phone_raw
	)


# ─────────────────────────────────────────────────────────────────────────────
# Party & Proxy Admins (Client & Supplier)
# ─────────────────────────────────────────────────────────────────────────────

@admin.register(Party)
class PartyAdmin(ModelAdmin):
	search_fields = ('name', 'phone', 'email')

	def has_module_permission(self, request):
		return False


@admin.register(Client)
class ClientAdmin(ModelAdmin):
	def has_module_permission(self, request):
		return False

	list_display = (
		'name',
		'party_type_badge',
		'phone_display',
		'billing_cycle_badge',
		'outstanding_balance_display',
		'trips_count_display',
		'is_active_badge',
		'quick_actions',
	)
	list_filter = ('party_type', 'billing_cycle', 'is_active')
	search_fields = ('name', 'phone', 'email', 'gstin')
	actions = ['mark_active', 'mark_inactive']

	class Media:
		js = ('admin/js/client_admin.js',)

	fieldsets = (
		('Basic Info', {
			'fields': ('name', 'party_type', 'phone', 'email', 'address', 'is_active')
		}),
		('Tax & Compliance', {
			'fields': ('gstin', 'state_code', 'tds_rate'),
		}),
		('B2B / Corporate Billing', {
			'fields': ('billing_cycle', 'credit_period_days', 'opening_balance'),
			'classes': ('b2b-corporate-billing',)
		}),
	)

	def get_queryset(self, request):
		qs = super().get_queryset(request)
		return qs.exclude(party_type='supplier')

	def get_changeform_initial_data(self, request):
		return {'party_type': 'corporate'}

	@admin.display(description='Client Type')
	def party_type_badge(self, obj):
		styles = {
			'corporate': ('#2563eb', 'fas fa-building', 'Corporate'),
			'travel_agency': ('#7c3aed', 'fas fa-plane', 'Travel Agency'),
			'hotel': ('#0891b2', 'fas fa-hotel', 'Hotel'),
			'individual': ('#4b5563', 'fas fa-user', 'Individual'),
			'other': ('#6b7280', 'fas fa-tag', 'Other'),
		}
		bg, icon, label = styles.get(obj.party_type, ('#6b7280', 'fas fa-tag', obj.get_party_type_display()))
		return format_html(
			'<span class="badge" style="background-color: {}; color: #fff; padding: 4px 8px; border-radius: 4px; font-weight: 500;">'
			'<i class="{} mr-1"></i>{}'
			'</span>',
			bg, icon, label
		)

	@admin.display(description='Contact')
	def phone_display(self, obj):
		return format_phone_display(obj.phone)

	@admin.display(description='Billing Cycle')
	def billing_cycle_badge(self, obj):
		return format_html(
			'<span style="font-size: 12px; color: #f1f5f9; font-weight: 500;">{} <span style="color: #94a3b8;">({}d credit)</span></span>',
			obj.get_billing_cycle_display(),
			obj.credit_period_days
		)

	@admin.display(description='Outstanding Balance')
	def outstanding_balance_display(self, obj):
		try:
			from finance.services import calculate_party_ledger
			ledger = calculate_party_ledger(obj)
			closing = ledger.get('closing_balance', Decimal('0'))
		except Exception:
			closing = obj.opening_balance

		if closing > 0:
			amt_str = f"₹{closing:,.2f} Due"
			return format_html(
				'<span style="color: #f87171; font-weight: 700;" title="Customer owes this amount">{}</span>',
				amt_str
			)
		elif closing < 0:
			amt_str = f"₹{abs(closing):,.2f} Cr"
			return format_html(
				'<span style="color: #4ade80; font-weight: 700;" title="Customer has credit balance">{}</span>',
				amt_str
			)
		return mark_safe('<span style="color: #4ade80; font-weight: 600;">₹0.00 Settled</span>')

	@admin.display(description='Trips')
	def trips_count_display(self, obj):
		count = obj.trips.count()
		return format_html(
			'<a href="/admin/operations/trip/?party__id__exact={}" class="badge badge-info" style="font-size: 12px; padding: 4px 8px; text-decoration: none;" title="View all trips for this client">'
			'<i class="fas fa-route mr-1"></i>{} Trips'
			'</a>',
			obj.id, count
		)

	@admin.display(description='Status')
	def is_active_badge(self, obj):
		if obj.is_active:
			return mark_safe('<span class="badge badge-success" style="background-color: #10b981; color: #fff; padding: 4px 8px;">Active</span>')
		return mark_safe('<span class="badge badge-secondary" style="background-color: #9ca3af; color: #fff; padding: 4px 8px;">Inactive</span>')

	@admin.display(description='Actions')
	def quick_actions(self, obj):
		return format_html(
			'<div style="display: flex; gap: 4px; align-items: center;">'
			'<a href="/parties/{}/ledger/" target="_blank" class="btn btn-xs btn-outline-primary" style="padding: 2px 6px; font-size: 11px;" title="View Client Ledger"><i class="fas fa-book mr-1"></i>Ledger</a>'
			'<a href="/admin/statements/statement/add/?party={}" class="btn btn-xs btn-outline-secondary" style="padding: 2px 6px; font-size: 11px;" title="Generate Statement"><i class="fas fa-file-invoice mr-1"></i>Statement</a>'
			'<a href="/admin/operations/booking/add/?party={}" class="btn btn-xs btn-outline-success" style="padding: 2px 6px; font-size: 11px;" title="New Booking for this Client"><i class="fas fa-plus mr-1"></i>Booking</a>'
			'</div>',
			obj.id, obj.id, obj.id
		)

	@admin.action(description="Mark selected clients as Active")
	def mark_active(self, request, queryset):
		updated = queryset.update(is_active=True)
		self.message_user(request, f"{updated} clients marked as active.")

	@admin.action(description="Mark selected clients as Inactive")
	def mark_inactive(self, request, queryset):
		updated = queryset.update(is_active=False)
		self.message_user(request, f"{updated} clients marked as inactive.")


@admin.register(Supplier)
class SupplierAdmin(ModelAdmin):
	def has_module_permission(self, request):
		return False

	list_display = (
		'name',
		'phone_display',
		'vehicles_count_display',
		'drivers_count_display',
		'payable_balance_display',
		'billing_cycle_badge',
		'is_active_badge',
		'quick_actions',
	)
	list_filter = ('billing_cycle', 'is_active')
	search_fields = ('name', 'phone', 'email', 'gstin')
	actions = ['mark_active', 'mark_inactive']

	fieldsets = (
		('Supplier Info', {
			'fields': ('name', 'phone', 'email', 'address', 'is_active')
		}),
		('Tax & Compliance', {
			'fields': ('gstin', 'state_code', 'tds_rate'),
		}),
		('Financial Terms', {
			'fields': ('billing_cycle', 'credit_period_days', 'opening_balance')
		}),
	)

	def get_queryset(self, request):
		qs = super().get_queryset(request)
		return qs.filter(party_type='supplier')

	def save_model(self, request, obj, form, change):
		obj.party_type = 'supplier'
		super().save_model(request, obj, form, change)

	@admin.display(description='Contact')
	def phone_display(self, obj):
		return format_phone_display(obj.phone)

	@admin.display(description='Supplied Fleet')
	def vehicles_count_display(self, obj):
		count = obj.supplied_vehicles.count()
		return format_html(
			'<a href="/admin/core/vehicle/?owner_party__id__exact={}" class="badge" style="background-color: #3b82f6; color: #fff; padding: 4px 8px; font-size: 12px; text-decoration: none;" title="View vehicles supplied by this vendor">'
			'<i class="fas fa-bus mr-1"></i>{} Vehicles'
			'</a>',
			obj.id, count
		)

	@admin.display(description='Employed Drivers')
	def drivers_count_display(self, obj):
		count = obj.employed_drivers.count()
		return format_html(
			'<a href="/admin/core/driver/?employer_party__id__exact={}" class="badge" style="background-color: #06b6d4; color: #fff; padding: 4px 8px; font-size: 12px; text-decoration: none;" title="View drivers employed by this supplier">'
			'<i class="fas fa-id-card mr-1"></i>{} Drivers'
			'</a>',
			obj.id, count
		)

	@admin.display(description='Payable Balance')
	def payable_balance_display(self, obj):
		try:
			from finance.services import calculate_supplier_ledger
			ledger = calculate_supplier_ledger(obj)
			closing = ledger.get('closing_balance', Decimal('0'))
		except Exception:
			closing = obj.opening_balance

		if closing > 0:
			amt_str = f"₹{closing:,.2f} Payable"
			return format_html(
				'<span style="color: #fb923c; font-weight: 700;" title="Amount company owes to supplier">{}</span>',
				amt_str
			)
		elif closing < 0:
			amt_str = f"₹{abs(closing):,.2f} Adv Paid"
			return format_html(
				'<span style="color: #4ade80; font-weight: 700;" title="Company has advance with supplier">{}</span>',
				amt_str
			)
		return mark_safe('<span style="color: #4ade80; font-weight: 600;">₹0.00 Settled</span>')

	@admin.display(description='Terms')
	def billing_cycle_badge(self, obj):
		return format_html(
			'<span style="font-size: 12px; color: #f1f5f9; font-weight: 500;">{} <span style="color: #94a3b8;">({}d)</span></span>',
			obj.get_billing_cycle_display(),
			obj.credit_period_days
		)

	@admin.display(description='Status')
	def is_active_badge(self, obj):
		if obj.is_active:
			return mark_safe('<span class="badge badge-success" style="background-color: #10b981; color: #fff; padding: 4px 8px;">Active</span>')
		return mark_safe('<span class="badge badge-secondary" style="background-color: #9ca3af; color: #fff; padding: 4px 8px;">Inactive</span>')

	@admin.display(description='Actions')
	def quick_actions(self, obj):
		return format_html(
			'<div style="display: flex; gap: 4px; align-items: center;">'
			'<a href="/parties/{}/ledger/" target="_blank" class="btn btn-xs btn-outline-primary" style="padding: 2px 6px; font-size: 11px;" title="View Supplier Ledger"><i class="fas fa-book mr-1"></i>Ledger</a>'
			'<a href="/admin/statements/statement/add/?party={}" class="btn btn-xs btn-outline-secondary" style="padding: 2px 6px; font-size: 11px;" title="Create Statement"><i class="fas fa-file-invoice mr-1"></i>Statement</a>'
			'<a href="/admin/core/vehicle/add/?owner_party={}&ownership_type=outsourced" class="btn btn-xs btn-outline-info" style="padding: 2px 6px; font-size: 11px;" title="Add Vehicle for Supplier"><i class="fas fa-plus mr-1"></i>Vehicle</a>'
			'</div>',
			obj.id, obj.id, obj.id
		)

	@admin.action(description="Mark selected suppliers as Active")
	def mark_active(self, request, queryset):
		updated = queryset.update(is_active=True)
		self.message_user(request, f"{updated} suppliers marked as active.")

	@admin.action(description="Mark selected suppliers as Inactive")
	def mark_inactive(self, request, queryset):
		updated = queryset.update(is_active=False)
		self.message_user(request, f"{updated} suppliers marked as inactive.")


# ─────────────────────────────────────────────────────────────────────────────
# License Class & Vehicle Type Admins
# ─────────────────────────────────────────────────────────────────────────────

@admin.register(LicenseClass)
class LicenseClassAdmin(ModelAdmin):
	def has_module_permission(self, request):
		return False

	list_display = ('code_badge', 'name', 'example_vehicles', 'drivers_count_display')
	search_fields = ('code', 'name', 'example_vehicles')

	@admin.display(description='License Code')
	def code_badge(self, obj):
		return format_html(
			'<span class="badge" style="background-color: #1e293b; color: #f8fafc; font-size: 12px; font-family: monospace; padding: 4px 8px; border-radius: 4px;">{}</span>',
			obj.code
		)

	@admin.display(description='Qualified Drivers')
	def drivers_count_display(self, obj):
		count = obj.driver_set.count()
		return format_html(
			'<a href="/admin/core/driver/?license_classes__id__exact={}" class="badge" style="background-color: #0284c7; color: #fff; padding: 4px 8px; font-size: 12px; text-decoration: none;" title="View drivers licensed for this class">'
			'<i class="fas fa-user-check mr-1"></i>{} Drivers'
			'</a>',
			obj.id, count
		)


@admin.register(VehicleType)
class VehicleTypeAdmin(ModelAdmin):
	list_display = ('name', 'category_badge', 'seating_capacity_display', 'fleet_count_display', 'rates_summary_display', 'features_summary')
	search_fields = ('name', 'category')
	list_filter = ('category', 'fuel_type', 'toll_class', 'transmission_type', 'has_ac', 'is_luxury')

	fieldsets = (
		('Basic Info', {
			'fields': ('name', 'category', 'description', 'stock_photo')
		}),
		('Pricing & Rates', {
			'fields': ('default_day_rate', 'default_km_rate', 'minimum_km_per_day', 'extra_km_rate', 'extra_hour_rate', 'driver_bata', 'night_halt_charge')
		}),
		('Operations & Specs', {
			'fields': ('seating_capacity', 'luggage_capacity', 'fuel_type', 'expected_mileage_kmpl', 'toll_class')
		}),
		('Customer Features', {
			'fields': ('has_ac', 'is_luxury', 'transmission_type', 'is_wheelchair_accessible', 'amenities')
		}),
	)

	@admin.display(description='Category')
	def category_badge(self, obj):
		if not obj.category:
			return mark_safe('<span style="color: #94a3b8;">—</span>')
		return format_html(
			'<span class="badge" style="background-color: #1e293b; color: #93c5fd; border: 1px solid #3b82f6; font-size: 12px; padding: 3px 8px;">{}</span>',
			obj.category
		)

	@admin.display(description='Seating')
	def seating_capacity_display(self, obj):
		return format_html(
			'<span class="badge" style="background-color: #334155; color: #f8fafc; border: 1px solid #475569; font-size: 12px; padding: 4px 8px;"><i class="fas fa-users mr-1"></i>{} Seats</span>',
			obj.seating_capacity
		)

	@admin.display(description='Fleet Count')
	def fleet_count_display(self, obj):
		total = obj.vehicle_set.count()
		owned = obj.vehicle_set.filter(ownership_type='owned').count()
		outsourced = obj.vehicle_set.filter(ownership_type='outsourced').count()
		return format_html(
			'<a href="/admin/core/vehicle/?vehicle_type__id__exact={}" class="badge" style="background-color: #3b82f6; color: #fff; padding: 4px 8px; font-size: 12px; text-decoration: none;" title="View fleet vehicles of this type">'
			'<i class="fas fa-bus mr-1"></i>{} Fleet ({} Own / {} Out)'
			'</a>',
			obj.id, total, owned, outsourced
		)

	@admin.display(description='Default Base Rates')
	def rates_summary_display(self, obj):
		rates_str = f"₹{obj.default_day_rate:,.0f}/day • ₹{obj.default_km_rate:,.2f}/km"
		min_km_str = f"(min {obj.minimum_km_per_day} km)"
		return format_html(
			'<span style="font-size: 13px; color: #38bdf8; font-weight: 600;">'
			'{} <span style="color: #94a3b8; font-weight: 400; font-size: 12px;">{}</span>'
			'</span>',
			rates_str, min_km_str
		)

	@admin.display(description='Features')
	def features_summary(self, obj):
		pills = []
		if obj.has_ac:
			pills.append('<span class="badge" style="background-color: #0284c7; color: #fff; margin-right: 3px;">AC</span>')
		else:
			pills.append('<span class="badge" style="background-color: #475569; color: #cbd5e1; border: 1px solid #64748b; margin-right: 3px;">Non-AC</span>')

		if obj.is_luxury:
			pills.append('<span class="badge" style="background-color: #d97706; color: #fff; margin-right: 3px;">Luxury ⭐</span>')

		if obj.fuel_type:
			fuel_styles = {
				'diesel': ('#059669', 'Diesel ⛽'),
				'petrol': ('#d97706', 'Petrol ⛽'),
				'cng': ('#0284c7', 'CNG 🌿'),
				'electric': ('#7c3aed', 'Electric ⚡'),
			}
			bg, label = fuel_styles.get(obj.fuel_type, ('#475569', obj.get_fuel_type_display()))
			pills.append(f'<span class="badge" style="background-color: {bg}; color: #fff; margin-right: 3px;">{label}</span>')

		if obj.is_wheelchair_accessible:
			pills.append('<span class="badge" style="background-color: #8b5cf6; color: #fff; margin-right: 3px;" title="Wheelchair Accessible"><i class="fas fa-wheelchair"></i></span>')

		return mark_safe(''.join(pills))


# ─────────────────────────────────────────────────────────────────────────────
# Driver & Cleaner Admins
# ─────────────────────────────────────────────────────────────────────────────

class LicenseExpiryFilter(admin.SimpleListFilter):
	title = 'License Validity'
	parameter_name = 'license_validity_status'

	def lookups(self, request, model_admin):
		return (
			('expired', '🔴 Expired License'),
			('expiring_soon', '🟡 Expiring within 30 Days'),
			('valid', '🟢 Valid (> 30 Days)'),
			('missing', '⚪ No Expiry Set'),
		)

	def queryset(self, request, queryset):
		today = timezone.localdate()
		in_30_days = today + timedelta(days=30)

		if self.value() == 'expired':
			return queryset.filter(
				Q(license_validity_tr__lt=today) |
				(Q(license_validity_tr__isnull=True) & Q(license_validity_nt__lt=today))
			)
		if self.value() == 'expiring_soon':
			return queryset.filter(
				(Q(license_validity_tr__gte=today) & Q(license_validity_tr__lte=in_30_days)) |
				(Q(license_validity_tr__isnull=True) & Q(license_validity_nt__gte=today) & Q(license_validity_nt__lte=in_30_days))
			)
		if self.value() == 'valid':
			return queryset.filter(
				Q(license_validity_tr__gt=in_30_days) |
				(Q(license_validity_tr__isnull=True) & Q(license_validity_nt__gt=in_30_days))
			)
		if self.value() == 'missing':
			return queryset.filter(license_validity_tr__isnull=True, license_validity_nt__isnull=True)
		return queryset


class DriverEmploymentPeriodInline(TabularInline):
	model = DriverEmploymentPeriod
	extra = 0
	fields = ('joined_on', 'left_on', 'notes')


@admin.register(Driver)
class DriverAdmin(ModelAdmin):
	def has_module_permission(self, request):
		return False

	list_display = (
		'name',
		'driver_type_badge',
		'phone_display',
		'license_status_badge',
		'deployment_status_display',
		'skills_display',
		'status_badge',
	)
	list_filter = ('driver_type', 'status', LicenseExpiryFilter, 'is_volvo_certified', 'hill_station_experience')
	search_fields = ('name', 'phone', 'license_number', 'employer_party__name', 'aadhar_number', 'badge_number')
	actions = ['mark_active', 'mark_inactive', 'mark_on_leave']

	class Media:
		js = ('admin/js/driver_admin.js',)

	filter_horizontal = ('license_classes',)
	inlines = [DriverEmploymentPeriodInline]

	fieldsets = (
		('Basic Info', {
			'fields': ('name', 'driver_type', 'employer_party', 'phone', 'address', 'joining_date', 'status')
		}),
		('Identity & Background', {
			'fields': ('date_of_birth', 'father_or_spouse_name', 'aadhar_number', 'profile_picture')
		}),
		('Official Driving License Details', {
			'fields': ('license_number', 'licensing_authority', 'license_issue_date', 'license_classes', 'license_validity_nt', 'license_validity_tr', 'badge_number', 'is_volvo_certified', 'license_document')
		}),
		('Safety & Emergencies', {
			'fields': ('emergency_contact_name', 'emergency_contact_phone', 'blood_group')
		}),
		('Financial Settlements', {
			'fields': ('bank_account_number', 'ifsc_code', 'bank_name', 'upi_id')
		}),
		('Customer Experience', {
			'fields': ('languages_spoken', 'hill_station_experience')
		}),
	)

	def get_queryset(self, request):
		qs = super().get_queryset(request)
		from operations.models import Trip
		today = timezone.localdate()
		active_trips_prefetch = Prefetch(
			'trips',
			queryset=Trip.objects.filter(
				status__in=['started', 'assigned', 'driver_confirmed'],
				start_date__lte=today,
				end_date__gte=today
			),
			to_attr='active_trips_list'
		)
		return qs.prefetch_related(active_trips_prefetch, 'license_classes')

	@admin.display(description='Driver Type')
	def driver_type_badge(self, obj):
		if obj.driver_type == 'owned':
			return mark_safe('<span class="badge" style="background-color: #10b981; color: #fff; padding: 4px 8px; border-radius: 4px;"><i class="fas fa-user-tie mr-1"></i>Company Own</span>')
		elif obj.driver_type == 'supplier':
			sup_name = obj.employer_party.name if obj.employer_party else "Supplier"
			return format_html(
				'<span class="badge" style="background-color: #8b5cf6; color: #fff; padding: 4px 8px; border-radius: 4px;"><i class="fas fa-truck-moving mr-1"></i>Supplier</span><br><small style="color: #cbd5e1; font-size: 11px;">{}</small>',
				sup_name
			)
		return mark_safe('<span class="badge" style="background-color: #f59e0b; color: #fff; padding: 4px 8px; border-radius: 4px;"><i class="fas fa-clock mr-1"></i>Contract / Ad-hoc</span>')

	@admin.display(description='Phone')
	def phone_display(self, obj):
		return format_phone_display(obj.phone)

	@admin.display(description='License Status')
	def license_status_badge(self, obj):
		st = obj.license_status
		if st['status'] == 'expired':
			return format_html(
				'<span class="badge" style="background-color: #ef4444; color: #fff; padding: 4px 8px; font-weight: 600;" title="Driving license is expired!">'
				'<i class="fas fa-exclamation-triangle mr-1"></i>{}'
				'</span>',
				st['label']
			)
		elif st['status'] == 'expiring_soon':
			return format_html(
				'<span class="badge" style="background-color: #f59e0b; color: #1e293b; padding: 4px 8px; font-weight: 600;" title="License expiring soon">'
				'<i class="fas fa-clock mr-1"></i>{}'
				'</span>',
				st['label']
			)
		elif st['status'] == 'valid':
			return format_html(
				'<span class="badge" style="background-color: #10b981; color: #fff; padding: 4px 8px;" title="License is valid">'
				'<i class="fas fa-check-circle mr-1"></i>{}'
				'</span>',
				st['label']
			)
		return mark_safe('<span class="badge" style="background-color: #475569; color: #f8fafc; padding: 4px 8px;">No Expiry Set</span>')

	@admin.display(description='Deployment')
	def deployment_status_display(self, obj):
		active_trips = getattr(obj, 'active_trips_list', None)
		if active_trips is None:
			from operations.models import Trip
			today = timezone.localdate()
			active_trips = obj.trips.filter(
				status__in=['started', 'assigned', 'driver_confirmed'],
				start_date__lte=today,
				end_date__gte=today
			)
		active_trip = active_trips[0] if active_trips else None

		if active_trip:
			trip_label = f"#{active_trip.trip_id}" if active_trip.trip_id else "Trip"
			return format_html(
				'<span class="badge" style="background-color: #f59e0b; color: #0f172a; padding: 4px 8px; font-weight: 700;">'
				'<i class="fas fa-route mr-1"></i>On Trip <a href="/admin/operations/trip/{}/change/" style="color: #0f172a; font-weight: bold; text-decoration: underline; margin-left: 2px;">{}</a>'
				'</span>',
				active_trip.id, trip_label
			)
		if obj.status == 'active':
			return mark_safe('<span class="badge" style="background-color: #10b981; color: #fff; padding: 4px 8px;"><i class="fas fa-check mr-1"></i>Available</span>')
		return mark_safe('<span class="badge" style="background-color: #475569; color: #f8fafc; padding: 4px 8px;">Off Duty</span>')

	@admin.display(description='Skills & Certs')
	def skills_display(self, obj):
		pills = []
		if obj.is_volvo_certified:
			pills.append('<span class="badge" style="background-color: #2563eb; color: #fff; padding: 3px 7px; font-size: 11px; margin-right: 3px;" title="Volvo Certified Multi-Axle">Volvo ⭐</span>')
		if obj.hill_station_experience:
			pills.append('<span class="badge" style="background-color: #059669; color: #fff; padding: 3px 7px; font-size: 11px; margin-right: 3px;" title="Hill Station Trained">Hills ⛰️</span>')
		if not pills:
			return mark_safe('<span style="color: #94a3b8; font-size: 11px;">Standard</span>')
		return mark_safe(''.join(pills))

	@admin.display(description='Status')
	def status_badge(self, obj):
		if obj.status == 'active':
			return mark_safe('<span class="badge badge-success" style="background-color: #10b981; color: #fff; padding: 4px 8px;">Active</span>')
		elif obj.status == 'on_leave':
			return mark_safe('<span class="badge badge-warning" style="background-color: #f97316; color: #fff; padding: 4px 8px;">On Leave</span>')
		return mark_safe('<span class="badge badge-secondary" style="background-color: #9ca3af; color: #fff; padding: 4px 8px;">Inactive</span>')

	@admin.action(description="Mark selected drivers as Active")
	def mark_active(self, request, queryset):
		updated = queryset.update(status='active')
		self.message_user(request, f"{updated} drivers marked as active.")

	@admin.action(description="Mark selected drivers as Inactive")
	def mark_inactive(self, request, queryset):
		updated = queryset.update(status='inactive')
		self.message_user(request, f"{updated} drivers marked as inactive.")

	@admin.action(description="Mark selected drivers as On Leave")
	def mark_on_leave(self, request, queryset):
		updated = queryset.update(status='on_leave')
		self.message_user(request, f"{updated} drivers marked as on leave.")


class CleanerEmploymentPeriodInline(TabularInline):
	model = CleanerEmploymentPeriod
	extra = 0
	fields = ('joined_on', 'left_on', 'notes')


@admin.register(Cleaner)
class CleanerAdmin(ModelAdmin):
	def has_module_permission(self, request):
		return False

	list_display = (
		'name',
		'employer_display',
		'phone_display',
		'can_drive_badge',
		'default_daily_rate_display',
		'status_badge',
	)
	list_filter = ('status', 'can_drive')
	search_fields = ('name', 'phone', 'employer_party__name', 'aadhar_number', 'license_number')
	actions = ['mark_active', 'mark_inactive', 'mark_on_leave']

	class Media:
		js = ('admin/js/cleaner_admin.js',)

	inlines = [CleanerEmploymentPeriodInline]

	fieldsets = (
		('Basic Info', {
			'fields': ('name', 'employer_party', 'phone', 'address', 'joining_date', 'status', 'default_daily_rate', 'can_drive')
		}),
		('Identity & Background', {
			'fields': ('date_of_birth', 'aadhar_number', 'profile_picture')
		}),
		('License Details', {
			'fields': ('license_number', 'license_validity'),
			'description': 'Only applicable if this cleaner is marked as "Can drive".'
		}),
		('Safety & Emergencies', {
			'fields': ('emergency_contact_name', 'emergency_contact_phone', 'blood_group')
		}),
		('Financial Settlements', {
			'fields': ('bank_account_number', 'ifsc_code', 'bank_name', 'upi_id')
		}),
	)

	@admin.display(description='Employer / Supplier')
	def employer_display(self, obj):
		if obj.employer_party:
			return format_html('<span style="color: #f1f5f9; font-weight: 500;">{}</span>', obj.employer_party.name)
		return mark_safe('<span class="badge badge-success" style="background-color: #10b981; color: #fff; padding: 3px 6px;">In-House Staff</span>')

	@admin.display(description='Phone')
	def phone_display(self, obj):
		return format_phone_display(obj.phone)

	@admin.display(description='Driving Capability')
	def can_drive_badge(self, obj):
		if obj.can_drive:
			today = timezone.localdate()
			if obj.license_validity and obj.license_validity < today:
				return format_html(
					'<span class="badge" style="background-color: #ef4444; color: #fff; padding: 4px 8px;" title="Driving license expired!">'
					'<i class="fas fa-id-card mr-1"></i>Lic Expired ({})'
					'</span>',
					obj.license_validity.strftime('%d/%m/%Y')
				)
			lic_txt = f" ({obj.license_number})" if obj.license_number else ""
			return format_html(
				'<span class="badge" style="background-color: #10b981; color: #fff; padding: 4px 8px;">'
				'<i class="fas fa-id-card mr-1"></i>Can Drive{}'
				'</span>',
				lic_txt
			)
		return mark_safe('<span class="badge" style="background-color: #475569; color: #f8fafc; padding: 3px 6px;">Helper Only</span>')

	@admin.display(description='Daily Allowance Rate')
	def default_daily_rate_display(self, obj):
		rate_str = f"₹{obj.default_daily_rate:,.2f}"
		return format_html('<span style="color: #38bdf8; font-weight: 600;">{}<small style="color: #94a3b8; font-weight: normal;"> /day</small></span>', rate_str)

	@admin.display(description='Status')
	def status_badge(self, obj):
		if obj.status == 'active':
			return mark_safe('<span class="badge badge-success" style="background-color: #10b981; color: #fff; padding: 4px 8px;">Active</span>')
		elif obj.status == 'on_leave':
			return mark_safe('<span class="badge badge-warning" style="background-color: #f97316; color: #fff; padding: 4px 8px;">On Leave</span>')
		return mark_safe('<span class="badge badge-secondary" style="background-color: #9ca3af; color: #fff; padding: 4px 8px;">Inactive</span>')

	@admin.action(description="Mark selected cleaners as Active")
	def mark_active(self, request, queryset):
		updated = queryset.update(status='active')
		self.message_user(request, f"{updated} cleaners marked as active.")

	@admin.action(description="Mark selected cleaners as Inactive")
	def mark_inactive(self, request, queryset):
		updated = queryset.update(status='inactive')
		self.message_user(request, f"{updated} cleaners marked as inactive.")

	@admin.action(description="Mark selected cleaners as On Leave")
	def mark_on_leave(self, request, queryset):
		updated = queryset.update(status='on_leave')
		self.message_user(request, f"{updated} cleaners marked as on leave.")


# ─────────────────────────────────────────────────────────────────────────────
# Vehicle Admin
# ─────────────────────────────────────────────────────────────────────────────

class VehicleComplianceFilter(admin.SimpleListFilter):
	title = 'Document Compliance'
	parameter_name = 'compliance_status'

	def lookups(self, request, model_admin):
		return (
			('expired', '🔴 Any Document Expired'),
			('expiring_soon', '🟡 Expiring within 30 Days'),
			('compliant', '🟢 Fully Compliant'),
		)

	def queryset(self, request, queryset):
		today = timezone.localdate()
		in_30_days = today + timedelta(days=30)

		if self.value() == 'expired':
			return queryset.filter(
				Q(insurance_expiry__lt=today) |
				Q(fc_expiry__lt=today) |
				Q(permit_expiry__lt=today) |
				Q(tax_expiry__lt=today) |
				Q(pollution_expiry__lt=today) |
				Q(rc_expiry__lt=today)
			)
		if self.value() == 'expiring_soon':
			return queryset.filter(
				(Q(insurance_expiry__gte=today) & Q(insurance_expiry__lte=in_30_days)) |
				(Q(fc_expiry__gte=today) & Q(fc_expiry__lte=in_30_days)) |
				(Q(permit_expiry__gte=today) & Q(permit_expiry__lte=in_30_days)) |
				(Q(tax_expiry__gte=today) & Q(tax_expiry__lte=in_30_days)) |
				(Q(pollution_expiry__gte=today) & Q(pollution_expiry__lte=in_30_days)) |
				(Q(rc_expiry__gte=today) & Q(rc_expiry__lte=in_30_days))
			).exclude(
				Q(insurance_expiry__lt=today) |
				Q(fc_expiry__lt=today) |
				Q(permit_expiry__lt=today) |
				Q(tax_expiry__lt=today) |
				Q(pollution_expiry__lt=today) |
				Q(rc_expiry__lt=today)
			)
		if self.value() == 'compliant':
			return queryset.exclude(
				Q(insurance_expiry__lte=in_30_days) |
				Q(fc_expiry__lte=in_30_days) |
				Q(permit_expiry__lte=in_30_days) |
				Q(tax_expiry__lte=in_30_days) |
				Q(pollution_expiry__lte=in_30_days) |
				Q(rc_expiry__lte=in_30_days)
			)
		return queryset


class VehiclePhotoInline(TabularInline):
	model = VehiclePhoto
	extra = 1


@admin.register(Vehicle)
class VehicleAdmin(ModelAdmin):
	list_display = (
		'registration_number_display',
		'vehicle_type',
		'ownership_badge',
		'assigned_driver_display',
		'compliance_alerts_display',
		'has_open_defects_display',
		'service_alerts_display',
		'status_toggle_display',
		'live_map_link',
	)
	list_filter = ('ownership_type', 'status', VehicleComplianceFilter, 'fuel_type', 'vehicle_type')
	search_fields = ('registration_number', 'brand', 'model', 'owner_party__name', 'default_driver__name', 'supplier_driver_name')

	class Media:
		css = {
			'all': ('admin/css/vehicle_status_toggle.css',)
		}
		js = ('admin/js/vehicle_status_toggle.js',)

	inlines = [VehiclePhotoInline]

	fieldsets = (
		('Basic Info', {
			'fields': ('registration_number', 'vehicle_type', 'ownership_type', 'owner_party', 'status', 'current_location')
		}),
		('Vehicle Overview', {
			'fields': ('brand', 'model', 'seating_capacity', 'has_ac', 'fuel_type'),
			'description': 'Key vehicle details visible for both owned and outsourced vehicles.'
		}),
		('Technical Specs (Detailed)', {
			'fields': ('year', 'color', 'fuel_tank_capacity', 'def_capacity', 'expected_mileage', 'current_km'),
			'classes': ('owned-only-tab',)
		}),
		('Amenities', {
			'fields': ('is_sleeper', 'has_air_suspension', 'has_video_coach'),
			'description': 'Passenger amenities and comfort features (available for both owned and outsourced vehicles).'
		}),
		('Crew Assignment', {
			'fields': ('default_driver',),
		}),
		('Compliance & Expiries', {
			'fields': ('rc_expiry', 'fc_expiry', 'permit_expiry', 'tax_expiry', 'pollution_expiry', 'next_service_due_km'),
			'classes': ('owned-only-tab',)
		}),
		('Insurance Details', {
			'fields': ('insurance_provider', 'insurance_policy_number', 'insurance_expiry', 'insurance_document'),
			'classes': ('owned-only-tab',)
		}),
		('Financing & Assets', {
			'fields': ('is_financed', 'financier_name', 'emi_amount', 'loan_end_date'),
			'classes': ('owned-only-tab',)
		}),
		('Ownership & Documents', {
			'fields': ('engine_number', 'chassis_number', 'rc_document', 'gps_imei', 'fastag_id'),
			'classes': ('owned-only-tab',)
		}),
		('Supplier Contact', {
			'fields': ('supplier_contact_person', 'supplier_driver_name', 'supplier_driver_phone'),
			'classes': ('outsourced-only-tab',),
			'description': 'Contact details for the supplier and their assigned driver.'
		}),
		('Supplier Terms & Rates', {
			'fields': ('supplier_daily_rate', 'supplier_km_rate', 'supplier_driver_bata', 'supplier_min_hours', 'supplier_min_km', 'supplier_payment_terms'),
			'classes': ('outsourced-only-tab',),
			'description': 'Rate and commitment details agreed with the supplier.'
		}),
		('Supplier Agreement', {
			'fields': ('supplier_contract_ref', 'supplier_contract_start', 'supplier_contract_end', 'supplier_notes'),
			'classes': ('outsourced-only-tab',),
			'description': 'Contract and agreement details with the supplier.'
		}),
	)

	def get_queryset(self, request):
		qs = super().get_queryset(request)
		from operations.models import Trip
		today = timezone.localdate()
		active_trips_prefetch = Prefetch(
			'trips',
			queryset=Trip.objects.filter(
				status__in=['started', 'assigned', 'driver_confirmed'],
				start_date__lte=today,
				end_date__gte=today
			),
			to_attr='active_trips_list'
		)
		return qs.select_related('vehicle_type', 'owner_party', 'default_driver').prefetch_related(
			active_trips_prefetch,
			'service_reminders',
			'defect_tickets'
		)

	@admin.display(description='Registration / Vehicle')
	def registration_number_display(self, obj):
		model_info = f"{obj.brand} {obj.model}".strip()
		subtext = f'<br><small style="color: #94a3b8; font-size: 11px;">{model_info}</small>' if model_info else ''
		return format_html(
			'<strong style="font-size: 13px; color: #f8fafc; letter-spacing: 0.5px;">{}</strong>{}',
			obj.registration_number,
			mark_safe(subtext)
		)

	@admin.display(description='Fleet Ownership')
	def ownership_badge(self, obj):
		if obj.ownership_type == 'owned':
			return mark_safe('<span class="badge" style="background-color: #10b981; color: #fff; padding: 4px 8px; border-radius: 4px;"><i class="fas fa-shield-alt mr-1"></i>Owned Fleet</span>')
		sup_name = obj.owner_party.name if obj.owner_party else "Supplier"
		return format_html(
			'<span class="badge" style="background-color: #6366f1; color: #fff; padding: 4px 8px; border-radius: 4px;"><i class="fas fa-handshake mr-1"></i>Outsourced</span><br><small style="color: #cbd5e1; font-size: 11px;">{}</small>',
			sup_name
		)

	@admin.display(description='Assigned Driver')
	def assigned_driver_display(self, obj):
		if obj.default_driver:
			return format_html(
				'<a href="/admin/core/driver/{}/change/" style="font-weight: 500; color: #60a5fa; text-decoration: none;" title="View Driver Record">'
				'<i class="fas fa-user-circle mr-1" style="color: #38bdf8;"></i>{}'
				'</a>',
				obj.default_driver.id,
				obj.default_driver.name
			)
		elif obj.supplier_driver_name:
			phone_sub = f" ({obj.supplier_driver_phone})" if obj.supplier_driver_phone else ""
			return format_html(
				'<span style="color: #f1f5f9;" title="Supplier-provided driver"><i class="fas fa-user mr-1" style="color: #94a3b8;"></i>{}{}</span>',
				obj.supplier_driver_name, phone_sub
			)
		return mark_safe('<span style="color: #94a3b8; font-size: 11px;">—</span>')

	@admin.display(description='Document Compliance')
	def compliance_alerts_display(self, obj):
		comp = obj.compliance_status
		if comp['status'] == 'expired':
			return format_html(
				'<span class="badge" style="background-color: #ef4444; color: #fff; padding: 4px 8px; font-weight: 600;" title="Document has expired!">'
				'<i class="fas fa-exclamation-triangle mr-1"></i>{}'
				'</span>',
				comp['label']
			)
		elif comp['status'] == 'expiring_soon':
			return format_html(
				'<span class="badge" style="background-color: #f59e0b; color: #1e293b; padding: 4px 8px; font-weight: 600;" title="Renewal due within 30 days">'
				'<i class="fas fa-clock mr-1"></i>{}'
				'</span>',
				comp['label']
			)
		return mark_safe('<span class="badge" style="background-color: #10b981; color: #fff; padding: 4px 8px;"><i class="fas fa-check-circle mr-1"></i>Compliant</span>')

	@admin.display(boolean=True, description='Has Open Defects')
	def has_open_defects_display(self, obj):
		return obj.has_open_defects

	@admin.display(description='Service Alerts')
	def service_alerts_display(self, obj):
		overdue_count = sum(1 for r in obj.service_reminders.filter(is_active=True) if r.is_due)
		if overdue_count > 0:
			return format_html('<span style="color: #f87171; font-weight: bold;">{} Overdue!</span>', overdue_count)
		return mark_safe('<span style="color: #4ade80; font-weight: 600;">Clear</span>')

	@admin.display(description='Live Status')
	def status_toggle_display(self, obj):
		today = timezone.localdate()

		active_trips = getattr(obj, 'active_trips_list', None)
		if active_trips is None:
			active_trips = obj.trips.filter(
				status__in=['started', 'assigned', 'driver_confirmed'],
				start_date__lte=today,
				end_date__gte=today
			)
		active_trip = active_trips[0] if active_trips else None

		if obj.status == 'on_trip' or active_trip:
			trip_label = f"#{active_trip.trip_id}" if active_trip and active_trip.trip_id else "Active Trip"
			trip_link = f"/admin/operations/trip/{active_trip.id}/change/" if active_trip else "#"
			return format_html(
				'<span class="vehicle-badge-trip" title="Vehicle is actively deployed on a trip">'
				'<i class="fas fa-route"></i> On Trip <a href="{}" style="color: #bfdbfe; text-decoration: underline; margin-left: 2px;">{}</a>'
				'</span>',
				trip_link,
				trip_label
			)
		elif obj.status == 'maintenance':
			return mark_safe(
				'<span class="vehicle-badge-maintenance" title="Under maintenance">'
				'<i class="fas fa-tools"></i> Maintenance'
				'</span>'
			)
		else:
			is_avail = (obj.status == 'available')
			checked_attr = 'checked' if is_avail else ''
			label_text = 'Available' if is_avail else 'Not Available'
			label_class = 'vehicle-status-label text-success font-weight-bold' if is_avail else 'vehicle-status-label text-muted'
			return format_html(
				'<div class="vehicle-toggle-wrapper">'
				'<label class="vehicle-switch">'
				'<input type="checkbox" id="toggle-vehicle-{}" data-vehicle-id="{}" {} onchange="toggleVehicleStatus({}, this)">'
				'<span class="vehicle-slider"></span>'
				'</label>'
				'<span id="status-label-{}" class="{}" style="min-width: 85px;">{}</span>'
				'</div>',
				obj.pk, obj.pk, mark_safe(checked_attr), obj.pk,
				obj.pk, label_class, label_text
			)

	@admin.display(description='Live Radar')
	def live_map_link(self, obj):
		return format_html(
			'<a href="/fleet/live/?search={}" target="_blank" class="badge" style="background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%); color: #fff; padding: 4px 8px; border-radius: 4px; font-weight: 600; text-decoration: none; display: inline-flex; align-items: center; gap: 4px;" title="Track {} on Live Fleet Map">'
			'<span class="material-symbols-outlined" style="font-size: 14px;">location_on</span> Live'
			'</a>',
			obj.registration_number, obj.registration_number
		)

	def changelist_view(self, request, extra_context=None):
		extra_context = extra_context or {}
		qs = self.get_queryset(request)
		total_count = qs.count()
		available_count = qs.filter(status='available').count()
		on_trip_count = qs.filter(status='on_trip').count()
		maintenance_count = qs.filter(status__in=['maintenance', 'out_of_service']).count()
		extra_context['fleet_kpi'] = {
			'total': total_count,
			'available': available_count,
			'on_trip': on_trip_count,
			'maintenance': maintenance_count,
		}
		return super().changelist_view(request, extra_context=extra_context)

	def get_urls(self):
		from django.urls import path
		urls = super().get_urls()
		custom_urls = [
			path('<int:vehicle_id>/toggle-status/', self.admin_site.admin_view(self.toggle_status_view), name='vehicle-toggle-status'),
		]
		return custom_urls + urls

	def toggle_status_view(self, request, vehicle_id):
		from django.http import JsonResponse
		from django.shortcuts import get_object_or_404
		if not self.has_change_permission(request):
			return JsonResponse({'success': False, 'error': 'Permission denied.'}, status=403)
		if request.method != 'POST':
			return JsonResponse({'success': False, 'error': 'POST request required.'}, status=405)

		vehicle = get_object_or_404(Vehicle, pk=vehicle_id)

		from operations.models import Trip
		today = timezone.localdate()
		active_trip = vehicle.trips.filter(
			status__in=['started', 'assigned', 'driver_confirmed'],
			start_date__lte=today,
			end_date__gte=today
		).first()

		if active_trip and (vehicle.status == 'on_trip' or active_trip.status == 'started'):
			return JsonResponse({
				'success': False,
				'error': f'Cannot change status: Vehicle is currently on active Trip #{active_trip.trip_id}.'
			})

		if vehicle.status == 'available':
			vehicle.status = 'inactive'
			new_status = 'inactive'
			label = 'Not Available'
		else:
			vehicle.status = 'available'
			new_status = 'available'
			label = 'Available'

		vehicle.save(update_fields=['status'])
		return JsonResponse({
			'success': True,
			'status': new_status,
			'label': label
		})

	actions = ['make_available', 'make_inactive']

	@admin.action(description="Mark selected vehicles as Available")
	def make_available(self, request, queryset):
		updated = queryset.exclude(status='on_trip').update(status='available')
		self.message_user(request, f"{updated} vehicles marked as Available.")

	@admin.action(description="Mark selected vehicles as Not Available (Inactive)")
	def make_inactive(self, request, queryset):
		updated = queryset.exclude(status='on_trip').update(status='inactive')
		self.message_user(request, f"{updated} vehicles marked as Not Available.")


# ─────────────────────────────────────────────────────────────────────────────
# Rate Card Admin
# ─────────────────────────────────────────────────────────────────────────────

@admin.register(RateCard)
class RateCardAdmin(ModelAdmin):
	def has_module_permission(self, request):
		return False

	list_display = (
		'party',
		'target_vehicle_display',
		'rate_summary_display',
		'status_badge',
		'effective_from',
		'effective_to',
	)
	list_filter = ('vehicle_type', 'effective_from')
	search_fields = ('party__name', 'vehicle__registration_number', 'vehicle_type__name')

	class Media:
		js = ('admin/js/ratecard_admin.js',)

	@admin.display(description='Applicable Vehicle / Category')
	def target_vehicle_display(self, obj):
		if obj.vehicle:
			return format_html(
				'<span class="badge" style="background-color: #10b981; color: #fff; padding: 4px 8px;">'
				'<i class="fas fa-car mr-1"></i>Vehicle: {}'
				'</span>',
				obj.vehicle.registration_number
			)
		elif obj.vehicle_type:
			return format_html(
				'<span class="badge" style="background-color: #3b82f6; color: #fff; padding: 4px 8px;">'
				'<i class="fas fa-layer-group mr-1"></i>Category: {}'
				'</span>',
				obj.vehicle_type.name
			)
		return mark_safe('<span class="badge badge-secondary">All Vehicles</span>')

	@admin.display(description='Agreed Rates')
	def rate_summary_display(self, obj):
		day_str = f"₹{obj.day_rate:,.0f}"
		km_str = f"₹{obj.km_rate:,.2f}"
		bata_str = f"₹{obj.driver_bata:,.0f}"
		return format_html(
			'<span style="font-size: 12px; color: #f1f5f9;">'
			'<strong style="color: #38bdf8;">{}</strong>/day • <strong style="color: #38bdf8;">{}</strong>/km • Bata: <span style="color: #fb923c; font-weight: 600;">{}</span>'
			'</span>',
			day_str, km_str, bata_str
		)

	@admin.display(description='Status')
	def status_badge(self, obj):
		today = timezone.localdate()
		if obj.effective_to and obj.effective_to < today:
			return mark_safe('<span class="badge" style="background-color: #ef4444; color: #fff; padding: 4px 8px;"><i class="fas fa-times-circle mr-1"></i>Expired</span>')
		elif obj.effective_from > today:
			return mark_safe('<span class="badge" style="background-color: #3b82f6; color: #fff; padding: 4px 8px;"><i class="fas fa-clock mr-1"></i>Upcoming</span>')
		return mark_safe('<span class="badge" style="background-color: #10b981; color: #fff; padding: 4px 8px;"><i class="fas fa-check-circle mr-1"></i>Active</span>')
