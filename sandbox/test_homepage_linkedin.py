import urllib.request
import re

domains = [
    "cullertongroup.com",
    "talentfish.com",
    "completestaffingsolutions.com",
    "bct-corp.com",
    "burnettspecialists.com",
    "calculatedhire.com",
    "carexconsulting.com",
    "innovien.com",
    "phaxis.com",
    "solvingit.com"
]

print("Testing direct website footer LinkedIn link extraction...")
for d in domains:
    url = f"https://{d}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
            m = re.findall(r"linkedin\.com/company/([a-zA-Z0-9_\-]+)", html, re.I)
            if m:
                # filter unique slugs
                slugs = list(set([s.lower() for s in m if s.lower() not in ["company", "jobs", "login"]]))
                print(f"  {d:25s} -> LinkedIn: {slugs}")
            else:
                print(f"  {d:25s} -> No LinkedIn link found on homepage")
    except Exception as e:
        print(f"  {d:25s} -> Error: {e}")
