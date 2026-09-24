import os
import sys
import re
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
django.setup()
sys.stdout.reconfigure(encoding='utf-8')

from packages.models import Package
from django.db.models import Q, Count
from collections import defaultdict, Counter

print("=" * 80)
print("AUDITING CLASSIFICATION RULES ACROSS ALL 6,246 PACKAGES")
print("=" * 80)

# Define comprehensive keyword dictionaries
INTL_COUNTRIES = [
    'dubai', 'uae', 'abu dhabi', 'sharjah', 'singapore', 'malaysia', 'kuala lumpur', 'genting',
    'thailand', 'bangkok', 'pattaya', 'phuket', 'krabi', 'bali', 'indonesia', 'sri lanka',
    'colombo', 'kandy', 'bentota', 'nuwara eliya', 'maldives', 'vietnam', 'hanoi', 'da nang',
    'ho chi minh', 'nepal', 'kathmandu', 'pokhara', 'bhutan', 'thimphu', 'paro', 'mauritius',
    'turkey', 'istanbul', 'cappadocia', 'egypt', 'cairo', 'alexandria', 'paris', 'france',
    'switzerland', 'zurich', 'lucerne', 'interlaken', 'europe', 'london', 'uk', 'united kingdom',
    'england', 'scotland', 'edinburgh', 'georgia', 'tbilisi', 'baku', 'azerbaijan', 'kazakhstan',
    'almaty', 'astana', 'uzbekistan', 'tashkent', 'samarkand', 'kenya', 'nairobi', 'masai mara',
    'south africa', 'cape town', 'johannesburg', 'australia', 'sydney', 'melbourne', 'new zealand',
    'auckland', 'usa', 'america', 'new york', 'california', 'canada', 'toronto', 'vancouver',
    'japan', 'tokyo', 'kyoto', 'osaka', 'korea', 'south korea', 'seoul', 'greece', 'athens',
    'santorini', 'italy', 'rome', 'florence', 'venice', 'spain', 'madrid', 'barcelona',
    'sweden', 'stockholm', 'norway', 'oslo', 'denmark', 'copenhagen', 'finland', 'helsinki',
    'cambodia', 'siem reap', 'angkor wat', 'saudi arabia', 'riyadh', 'jeddah', 'mecca', 'medina',
    'israel', 'jerusalem', 'tel aviv', 'jordan', 'amman', 'petra', 'myanmar', 'yangon',
    'afghanistan', 'czech', 'prague', 'malta', 'cyprus', 'iran', 'tehran', 'trinidad',
    'tobago', 'peru', 'lima', 'namibia', 'windhoek', 'zanzibar', 'tanzania', 'kilimanjaro',
    'seychelles', 'fiji', 'hong kong', 'macau', 'taiwan', 'philippines', 'manila', 'boracay',
    'austria', 'vienna', 'germany', 'berlin', 'munich', 'netherlands', 'amsterdam', 'belgium',
    'brussels', 'hungary', 'budapest', 'portugal', 'lisbon', 'ireland', 'dublin', 'morocco',
    'brazil', 'argentina', 'russia', 'moscow', 'china', 'beijing', 'shanghai'
]

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
    'ranakpur jain', 'dilwara jain', 'palitana', 'girnar', 'shikharji', 'shravanabelagola'
]

HILL_STATION_KEYWORDS = [
    'ooty', 'kodaikanal', 'munnar', 'coorg', 'wayanad', 'chikmagalur', 'yercaud',
    'kolli hills', 'yelagiri', 'valparai', 'vagamon', 'thekkady', 'manali', 'shimla',
    'dharamshala', 'dalhousie', 'nainital', 'mussoorie', 'kasauli', 'darjeeling',
    'gangtok', 'shillong', 'cherrapunji', 'tawang', 'mahabaleshwar', 'lonavala',
    'khandala', 'panchgani', 'matheran', 'mount abu', 'spiti', 'leh', 'ladakh',
    'kashmir', 'srinagar', 'gulmarg', 'pahalgam', 'sonamarg', 'chamoli', 'almora',
    'ranikhet', 'lansdowne', 'kanatal', 'chopta', 'aulii', 'auli', 'pelling',
    'lachung', 'lachen', 'kalimpong', 'kurseong', 'mirik', 'haflong', 'dima hasao',
    'saputara', 'chail', 'kufri', 'solan', 'mashobra', 'narkanda', 'bir billing',
    'palampur', 'mcleodganj', 'kasol', 'tirthan valley', 'jibhi', 'kinnaur',
    'kalpa', 'sangla', 'chitkul', 'kaza', 'keylong', 'jispa', 'nubra valley',
    'pangong lake', 'tsomoriri', 'zanskar', 'kargil', 'drass'
]

CORPORATE_KEYWORDS = [
    'corporate', 'leadership retreat', 'executive retreat', 'team offsite', 'team building',
    'annual outing', 'corporate conclave', 'strategy offsite', 'corporate beachside summit'
]

COLLEGE_IV_KEYWORDS = [
    'college iv', 'industrial visit', 'iv expedition', 'students tour', 'educational tour',
    'school tour', 'college tour', 'iv tour', 'mega iv', 'college industrial', 'campus tour'
]

FIXED_DEPARTURE_KEYWORDS = [
    'fixed departure', 'group departure', 'scheduled departure', 'convoy departure'
]

