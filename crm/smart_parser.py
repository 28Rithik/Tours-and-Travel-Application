"""
Rathasārathi AI Smart Lead & Inquiry Parser (Sivagayathiri Travels ERP)
Extracts structured booking and tour inquiry fields from raw unstructured text
(WhatsApp chats, SMS, emails, phone notes, or Tamil-English transliterations).

Combines high-speed heuristic regex NLP with Groq LLM intelligence fallback.
"""

import os
import re
import json
import logging
from datetime import datetime, timedelta
from decimal import Decimal
import requests
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

# Destination Mapping for Sivagayathiri Travel Circuits
DESTINATIONS_MAP = {
    'ooty': ('ooty', '🌲 Ooty / Nilgiris, TN', ['ooty', 'nilgiris', 'coonoor', 'kotagiri']),
    'kodaikanal': ('kodaikanal', '🌸 Kodaikanal, TN', ['kodaikanal', 'kodai']),
    'munnar': ('munnar', '🍃 Munnar Tea Hills, KL', ['munnar', 'thekkady']),
    'kochi': ('kochi', '⛵ Kochi / Alleppey Backwaters, KL', ['kochi', 'cochin', 'alleppey', 'alappuzha', 'kumarakom']),
    'wayanad': ('wayanad', '🌿 Wayanad Wildlife, KL', ['wayanad', 'sulthan bathery']),
    'madurai': ('madurai', '🛕 Madurai Temple Circuit, TN', ['madurai', 'meenakshi amman']),
    'rameshwaram': ('rameshwaram', '🌊 Rameshwaram & Dhanushkodi, TN', ['rameshwaram', 'dhanushkodi', 'pamban']),
    'kanyakumari': ('kanyakumari', '🌅 Kanyakumari Sunset Point, TN', ['kanyakumari', 'cape comorin']),
    'pondicherry': ('pondicherry', '🏖️ Pondicherry / Auroville', ['pondicherry', 'pondy', 'auroville']),
    'mysore_coorg': ('mysore_coorg', '🏰 Mysore Palace & Coorg, KA', ['mysore', 'coorg', 'madikeri', 'chikmagalur']),
    'bangalore': ('bangalore', '🏙️ Bangalore Tech Hub / Transit', ['bangalore', 'bengaluru']),
    'chennai': ('chennai', '🏛️ Chennai Metropolitan & Mahabalipuram', ['chennai', 'madras', 'mahabalipuram']),
    'goa': ('goa', '🌴 Goa Coastal Holiday', ['goa', 'panaji', 'calangute']),
    'tirupati': ('tirupati', '🙏 Tirupati Balaji Darshan, AP', ['tirupati', 'balaji']),
    'yercaud': ('yercaud', '⛰️ Yercaud Shevaroy Hills, TN', ['yercaud', 'shevaroy']),
    'coimbatore': ('coimbatore', '🏭 Coimbatore Hub / Isha Yoga', ['coimbatore', 'isha', 'marudhamalai', 'pollachi', 'valparai']),
}


def parse_inquiry_text(raw_text: str) -> dict:
    """
    Primary entry point: parses unstructured text into structured inquiry dictionary.
    First attempts fast heuristic NLP. If Groq API key is configured and heuristics
    miss crucial details, leverages Groq LLM for deep entity resolution.
    """
    if not raw_text or not raw_text.strip():
        return _empty_result()

    # 1. Run local heuristic NLP parser
    extracted = _heuristic_nlp_parse(raw_text)

    # 2. Check if Groq LLM is available and can enrich/refine
    groq_api_key = os.environ.get('GROQ_API_KEY') or getattr(settings, 'GROQ_API_KEY', '')
    if groq_api_key and (not extracted.get('guest_name') or not extracted.get('destination')):
        try:
            llm_result = _groq_llm_parse(raw_text, groq_api_key)
            if llm_result:
                # Merge: prefer LLM values where heuristics had low confidence
                for k, v in llm_result.items():
                    if v and not extracted.get(k):
                        extracted[k] = v
        except Exception as e:
            logger.warning(f"Groq LLM parse fallback to heuristics: {e}")

    # 3. Post-processing & normalization
    _normalize_and_enrich(extracted)
    return extracted


