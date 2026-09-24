import os
import sys
import re

sys.stdout.reconfigure(encoding='utf-8')

LOWERCASE_WORDS = {
    'a', 'an', 'and', 'as', 'at', 'but', 'by', 'for', 'in', 'into', 'nor', 'of',
    'on', 'onto', 'or', 'per', 'the', 'to', 'with', 'via', 'from'
}

UPPERCASE_WORDS = {
    'IV', 'DJ', 'AC', 'IT', 'USA', 'UK', 'UAE', 'APJ', 'KRS', 'HAL', 'ISKCON',
    'AP', 'EP', 'CP', 'MAP', 'CTC', 'DMC', 'INR', 'AED', 'SGD', 'MYR', 'THB',
    'UNESCO', 'TN', 'KL', 'KA', 'FL', 'MP', 'UP'
}

def beautify_title(raw_title):
    if not raw_title:
        return ""
    
    t = raw_title.strip()

    # 1. Un-glue common concatenated words from bad scrapers
    t = re.sub(r'([A-Za-z]+)TOUR\b', r'\1 Tour', t, flags=re.IGNORECASE)
    t = re.sub(r'([A-Za-z]+)PACKAGE\b', r'\1 Package', t, flags=re.IGNORECASE)
    t = re.sub(r'([A-Za-z]+)TRIP\b', r'\1 Trip', t, flags=re.IGNORECASE)

    # 2. Convert (FROM <CITY>) or FROM <CITY> to (Ex-<City>)
    t = re.sub(r'\(\s*FROM\s+([A-Za-z]+)\s*\)', r'(Ex-\1)', t, flags=re.IGNORECASE)
    t = re.sub(r'\bFROM\s+([A-Za-z]+)\b', r'(Ex-\1)', t, flags=re.IGNORECASE)

    # 3. Clean double dashes and underscores
    t = t.replace('--', ' - ').replace('_', ' ')

    # 4. Standardize hyphens between words: e.g. MYSORE-COORG -> Mysore - Coorg
    t = re.sub(r'([A-Za-z])-([A-Za-z])', r'\1 - \2', t)

    # 5. Normalize duration tags e.g. (2N/3D), 4N 5D, 1 DAYS -> 1 Day
    t = re.sub(r'(\d+)\s*DAYS\b', r'\1 Days', t, flags=re.IGNORECASE)
    t = re.sub(r'1\s*Days\b', r'1 Day', t)
    t = re.sub(r'(\d+)\s*NIGHTS\b', r'\1 Nights', t, flags=re.IGNORECASE)
    t = re.sub(r'1\s*Nights\b', r'1 Night', t)
    t = re.sub(r'(\d+)[nN]\s*[/-]?\s*(\d+)[dD]', r'\1N/\2D', t)
    t = re.sub(r'(\d+)[dD]\s*[/-]?\s*(\d+)[nN]', r'\1D/\2N', t)
    t = re.sub(r'(\d+)[nN]\s+(\d+)[dD]', r'\1N/\2D', t)

    # 6. Remove redundant "TOUR PACKAGE", "TOUR PACKAGES", "PACKAGE TOUR"
    # Remove repeated instances
    t = re.sub(r'\b(?:tour\s+package[s]?|package\s+tour[s]?)\s+(?:tour\s+package[s]?|package\s+tour[s]?)\b', 'Tour Package', t, flags=re.IGNORECASE)

    # Clean double Ex-City (e.g. Coimbatore Black Thunder ... Coimbatore Tour)
    m_city = re.match(r'^(Coimbatore|Chennai|Bangalore|Madurai|Trichy|Kochi|Delhi|Mumbai)\s+(.*)\s+\1\s+Tour\s+Package', t, flags=re.IGNORECASE)
    if m_city:
        city = m_city.group(1).title()
        rest = m_city.group(2).strip()
        t = f"{rest} Tour Package (Ex-{city})"

    # Word-by-word title-casing
    words = t.split()
    clean_words = []
    for i, w in enumerate(words):
        # Extract punctuation
        m = re.match(r'^([^a-zA-Z0-9]*)(.*?)([^a-zA-Z0-9]*)$', w)
        if m:
            pfx, core, sfx = m.groups()
        else:
            pfx, core, sfx = '', w, ''

        core_upper = core.upper()
        
        # Keep duration e.g. 2N/3D or 3D/2N
        if re.match(r'^\d+[ND]/\d+[ND]$', core_upper):
            c_word = core_upper
        elif core_upper.startswith('EX-'):
            c_word = 'Ex-' + core[3:].capitalize()
        elif core_upper in UPPERCASE_WORDS:
            c_word = core_upper
        elif core.lower() in LOWERCASE_WORDS and i > 0 and clean_words and not clean_words[-1].endswith(('-', ':', '|', '(')):
            c_word = core.lower()
        else:
            c_word = core.capitalize()

        clean_words.append(pfx + c_word + sfx)

    res = ' '.join(clean_words)

    # Clean redundant Tour Package if it occurs twice
    parts = re.split(r'\bTour Package\b', res, flags=re.IGNORECASE)
    if len(parts) > 2:
        # Keep only the last one
        res = ''.join(parts[:-1]).strip() + ' Tour Package' + parts[-1]

    # Clean spaces around parentheses and dashes
    res = re.sub(r'\(\s+', '(', res)
    res = re.sub(r'\s+\)', ')', res)
    res = re.sub(r'\s+-\s+', ' - ', res)
    res = re.sub(r'\s+', ' ', res).strip()
    return res

