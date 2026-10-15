import os
import sys
from pathlib import Path
import json
import requests

# Set stdout to UTF-8 to prevent Windows cp1252 charmap crashes
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

os.environ['DJANGO_SETTINGS_MODULE'] = 'travelerp.settings'
os.environ['USE_POSTGRES'] = '1'

import django
django.setup()

from django.conf import settings
from operations.rathasarathi_copilot import ask_rathasarathi

API_KEY = "gsk_your_groq_api_key_here"
MODEL = "qwen/qwen3.8-27b"

test_queries = [
    "How many tours are running today?",
    "Which vehicles have insurance or fitness expiring soon?",
    "Search devotional packages to Tirupati or Madurai",
    "What is our revenue and collection rate this month?",
    "What are temple dress code rules for Madurai Meenakshi Amman Temple?"
]

print("=" * 80)
print(f"TESTING RATHASĀRATHI AI WITH GROQ CLOUD MODEL: {MODEL}")
print("=" * 80)

for idx, q in enumerate(test_queries, 1):
    print(f"\n[QUERY {idx}]: \"{q}\"")
    print("-" * 80)
    try:
        res = ask_rathasarathi(
            user_message=q,
            custom_api_key=API_KEY,
            custom_model=MODEL
        )
        print(f"Status:   {res.get('status')}")
        print(f"Provider: {res.get('provider')}")
        print(f"Model:    {res.get('model')}")
        print(f"KPIs:     {len(res.get('kpi_cards', []))} cards -> {[k['label'] + ': ' + k['value'] for k in res.get('kpi_cards', [])]}")
        print(f"Actions:  {[a['label'] for a in res.get('action_buttons', [])]}")
        print(f"\nResponse Content:\n{res.get('reply', '')}")
    except Exception as e:
        print(f"Error on query {idx}: {e}")
    print("=" * 80)
