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

tools = [
    {
        "type": "function",
        "function": {
            "name": "get_active_tours",
            "description": "Returns current active tours running today",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
]

messages = [
    {"role": "system", "content": "You are Rathasārathi AI for Sivagayathiri Travels. Answer questions using tools when needed."},
    {"role": "user", "content": "How many tours are running today?"}
]

payload1 = {
    "model": "qwen/qwen3.8-27b",
    "messages": messages,
    "tools": tools,
    "tool_choice": "auto",
    "temperature": 0.2,
    "max_tokens": 300
}

res1 = requests.post(GROQ_API_URL, headers=headers, json=payload1, timeout=15)
print("Turn 1 Status:", res1.status_code)
res1_json = res1.json()
print("Turn 1 Response:", json.dumps(res1_json, indent=2))

choice = res1_json['choices'][0]
msg1 = choice['message']
tool_calls = msg1.get('tool_calls')

if tool_calls:
    print("\nModel called tool:", tool_calls[0]['function']['name'])
    messages.append(msg1)
    messages.append({
        "role": "tool",
        "tool_call_id": tool_calls[0]['id'],
        "content": json.dumps({"total_active_tours": 5, "tours": ["Coimbatore to Ooty Express", "Madurai Temple Darshan"]})
    })

    # Test passing tools vs not passing tools on Turn 2
    print("\n--- Testing Turn 2 with tools passed ---")
    payload2 = {
        "model": "qwen/qwen3.8-27b",
        "messages": messages,
        "tools": tools,
        "tool_choice": "none",
        "temperature": 0.2,
        "max_tokens": 500
    }
    res2 = requests.post(GROQ_API_URL, headers=headers, json=payload2, timeout=15)
    print("Turn 2 (tool_choice=none) Status:", res2.status_code)
    if res2.status_code == 200:
        print("Turn 2 Reply:", res2.json()['choices'][0]['message']['content'])
    else:
        print("Turn 2 Error:", res2.text)

    print("\n--- Testing Turn 2 without tool_choice (auto) ---")
    payload3 = {
        "model": "qwen/qwen3.8-27b",
        "messages": messages,
        "tools": tools,
        "tool_choice": "auto",
        "temperature": 0.2,
        "max_tokens": 500
    }
    res3 = requests.post(GROQ_API_URL, headers=headers, json=payload3, timeout=15)
    print("Turn 3 (tool_choice=auto) Status:", res3.status_code)
    if res3.status_code == 200:
        print("Turn 3 Reply:", res3.json()['choices'][0]['message']['content'])
    else:
        print("Turn 3 Error:", res3.text)
