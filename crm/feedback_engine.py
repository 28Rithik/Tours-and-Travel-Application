"""
Post-Trip Automated Customer Feedback & Google Review Conversion Engine
Sivagayathiri Tours & Travels ERP

Captures mobile-first customer trip feedback via unique secure tokens.
- Ratings 4-5 Stars (Promoters): Prompts instant Google Business Review conversion.
- Ratings 1-3 Stars (Detractors): Auto-lodges high-priority CRM Quality Complaint with operations manager alert.
"""

import uuid
import secrets
from decimal import Decimal
from django.utils import timezone
from django.db.models import Avg, Count, Q
from crm.models import TripCustomerFeedback, TravelComplaint
from operations.models import Trip


# Google Review direct review URL for Sivagayathiri Travels (place ID link)
GOOGLE_BUSINESS_REVIEW_URL = "https://search.google.com/local/writereview?placeid=ChIJN1t_tDeuEmsRUsoyG83frY4"


def generate_feedback_token():
    """Generates a URL-safe random token for the post-trip guest review link."""
    return secrets.token_urlsafe(32)


def get_or_create_feedback_token_for_trip(trip):
    """Retrieves or provisions a feedback token for a completed Trip."""
    feedback = TripCustomerFeedback.objects.filter(trip=trip).first()
    if feedback:
        return feedback.feedback_token

    cust_name = trip.guest_name or (trip.booking.guest_name if trip.booking else "Valued Traveler")
    cust_phone = trip.booking.guest_phone if trip.booking and trip.booking.guest_phone else ""

    new_token = generate_feedback_token()
    fb = TripCustomerFeedback.objects.create(
        trip=trip,
        customer_name=cust_name,
        customer_phone=cust_phone,
        feedback_token=new_token,
        overall_rating=5,
        driver_politeness_rating=5,
        vehicle_cleanliness_rating=5,
        ac_punctuality_rating=5,
    )
    return fb.feedback_token


def process_guest_feedback_submission(token, overall_rating, driver_rating, cleanliness_rating, punctuality_rating, tags_list, feedback_text):
    """
    Processes guest feedback form submission, updates feedback record,
    routes promoters to Google Reviews, and auto-escalates detractors to CRM complaints.
    """
    feedback = TripCustomerFeedback.objects.filter(feedback_token=token).select_related('trip').first()
    if not feedback:
        return {'status': 'error', 'message': 'Invalid or expired feedback link'}

    overall_rating = int(overall_rating or 5)
    driver_rating = int(driver_rating or 5)
    cleanliness_rating = int(cleanliness_rating or 5)
    punctuality_rating = int(punctuality_rating or 5)

    tags_str = ", ".join(tags_list) if isinstance(tags_list, list) else str(tags_list or "")

    feedback.overall_rating = overall_rating
    feedback.driver_politeness_rating = driver_rating
    feedback.vehicle_cleanliness_rating = cleanliness_rating
    feedback.ac_punctuality_rating = punctuality_rating
    feedback.positive_tags = tags_str
    feedback.feedback_text = feedback_text or ""

    is_promoter = overall_rating >= 4
    escalated_complaint = None

    if is_promoter:
        feedback.google_review_prompted = True
        # Generate prefilled Google Review text
        highlight_phrases = []
        if 'Polite Chauffeur' in tags_str or driver_rating >= 5:
            highlight_phrases.append("courteous & safe chauffeur")
        if 'Clean Vehicle' in tags_str or cleanliness_rating >= 5:
            highlight_phrases.append("spotless air-conditioned vehicle")
        if 'On-Time Service' in tags_str or punctuality_rating >= 5:
            highlight_phrases.append("perfect on-time punctuality")

        phrases_text = ", ".join(highlight_phrases) if highlight_phrases else "professional service and comfortable ride"
        prefilled_review = f"Had a wonderful experience with Sivagayathiri Travels! Appreciated the {phrases_text}. Highly recommended for family outstation trips and South India tours."
    else:
        # Detractor (<= 3 Stars): Auto-create CRM Quality Complaint
        feedback.complaint_escalated = True

        # Determine category based on lowest sub-rating
        min_rating = min(driver_rating, cleanliness_rating, punctuality_rating)
        if driver_rating == min_rating and driver_rating < 4:
            category = 'driver_conduct'
        elif cleanliness_rating == min_rating and cleanliness_rating < 4:
            category = 'vehicle_condition'
        else:
            category = 'itinerary_delay'

        severity = 'critical' if overall_rating <= 2 else 'high'
        complaint_title = f"Post-Trip Deficit ({overall_rating}★) - Trip #{feedback.trip.trip_id} - {feedback.customer_name}"
        desc = (
            f"Automated post-trip rating escalation.\n"
            f"Overall Rating: {overall_rating}/5 Stars\n"
            f"Driver Politeness: {driver_rating}/5\n"
            f"Vehicle Cleanliness: {cleanliness_rating}/5\n"
            f"AC & Punctuality: {punctuality_rating}/5\n"
            f"Guest Comments: {feedback_text or 'No written feedback provided.'}\n"
            f"Immediate supervisor callback required within 2 hours."
        )

        escalated_complaint = TravelComplaint.objects.create(
            complainant_type='b2c_traveler',
            complainant_name=feedback.customer_name,
            complainant_phone=feedback.customer_phone or '',
            category=category,
            severity=severity,
            issue_description=f"{complaint_title}\n\n{desc}",
            status='lodged'
        )
        feedback.complaint = escalated_complaint
        prefilled_review = ""

    feedback.save()

    return {
        'status': 'success',
        'is_promoter': is_promoter,
        'overall_rating': overall_rating,
        'google_review_url': GOOGLE_BUSINESS_REVIEW_URL if is_promoter else None,
        'prefilled_review': prefilled_review if is_promoter else None,
        'escalated_to_complaint': not is_promoter,
        'complaint_number': escalated_complaint.complaint_number if escalated_complaint else None,
    }


