import json, sys

sys.stdout.reconfigure(encoding='utf-8')
with open(r'C:\Users\chuan\.gemini\antigravity\brain\d97b9f29-a537-409d-b432-b06e88281223\.system_generated\logs\transcript_full.jsonl', 'r', encoding='utf-8') as f:
    for line in f:
        obj = json.loads(line)
        if obj.get('type') == 'USER_INPUT' and obj.get('step_index') >= 1470:
            print(f"STEP {obj.get('step_index')}: {obj.get('content')}")