def _heuristic_nlp_parse(text: str) -> dict:
    """
    Fast, reliable offline rule-based parser (< 5ms execution).
    """
    clean_text = text.replace('\r\n', '\n').strip()
    res = _empty_result()
    res['raw_input'] = clean_text

    # --- A. Mobile Phone Number ---
    phone_match = re.search(r'(?:\+?91[\-\s]?)?[6-9]\d{4}[\-\s]?\d{5}', clean_text)
    if phone_match:
        phone_digits = re.sub(r'[^\d]', '', phone_match.group())
        if len(phone_digits) >= 10:
            res['guest_phone'] = phone_digits[-10:]

    # --- B. Email Address ---
    email_match = re.search(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', clean_text)
    if email_match:
        res['guest_email'] = email_match.group()

    # --- C. Guest Name ---
    name_patterns = [
        r'(?:name|contact|customer|guest|mr\.?|mrs\.?|dr\.?)\s*[:\-]?\s*([a-zA-Z\s\.]{2,35})',
        r'(?:i am|this is|caller)\s+([a-zA-Z\s]{2,25})',
        r'from\s*:\s*([a-zA-Z\s]{2,30})',
    ]
    for pat in name_patterns:
        m = re.search(pat, clean_text, re.IGNORECASE)
        if m:
            candidate = m.group(1).strip()
            # Clean common trailing punctuation or words
            candidate = re.split(r'[,;\n\d]', candidate)[0].strip()
            if candidate and len(candidate.split()) <= 4:
                res['guest_name'] = candidate.title()
                break

    # If still not found, check the first line for a 2-word name if not matching keywords
    if not res['guest_name']:
        lines = [line.strip() for line in clean_text.split('\n') if line.strip()]
        if lines:
            first_line = lines[0]
            words = first_line.split()
            if 2 <= len(words) <= 3 and all(w.isalpha() for w in words):
                ignore_words = {'hi', 'hello', 'need', 'want', 'sir', 'madam', 'dear', 'travels', 'inquiry'}
                if not any(w.lower() in ignore_words for w in words):
                    res['guest_name'] = first_line.title()

    # --- D. Destination & Dropdown ---
    text_lower = clean_text.lower()
    matched_dest = None
    for code, (key, label, aliases) in DESTINATIONS_MAP.items():
        for alias in aliases:
            if re.search(rf'\b{re.escape(alias)}\b', text_lower):
                matched_dest = (code, label, alias)
                break
        if matched_dest:
            break

    if matched_dest:
        res['destination_dropdown'] = matched_dest[0]
        res['destination'] = matched_dest[1]
    else:
        # Generic destination pattern: "to [Location]" or "trip to [Location]"
        to_match = re.search(r'(?:to|for|destination|circuit)\s+([a-zA-Z\s]{3,30})', clean_text, re.IGNORECASE)
        if to_match:
            dest_cand = to_match.group(1).strip()
            dest_cand = re.split(r'[,;\n\d]', dest_cand)[0].strip()
            res['destination'] = dest_cand.title()
            res['destination_dropdown'] = 'other'

    # --- E. Pickup Location ---
    from_match = re.search(r'(?:from|pickup\s*(?:at|from)?|ex[\-–])\s*([a-zA-Z\s]{3,30})', clean_text, re.IGNORECASE)
    if from_match:
        pickup_cand = from_match.group(1).strip()
        pickup_cand = re.split(r'[,;\n\d]|to\b', pickup_cand)[0].strip()
        res['pickup_location'] = pickup_cand.title()
    else:
        res['pickup_location'] = 'Coimbatore HQ'

    # --- F. Dates (Pickup Date, Duration, Drop Date) ---
    today = timezone.localdate()
    pickup_date = None
    duration_days = 1

    # Relative date patterns
    if 'tomorrow' in text_lower:
        pickup_date = today + timedelta(days=1)
    elif 'day after tomorrow' in text_lower:
        pickup_date = today + timedelta(days=2)
    elif 'today' in text_lower:
        pickup_date = today

    # Explicit date regex (DD/MM/YYYY or DD-MM-YYYY or DD/MM)
    if not pickup_date:
        d_match = re.search(r'(\d{1,2})[\/\-\.](\d{1,2})(?:[\/\-\.](\d{2,4}))?', clean_text)
        if d_match:
            day = int(d_match.group(1))
            month = int(d_match.group(2))
            year = int(d_match.group(3)) if d_match.group(3) else today.year
            if year < 100:
                year += 2000
            try:
                pickup_date = datetime(year, month, day).date()
            except ValueError:
                pass

    # Word month date regex (e.g. 15th Nov, Nov 15, 28 October)
    if not pickup_date:
        wm_match = re.search(r'(\d{1,2})(?:st|nd|rd|th)?\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*(?:\s+(\d{4}))?', clean_text, re.IGNORECASE)
        if wm_match:
            day = int(wm_match.group(1))
            month_str = wm_match.group(2)[:3].lower()
            months = {'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6, 'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12}
            month = months.get(month_str, 1)
            year = int(wm_match.group(3)) if wm_match.group(3) else today.year
            try:
                pickup_date = datetime(year, month, day).date()
            except ValueError:
                pass

    if not pickup_date:
        # Default to tomorrow if not specified
        pickup_date = today + timedelta(days=1)

    res['pickup_date'] = pickup_date.strftime('%Y-%m-%d')

    # Duration parsing (e.g. "3 days", "3d 2n", "4 nights")
    dur_match = re.search(r'(\d+)\s*(?:days?|d\b)', clean_text, re.IGNORECASE)
    if dur_match:
        duration_days = max(1, int(dur_match.group(1)))
    else:
        nights_match = re.search(r'(\d+)\s*(?:nights?|n\b)', clean_text, re.IGNORECASE)
        if nights_match:
            duration_days = max(1, int(nights_match.group(1)) + 1)

    res['duration_days'] = duration_days
    drop_date = pickup_date + timedelta(days=duration_days - 1)
    res['drop_date'] = drop_date.strftime('%Y-%m-%d')
    res['pickup_time'] = '06:00'

    # --- G. Adult & Child Pax Count ---
    adult_match = re.search(r'(\d+)\s*(?:adults?|pax|persons?|people|members?|per)\b', clean_text, re.IGNORECASE)
    if adult_match:
        res['adult_count'] = int(adult_match.group(1))
    else:
        # Standalone count before pax/people
        gen_pax = re.search(r'(\d+)\s*(?:nos|no|count)\b', clean_text, re.IGNORECASE)
        if gen_pax:
            res['adult_count'] = int(gen_pax.group(1))
        else:
            res['adult_count'] = 4 if 'family' in text_lower else 2

    child_match = re.search(r'(\d+)\s*(?:children|child|kids?)\b', clean_text, re.IGNORECASE)
    if child_match:
        res['child_count'] = int(child_match.group(1))
    else:
        res['child_count'] = 0

    # --- H. Vehicle Type Resolution ---
    _resolve_vehicle_type(clean_text, res)

    # --- I. Quoted / Estimated Deal Value ---
    price_match = re.search(r'(?:rs\.?|inr|₹|budget|quote|cost|rate)\s*[:\-]?\s*(\d[\d,]{3,9})', clean_text, re.IGNORECASE)
    if price_match:
        price_str = price_match.group(1).replace(',', '')
        try:
            res['quoted_price'] = float(price_str)
        except ValueError:
            pass
    else:
        k_match = re.search(r'(\d{1,3})\s*k\b', clean_text, re.IGNORECASE)
        if k_match:
            try:
                res['quoted_price'] = float(k_match.group(1)) * 1000.0
            except ValueError:
                pass

    # --- J. Journey Type & Priority ---
    if 'airport' in text_lower:
        res['journey_type'] = 'airport'
    elif 'local' in text_lower or '8hr' in text_lower or 'hourly' in text_lower:
        res['journey_type'] = 'local'
    else:
        res['journey_type'] = 'outstation'

    if any(w in text_lower for w in ['urgent', 'vip', 'asap', 'immediate', 'today itself', 'emergency']):
        res['priority'] = 'urgent'
    elif any(w in text_lower for w in ['corporate', 'ceo', 'wedding', 'group']):
        res['priority'] = 'high'
    else:
        res['priority'] = 'medium'

    # Special requirements captures notes
    res['special_requirements'] = clean_text[:400]
    return res


def _resolve_vehicle_type(text: str, res: dict):
    """Matches text against VehicleType database models."""
    from core.models import VehicleType

    text_lower = text.lower()
    candidate_id = None
    candidate_name = None

    # Priority vehicle keyword mapping
    mappings = [
        (['innova crysta', 'crysta'], 'Innova Crysta'),
        (['innova'], 'Innova'),
        (['ertiga'], 'Ertiga'),
        (['dzire', 'etios', 'sedan'], 'Sedan'),
        (['urbania'], 'Force Urbania'),
        (['tempo', 'traveller', '12 seater', '17 seater', '20 seater', '26 seater'], 'Force Traveller'),
        (['bharat benz', 'bharatbenz'], 'Bharat Benz'),
        (['volvo'], 'Volvo'),
        (['coach', 'bus', '40 seater', '50 seater'], 'Coach'),
    ]

    for keywords, search_term in mappings:
        if any(kw in text_lower for kw in keywords):
            vt = VehicleType.objects.filter(name__icontains=search_term).first()
            if vt:
                candidate_id = vt.id
                candidate_name = vt.name
                break

    if not candidate_id:
        # Default to a standard Innova Crysta or first available vehicle type
        vt = VehicleType.objects.filter(name__icontains='Innova').first() or VehicleType.objects.first()
        if vt:
            candidate_id = vt.id
            candidate_name = vt.name

    res['vehicle_type_id'] = candidate_id
    res['vehicle_type_name'] = candidate_name


def _groq_llm_parse(text: str, api_key: str) -> dict:
    """
    Leverages Groq LLaMA 3.3-70B to resolve conversational/dialect subtleties.
    """
    system_prompt = (
        "You are an AI data extractor for Sivagayathiri Travels, a premium tours and fleet operator in Coimbatore, Tamil Nadu. "
        "Extract structured JSON fields from the user's travel inquiry text. "
        "Return ONLY a valid JSON object with keys: guest_name, guest_phone, guest_email, pickup_location, destination, "
        "pickup_date (YYYY-MM-DD), duration_days (integer), adult_count (integer), child_count (integer), vehicle_hint, special_requirements."
    )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text}
        ],
        "temperature": 0.1,
        "response_format": {"type": "json_object"}
    }

    resp = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=4.0)
    if resp.status_code == 200:
        content = resp.json()['choices'][0]['message']['content']
        return json.loads(content)
    return {}


