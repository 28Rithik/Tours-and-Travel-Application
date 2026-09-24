import os
import sys
import re
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
django.setup()
sys.stdout.reconfigure(encoding='utf-8')

from packages.models import Package
from django.db import transaction
from collections import defaultdict, Counter

# ==============================================================================
# TAXONOMY & KEYWORD DICTIONARIES
# ==============================================================================

# Genuine Foreign Countries and International Destinations
INTL_COUNTRIES = {
    'dubai': 'United Arab Emirates (UAE)',
    'uae': 'United Arab Emirates (UAE)',
    'abu dhabi': 'United Arab Emirates (UAE)',
    'sharjah': 'United Arab Emirates (UAE)',
    'singapore': 'Singapore',
    'malaysia': 'Malaysia',
    'kuala lumpur': 'Malaysia',
    'genting': 'Malaysia',
    'langkawi': 'Malaysia',
    'penang': 'Malaysia',
    'thailand': 'Thailand',
    'bangkok': 'Thailand',
    'pattaya': 'Thailand',
    'phuket': 'Thailand',
    'krabi': 'Thailand',
    'koh samui': 'Thailand',
    'bali': 'Indonesia',
    'indonesia': 'Indonesia',
    'sri lanka': 'Sri Lanka',
    'colombo': 'Sri Lanka',
    'kandy': 'Sri Lanka',
    'bentota': 'Sri Lanka',
    'nuwara eliya': 'Sri Lanka',
    'maldives': 'Maldives',
    'vietnam': 'Vietnam',
    'hanoi': 'Vietnam',
    'da nang': 'Vietnam',
    'ho chi minh': 'Vietnam',
    'nepal': 'Nepal',
    'kathmandu': 'Nepal',
    'pokhara': 'Nepal',
    'bhutan': 'Bhutan',
    'thimphu': 'Bhutan',
    'paro': 'Bhutan',
    'mauritius': 'Mauritius',
    'turkey': 'Turkey',
    'istanbul': 'Turkey',
    'cappadocia': 'Turkey',
    'egypt': 'Egypt',
    'egyptian': 'Egypt',
    'cairo': 'Egypt',
    'alexandria': 'Egypt',
    'paris': 'France',
    'france': 'France',
    'switzerland': 'Switzerland',
    'zurich': 'Switzerland',
    'lucerne': 'Switzerland',
    'interlaken': 'Switzerland',
    'swiss alps': 'Switzerland',
    'europe': 'Europe',
    'london': 'United Kingdom (UK)',
    'united kingdom': 'United Kingdom (UK)',
    'england': 'United Kingdom (UK)',
    'scotland': 'United Kingdom (UK)',
    'edinburgh': 'United Kingdom (UK)',
    'georgia': 'Georgia',
    'tbilisi': 'Georgia',
    'baku': 'Azerbaijan',
    'azerbaijan': 'Azerbaijan',
    'kazakhstan': 'Kazakhstan',
    'almaty': 'Kazakhstan',
    'astana': 'Kazakhstan',
    'uzbekistan': 'Uzbekistan',
    'tashkent': 'Uzbekistan',
    'samarkand': 'Uzbekistan',
    'kenya': 'Kenya',
    'nairobi': 'Kenya',
    'masai mara': 'Kenya',
    'south africa': 'South Africa',
    'south african': 'South Africa',
    'cape town': 'South Africa',
    'johannesburg': 'South Africa',
    'australia': 'Australia',
    'sydney': 'Australia',
    'melbourne': 'Australia',
    'new zealand': 'New Zealand',
    'auckland': 'New Zealand',
    'queenstown': 'New Zealand',
    'usa': 'United States (USA)',
    'america': 'United States (USA)',
    'new york': 'United States (USA)',
    'california': 'United States (USA)',
    'alaska': 'United States (USA)',
    'canada': 'Canada',
    'toronto': 'Canada',
    'vancouver': 'Canada',
    'japan': 'Japan',
    'tokyo': 'Japan',
    'kyoto': 'Japan',
    'osaka': 'Japan',
    'korea': 'South Korea',
    'south korea': 'South Korea',
    'seoul': 'South Korea',
    'greece': 'Greece',
    'athens': 'Greece',
    'santorini': 'Greece',
    'italy': 'Italy',
    'rome': 'Italy',
    'florence': 'Italy',
    'venice': 'Italy',
    'spain': 'Spain',
    'madrid': 'Spain',
    'barcelona': 'Spain',
    'sweden': 'Sweden',
    'stockholm': 'Sweden',
    'norway': 'Norway',
    'oslo': 'Norway',
    'denmark': 'Denmark',
    'copenhagen': 'Denmark',
    'finland': 'Finland',
    'helsinki': 'Finland',
    'cambodia': 'Cambodia',
    'siem reap': 'Cambodia',
    'angkor wat': 'Cambodia',
    'saudi arabia': 'Saudi Arabia',
    'riyadh': 'Saudi Arabia',
    'jeddah': 'Saudi Arabia',
    'israel': 'Israel',
    'jerusalem': 'Israel',
    'tel aviv': 'Israel',
    'jordan': 'Jordan',
    'petra': 'Jordan',
    'myanmar': 'Myanmar',
    'yangon': 'Myanmar',
    'afghanistan': 'Afghanistan',
    'czech': 'Czech Republic',
    'prague': 'Czech Republic',
    'malta': 'Malta',
    'cyprus': 'Cyprus',
    'iran': 'Iran',
    'tehran': 'Iran',
    'trinidad': 'Trinidad and Tobago',
    'tobago': 'Trinidad and Tobago',
    'peru': 'Peru',
    'lima': 'Peru',
    'namibia': 'Namibia',
    'windhoek': 'Namibia',
    'zanzibar': 'Tanzania',
    'tanzania': 'Tanzania',
    'kilimanjaro': 'Tanzania',
    'seychelles': 'Seychelles',
    'fiji': 'Fiji',
    'hong kong': 'Hong Kong',
    'macau': 'Macau',
    'taiwan': 'Taiwan',
    'philippines': 'Philippines',
    'manila': 'Philippines',
    'boracay': 'Philippines',
    'austria': 'Austria',
    'vienna': 'Austria',
    'germany': 'Germany',
    'berlin': 'Germany',
    'munich': 'Germany',
    'netherlands': 'Netherlands',
    'amsterdam': 'Netherlands',
    'belgium': 'Belgium',
    'brussels': 'Belgium',
    'hungary': 'Hungary',
    'budapest': 'Hungary',
    'portugal': 'Portugal',
    'lisbon': 'Portugal',
    'ireland': 'Ireland',
    'dublin': 'Ireland',
    'morocco': 'Morocco',
    'brazil': 'Brazil',
    'argentina': 'Argentina',
    'russia': 'Russia',
    'moscow': 'Russia',
    'china': 'China',
    'beijing': 'China',
    'shanghai': 'China',
    'armenia': 'Armenia',
    'croatia': 'Croatia',
    'qatar': 'Qatar',
    'bulgaria': 'Bulgaria',
    'iceland': 'Iceland',
    'oman': 'Oman',
    'romania': 'Romania',
    'greenland': 'Greenland',
    'caribbean': 'Caribbean Islands',
    'antarctica': 'Antarctica',
    'costa rica': 'Costa Rica',
    'jamaica': 'Jamaica',
    'san juan': 'Puerto Rico',
}

