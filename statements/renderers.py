from io import BytesIO
from decimal import Decimal

from openpyxl import Workbook
from openpyxl.styles import Font
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, SimpleDocTemplate, Spacer, Table, TableStyle, Paragraph

COLUMNS = [
    ('Book No', 'booking_number'), ('Guest Name', 'guest_name'), ('Veh.Type', 'vehicle_type'), ('Supplier', 'supplier_name'),
    ('St. Date', 'start_date'), ('Cl. Date', 'end_date'), ('Tot. Days', 'days'), ('Rent', 'rent'),
    ('Used Kms', 'used_km'), ('KM Rate', 'km_rate'), ('KM Amt', 'km_amount'), ('Day Amt', 'day_amount'),
    ('Bill Value', 'bill_value'), ('Coms Amt', 'commission'), ('Batta', 'batta'), ('Toll', 'toll'),
    ('Permit', 'permit'), ('Parking', 'parking'), ('Total Amt', 'total'), ('Rec. Amt', 'received'), ('Balance', 'balance'),
]

CONTRACT_COLUMNS = [
    ('Date', 'date'), ('Description', 'description'), ('Rent/Rate', 'rent'), ('Taxable Value', 'taxable'), 
    ('Total Amt', 'total'), ('Rec. Amt', 'received'), ('Balance', 'balance')
]


class NumberedCanvas:
    def __init__(self, *args, **kwargs):
        from reportlab.pdfgen.canvas import Canvas

        self._canvas = Canvas(*args, **kwargs)
        self._saved_page_states = []

    def __getattr__(self, name):
        return getattr(self._canvas, name)

    def showPage(self):
        self._saved_page_states.append(dict(self._canvas.__dict__))
        self._canvas._startPage()

    def save(self):
        number_of_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self._canvas.__dict__.update(state)
            
            # Draw Header on every page
            self._canvas.setFont('Helvetica-Bold', 16)
            self._canvas.setFillColor(colors.HexColor('#1f2937'))
            self._canvas.drawString(6 * mm, 190 * mm, "SIVAGAYATHIRI TOURS AND TRAVELS")
            
            self._canvas.setFont('Helvetica', 9)
            self._canvas.setFillColor(colors.grey)
            self._canvas.drawString(6 * mm, 185 * mm, "123 Main Road, Coimbatore, Tamil Nadu - 641001")
            self._canvas.drawString(6 * mm, 180 * mm, "Phone: +91 98765 43210 | Email: contact@example.com")
            self._canvas.drawString(6 * mm, 175 * mm, "GSTIN: 33XXXXX1234X1ZX")
            
            # Note: Statement type, Party, and Dates are drawn in render_pdf directly 
            # or we can draw a dividing line here
            self._canvas.setStrokeColor(colors.HexColor('#e5e7eb'))
            self._canvas.setLineWidth(1)
            self._canvas.line(6 * mm, 170 * mm, 291 * mm, 170 * mm)
            
            self._canvas.setFillColor(colors.black)
            self._canvas.setFont('Helvetica', 8)
            self._canvas.drawRightString(291 * mm, 7 * mm, f'Page {self._canvas.getPageNumber()} of {number_of_pages}')
            self._canvas.showPage()
        self._canvas.save()


