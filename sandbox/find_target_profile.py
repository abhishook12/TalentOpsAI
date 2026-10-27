import json
from pathlib import Path

user_data = Path(r"C:\Users\User\AppData\Local\Google\Chrome\User Data")

profiles_to_check = []
for p in user_data.iterdir():
    bm = p / "Bookmarks"
    if bm.exists() and bm.stat().st_size > 10000: # larger bookmark files
        profiles_to_check.append((p.name, bm))

print(f"Profiles with substantial bookmarks: {[p[0] for p in profiles_to_check]}")

target_keywords = ["cullerton", "idr inc", "talentfish", "bravotech", "phoenix staff", "prosearch"]

for prof_name, bm_path in profiles_to_check:
    try:
        with open(bm_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        matches = []
        def search_node(node):
            if isinstance(node, dict):
                if node.get("type") == "url":
                    name = node.get("name", "")
                    url = node.get("url", "")
                    for kw in target_keywords:
                        if kw in name.lower() or kw in url.lower():
                            matches.append((name, url))
                            break
                for v in node.values():
                    search_node(v)
            elif isinstance(node, list):
                for item in node:
                    search_node(item)
                    
        search_node(data)
        print(f"Profile '{prof_name}' matches: {len(matches)}")
        if matches:
            print(f"  Sample: {matches[:3]}")
    except Exception as e:
        print(f"Profile '{prof_name}' error: {e}")
