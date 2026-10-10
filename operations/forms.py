from django import forms

from core.models import Driver, Vehicle
from .models import Booking, Trip


class BookingForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = [
            'party',
            'guest_name',
            'guest_phone',
            'pickup_location',
            'destination',
            'pickup_date',
            'pickup_time',
            'reporting_time',
            'drop_date',
            'journey_type',
            'vehicle_type',
            'special_requirements',
            'billing_type',
            'quoted_price',
            'payment_terms_override',
            'expected_km',
            'plan_details',
            'status',
            'hotel_confirmation_status',
            'hotel_paid_by',
            'notes',
        ]
        widgets = {
            'pickup_date': forms.DateInput(attrs={'type': 'date'}),
            'pickup_time': forms.TimeInput(attrs={'type': 'time'}),
            'drop_date': forms.DateInput(attrs={'type': 'date'}),
            'reporting_time': forms.TimeInput(attrs={'type': 'time'}),
            'plan_details': forms.Textarea(attrs={'rows': 4}),
            'special_requirements': forms.Textarea(attrs={'rows': 3}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'hotel_confirmation_status' in self.fields:
            self.fields['hotel_confirmation_status'].initial = 'pending'
            self.fields['hotel_confirmation_status'].required = False
        if 'hotel_paid_by' in self.fields:
            self.fields['hotel_paid_by'].initial = 'company'
            self.fields['hotel_paid_by'].required = False
        if 'billing_type' in self.fields:
            self.fields['billing_type'].initial = 'package'

    def clean(self):
        cleaned_data = super().clean()
        pickup_date = cleaned_data.get('pickup_date')
        drop_date = cleaned_data.get('drop_date')
        quoted_price = cleaned_data.get('quoted_price')
        guest_phone = cleaned_data.get('guest_phone')

        if pickup_date and drop_date and drop_date < pickup_date:
            self.add_error('drop_date', 'Drop date cannot be before pickup date.')

        if quoted_price is not None and quoted_price < 0:
            self.add_error('quoted_price', 'Quoted price cannot be negative.')

        if guest_phone:
            clean_digits = ''.join(c for c in guest_phone if c.isdigit())
            if len(clean_digits) < 10:
                self.add_error('guest_phone', 'Please enter a valid phone number with at least 10 digits.')

        return cleaned_data


class TripForm(forms.ModelForm):
    class Meta:
        model = Trip
        fields = [
            'booking',
            'bulk_contract_day',
            'vehicle',
            'driver',
            'status',
            'start_date',
            'end_date',
            'start_time',
            'end_time',
            'billing_model',
            'day_rate',
            'km_rate',
            'fixed_amount',
            'days_count',
            'driver_bata',
            'partner_handover_notes',
            'notes',
        ]
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'type': 'time'}),
            'partner_handover_notes': forms.Textarea(attrs={'rows': 4}),
            'notes': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['vehicle'].queryset = Vehicle.objects.order_by('vehicle_type__name', 'registration_number')
        self.fields['driver'].queryset = Driver.objects.order_by('name')
        if 'booking' in self.fields:
            self.fields['booking'].required = False
        if 'bulk_contract_day' in self.fields:
            self.fields['bulk_contract_day'].required = False
        if 'km_rate' in self.fields:
            self.fields['km_rate'].required = False
        if 'fixed_amount' in self.fields:
            self.fields['fixed_amount'].required = False
        if 'day_rate' in self.fields:
            self.fields['day_rate'].required = False
        if 'driver_bata' in self.fields:
            self.fields['driver_bata'].required = False

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get('booking') and getattr(self.instance, 'booking_id', None):
            cleaned_data['booking'] = self.instance.booking
        if not cleaned_data.get('bulk_contract_day') and getattr(self.instance, 'bulk_contract_day_id', None):
            cleaned_data['bulk_contract_day'] = self.instance.bulk_contract_day

        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        vehicle = cleaned_data.get('vehicle')
        driver = cleaned_data.get('driver')
        status = cleaned_data.get('status')

        if start_date and end_date and end_date < start_date:
            self.add_error('end_date', 'Trip end date cannot be earlier than start date.')

        # 1. Statutory Compliance Guard: Check vehicle document expiries
        if vehicle and start_date:
            compliance_errors = []
            if vehicle.fc_expiry and vehicle.fc_expiry < start_date:
                compliance_errors.append(f"Fitness Certificate (FC) expired on {vehicle.fc_expiry}")
            if vehicle.insurance_expiry and vehicle.insurance_expiry < start_date:
                compliance_errors.append(f"Insurance expired on {vehicle.insurance_expiry}")
            if vehicle.permit_expiry and vehicle.permit_expiry < start_date:
                compliance_errors.append(f"Road Permit expired on {vehicle.permit_expiry}")
            
            if compliance_errors:
                self.add_error('vehicle', f"Statutory Compliance Breach: {vehicle.registration_number} has {', '.join(compliance_errors)}. Vehicle cannot be assigned until renewed.")

        # 2. Overlap Conflict Guard: Check for double-booking on active trips
        active_statuses = ['assigned', 'driver_confirmed', 'started', 'completed']
        if status in active_statuses and start_date and end_date:
            if vehicle:
                overlapping_v = Trip.objects.filter(
                    vehicle=vehicle,
                    status__in=active_statuses,
                    start_date__lte=end_date,
                    end_date__gte=start_date
                )
                if self.instance and self.instance.pk:
                    overlapping_v = overlapping_v.exclude(pk=self.instance.pk)
                if overlapping_v.exists():
                    conflict = overlapping_v.first()
                    self.add_error('vehicle', f"Vehicle Conflict: {vehicle.registration_number} is already assigned to Trip #{conflict.trip_id} ({conflict.start_date} to {conflict.end_date}).")

            if driver:
                overlapping_d = Trip.objects.filter(
                    driver=driver,
                    status__in=active_statuses,
                    start_date__lte=end_date,
                    end_date__gte=start_date
                )
                if self.instance and self.instance.pk:
                    overlapping_d = overlapping_d.exclude(pk=self.instance.pk)
                if overlapping_d.exists():
                    conflict = overlapping_d.first()
                    self.add_error('driver', f"Driver Conflict: {driver.name} is already assigned to Trip #{conflict.trip_id} ({conflict.start_date} to {conflict.end_date}).")

        return cleaned_data
