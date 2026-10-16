import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
django.setup()
from django.test import Client
from django.contrib.auth import get_user_model
from bs4 import BeautifulSoup

User = get_user_model()
admin = User.objects.filter(is_superuser=True).first()
c = Client()
c.force_login(admin)
resp = c.get('/analytics/fleet/')
html = resp.content.decode('utf-8')
soup = BeautifulSoup(html, 'html.parser')

with open('non_ascii_results.txt', 'w', encoding='utf-8') as out:
    for el in soup.find_all(True):
        for child in el.children:
            if isinstance(child, str) and child.strip():
                non_ascii = [ch for ch in child if ord(ch) > 127]
                if non_ascii:
                    s = ''.join(non_ascii)
                    if not any(k in s for k in ['₹', '·', '©', '–', '—', '…', '↑', '↓', '→', '&', '▾', '✓']):
                        items = [f"U+{ord(c):04X}" for c in s]
                        out.write(f"<{el.name} class='{el.get('class')}'> text='{child.strip()[:30]}' chars={items}\n")
print("Done writing non_ascii_results.txt")