# Devotional / Temple / Spiritual Keywords
DEVOTIONAL_KEYWORDS = [
    'temple', 'darshan', 'pilgrimage', 'divine', 'spiritual', 'jyotirlinga', 'jyotirling',
    'tirupati', 'balaji', 'shirdi', 'kashi', 'varanasi', 'rameswaram', 'rameshwaram',
    'meenakshi', 'chidambaram', 'brihadeeswarar', 'srirangam', 'palani', 'tiruchendur',
    'swamimalai', 'thiruthani', 'pazhamudircholai', 'arupadai veedu', 'navagraha',
    'divya desam', 'divyadesam', 'kedarnath', 'badrinath', 'char dham', 'chardham',
    'amarnath', 'vaishno devi', 'haridwar', 'rishikesh', 'somnath', 'dwarka',
    'mahakaleshwar', 'omkareshwar', 'trimbakeshwar', 'grishneshwar', 'bhimashankar',
    'mallikarjuna', 'srisailam', 'kalahasti', 'kanchipuram', 'kumbakonam', 'velankanni',
    'nagore', 'golden temple', 'guruvayur', 'sabarimala', 'padmanabhaswamy',
    'murudeshwar', 'kukke subramanya', 'dharmasthala', 'horanadu', 'sringeri',
    'udupi krishna', 'kollur mookambika', 'thiruvannamalai', 'arunachaleswarar',
    'girivalam', 'thirukadaiyur', 'samayapuram', 'mariamman', 'nava tirupathi',
    'nava kailasam', 'dhanushkodi', 'suchindram', 'kaniyakumari bhagavathy',
    'madurai sundareswarar', 'oppiliappan', 'sarangapani', 'alagar kovil',
    'papanasam', 'alwar thirunagari', 'srivaikuntam', 'srivilliputhur andal',
    'tiruchengode', 'bhavani sangameshwarar', 'perur pateeswarar', 'marudhamalai',
    'subramaniyaswami', 'dhandayuthapani', 'swami malai', 'thiruchendur murugan',
    'thiruthani murugan', 'tiruttani murugan', 'shri ram janmabhoomi', 'ayodhya',
    'mathura', 'vrindavan', 'banke bihari', 'jagannath puri', 'konark sun temple',
    'lingaraj', 'kamakhya', 'dakshineswar', 'kalighat', 'belur math', 'tarapith',
    'gangotri', 'yamunotri', 'tungnath', 'rudraprayag', 'devprayag', 'joshimath',
    'manikaran', 'chamunda devi', 'jwala ji', 'naina devi', 'chintpurni',
    'brahma temple pushkar', 'nathdwara', 'shrinathji', 'khatu shyam', 'salasar balaji',
    'ranakpur jain', 'dilwara jain', 'palitana', 'girnar', 'shikharji', 'shravanabelagola',
    'muktinath', 'pashupatinath'
]

