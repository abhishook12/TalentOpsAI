import urllib.request
import re

url = "https://www.linkedin.com/company/ndx-human-capital-solutions/"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
try:
    with urllib.request.urlopen(req, timeout=5) as r:
        html = r.read().decode("utf-8", errors="ignore")
        m = re.findall(r"organization[/:]([0-9]+)", html) or re.findall(r"fsd_company:([0-9]+)", html)
        print("NDX ID matches:", m)
except Exception as e:
    print("Error:", e)
