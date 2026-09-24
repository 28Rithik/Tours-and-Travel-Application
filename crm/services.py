from io import BytesIO
from decimal import Decimal
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from django.conf import settings

def generate_quotation_pdf(inquiry):
    output = BytesIO()
    # Use standard A4 portrait for quotation
    document = SimpleDocTemplate(output, pagesize=A4, leftMargin=12 * mm, rightMargin=12 * mm, topMargin=12 * mm, bottomMargin=12 * mm)
    styles = getSampleStyleSheet()
    story = []
    
    # Header
    story.append(Paragraph(f'<font size=18><b>{settings.COMPANY_NAME}</b></font>', styles['Heading1']))
    story.append(Paragraph(f'<font size=10>{settings.COMPANY_LOCATION}</font>', styles['Normal']))
    story.append(Spacer(1, 10 * mm))
    
    # Title
    story.append(Paragraph('<font size=16><b>QUOTATION</b></font>', styles['Heading2']))
    story.append(Spacer(1, 5 * mm))
    
    # Inquiry Details
    inquiry_details = [
        ['Quotation No:', inquiry.inquiry_number, 'Date:', inquiry.created_at.strftime('%d-%m-%Y')],
        ['Client Name:', inquiry.party.name, 'Guest Name:', inquiry.guest_name],
        ['Phone:', inquiry.guest_phone, 'Vehicle:', inquiry.vehicle_type],
    ]
    detail_table = Table(inquiry_details, colWidths=[30*mm, 60*mm, 20*mm, 70*mm])
    detail_table.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTNAME', (2,0), (2,-1), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(detail_table)
    story.append(Spacer(1, 10 * mm))
    
    # Journey Itinerary
    story.append(Paragraph('<b>Journey Itinerary</b>', styles['Heading4']))
    itinerary_data = [
        ['Pickup Date:', inquiry.pickup_date.strftime('%d-%m-%Y')],
        ['Pickup Time:', inquiry.pickup_time.strftime('%I:%M %p')],
        ['Pickup Loc:', inquiry.pickup_location],
        ['Destination:', inquiry.destination],
    ]
    if inquiry.drop_date:
        itinerary_data.append(['Return Date:', inquiry.drop_date.strftime('%d-%m-%Y')])
        
    itinerary_table = Table(itinerary_data, colWidths=[30*mm, 150*mm])
    itinerary_table.setStyle(TableStyle([
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(itinerary_table)
    story.append(Spacer(1, 10 * mm))
    
    # Commercials
    story.append(Paragraph('<b>Commercials</b>', styles['Heading4']))
    price = inquiry.quoted_price or 0
    commercials_data = [
        ['Description', 'Amount (INR)'],
        [f'{inquiry.get_journey_type_display()} Trip - {inquiry.vehicle_type}', f'{price:,.2f}'],
        ['Total Estimated Cost', f'{price:,.2f}']
    ]
    comm_table = Table(commercials_data, colWidths=[140*mm, 40*mm])
    comm_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e3a8a')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e5e7eb')),
        ('ALIGN', (1,0), (1,-1), 'RIGHT'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(comm_table)
    story.append(Spacer(1, 15 * mm))
    
    # Terms and Conditions
    story.append(Paragraph('<b>Terms & Conditions</b>', styles['Heading4']))
    terms = [
        "1. Toll, Parking & Inter-state taxes will be charged extra as per actuals.",
        "2. Driver Batta is applicable for trips operating between 10 PM and 6 AM.",
        "3. Starting and closing kms/hrs will be calculated from garage to garage.",
        "4. A 50% advance payment is required to confirm the booking.",
        "5. Cancellation within 24 hours of pickup will incur a 20% cancellation fee."
    ]
    for term in terms:
        story.append(Paragraph(f'<font size=9>{term}</font>', styles['Normal']))
        story.append(Spacer(1, 2 * mm))
        
    story.append(Spacer(1, 20 * mm))
    story.append(Paragraph('<b>For Sivagayathiri Tours and Travels</b>', styles['Normal']))
    story.append(Spacer(1, 15 * mm))
    story.append(Paragraph('Authorized Signatory', styles['Normal']))
    
    document.build(story)
    return output.getvalue()