def render_excel(party, from_date, to_date, rows, ledger, is_fleet_contract=False):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = 'CAB Statement'
    sheet.append([f'CABSTATEMENT From {from_date:%d-%m-%y} To {to_date:%d-%m-%y}'])
    sheet.append([f'Party Name: {party.name}'])
    
    is_supplier = party.party_type == 'supplier'
    
    cols_to_use = CONTRACT_COLUMNS if is_fleet_contract else COLUMNS
    if is_supplier:
        cols_to_use = [
            ('Date', 'date'), ('Description', 'description'), ('Guest Name', 'guest_name'), 
            ('Vehicle', 'vehicle_number'), ('Gross Rent', 'rent'), ('Commission', 'commission'), 
            ('Net Payable', 'total')
        ]
        
    sheet.append([label for label, _ in cols_to_use])
    for cell in sheet[3]:
        cell.font = Font(bold=True)
    for row in rows:
        if is_fleet_contract or is_supplier:
            sheet.append([row.get(key, '') for _, key in cols_to_use])
        else:
            if row['row_type'] == 'trip':
                sheet.append([row.get(key, '') for _, key in COLUMNS])
            else:
                sheet.append([row.get('description', ''), '', '', row.get('supplier_name', ''), row.get('date', ''), '', '', '', '', '', '', '', '', '', '', '', '', '', row.get('total', ''), row.get('received', ''), ''])
    sheet.append([])
    sheet.append(['Opening balance', ledger['opening_balance']])
    if is_supplier:
        sheet.append(['Gross Trip Costs', ledger['supplier_cost_total']])
        sheet.append(['Less: Commission', -ledger.get('commission_total', Decimal('0'))])
        sheet.append(['Less: Fuel Ded.', -ledger.get('fuel_total', Decimal('0'))])
        sheet.append(['Supplier Payments', ledger['supplier_total']])
    else:
        sheet.append(['Trip total', ledger['trip_total']])
        sheet.append(['Customer receipts', ledger['receipt_total']])
        sheet.append(['Supplier payments and advances', ledger.get('supplier_total', 0)])
        
    sheet.append(['Adjustments', ledger['adjustment_total']])
    sheet.append(['Closing balance', ledger['closing_balance']])
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


