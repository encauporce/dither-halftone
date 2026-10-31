import json

with open(r'C:\Users\chuan\.gemini\antigravity\brain\d97b9f29-a537-409d-b432-b06e88281223\.system_generated\logs\transcript_full.jsonl', 'r', encoding='utf-8') as f:
    for i, line in enumerate(f):
        data = json.loads(line)
        if data.get('step_index') == 227:
            tc = data.get('tool_calls', [])
            for c in tc:
                args = c.get('args', {})
                content = args.get('Content', '')
                if content:
                    print("Found Content length:", len(content))
                    with open(r'C:\Users\chuan\.gemini\antigravity\scratch\hisense_a7_video_shader\step227_halftone.glsl', 'w', encoding='utf-8') as out:
                        out.write(content)
                    print("Wrote to step227_halftone.glsl")
