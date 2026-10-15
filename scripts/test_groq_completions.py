import requests
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

API_KEY = "gsk_your_groq_api_key_here"
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

models_to_test = [
    "qwen/qwen3.8-27b",
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b"
]

print("Testing Chat Completions on Groq Models:")
for m in models_to_test:
    print(f"\n--- Testing Model: {m} ---")
    payload = {
        "model": m,
        "messages": [
            {"role": "system", "content": "You are Rathasārathi AI for Sivagayathiri Travels & Tours."},
            {"role": "user", "content": "Hello! Give a 1-sentence royal greeting for our Coimbatore travels company."}
        ],
        "temperature": 0.2,
        "max_tokens": 100
    }
    try:
        res = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=15)
        print(f"Status: {res.status_code}")
        if res.status_code == 200:
            print("Response:", res.json()['choices'][0]['message']['content'])
        else:
            print("Error:", res.text)
    except Exception as e:
        print("Exception:", e)