def render_pdf(party, from_date, to_date, rows, ledger, is_fleet_contract=False):
    output = BytesIO()
    document = SimpleDocTemplate(output, pagesize=landscape(A4), leftMargin=6 * mm, rightMargin=6 * mm, topMargin=45 * mm, bottomMargin=12 * mm)
    styles = getSampleStyleSheet()
    story = []
    
    is_supplier = party.party_type == 'supplier'
    
    # Document Title and Party info
    statement_title = "VENDOR SETTLEMENT" if is_supplier else "TAX INVOICE / STATEMENT OF ACCOUNT"
    story.append(Paragraph(f'<font size=14><b>{statement_title}</b></font>', styles['Heading2']))
    
    party_details = f'<b>Party:</b> {party.name} <br/>'
    if party.gstin:
        party_details += f'<b>GSTIN:</b> {party.gstin} '
        if party.state_code:
            party_details += f'(State: {party.state_code})'
        party_details += '<br/>'
        
    story.append(Paragraph(f'{party_details}<b>Period:</b> {from_date:%d-%m-%Y} to {to_date:%d-%m-%Y}', styles['Normal']))
    story.append(Spacer(1, 6 * mm))

    # Calculate Totals for GST
    if is_fleet_contract:
        total_taxable = ledger.get('taxable_amount', Decimal('0'))
        total_gst = ledger.get('gst_amount', Decimal('0'))
    else:
        total_taxable = sum((Decimal(row.get('taxable', 0)) for row in rows if row.get('row_type') == 'trip'), Decimal('0'))
        total_gst = sum((Decimal(row.get('gst_amount', 0)) for row in rows if row.get('row_type') == 'trip'), Decimal('0'))
    
    # Reconciliation Box at the top
    summary_title = 'Vendor Reconciliation' if is_supplier else 'Statement Reconciliation'
    story.append(Paragraph(f'<b>{summary_title}</b>', styles['Heading4']))
    
    summary = [
        ['OPENING BALANCE', f"{ledger['opening_balance']:.2f}"],
    ]
    
    if total_gst > 0 and not is_supplier:
        summary.append(['TOTAL TAXABLE VALUE', f"{total_taxable:.2f}"])
        # Our company is 33 (TN). If client is also 33, CGST/SGST. Otherwise IGST.
        if party.state_code == '33':
            half_gst = total_gst / Decimal('2')
            summary.append(['CGST', f"{half_gst:.2f}"])
            summary.append(['SGST', f"{half_gst:.2f}"])
        else:
            summary.append(['IGST', f"{total_gst:.2f}"])
        summary.append(['TOTAL INVOICE VALUE (Inc. Tax)', f"{(total_taxable + total_gst):.2f}"])
    elif is_supplier:
        summary.append(['GROSS TRIP COSTS', f"{ledger.get('supplier_cost_total', 0):.2f}"])
        summary.append(['LESS: COMMISSION', f"-{ledger.get('commission_total', 0):.2f}"])
        summary.append(['LESS: FUEL PAID', f"-{ledger.get('fuel_total', 0):.2f}"])
        summary.append(['NET TRIP EARNINGS', f"{ledger.get('net_earnings', 0):.2f}"])
    else:
        summary.append(['TRIP CHARGES', f"{ledger['trip_total']:.2f}"])
        
    summary.extend([
        ['CUSTOMER RECEIPTS' if not is_supplier else 'SUPPLIER PAYMENTS / ADVANCES', f"{ledger['receipt_total'] if not is_supplier else ledger['supplier_total']:.2f}"],
        ['ADJUSTMENTS', f"{ledger['adjustment_total']:.2f}"],
        ['CLOSING BALANCE', f"{ledger['closing_balance']:.2f}"],
    ])
    
    summary_table = Table(summary, colWidths=[75 * mm, 35 * mm])
    summary_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')), 
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f3f4f6')), 
        ('BACKGROUND', (1, -1), (1, -1), colors.HexColor('#dbeafe')),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'), 
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4)
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 8 * mm))
    
    # Detailed Rows
    cols_to_use = CONTRACT_COLUMNS if is_fleet_contract else COLUMNS
    if is_supplier:
        cols_to_use = [
            ('Date', 'date'), ('Description', 'description'), ('Guest Name', 'guest_name'), 
            ('Vehicle', 'vehicle_number'), ('Gross Rent', 'rent'), ('Commission', 'commission'), 
            ('Net Payable', 'total')
        ]
        
    table_data = [[label for label, _ in cols_to_use]]
    for row in rows:
        if is_fleet_contract or is_supplier:
            table_data.append([str(row.get(key, '') or '') for _, key in cols_to_use])
        else:
            if row['row_type'] == 'trip':
                table_data.append([str(row.get(key, '') or '') for _, key in COLUMNS])
            else:
                table_data.append([row.get('description', ''), '', '', row.get('supplier_name', ''), str(row.get('date', '')), '', '', '', '', '', '', '', '', '', '', '', '', '', str(row.get('total', '')), str(row.get('received', '')), ''])
            
    # Add zebra striping and styling
    table_style = [
        ('GRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#e5e7eb')), 
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3a8a')), # Dark blue header
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 6 if not is_supplier and not is_fleet_contract else 8), 
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT' if is_supplier else 'LEFT'), # Default right align for numbers
        ('ALIGN', (0, 0), (0, -1), 'LEFT'), 
    ]
    
    if not is_supplier and not is_fleet_contract:
        table_style.append(('ALIGN', (7, 0), (-1, -1), 'RIGHT'))
        
    if is_supplier:
        table_style.append(('ALIGN', (1, 0), (3, -1), 'LEFT')) # Text columns
        table_style.append(('ALIGN', (4, 0), (6, -1), 'RIGHT')) # Money columns
    
    for i in range(1, len(table_data)):
        if i % 2 == 0:
            table_style.append(('BACKGROUND', (0, i), (-1, i), colors.HexColor('#f9fafb')))
            
    if is_fleet_contract:
        col_widths = [25 * mm, 120 * mm, 30 * mm, 30 * mm, 30 * mm, 30 * mm, 15 * mm]
    elif is_supplier:
        col_widths = [20 * mm, 70 * mm, 40 * mm, 30 * mm, 30 * mm, 30 * mm, 30 * mm]
    else:
        col_widths = [
            18 * mm, 25 * mm, 18 * mm, 19 * mm, # Book No, Guest Name, Veh.Type, Supplier
            15 * mm, 15 * mm, 10 * mm, 12 * mm, # St. Date, Cl. Date, Tot. Days, Rent
            12 * mm, 10 * mm, 12 * mm, 12 * mm, # Used Kms, KM Rate, KM Amt, Day Amt
            13 * mm, 12 * mm, 11 * mm, 10 * mm, # Bill Value, Coms Amt, Batta, Toll
            10 * mm, 10 * mm, 15 * mm, 13 * mm, 13 * mm # Permit, Parking, Total Amt, Rec. Amt, Balance
        ]
    table = Table(table_data, repeatRows=1, colWidths=col_widths, hAlign='LEFT')
    table.setStyle(TableStyle(table_style))
    story.append(table)

    document.build(story, canvasmaker=NumberedCanvas)
    return output.getvalue()
