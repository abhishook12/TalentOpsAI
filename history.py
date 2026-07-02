import json

transcript_path = r"C:\Users\User\.gemini\antigravity\brain\15aabb56-dcdf-44fd-be32-72119f59740d\.system_generated\logs\transcript.jsonl"

print("--- PAST USER REQUESTS ---")
try:
    with open(transcript_path, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                data = json.loads(line)
                if data.get("type") == "USER_INPUT":
                    content = data.get("content", "")
                    if "<USER_REQUEST>" in content:
                        req = content.split("<USER_REQUEST>")[1].split("</USER_REQUEST>")[0].strip()
                        print(f"Step {data.get('step_index')}: {req}")
            except Exception:
                pass
except Exception as e:
    print(f"Error reading transcript: {e}")