def compute_nps_and_review_metrics():
    """Computes fleet NPS score, promoter %, detractor %, and Google conversion rate."""
    all_feedbacks = TripCustomerFeedback.objects.all()
    total = all_feedbacks.count()

    if total == 0:
        return {
            'total_feedback': 0,
            'avg_rating': 5.0,
            'nps_score': 100,
            'promoters_count': 0,
            'passives_count': 0,
            'detractors_count': 0,
            'google_prompted_count': 0,
            'google_clicked_count': 0,
            'google_conversion_rate': 0.0,
            'complaints_escalated_count': 0,
        }

    promoters = all_feedbacks.filter(overall_rating__gte=4).count()
    passives = all_feedbacks.filter(overall_rating=3).count()
    detractors = all_feedbacks.filter(overall_rating__lte=2).count()

    # Net Promoter Score = % Promoters - % Detractors
    pct_promoters = (promoters / total) * 100
    pct_detractors = (detractors / total) * 100
    nps_score = round(pct_promoters - pct_detractors)

    avg_overall = all_feedbacks.aggregate(a=Avg('overall_rating'))['a'] or 5.0
    google_prompted = all_feedbacks.filter(google_review_prompted=True).count()
    google_clicked = all_feedbacks.filter(google_review_clicked=True).count()
    conversion_rate = round((google_clicked / google_prompted * 100), 1) if google_prompted > 0 else 0.0
    complaints_escalated = all_feedbacks.filter(complaint_escalated=True).count()

    return {
        'total_feedback': total,
        'avg_rating': round(float(avg_overall), 1),
        'nps_score': nps_score,
        'promoters_count': promoters,
        'passives_count': passives,
        'detractors_count': detractors,
        'google_prompted_count': google_prompted,
        'google_clicked_count': google_clicked,
        'google_conversion_rate': conversion_rate,
        'complaints_escalated_count': complaints_escalated,
    }


def seed_sample_customer_feedbacks():
    """Seeds realistic customer feedback records with promoter and detractor cases."""
    trips = list(Trip.objects.all()[:6])
    if not trips:
        return []

    created = []
    cases = [
        ('Dr. K. Swaminathan', '9840123456', 5, 5, 5, 5, 'Polite Chauffeur, Clean Vehicle, On-Time Service', 'Exceptional pilgrimage trip to Madurai Meenakshi Amman Temple and Rameshwaram. Chauffeur Saravanan was extremely patient and knowledgeable.', True, True, False),
        ('Meenakshi Sundaram', '9443210987', 5, 5, 5, 4, 'Clean Vehicle, Smooth Driving', 'Innova was very clean and well maintained. Perfect family outstation experience.', True, False, False),
        ('Rajesh Kumar (Cognizant)', '9884567890', 4, 4, 4, 5, 'On-Time Service, AC Cooling', 'Punctual airport pickup at Madurai. Good corporate transfer service.', True, True, False),
        ('Venkatesh Prasad', '9790123456', 2, 2, 3, 2, 'Late Pickup, AC Cooling Issue', 'AC cooling was weak during noon travel between Dindigul and Theni. Driver took personal phone calls while driving.', False, False, True),
        ('Ananya Sen', '9811223344', 5, 5, 5, 5, 'Polite Chauffeur, Mountain Driving, Clean Vehicle', 'Splendid Munnar hill tour! Safe driving through all hairpin bends.', True, True, False),
    ]

    for idx, t in enumerate(trips):
        if idx >= len(cases):
            break
        c_name, c_phone, ov, dr, cl, pu, tags, txt, prm, clk, esc = cases[idx]
        token = f"demo-token-{idx + 1}-{uuid.uuid4().hex[:12]}"
        
        fb, _ = TripCustomerFeedback.objects.get_or_create(
            trip=t,
            defaults={
                'customer_name': c_name,
                'customer_phone': c_phone,
                'feedback_token': token,
                'overall_rating': ov,
                'driver_politeness_rating': dr,
                'vehicle_cleanliness_rating': cl,
                'ac_punctuality_rating': pu,
                'positive_tags': tags,
                'feedback_text': txt,
                'google_review_prompted': prm,
                'google_review_clicked': clk,
                'complaint_escalated': esc,
            }
        )

        if esc and not fb.complaint:
            comp = TravelComplaint.objects.create(
                complainant_type='b2c_traveler',
                complainant_name=c_name,
                complainant_phone=c_phone,
                category='vehicle_condition',
                severity='high',
                issue_description=f"Post-Trip Deficit ({ov}★) - Trip #{t.trip_id} - {c_name}\n\n{txt}",
                status='lodged'
            )
            fb.complaint = comp
            fb.save()

        created.append(fb)
    return created
