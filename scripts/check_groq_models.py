import os
import sys
from pathlib import Path
import json
import requests

# Set stdout to UTF-8 to avoid Windows charmap encoding errors
sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

os.environ['DJANGO_SETTINGS_MODULE'] = 'travelerp.settings'
os.environ['USE_POSTGRES'] = '1'

import django
django.setup()

from django.conf import settings
from operations.rathasarathi_copilot import (
    ask_rathasarathi,
    execute_groq_llm,
)

API_KEY = "gsk_your_groq_api_key_here"

def test_groq_models():
    print("=" * 70)
    print("STEP 1: QUERYING GROQ /v1/models WITH USER KEY")
    print("=" * 70)
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    try:
        res = requests.get("https://api.groq.com/openai/v1/models", headers=headers, timeout=10)
        print(f"Status Code: {res.status_code}")
        if res.status_code == 200:
            data = res.json().get('data', [])
            all_ids = sorted([m['id'] for m in data])
            print(f"Total Models Available: {len(all_ids)}")
            for mid in all_ids:
                print(f"  - {mid}")
            return all_ids
        else:
            print(f"Error Response: {res.status_code} {res.text}")
            return []
    except Exception as e:
        print(f"Connection Exception: {e}")
        return []

if __name__ == '__main__':
    models = test_groq_models()
