from django import forms

from core.models import Driver, Party, Vehicle
from fleet_contracts.models import TransportContract

class StatementForm(forms.Form):
    STATEMENT_TYPES = [('party', 'Client / Supplier Statement'), ('fleet_contract', 'Fleet Contract Statement')]
    statement_type = forms.ChoiceField(choices=STATEMENT_TYPES, widget=forms.RadioSelect, initial='party')
    party = forms.ChoiceField(choices=[], required=False)
    transport_contract = forms.ModelChoiceField(queryset=TransportContract.objects.filter(status='active'), required=False)
    from_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    to_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    file_format = forms.ChoiceField(choices=[('pdf', 'PDF'), ('excel', 'Excel')])
    vehicle = forms.ModelChoiceField(queryset=Vehicle.objects.all(), required=False)
    driver = forms.ModelChoiceField(queryset=Driver.objects.all(), required=False)
    status = forms.ChoiceField(choices=[('', 'All eligible statuses'), ('completed', 'Completed'), ('billed', 'Billed'), ('settled', 'Settled')], required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Group parties by type for the dropdown
        parties = Party.objects.filter(is_active=True).order_by('party_type', 'name')
        grouped_choices = {}
        for party in parties:
            group = 'Suppliers' if party.party_type == 'supplier' else 'Clients'
            if group not in grouped_choices:
                grouped_choices[group] = []
            grouped_choices[group].append((party.id, party.name))
        self.fields['party'].choices = [('', '---------')] + [(group, choices) for group, choices in grouped_choices.items()]

    def clean(self):
        cleaned = super().clean()
        statement_type = cleaned.get('statement_type')
        if statement_type == 'party':
            party_id = cleaned.get('party')
            if not party_id:
                self.add_error('party', 'Please select a party.')
            else:
                try:
                    cleaned['party'] = Party.objects.get(id=party_id)
                except Party.DoesNotExist:
                    self.add_error('party', 'Invalid party selected.')
        elif statement_type == 'fleet_contract':
            if not cleaned.get('transport_contract'):
                self.add_error('transport_contract', 'Please select a fleet contract.')
            # A fleet contract implicitly belongs to the contract's customer party
            if cleaned.get('transport_contract'):
                cleaned['party'] = cleaned['transport_contract'].customer

        if cleaned.get('from_date') and cleaned.get('to_date'):
            if cleaned['from_date'] > cleaned['to_date']:
                self.add_error('to_date', 'The statement end date must be on or after the start date.')
            else:
                delta = (cleaned['to_date'] - cleaned['from_date']).days
                if delta > 366:
                    self.add_error('to_date', 'Statement date range cannot exceed 366 days (1 year) per export request.')
        return cleaned