LOCAL_TOUR_KEYWORDS = [
    'local sightseeing', 'city sightseeing', '1-day local', 'one day local',
    'chennai local', 'city tour', 'half day tour', 'outside city sightseeing',
    'sightseeing day tour', 'day trip', 'day outing'
]

reclass_counts = defaultdict(int)
reclass_details = defaultdict(list)

def detect_best_category(pkg):
    name_lower = pkg.name.lower()
    dest_lower = pkg.destination.lower() if pkg.destination else ''
    desc_lower = pkg.description.lower() if pkg.description else ''
    full_text = f"{name_lower} {dest_lower} {desc_lower}"
    title_dest = f"{name_lower} {dest_lower}"

    # 1. Corporate Offsite Check
    if any(kw in title_dest for kw in CORPORATE_KEYWORDS):
        return 'corporate_offsite', 'Corporate keywords matched'

    # 2. College IV / Educational Check
    if any(kw in title_dest for kw in COLLEGE_IV_KEYWORDS):
        return 'college_iv', 'College IV keywords matched'

    # 3. International Check
    # Check if foreign country / visa assistance
    is_visa = 'visa' in title_dest or 'visa assistance' in dest_lower
    has_foreign_dest = any(re.search(r'\b' + re.escape(kw) + r'\b', title_dest) for kw in INTL_COUNTRIES)
    if is_visa or has_foreign_dest or pkg.is_international:
        # Check if it was falsely marked as foreign when it's clearly domestic
        # e.g., "Madurai to Tiruchendur" or "Chennai to Ooty"
        domestic_places = ['tamil nadu', 'kerala', 'karnataka', 'andhra', 'telangana', 'himachal', 'kashmir', 'ladakh', 'rajasthan', 'goa', 'uttarakhand', 'maharashtra', 'odisha', 'sikkim', 'assam', 'meghalaya', 'chennai', 'coimbatore', 'madurai', 'ooty', 'kodaikanal', 'munnar', 'tirupati']
        is_pure_domestic = any(re.search(r'\b' + re.escape(dp) + r'\b', title_dest) for dp in domestic_places) and not has_foreign_dest and not is_visa
        if not is_pure_domestic:
            return 'international', 'International destination/visa'

    # 4. Devotional / Pilgrimage Check
    # Check if temple / pilgrimage circuit
    has_devotional = any(re.search(r'\b' + re.escape(kw) + r'\b', title_dest) for kw in DEVOTIONAL_KEYWORDS)
    if has_devotional or pkg.is_devotional or pkg.category in ['devotional', 'pilgrimage']:
        # If it's pure temple darshan, categorize as devotional
        # (even if 1-day, devotional packages have temple darshan slots, pooja timings, etc.)
        return 'devotional', 'Devotional / Temple pilgrimage circuit'

    # 5. Local 1-Day Tour Check
    # If duration is 1 day and non-devotional, non-international
    if (pkg.duration_days == 1 or pkg.duration_nights == 0) and any(kw in title_dest for kw in LOCAL_TOUR_KEYWORDS):
        return 'local_tour', '1-Day local sightseeing / city tour'

    # 6. Hill Station Check
    has_hill = any(re.search(r'\b' + re.escape(kw) + r'\b', title_dest) for kw in HILL_STATION_KEYWORDS)
    if has_hill:
        return 'hill_station', 'Hill station destination'

    # 7. Fixed Departure Check
    if any(kw in title_dest for kw in FIXED_DEPARTURE_KEYWORDS):
        return 'fixed_departure', 'Fixed departure convoy'

    # 8. Family Vacation / Leisure / Theme Park
    family_keywords = ['theme park', 'black thunder', 'wonderla', 'family vacation', 'family trip', 'custom vacation', 'leisure']
    if any(kw in title_dest for kw in family_keywords):
        return 'family_vacation', 'Family vacation / theme park / leisure'

    # 9. Fallback to existing or Holiday
    if pkg.category in ['holiday', 'family_vacation', 'local_tour']:
        return pkg.category, 'Retain existing category'
    
    # If currently hill_station but has no hill keywords, check if it's general holiday (beaches, wildlife, heritage)
    if pkg.category == 'hill_station' and not has_hill:
        return 'holiday', 'Non-hill station getaway (beach/heritage/wildlife)'

    return pkg.category, 'Retain existing'

# Run audit on all packages
changed_count = 0
for pkg in Package.objects.all():
    target_cat, reason = detect_best_category(pkg)
    if target_cat != pkg.category:
        changed_count += 1
        reclass_counts[f"{pkg.category} -> {target_cat}"] += 1
        if len(reclass_details[f"{pkg.category} -> {target_cat}"]) < 5:
            reclass_details[f"{pkg.category} -> {target_cat}"].append((pkg.id, pkg.package_code, pkg.name, pkg.destination, reason))

print(f"\nTotal packages that will be reclassified: {changed_count} / {Package.objects.count()}")
print("\nReclassification breakdown:")
for shift, count in sorted(reclass_counts.items(), key=lambda x: -x[1]):
    print(f"\n  {shift}: {count} packages")
    for sample in reclass_details[shift]:
        print(f"     [{sample[0]}] {sample[1]}: {sample[2]} (Dest: {sample[3]}) -> Reason: {sample[4]}")

print("\n" + "=" * 80)
