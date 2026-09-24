import json

transcript_path = r'C:\Users\rithi\.gemini\antigravity-ide\brain\12e9440a-ec76-4489-aa28-9f0807948a00\.system_generated\logs\transcript.jsonl'

with open(transcript_path, 'r', encoding='utf-8') as f, open('scratch_prompts.txt', 'w', encoding='utf-8') as out:
    for line in f:
        data = json.loads(line)
        if data.get('type') == 'USER_INPUT':
            step = data.get('step_index')
            content = data.get('content', '')
            out.write(f"\n================ USER STEP {step} ================\n")
            out.write(content + "\n")
print("Saved prompts to scratch_prompts.txt")