# Genuine Hill Station Keywords
HILL_STATION_KEYWORDS = [
    'ooty', 'kodaikanal', 'munnar', 'coorg', 'wayanad', 'chikmagalur', 'yercaud',
    'kolli hills', 'yelagiri', 'valparai', 'vagamon', 'thekkady', 'manali', 'shimla',
    'dharamshala', 'dalhousie', 'nainital', 'mussoorie', 'kasauli', 'darjeeling',
    'gangtok', 'shillong', 'cherrapunji', 'tawang', 'mahabaleshwar', 'lonavala',
    'khandala', 'panchgani', 'matheran', 'mount abu', 'spiti', 'leh', 'ladakh',
    'kashmir', 'srinagar', 'gulmarg', 'pahalgam', 'sonamarg', 'chamoli', 'almora',
    'ranikhet', 'lansdowne', 'kanatal', 'chopta', 'auli', 'pelling',
    'lachung', 'lachen', 'kalimpong', 'kurseong', 'mirik', 'haflong',
    'saputara', 'chail', 'kufri', 'solan', 'mashobra', 'narkanda', 'bir billing',
    'palampur', 'mcleodganj', 'kasol', 'tirthan valley', 'jibhi', 'kinnaur',
    'kalpa', 'sangla', 'chitkul', 'kaza', 'keylong', 'jispa', 'nubra valley',
    'pangong lake', 'tsomoriri', 'zanskar', 'kargil', 'drass'
]

