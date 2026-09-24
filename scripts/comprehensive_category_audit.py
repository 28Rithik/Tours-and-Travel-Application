import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
django.setup()
sys.stdout.reconfigure(encoding='utf-8')

from packages.models import Package
from django.db.models import Q, Count

print("=" * 80)
print("COMPREHENSIVE PACKAGE CATEGORY & CLASSIFICATION AUDIT")
print("=" * 80)

total_pkgs = Package.objects.count()
print(f"Total Packages: {total_pkgs}")

# 1. Check International vs Domestic
intl_keywords = [
    'dubai', 'singapore', 'malaysia', 'thailand', 'bangkok', 'pattaya', 'phuket',
    'bali', 'indonesia', 'sri lanka', 'colombo', 'kandy', 'maldives', 'vietnam',
    'nepal', 'kathmandu', 'bhutan', 'thimphu', 'mauritius', 'turkey', 'istanbul',
    'egypt', 'cairo', 'paris', 'france', 'switzerland', 'zurich', 'europe',
    'london', 'uk', 'united kingdom', 'scotland', 'georgia', 'tbilisi', 'baku',
    'azerbaijan', 'kazakhstan', 'almaty', 'uzbekistan', 'tashkent', 'kenya',
    'south africa', 'australia', 'sydney', 'new zealand', 'usa', 'america',
    'canada', 'japan', 'tokyo', 'korea', 'seoul', 'greece', 'athens', 'italy', 'rome'
]

# Domestic keywords/places that are definitely NOT international
domestic_keywords = [
    'tamil nadu', 'tamilnadu', 'chennai', 'coimbatore', 'madurai', 'trichy', 'salem',
    'ooty', 'kodaikanal', 'kerala', 'kochi', 'munnar', 'alleppey', 'wayanad', 'thekkady',
    'karnataka', 'bangalore', 'bengaluru', 'mysore', 'coorg', 'hampi', 'chikmagalur',
    'andhra', 'tirupati', 'vijayawada', 'visakhapatnam', 'hyderabad', 'telangana',
    'goa', 'maharashtra', 'mumbai', 'pune', 'shirdi', 'mahabaleshwar', 'lonavala',
    'rajasthan', 'jaipur', 'udaipur', 'jodhpur', 'jaisalmer', 'pushkar',
    'delhi', 'agra', 'uttar pradesh', 'varanasi', 'kashi', 'ayodhya', 'mathura', 'vrindavan',
    'uttarakhand', 'rishikesh', 'haridwar', 'nainital', 'mussoorie', 'kedarnath', 'badrinath',
    'himachal', 'shimla', 'manali', 'dharamshala', 'dalhousie', 'spiti',
    'kashmir', 'srinagar', 'gulmarg', 'pahalgam', 'ladakh', 'leh',
    'punjab', 'amritsar', 'golden temple',
    'west bengal', 'kolkata', 'darjeeling', 'sikkim', 'gangtok',
    'odisha', 'puri', 'bhubaneswar', 'konark',
    'assam', 'guwahati', 'meghalaya', 'shillong',
    'andaman', 'port blair', 'havelock', 'neil island'
]

# Find domestic packages marked as international
intl_pkgs = Package.objects.filter(Q(category='international') | Q(is_international=True))
print(f"\n1. Packages marked as International: {intl_pkgs.count()}")

domestic_in_intl = []
for p in intl_pkgs:
    text = f"{p.name} {p.destination} {p.description}".lower()
    # check if has foreign keyword
    has_foreign = any(kw in text for kw in intl_keywords)
    # check if has domestic keyword
    has_domestic = any(kw in text for kw in domestic_keywords)
    if has_domestic and not has_foreign:
        domestic_in_intl.append((p.id, p.package_code, p.name, p.destination))

print(f"   --> Found {len(domestic_in_intl)} domestic packages erroneously marked as International!")
for item in domestic_in_intl[:10]:
    print(f"       [{item[0]}] {item[1]}: {item[2]} | Dest: {item[3]}")

# Find international packages NOT marked as international
non_intl_pkgs = Package.objects.exclude(category='international').filter(is_international=False)
intl_in_domestic = []
for p in non_intl_pkgs:
    text = f"{p.name} {p.destination} {p.description}".lower()
    # Check if matches foreign keywords and not merely mentioning it
    has_foreign = any(kw in f"{p.name} {p.destination}".lower() for kw in intl_keywords)
    if has_foreign:
        intl_in_domestic.append((p.id, p.package_code, p.name, p.destination, p.category))

print(f"\n2. International packages NOT categorized as International: {len(intl_in_domestic)}")
for item in intl_in_domestic[:10]:
    print(f"       [{item[0]}] {item[1]}: {item[2]} | Dest: {item[3]} | Current Cat: {item[4]}")

