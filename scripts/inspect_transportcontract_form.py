import os
import sys
import django
import re

sys.path.insert(0, os.path.abspath('.'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model

client = Client()
user = get_user_model().objects.get(username='rithik')
client.force_login(user)

resp = client.get('/admin/fleet_contracts/transportcontract/add/')
print('Status:', resp.status_code)
html = resp.content.decode('utf-8')
print('Has jazzy-tabs:', 'jazzy-tabs' in html)

tabs = re.findall(r'<a class="nav-link[^"]*"[^>]*href="([^"]*)"[^>]*>(.*?)</a>', html)
print('Found tabs:', len(tabs))
for h, t in tabs:
    clean_title = re.sub(r'<[^>]+>', '', t).strip()
    print('  Tab href:', h, '->', clean_title)

panes = re.findall(r'<div class="tab-pane[^"]*" id="([^"]*)"', html)
print('Found tab panes:', len(panes), panes)

# Check what scripts are included on the page
scripts = re.findall(r'<script[^>]*src="([^"]*)"', html)
print('\nScripts on page:')
for s in scripts:
    print('  ', s)
