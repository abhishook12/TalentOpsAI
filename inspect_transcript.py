import json

transcript_path = r"C:\Users\User\.gemini\antigravity\brain\285f6c8d-71ab-4abe-9e7b-e4d39e260a9f\.system_generated\logs\transcript.jsonl"
targets = [12307, 12309, 12311, 12313, 12353, 12411, 12478, 12502, 12542, 12562, 12619, 12667, 12695, 12760, 12823, 12847, 12928, 12979, 13055, 13069, 13085, 13164]

with open(transcript_path, "r", encoding="utf-8", errors="ignore") as f:
    for line in f:
        try:
            data = json.loads(line)
            idx = data.get("step_index")
            if data.get("type") == "USER_INPUT" and idx in targets:
                print(f"\n==================== STEP {idx} ====================")
                print(data.get("content"))
        except Exception as e:
            pass
