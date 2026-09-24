import json
import re

urls = json.load(open('scripts/holidify_package_urls.json', encoding='utf-8'))
print(f"Total package listing URLs: {len(urls)}")

south_keywords = [
    'kerala', 'alleppey', 'munnar', 'thekkady', 'wayanad', 'kochi', 'cochin', 'kovalam', 'varkala', 'kumarakom', 'poovar',
    'ooty', 'kodaikanal', 'tamil-nadu', 'tamilnadu', 'chennai', 'madurai', 'rameshwaram', 'kanyakumari', 'coimbatore', 'yercaud',
    'coorg', 'karnataka', 'mysore', 'hampi', 'gokarna', 'chikmagalur', 'bangalore', 'bengaluru', 'kabini', 'bandipur', 'dandeli',
    'andhra', 'tirupati', 'araku', 'vizag', 'hyderabad', 'telangana', 'pondicherry', 'pondi', 'lakshadweep', 'south-india'
]

north_keywords = [
    'himachal', 'shimla', 'manali', 'dharamshala', 'dalhousie', 'kasol', 'spiti', 'kullu', 'kaza',
    'uttarakhand', 'rishikesh', 'haridwar', 'mussoorie', 'nainital', 'auli', 'kedarnath', 'badrinath', 'corbett', 'dehradun',
    'kashmir', 'srinagar', 'gulmarg', 'pahalgam', 'ladakh', 'leh',
    'rajasthan', 'jaipur', 'udaipur', 'jodhpur', 'jaisalmer', 'pushkar', 'mount-abu', 'ranthambore',
    'delhi', 'agra', 'golden-triangle', 'varanasi', 'kashi', 'ayodhya', 'mathura', 'amritsar', 'north-india'
]

intl_keywords = [
    'dubai', 'singapore', 'malaysia', 'thailand', 'bangkok', 'pattaya', 'phuket', 'bali', 'indonesia', 'vietnam', 'cambodia',
    'maldives', 'mauritius', 'seychelles', 'sri-lanka', 'bhutan', 'nepal', 'europe', 'switzerland', 'paris', 'london', 'africa',
    'cape-town', 'kenya', 'turkey', 'greece', 'egypt', 'baku', 'georgia', 'almaty', 'international'
]

south = []
north = []
other_india = []
intl = []

for u in urls:
    u_lower = u.lower()
    if any(k in u_lower for k in south_keywords):
        south.append(u)
    elif any(k in u_lower for k in north_keywords):
        north.append(u)
    elif any(k in u_lower for k in intl_keywords):
        intl.append(u)
    else:
        other_india.append(u)

print(f"\n1. SOUTH INDIA LISTINGS: {len(south)}")
for u in south:
    print("  ", u.split('/')[-1])

print(f"\n2. NORTH INDIA LISTINGS: {len(north)}")
for u in north[:20]:
    print("  ", u.split('/')[-1])
print(f"   ... and {len(north)-20} more North India listings")

print(f"\n3. OTHER INDIA LISTINGS (Goa, Andaman, Sikkim, Darjeeling, Northeast, etc.): {len(other_india)}")
for u in other_india:
    print("  ", u.split('/')[-1])

print(f"\n4. INTERNATIONAL LISTINGS: {len(intl)}")
for u in intl[:10]:
    print("  ", u.split('/')[-1])