# Corporate Outings & Leadership Offsite Keywords
CORPORATE_KEYWORDS = [
    'corporate', 'leadership retreat', 'executive retreat', 'team offsite', 'team building',
    'annual outing', 'corporate conclave', 'strategy offsite', 'corporate beachside summit'
]

# College IV & Industrial Visit Keywords
COLLEGE_IV_KEYWORDS = [
    'college iv', 'industrial visit', 'iv expedition', 'students tour', 'educational tour',
    'school tour', 'college tour', 'iv tour', 'mega iv', 'college industrial', 'campus tour'
]

# 1-Day Sightseeing / City Tour Keywords
LOCAL_TOUR_KEYWORDS = [
    'local sightseeing', 'city sightseeing', '1-day local', 'one day local',
    'chennai local', 'city tour', 'half day tour', 'outside city sightseeing',
    'sightseeing day tour', 'day outing'
]

# Family Vacation & Theme Park Keywords
FAMILY_KEYWORDS = [
    'theme park', 'black thunder', 'wonderla', 'family vacation', 'family leisure',
    'custom vacation', 'family trip'
]

# Known domestic areas that should NOT be marked as international
DOMESTIC_REGIONS = [
    'tamil nadu', 'tamilnadu', 'kerala', 'karnataka', 'andhra', 'telangana', 'himachal',
    'kashmir', 'ladakh', 'rajasthan', 'goa', 'uttarakhand', 'maharashtra', 'odisha',
    'sikkim', 'assam', 'meghalaya', 'chennai', 'coimbatore', 'madurai', 'ooty',
    'kodaikanal', 'munnar', 'tirupati', 'pondicherry', 'mahabalipuram', 'kanchipuram',
    'chidambaram', 'mysore', 'bangalore', 'bengaluru', 'hyderabad', 'delhi', 'agra',
    'jaipur', 'udaipur', 'jodhpur', 'jaisalmer', 'varanasi', 'kashi', 'haridwar', 'rishikesh'
]

from django.db.models import Count

