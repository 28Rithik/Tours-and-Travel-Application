import os
import sys
import time
import django

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from django.db import connection, reset_queries

User = get_user_model()
admin = User.objects.filter(is_superuser=True).first()

client = Client()
client.force_login(admin)

print("Benchmarking /analytics/fleet/ view...")
reset_queries()
t0 = time.time()
resp = client.get('/analytics/fleet/')
t1 = time.time()
print(f"Status: {resp.status_code} | Time: {(t1-t0)*1000:.2f}ms | Queries: {len(connection.queries)}")

reset_queries()
t0 = time.time()
resp_repeat = client.get('/analytics/fleet/')
t1 = time.time()
print(f"Repeat /analytics/fleet/ -> Status: {resp_repeat.status_code} | Time: {(t1-t0)*1000:.2f}ms | Queries: {len(connection.queries)}")

print("\nBenchmarking /analytics/dashboard/ view (package profitability)...")
reset_queries()
t0 = time.time()
resp2 = client.get('/analytics/dashboard/')
t1 = time.time()
print(f"Status: {resp2.status_code} | Time: {(t1-t0)*1000:.2f}ms | Queries: {len(connection.queries)}")
