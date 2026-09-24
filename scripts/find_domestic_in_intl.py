import os
import sys
import re
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
django.setup()
sys.stdout.reconfigure(encoding='utf-8')

from packages.models import Package

INTL_COUNTRIES = [
    'dubai', 'uae', 'abu dhabi', 'sharjah', 'singapore', 'malaysia', 'kuala lumpur', 'genting',
    'thailand', 'bangkok', 'pattaya', 'phuket', 'krabi', 'bali', 'indonesia', 'sri lanka',
    'colombo', 'kandy', 'bentota', 'nuwara eliya', 'maldives', 'vietnam', 'hanoi', 'da nang',
    'ho chi minh', 'nepal', 'kathmandu', 'pokhara', 'bhutan', 'thimphu', 'paro', 'mauritius',
    'turkey', 'istanbul', 'cappadocia', 'egypt', 'cairo', 'alexandria', 'paris', 'france',
    'switzerland', 'zurich', 'lucerne', 'interlaken', 'europe', 'london', 'united kingdom',
    'england', 'scotland', 'edinburgh', 'georgia', 'tbilisi', 'baku', 'azerbaijan', 'kazakhstan',
    'almaty', 'astana', 'uzbekistan', 'tashkent', 'samarkand', 'kenya', 'nairobi', 'masai mara',
    'south africa', 'cape town', 'johannesburg', 'australia', 'sydney', 'melbourne', 'new zealand',
    'auckland', 'usa', 'america', 'new york', 'california', 'canada', 'toronto', 'vancouver',
    'japan', 'tokyo', 'kyoto', 'osaka', 'korea', 'south korea', 'seoul', 'greece', 'athens',
    'santorini', 'italy', 'rome', 'florence', 'venice', 'spain', 'madrid', 'barcelona',
    'sweden', 'stockholm', 'norway', 'oslo', 'denmark', 'copenhagen', 'finland', 'helsinki',
    'cambodia', 'siem reap', 'angkor wat', 'saudi arabia', 'riyadh', 'jeddah', 'mecca', 'medina',
    'israel', 'jerusalem', 'tel aviv', 'jordan', 'petra', 'myanmar', 'yangon',
    'afghanistan', 'czech', 'prague', 'malta', 'cyprus', 'iran', 'tehran', 'trinidad',
    'tobago', 'peru', 'lima', 'namibia', 'windhoek', 'zanzibar', 'tanzania', 'kilimanjaro',
    'seychelles', 'fiji', 'hong kong', 'macau', 'taiwan', 'philippines', 'manila', 'boracay',
    'austria', 'vienna', 'germany', 'berlin', 'munich', 'netherlands', 'amsterdam', 'belgium',
    'brussels', 'hungary', 'budapest', 'portugal', 'lisbon', 'ireland', 'dublin', 'morocco',
    'brazil', 'argentina', 'russia', 'moscow', 'china', 'beijing', 'shanghai'
]

print("=== Checking all packages with category='international' or is_international=True ===")
intl_pkgs = Package.objects.filter(category='international')
print(f"Total category='international': {intl_pkgs.count()}")

domestic_misclassified = []
for p in intl_pkgs:
    title_dest = f"{p.name} {p.destination} {p.description}".lower()
    # Check for genuine foreign country match
    # Exclude "switzerland of india"
    title_dest_clean = title_dest.replace("switzerland of india", "")
    has_foreign = any(re.search(r'\b' + re.escape(kw) + r'\b', title_dest_clean) for kw in INTL_COUNTRIES)
    is_visa = 'visa' in title_dest
    if not has_foreign and not is_visa:
        domestic_misclassified.append(p)

print(f"\nFound {len(domestic_misclassified)} domestic packages wrongly in 'international':")
for p in domestic_misclassified:
    print(f"[{p.id}] {p.package_code}: {p.name} | Dest: {p.destination}")