def beautify_destination(raw_dest, pkg_name=""):
    if not raw_dest:
        return "Tamil Nadu, South India"
    
    d = raw_dest.strip()
    
    # Remove durations from destination
    d = re.sub(r'\b\d+\s*(?:NIGHTS?|DAYS?|N|D)\b.*', '', d, flags=re.IGNORECASE).strip()
    
    # Remove trailing words
    d = re.sub(r'\b(?:TOUR\s+PACKAGE[S]?|PACKAGE|TRIP|SPECIAL)\b.*', '', d, flags=re.IGNORECASE).strip()
    d = d.rstrip('-').rstrip(',').strip()

    # If destination was an attraction dump from Prabu Tours
    if len(d.split()) > 7 and any(k in d.lower() for k in ['rose garden', 'boat house', 'botanical garden', 'museum']):
        if 'ooty' in d.lower():
            return "Ooty & Coonoor, Nilgiris"
        elif 'kodaikanal' in d.lower():
            return "Kodaikanal, Tamil Nadu"
        elif 'valparai' in d.lower():
            return "Valparai & Pollachi, Tamil Nadu"

    # Clean comma-separated words that are just fragmented words (e.g. Coimbatore, Black, Thunder, Water)
    if 'Black, Thunder' in d or 'Black Thunder' in d:
        return "Black Thunder Theme Park, Mettupalayam"
    if 'Athirappilly, Water, Falls' in d or 'Athirappilly' in d and 'Malampuzha' in d:
        return "Athirappilly & Malampuzha, Kerala"
    
    # Comma India
    if d == ', India' or d == 'India' or len(d) <= 2:
        if pkg_name:
            first_part = pkg_name.split('-')[0].split('|')[0].strip()
            return f"{first_part.title()}, India"
        return "South India, India"

    # Title-case destination
    words = d.split()
    clean_words = []
    for i, w in enumerate(words):
        core = w.strip(',.-')
        if core.upper() in UPPERCASE_WORDS:
            clean_words.append(w.replace(core, core.upper()))
        elif core.lower() in LOWERCASE_WORDS and i > 0:
            clean_words.append(w.replace(core, core.lower()))
        else:
            clean_words.append(w.replace(core, core.capitalize()))

    res = ' '.join(clean_words)
    res = re.sub(r'\s*,\s*', ', ', res)
    res = re.sub(r'\s+-\s+', ' - ', res)
    return res

test_samples = [
    ("BHUBANESWAR, PURI JAGANATH TOUR PACKAGE(2N/3D) TOUR PACKAGE", "Bhubaneswar, Puri Jaganath TOUR PACKAGE(2N/10)"),
    ("BEST OF DANDELI (FROM HUBLI) TOUR PACKAGE", "Dandeli"),
    ("3 DAYS TRIP FROM DELHI | HARIDWAR - RISHIKESH TOUR PACKAGE", "Haridwar - Rishikesh"),
    ("THIRUVANNAMALAI TOUR PACKAGE", "Tamil Nadu"),
    ("AMAZING EUROPE SPECIAL 6N 7D TOUR PACKAGE", "Amazing Europe Special 6N 7D"),
    ("COIMBATORE BLACK THUNDER WATER THEME PARK COIMBATORE TOUR PACKAGE", "Coimbatore, Black, Thunder, Water"),
    ("COIMBATORE ATHIRAPPILLY WATER FALLS MALAMPUZHA DAM COIMBATORE TOUR PACKAGE", "Coimbatore, Athirappilly, Water, Falls"),
    ("OOTY & COONOORTOUR FROM COIMBATORE TOUR PACKAGE", "Ooty Rose Garden Boat House Children Park Government Museum Dodabeta Peak Botanical Garden Coonoor Sims Park Wax Museum Ketti Valley View"),
    ("GURUVAYURTOUR FROM COIMBATORE TOUR PACKAGE", "GURUVAYUR"),
    ("SHIMLA MANALI HONEYMOON TOUR PACKAGES TOUR PACKAGE", "Shimla Manali Honeymoon  S"),
    ("ARUPADAI VEEDU TOUR PACKAGE FROM TRICHY", "Arupadai Veedu   From Trichy"),
    ("ISHA-MARUDHAMALAI 1 DAYS TOUR PACKAGE", "Isha-Marudhamalai"),
    ("2 NIGHTS 3 DAYS TOUR PLAN (MYSORE-COORG-CHIKMANGALUR)", "TAMILNADU/KARNATAKA"),
    ("4 NIGHTS 5 DAYS KERALA COLLEGE IV (KOCHI IT HUB - VARKALA BEACH)", "Kerala"),
    ("VARKALA BEACH TOUR PACKAGE2 NIGHTS AND 3 DAYS", "VARKALA BEACH TOUR PACKAGE2 NIGHTS AND 3 DAYS")
]

print("BEFORE -> AFTER BEAUTIFICATION:")
for name, dest in test_samples:
    print(f"\nBefore Title: {name}")
    print(f"After  Title: {beautify_title(name)}")
    print(f"Before Dest : {dest}")
    print(f"After  Dest : {beautify_destination(dest, name)}")