def reclassify_package(pkg):
    """
    Determines the correct category and associated flags for a package.
    Returns: (new_category, is_devotional, is_international, has_industrial_visit, dest_country, reason)
    """
    code = (pkg.package_code or '').strip()
    name_lower = (pkg.name or '').lower()
    dest_lower = (pkg.destination or '').lower()
    desc_lower = (pkg.description or '').lower()
    full_text = f"{name_lower} {dest_lower} {desc_lower}"
    title_dest = f"{name_lower} {dest_lower}"

    # Clean text to avoid false international triggers like "Switzerland of India"
    clean_title_dest = title_dest.replace("switzerland of india", "khajjiar himachal")
    clean_title_dest = re.sub(r'travels([a-z])', r'travels \1', clean_title_dest)

    # --------------------------------------------------------------------------
    # 1. PRIORITY 1: Corporate Outing / Team Offsite
    # --------------------------------------------------------------------------
    if any(kw in clean_title_dest for kw in CORPORATE_KEYWORDS) or code.startswith('CORP-'):
        return 'corporate_offsite', False, False, False, '', 'Corporate retreat / team offsite'

    # --------------------------------------------------------------------------
    # 2. PRIORITY 2: College / School Industrial Visit (IV)
    # --------------------------------------------------------------------------
    is_iv_code = (
        code.startswith('IV-') or
        code.startswith('PKG-KL-IV-') or
        code.startswith('PKG-KA-KL-IV-') or
        bool(re.search(r'(^|[-_])iv([-_]|$)', code.lower()))
    )
    is_iv_text = bool(re.search(r'\b(college iv|industrial visit|students tour|educational tour|students iv|school tour)\b', clean_title_dest))
    if is_iv_code or is_iv_text:
        return 'college_iv', False, False, True, '', 'College / Student Industrial Visit (IV)'

    # --------------------------------------------------------------------------
    # 3. PRIORITY 3: Cross-Border Holy Yatras (e.g. Nepal / Muktinath)
    # --------------------------------------------------------------------------
    is_nepal_yatra = any(kw in clean_title_dest for kw in ['muktinath', 'pashupatinath']) or ('nepal' in clean_title_dest and any(kw in clean_title_dest for kw in ['yatra', 'darshan', 'pilgrimage', 'spiritual', 'temple', 'divya desam']))
    if is_nepal_yatra:
        return 'devotional', True, True, False, 'Nepal', 'Cross-border Holy Pilgrimage (Nepal / Muktinath)'

    # --------------------------------------------------------------------------
    # 4. PRIORITY 4: International Packages
    # --------------------------------------------------------------------------
    is_visa = 'visa' in clean_title_dest or 'visa assistance' in dest_lower
    has_foreign_dest = None
    for kw, country_name in INTL_COUNTRIES.items():
        if re.search(r'\b' + re.escape(kw) + r'\b', clean_title_dest):
            has_foreign_dest = country_name
            break

    # Check if mistakenly marked as international when it's domestic
    is_domestic = any(re.search(r'\b' + re.escape(dr) + r'\b', clean_title_dest) for dr in DOMESTIC_REGIONS) and not has_foreign_dest and not is_visa

    if (has_foreign_dest or is_visa or (pkg.is_international and not is_domestic)) and not is_domestic:
        country = has_foreign_dest or pkg.destination_country or ('Overseas Visa' if is_visa else 'International')
        return 'international', False, True, False, country, f'International overseas tour / visa ({country})'

    # --------------------------------------------------------------------------
    # 5. PRIORITY 5: Local 1-Day Tours (duration_days <= 1 or duration_nights == 0)
    # --------------------------------------------------------------------------
    is_1day = (pkg.duration_days == 1 or pkg.duration_nights == 0)
    has_local_kw = any(kw in clean_title_dest for kw in LOCAL_TOUR_KEYWORDS) or '1-day' in clean_title_dest or '1 day' in clean_title_dest or 'one day' in clean_title_dest or code.endswith('-1D')

    if is_1day and (has_local_kw or pkg.category == 'local_tour'):
        # Check if it's a 1-day temple tour
        has_devotional = any(re.search(r'\b' + re.escape(kw) + r'\b', clean_title_dest) for kw in DEVOTIONAL_KEYWORDS)
        if has_devotional:
            # Dedicated 1-day temple darshan
            return 'devotional', True, False, False, '', '1-Day Devotional & Temple Darshan Tour'
        return 'local_tour', False, False, False, '', '1-Day local sightseeing / city tour'

    # --------------------------------------------------------------------------
    # 6. PRIORITY 6: Devotional & Pilgrimage Tour (Temple Circuits)
    # --------------------------------------------------------------------------
    has_devotional = any(re.search(r'\b' + re.escape(kw) + r'\b', clean_title_dest) for kw in DEVOTIONAL_KEYWORDS)
    if has_devotional or pkg.is_devotional or pkg.category in ['devotional', 'pilgrimage']:
        return 'devotional', True, False, False, '', 'Devotional & Pilgrimage Tour (Temple Circuit)'

    # --------------------------------------------------------------------------
    # 7. PRIORITY 7: Hill Station Getaway
    # --------------------------------------------------------------------------
    has_hill = any(re.search(r'\b' + re.escape(kw) + r'\b', clean_title_dest) for kw in HILL_STATION_KEYWORDS)
    if has_hill:
        return 'hill_station', False, False, False, '', 'Hill station scenic getaway'

    # --------------------------------------------------------------------------
    # 8. PRIORITY 8: Family Vacation & Theme Parks
    # --------------------------------------------------------------------------
    if any(kw in clean_title_dest for kw in FAMILY_KEYWORDS) or pkg.category == 'family_vacation':
        return 'family_vacation', False, False, False, '', 'Family vacation & theme park leisure'

    # --------------------------------------------------------------------------
    # 9. PRIORITY 9: Fixed Departure Group Tour Bus Trip
    # --------------------------------------------------------------------------
    if 'fixed departure' in clean_title_dest or pkg.category == 'fixed_departure':
        return 'fixed_departure', False, False, False, '', 'Fixed departure group convoy'

    # --------------------------------------------------------------------------
    # 10. PRIORITY 10: General Holiday & Beach / Wildlife / Heritage Getaways
    # --------------------------------------------------------------------------
    return 'holiday', False, False, False, '', 'Holiday getaway (beach / wildlife / heritage / plains)'