def _normalize_and_enrich(res: dict):
    """Ensures fallback values and calculate estimated pricing if absent."""
    if not res.get('guest_name'):
        res['guest_name'] = 'Valued Guest'
    if not res.get('destination'):
        res['destination'] = 'Ooty / Nilgiris Circuit'
        res['destination_dropdown'] = 'ooty'
    if not res.get('pickup_location'):
        res['pickup_location'] = 'Coimbatore HQ'

    # Compute default estimated deal value if not present
    if not res.get('quoted_price'):
        duration = res.get('duration_days', 1)
        # Approximate standard tariff: ₹4,500/day for SUV/Innova
        res['quoted_price'] = duration * 4500.0


def _empty_result() -> dict:
    return {
        'guest_name': '',
        'guest_phone': '',
        'guest_email': '',
        'pickup_location': 'Coimbatore HQ',
        'destination': '',
        'destination_dropdown': 'ooty',
        'pickup_date': '',
        'pickup_time': '06:00',
        'drop_date': '',
        'duration_days': 1,
        'adult_count': 2,
        'child_count': 0,
        'vehicle_type_id': None,
        'vehicle_type_name': '',
        'journey_type': 'outstation',
        'priority': 'medium',
        'source': 'whatsapp',
        'special_requirements': '',
        'quoted_price': None,
        'raw_input': '',
    }
