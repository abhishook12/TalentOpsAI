import sys
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

import json
import re
from pathlib import Path
import urllib.parse

bm_path = Path(r"C:\Users\User\AppData\Local\Google\Chrome\User Data\Profile 65\Bookmarks")

with open(bm_path, "r", encoding="utf-8") as f:
    data = json.load(f)

companies = []

def extract(node, folder=""):
    if isinstance(node, dict):
        current_folder = folder
        if node.get("type") == "folder":
            current_folder = f"{folder}/{node.get('name', '')}"
        elif node.get("type") == "url":
            name = node.get("name", "")
            url = node.get("url", "")
            domain = urllib.parse.urlparse(url).netloc.lower()
            if not any(skip in domain for skip in ["google.com", "openai.com", "anthropic.com", "claude.ai", "chatgpt.com", "mailmeteor.com"]):
                companies.append({
                    "folder": current_folder,
                    "raw_title": name,
                    "url": url,
                    "domain": domain
                })
        for v in node.values():
            extract(v, current_folder)
    elif isinstance(node, list):
        for item in node:
            extract(item, folder)

extract(data)

print(f"Total relevant job/company bookmarks extracted: {len(companies)}")

with open(r"c:\TalentOpsAI\sandbox\chrome_staffing_companies.json", "w", encoding="utf-8") as f:
    json.dump(companies, f, indent=2, ensure_ascii=False)

for idx, c in enumerate(companies):
    print(f"[{idx+1:02d}] {c['raw_title'][:45]:45s} -> {c['domain']}")
