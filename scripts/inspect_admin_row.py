import os, sys, django
sys.path.insert(0, os.path.abspath('.'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
django.setup()
from django.test import Client
from django.contrib.auth import get_user_model
import re

User = get_user_model()
admin_user = User.objects.filter(is_superuser=True).first()
c = Client()
c.force_login(admin_user)
resp = c.get('/admin/crm/supplierservicevoucher/')
html = resp.content.decode('utf-8')
m = re.search(r'<style[^>]*id="unfold-theme-colors"[^>]*>(.*?)</style>', html, re.DOTALL)
if m:
    print(m.group(1))