# 3. Devotional & Pilgrimage Check
devotional_keywords = [
    'temple', 'darshan', 'pilgrimage', 'divine', 'spiritual', 'jyotirlinga', 'jyotirling',
    'tirupati', 'balaji', 'shirdi', 'kashi', 'varanasi', 'rameswaram', 'rameshwaram',
    'madurai meenakshi', 'meenakshi temple', 'chidambaram', 'thanjavur big temple',
    'brihadeeswarar', 'srirangam', 'palani', 'tiruchendur', 'swamimalai', 'thiruthani',
    'pazhamudircholai', 'arupadai veedu', 'navagraha', 'divya desam', 'divyadesam',
    'kedarnath', 'badrinath', 'char dham', 'chardham', 'amarnath', 'vaishno devi',
    'haridwar', 'rishikesh', 'somnath', 'dwarka', 'mahakaleshwar', 'omkareshwar',
    'trimbakeshwar', 'grishneshwar', 'bhimashankar', 'mallikarjuna', 'srisailam',
    'kalahasti', 'kanchipuram', 'kumbakonam', 'velankanni', 'nagore', 'golden temple amritsar',
    'guruvayur', 'sabarimala', 'padmanabhaswamy', 'murudeshwar', 'kukke subramanya',
    'dharmasthala', 'horanadu', 'sringeri', 'udupi krishna', 'kollur mookambika'
]

dev_pkgs = Package.objects.filter(Q(category__in=['devotional', 'pilgrimage']) | Q(is_devotional=True))
print(f"\n3. Packages currently marked as Devotional/Pilgrimage: {dev_pkgs.count()}")

dev_in_other = []
for p in Package.objects.exclude(category__in=['devotional', 'pilgrimage', 'international']):
    title_dest = f"{p.name} {p.destination}".lower()
    matches = [kw for kw in devotional_keywords if kw in title_dest]
    if len(matches) >= 1:
        dev_in_other.append((p.id, p.package_code, p.name, p.destination, p.category, matches))

print(f"   --> Found {len(dev_in_other)} packages with Temple/Pilgrimage content marked as other categories ({set(x[4] for x in dev_in_other)})!")
for item in dev_in_other[:10]:
    print(f"       [{item[0]}] {item[1]}: {item[2]} | Cat: {item[4]} | Matched: {item[5]}")

# 4. Hill Station vs Beach vs Plains / Heritage
hill_station_keywords = [
    'ooty', 'kodaikanal', 'munnar', 'coorg', 'wayanad', 'chikmagalur', 'yercaud',
    'kolli hills', 'yelagiri', 'valparai', 'vagamon', 'manali', 'shimla', 'dharamshala',
    'dalhousie', 'nainital', 'mussoorie', 'kasauli', 'darjeeling', 'gangtok', 'shillong',
    'cherrapunji', 'tawang', 'mahabaleshwar', 'lonavala', 'khandala', 'panchgani',
    'matheran', 'mount abu', 'spiti', 'leh', 'ladakh', 'kashmir', 'srinagar', 'gulmarg',
    'pahalgam', 'sonamarg', 'arunachal', 'chamoli', 'almora', 'ranikhet', 'lansdowne'
]

hill_pkgs = Package.objects.filter(category='hill_station')
print(f"\n4. Packages currently categorized as 'hill_station': {hill_pkgs.count()}")
not_hills_in_hill = []
for p in hill_pkgs:
    title_dest = f"{p.name} {p.destination}".lower()
    has_hill = any(kw in title_dest for kw in hill_station_keywords)
    if not has_hill:
        not_hills_in_hill.append((p.id, p.package_code, p.name, p.destination))

print(f"   --> {len(not_hills_in_hill)} packages in 'hill_station' do not match known hill station keywords!")
for item in not_hills_in_hill[:10]:
    print(f"       [{item[0]}] {item[1]}: {item[2]} | Dest: {item[3]}")

# 5. Local 1-Day Tours (duration_days == 1 or duration_nights == 0)
one_day_pkgs = Package.objects.filter(Q(duration_days=1) | Q(duration_nights=0))
print(f"\n5. Total 1-Day packages (duration_days=1 or duration_nights=0): {one_day_pkgs.count()}")
one_day_cat_counts = one_day_pkgs.values('category').annotate(count=Count('id')).order_by('-count')
for item in one_day_cat_counts:
    print(f"   - {item['category']}: {item['count']}")

# 6. College IV & Industrial Visits
iv_keywords = ['college iv', 'industrial visit', 'iv tour', 'students tour', 'educational tour', 'school tour', 'college tour']
iv_pkgs = Package.objects.filter(category='college_iv')
print(f"\n6. Total College IV packages: {iv_pkgs.count()}")
iv_in_other = []
for p in Package.objects.exclude(category='college_iv'):
    text = f"{p.name} {p.destination} {p.description}".lower()
    if any(kw in text for kw in iv_keywords):
        iv_in_other.append((p.id, p.package_code, p.name, p.category))
print(f"   --> Found {len(iv_in_other)} IV packages categorized elsewhere: {iv_in_other}")

# 7. Consolidation of 'pilgrimage' vs 'devotional'
pilg_count = Package.objects.filter(category='pilgrimage').count()
dev_count = Package.objects.filter(category='devotional').count()
print(f"\n7. 'pilgrimage' count: {pilg_count} vs 'devotional' count: {dev_count}")
print("=" * 80)
