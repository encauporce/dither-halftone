import json, sys

sys.stdout.reconfigure(encoding='utf-8')
with open(r'C:\Users\chuan\.gemini\antigravity\brain\d97b9f29-a537-409d-b432-b06e88281223\.system_generated\logs\transcript_full.jsonl', 'r', encoding='utf-8') as f:
    for line in f:
        obj = json.loads(line)
        idx = obj.get('step_index')
        if idx in range(1470, 1495) and obj.get('source') == 'MODEL' and obj.get('content'):
            print(f"=== STEP {idx} ===")
            print(obj.get('content')[:1500])
