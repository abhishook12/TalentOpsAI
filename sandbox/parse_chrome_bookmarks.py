import json
from pathlib import Path

path = Path(r"C:\Users\User\AppData\Local\Google\Chrome\User Data\Profile 34\Bookmarks")

with open(path, "r", encoding="utf-8") as f:
    data = json.load(f)

bookmarks = []

def extract(node, folder=""):
    if isinstance(node, dict):
        current_folder = folder
        if node.get("type") == "folder":
            current_folder = f"{folder}/{node.get('name', '')}"
        elif node.get("type") == "url":
            bookmarks.append({
                "folder": current_folder,
                "name": node.get("name", ""),
                "url": node.get("url", "")
            })
        for k, v in node.items():
            extract(v, current_folder)
    elif isinstance(node, list):
        for item in node:
            extract(item, folder)

extract(data)
print(f"Total bookmarks in Profile 34: {len(bookmarks)}")

folders = {}
for b in bookmarks:
    folders[b["folder"]] = folders.get(b["folder"], 0) + 1

print("\nFolders found:")
for f, count in folders.items():
    print(f"  {f:40s} : {count} bookmarks")

print("\nSample bookmarks (matching screenshots):")
for b in bookmarks:
    name = b["name"].lower()
    url = b["url"].lower()
    if any(k in name or k in url for k in ["cullerton", "idr", "talentfish", "bravo", "prosearch", "agile", "genesys", "marchon"]):
        print(f"  [{b['folder']}] {b['name']} -> {b['url']}")

with open(r"c:\TalentOpsAI\sandbox\extracted_bookmarks.json", "w", encoding="utf-8") as f:
    json.dump(bookmarks, f, indent=2, ensure_ascii=False)
