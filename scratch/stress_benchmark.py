import os
import sys
import time
import statistics
import concurrent.futures

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')

import django
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from operations.models import Trip, Booking
from fleet_commute.models import CommuterBoardingPass
from core.models import Vehicle

def run_stress_test(name, task_fn, iterations=100, concurrency=10):
    """
    Executes a high-concurrency stress test measuring RPS, p50, p95, and p99 latency.
    """
    latencies_ms = []
    successes = 0
    failures = 0

    t_start = time.perf_counter()

    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(task_fn) for _ in range(iterations)]
        for f in concurrent.futures.as_completed(futures):
            try:
                duration_ms, status_code = f.result()
                if 200 <= status_code < 400:
                    successes += 1
                    latencies_ms.append(duration_ms)
                else:
                    failures += 1
            except Exception as e:
                failures += 1

    total_time = time.perf_counter() - t_start
    rps = iterations / total_time if total_time > 0 else 0

    latencies_ms.sort()
    avg_ms = statistics.mean(latencies_ms) if latencies_ms else 0
    p50_ms = latencies_ms[int(len(latencies_ms) * 0.50)] if latencies_ms else 0
    p95_ms = latencies_ms[min(int(len(latencies_ms) * 0.95), len(latencies_ms) - 1)] if latencies_ms else 0
    p99_ms = latencies_ms[min(int(len(latencies_ms) * 0.99), len(latencies_ms) - 1)] if latencies_ms else 0

    print(f"\n⚡ [{name.upper()}] (Iterations: {iterations}, Concurrency: {concurrency})")
    print("-" * 65)
    print(f"  • Throughput:        {rps:8.1f} Requests/Second (RPS)")
    print(f"  • Average Latency:   {avg_ms:8.2f} ms")
    print(f"  • Median (p50):      {p50_ms:8.2f} ms")
    print(f"  • 95th Percentile:   {p95_ms:8.2f} ms")
    print(f"  • 99th Percentile:   {p99_ms:8.2f} ms")
    print(f"  • Success Rate:      {(successes / iterations) * 100:.1f}% ({successes} OK, {failures} Err)")

    return {
        "name": name,
        "rps": rps,
        "avg_ms": avg_ms,
        "p50_ms": p50_ms,
        "p95_ms": p95_ms,
        "p99_ms": p99_ms,
        "success_rate": (successes / iterations) * 100
    }

print("=" * 70)
print("🚀 TRAVELERP PRODUCTION ARCHITECTURE STRESS & LATENCY BENCHMARK")
print("=" * 70)

# Setup Test Client & Session
user = User.objects.filter(is_superuser=True).first()
trip = Trip.objects.first()
bp = CommuterBoardingPass.objects.first()
vehicle = Vehicle.objects.first()

def make_client():
    c = Client()
    if user:
        c.force_login(user)
    return c

# 1. Landing Page (Static delivery + HTML)
def test_landing_page():
    c = make_client()
    t0 = time.perf_counter()
    resp = c.get('/')
    duration = (time.perf_counter() - t0) * 1000.0
    return duration, resp.status_code

# 2. In-Memory Master Data API
def test_master_data_api():
    c = make_client()
    t0 = time.perf_counter()
    resp = c.get('/api/vehicle-types/')
    duration = (time.perf_counter() - t0) * 1000.0
    return duration, resp.status_code

# 3. Live Telematics Polling API (RAM Cache hit)
token = bp.pass_token if bp else "demo_token"
def test_telematics_live():
    c = make_client()
    t0 = time.perf_counter()
    resp = c.get(f'/commute/api/track/{token}/live/')
    duration = (time.perf_counter() - t0) * 1000.0
    return duration, resp.status_code

# 4. CRM Live Kanban Data API (Composite Index optimized)
def test_crm_kanban():
    c = make_client()
    t0 = time.perf_counter()
    resp = c.get('/crm/api/kanban-data/')
    duration = (time.perf_counter() - t0) * 1000.0
    return duration, resp.status_code

# 5. In-Memory ReportLab PDF Retrieval
trip_id = trip.id if trip else 1
def test_pdf_cache_retrieval():
    c = make_client()
    t0 = time.perf_counter()
    resp = c.get(f'/trips/{trip_id}/pdf/trip-sheet/')
    duration = (time.perf_counter() - t0) * 1000.0
    return duration, resp.status_code

# Prime caches before running concurrent stress
c_prime = make_client()
c_prime.get('/api/vehicle-types/')
c_prime.get(f'/trips/{trip_id}/pdf/trip-sheet/')

# Run Stress Test Suite
results = []
results.append(run_stress_test("Master Data API (RAM Caching)", test_master_data_api, iterations=150, concurrency=12))
results.append(run_stress_test("Live GPS Telematics (Zero-Disk Cache)", test_telematics_live, iterations=150, concurrency=12))
results.append(run_stress_test("CRM Kanban API (Single Composite Query)", test_crm_kanban, iterations=100, concurrency=8))
results.append(run_stress_test("Trip Sheet PDF (In-Memory Binary)", test_pdf_cache_retrieval, iterations=100, concurrency=8))
results.append(run_stress_test("Public Portal / Landing Page", test_landing_page, iterations=80, concurrency=6))

print("\n" + "=" * 70)
print("🏆 BENCHMARK SUMMARY TABLE")
print("=" * 70)
print(f"{'Endpoint':<35} | {'RPS':<8} | {'Avg (ms)':<9} | {'p95 (ms)':<9} | {'Success':<7}")
print("-" * 75)
for r in results:
    print(f"{r['name']:<35} | {r['rps']:<8.1f} | {r['avg_ms']:<9.2f} | {r['p95_ms']:<9.2f} | {r['success_rate']:<6.1f}%")
print("=" * 70)
