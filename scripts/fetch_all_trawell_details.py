import os
import sys
import time
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

sys.stdout.reconfigure(encoding='utf-8')

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
    'service_key': '3b91cab8-926f-49b6-ba00-920bcf934c2a',
    'Origin': 'https://www.trawell.in',
    'Referer': 'https://www.trawell.in/tour-packages'
}

def fetch_details(code):
    url = f"https://www.trawell.in/user-services/rest/customer/get-tour-details/{code}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code == 200:
            return code, r.json()
    except Exception as e:
        pass
    return code, None

def main():
    print("=" * 70, flush=True)
    print("FETCHING FULL DETAILS FOR ALL 1,369 TRAWELL TOURS VIA REST API", flush=True)
    print("=" * 70, flush=True)

    with open('scripts/trawell_all_api_tours.json', 'r', encoding='utf-8') as f:
        all_tours = json.load(f)

    cache_path = 'scripts/trawell_all_details_cache.json'
    cached_details = {}
    if os.path.exists(cache_path):
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                cached_details = json.load(f)
            print(f"Loaded {len(cached_details)} previously cached details.", flush=True)
        except Exception:
            cached_details = {}

    to_fetch = [code for code in all_tours.keys() if code not in cached_details]
    print(f"Remaining details to fetch: {len(to_fetch)}", flush=True)

    if to_fetch:
        done = 0
        total = len(to_fetch)
        t0 = time.time()
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = {executor.submit(fetch_details, code): code for code in to_fetch}
            for f in as_completed(futures):
                code, details = f.result()
                if details:
                    cached_details[code] = details
                done += 1
                if done % 100 == 0 or done == total:
                    elapsed = time.time() - t0
                    rate = done / max(elapsed, 0.001)
                    print(f"Progress: {done}/{total} fetched ({done/total*100:.1f}%) | {rate:.1f} req/s | Success: {len(cached_details)}", flush=True)

        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(cached_details, f, indent=2)
        print(f"Saved {len(cached_details)} details to {cache_path}", flush=True)

    print("=" * 70, flush=True)
    print(f"ALL DETAILS FETCH COMPLETE! Total in cache: {len(cached_details)}", flush=True)
    print("=" * 70, flush=True)

if __name__ == '__main__':
    main()
