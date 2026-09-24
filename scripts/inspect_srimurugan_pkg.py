import urllib.request
import re
from bs4 import BeautifulSoup

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

urls = [
    'https://www.srimurugantravel.com/domestic/ayodhya-ram-mandir-special',
    'https://www.srimurugantravel.com/train/udupi-murudeswarar-kollur-dharmasthala---kukke',
    'https://www.srimurugantravel.com/international/dubai-abudhabi'
]

for url in urls:
    print('='*70)
    print('FETCHING:', url)
    try:
        req = urllib.request.Request(url, headers=headers)
        html = urllib.request.urlopen(req, timeout=15).read().decode('utf-8', errors='ignore')
        soup = BeautifulSoup(html, 'html.parser')
        print('Title tag:', soup.title.string if soup.title else '')
        h1 = soup.find(['h1', 'h2'])
        print('Heading (H1/H2):', h1.text.strip() if h1 else 'None')
        
        # Look for duration, nights, days
        dur = soup.find(text=re.compile(r'Days?|Nights?', re.I))
        if dur:
            print('Duration snippet:', dur.parent.text.strip()[:100])

        # Look for price
        price = soup.find(text=re.compile(r'₹|Rs\.?', re.I))
        if price:
            print('Price snippet:', price.parent.text.strip()[:100])

        # Look for itinerary / day elements
        days = soup.find_all(text=re.compile(r'Day\s*\d+', re.I))
        print('Day mentions found:', len(days))
        for d in days[:5]:
            p = d.parent
            print('  Day element:', p.name, p.text.strip()[:120].replace('\n', ' '))

        # Look for inclusions / exclusions
        inc = soup.find(text=re.compile(r'Inclusion', re.I))
        if inc:
            print('Inclusion container:', inc.parent.parent.text.strip()[:200].replace('\n', ' '))

        # Look for images
        imgs = [img.get('src') for img in soup.find_all('img') if img.get('src') and not any(k in img.get('src').lower() for k in ['logo', 'icon', 'arrow', 'banner'])]
        print('Content images:', imgs[:5])
    except Exception as e:
        print('Error:', e)
