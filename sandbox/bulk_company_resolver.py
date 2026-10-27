import urllib.request
import re
import json

def get_linkedin_company_id(slug):
    url = f"https://www.linkedin.com/company/{slug}/"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
            # Multiple patterns where LinkedIn puts organization ID
            patterns = [
                r"\"objectUrn\":\"urn:li:organization:(\d+)\"",
                r"organization/(\d+)",
                r"urn:li:fsd_company:(\d+)",
                r"urn:li:organization:(\d+)",
                r"\"universalName\":\"[^\"]*\",\"id\":\"?(\d+)\"?"
            ]
            for p in patterns:
                m = re.search(p, html)
                if m:
                    return m.group(1)
            return None
    except Exception as e:
        return None

# Test with a few prominent staffing agencies
agencies = [
    ("kforce-inc", "Kforce"),
    ("apex-systems", "Apex Systems"),
    ("randstad-usa", "Randstad USA"),
    ("beacon-hill-staffing-group", "Beacon Hill Staffing"),
    ("collabera", "Collabera"),
    ("judge-group", "The Judge Group"),
    ("diversant-llc", "Diversant"),
    ("akkodis", "Akkodis"),
    ("experis", "Experis")
]

print("Resolving agency IDs in bulk...")
resolved = {}
for slug, name in agencies:
    cid = get_linkedin_company_id(slug)
    resolved[name] = {"slug": slug, "id": cid}
    print(f"  {name:25s} ({slug}) -> ID: {cid}")

with open(r"c:\TalentOpsAI\sandbox\resolved_sample.json", "w", encoding="utf-8") as f:
    json.dump(resolved, f, indent=2)
