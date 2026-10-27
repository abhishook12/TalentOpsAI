import urllib.request
import re

slugs = [
    'cullerton-group',
    'talentfishllc',
    'complete-staffing-solutions',
    'calculated-hire',
    'carex-consulting-group',
    'innovien-solutions',
    'phaxis-consulting',
    'solving-it'
]

print("Resolving numeric IDs from LinkedIn slugs...")
for slug in slugs:
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
            m = re.search(r"organization/(\d+)", html) or re.search(r"urn:li:organization:(\d+)", html) or re.search(r"\"id\":\"?(\d+)\"?", html)
            if m:
                print(f"  {slug:30s} -> ID: {m.group(1)}")
            else:
                print(f"  {slug:30s} -> ID not found in page")
    except Exception as e:
        print(f"  {slug:30s} -> Error: {e}")
