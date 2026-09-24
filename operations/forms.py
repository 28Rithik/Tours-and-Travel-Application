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
        return cleaned_data
