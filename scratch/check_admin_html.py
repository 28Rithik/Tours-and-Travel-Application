import os
import sys
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
import django
django.setup()

from django.test import Client
from django.contrib.auth.models import User

user = User.objects.filter(is_superuser=True).first()
client = Client()
client.force_login(user)

response = client.get('/admin/core_crew/driver/')
html = response.content.decode('utf-8')

lines = html.splitlines()
print("\n--- Lines 20 to 85 of HTML (<head> and scripts) ---")
for i, line in enumerate(lines[20:85], start=21):
    print(f"Line {i}: {line}")
