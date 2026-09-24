from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from decimal import Decimal

from finance.services import calculate_party_ledger, calculate_supplier_ledger
from .forms import StatementForm
from .models import GeneratedStatement
from .renderers import render_excel, render_pdf
from .services import build_statement_rows


def _statement_response(statement, content, content_type, extension):
	response = HttpResponse(content, content_type=content_type)
	response['Content-Disposition'] = f'attachment; filename="statement-{statement.pk}.{extension}"'
	return response


@login_required
def generate_statement(request):
	form = StatementForm(request.POST or None)
	if request.method == 'POST' and form.is_valid():
		data = form.cleaned_data
		filters = {'vehicle': data['vehicle'], 'driver': data['driver'], 'status': data['status']}
		
		transport_contract = data.get('transport_contract')
		
		if transport_contract:
			from .services import calculate_contract_ledger, _build_contract_statement_rows
			ledger = calculate_contract_ledger(transport_contract, data['from_date'], data['to_date'], **filters)
			rows = _build_contract_statement_rows(transport_contract, data['from_date'], data['to_date'], **filters)
		else:
			ledger_service = calculate_supplier_ledger if data['party'].party_type == 'supplier' else calculate_party_ledger
			ledger = ledger_service(data['party'], data['from_date'], data['to_date'], **filters)
			rows = build_statement_rows(data['party'], data['from_date'], data['to_date'], **filters)
			
		party = data['party'] if not transport_contract else transport_contract.customer
		subtotal = ledger.get('taxable_amount', ledger.get('trip_total', Decimal('0')))
		
		cgst, sgst, igst, tds = Decimal('0'), Decimal('0'), Decimal('0'), Decimal('0')
		
		if party and party.party_type == 'corporate':
			gst_rate = Decimal('5')
			if transport_contract and transport_contract.gst_rate > 0:
				gst_rate = transport_contract.gst_rate
			
			# Assuming TN state code is 33
			if party.state_code == '33':
				cgst = subtotal * (gst_rate / Decimal('2')) / Decimal('100')
				sgst = subtotal * (gst_rate / Decimal('2')) / Decimal('100')
			else:
				igst = subtotal * gst_rate / Decimal('100')
			
			if party.tds_rate:
				tds = subtotal * (party.tds_rate / Decimal('100'))
		
		statement = GeneratedStatement.objects.create(
			party=data['party'], transport_contract=transport_contract, from_date=data['from_date'], to_date=data['to_date'],
			file_format=data['file_format'], opening_balance=ledger['opening_balance'],
			closing_balance=ledger['closing_balance'], vehicle=data['vehicle'],
			driver=data['driver'], status=data.get('status', 'unpaid'),
			subtotal=subtotal, cgst_amount=cgst, sgst_amount=sgst, igst_amount=igst, tds_deducted=tds
		)
		if data['file_format'] == 'excel':
			return _statement_response(statement, render_excel(data['party'], data['from_date'], data['to_date'], rows, ledger, is_fleet_contract=bool(transport_contract)), 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'xlsx')
		return _statement_response(statement, render_pdf(data['party'], data['from_date'], data['to_date'], rows, ledger, is_fleet_contract=bool(transport_contract)), 'application/pdf', 'pdf')
	return render(request, 'statements/generate.html', {'form': form})


@login_required
def download_statement(request, statement_id):
	statement = get_object_or_404(GeneratedStatement, pk=statement_id)
	filters = {'vehicle': statement.vehicle, 'driver': statement.driver, 'status': statement.status}
	
	if statement.transport_contract:
		from .services import calculate_contract_ledger, _build_contract_statement_rows
		ledger = calculate_contract_ledger(statement.transport_contract, statement.from_date, statement.to_date, **filters)
		rows = _build_contract_statement_rows(statement.transport_contract, statement.from_date, statement.to_date, **filters)
	else:
		ledger_service = calculate_supplier_ledger if statement.party.party_type == 'supplier' else calculate_party_ledger
		ledger = ledger_service(statement.party, statement.from_date, statement.to_date, **filters)
		rows = build_statement_rows(statement.party, statement.from_date, statement.to_date, **filters)
		
	if statement.file_format == 'excel':
		return _statement_response(statement, render_excel(statement.party, statement.from_date, statement.to_date, rows, ledger, is_fleet_contract=bool(statement.transport_contract)), 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'xlsx')
	return _statement_response(statement, render_pdf(statement.party, statement.from_date, statement.to_date, rows, ledger, is_fleet_contract=bool(statement.transport_contract)), 'application/pdf', 'pdf')