def main():
    print("=" * 80)
    print("EXECUTING RECLASSIFICATION & CLEANING ACROSS ALL PACKAGES")
    print("=" * 80)

    total_pkgs = Package.objects.count()
    print(f"Total packages in DB: {total_pkgs}")

    category_changes = defaultdict(int)
    flag_changes = defaultdict(int)
    reclassified_pkgs = []

    with transaction.atomic():
        for pkg in Package.objects.all():
            old_cat = pkg.category
            old_is_dev = pkg.is_devotional
            old_is_intl = pkg.is_international
            old_has_iv = pkg.has_industrial_visit
            old_dest_country = pkg.destination_country

            new_cat, new_is_dev, new_is_intl, new_has_iv, new_country, reason = reclassify_package(pkg)

            changed = False

            # Clean any concatenated "Travels<Word>" in title
            cleaned_name = re.sub(r'Travels([A-Za-z])', r'Travels \1', pkg.name)
            if cleaned_name != pkg.name:
                pkg.name = cleaned_name
                changed = True

            if old_cat != new_cat:
                pkg.category = new_cat
                category_changes[f"{old_cat} -> {new_cat}"] += 1
                changed = True

            if old_is_dev != new_is_dev:
                pkg.is_devotional = new_is_dev
                flag_changes[f"is_devotional: {old_is_dev} -> {new_is_dev}"] += 1
                changed = True
                if new_is_dev:
                    pkg.satvik_pure_veg_meals = True
                    pkg.senior_citizen_friendly = True
                    if not pkg.temple_dress_code:
                        pkg.temple_dress_code = "Traditional Dhoti/Kurta for Men, Saree/Chudidar for Women"

            if old_is_intl != new_is_intl:
                pkg.is_international = new_is_intl
                flag_changes[f"is_international: {old_is_intl} -> {new_is_intl}"] += 1
                changed = True

            if old_has_iv != new_has_iv:
                pkg.has_industrial_visit = new_has_iv
                flag_changes[f"has_industrial_visit: {old_has_iv} -> {new_has_iv}"] += 1
                changed = True

            if new_country and old_dest_country != new_country:
                pkg.destination_country = new_country
                changed = True

            if changed:
                pkg.save()
                reclassified_pkgs.append((pkg.id, pkg.package_code, pkg.name, old_cat, new_cat, reason))

    print(f"\nSuccessfully evaluated {total_pkgs} packages.")
    print(f"Total packages updated: {len(reclassified_pkgs)}")

    print("\n--- Category Shifts ---")
    for shift, count in sorted(category_changes.items(), key=lambda x: -x[1]):
        print(f"  {shift}: {count} packages")

    print("\n--- Boolean Flag Alignments ---")
    for flag_shift, count in sorted(flag_changes.items(), key=lambda x: -x[1]):
        print(f"  {flag_shift}: {count} packages")

    print("\n--- New Package Distribution by Category ---")
    new_counts = Package.objects.values('category').annotate(count=Count('id')).order_by('-count')
    for item in new_counts:
        print(f"  {item['category']}: {item['count']}")

    print("\n" + "=" * 80)
    print("RECLASSIFICATION COMPLETED SUCCESSFULLY")
    print("=" * 80)

if __name__ == '__main__':
    main()
