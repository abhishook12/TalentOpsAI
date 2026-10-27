import urllib.request
import re
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

candidates = [
    ("Agility Connect", "agilityconnect.io"),
    ("Aktra", "aktra.com"),
    ("WGA Consulting", "wgaconsulting.com"),
    ("Benchmark IT", "bmarkits.com"),
    ("Compri Consulting", "compri.com"),
    ("Hicks Pro", "hickspro.com"),
    ("NDX Human Capital", "ndxsolutions.com")
]

print("Checking remaining bookmark homepages for LinkedIn IDs...")
for name, domain in candidates:
    url = f"https://{domain}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=5, context=ctx) as r:
            html = r.read().decode("utf-8", errors="ignore")
            m = re.findall(r"linkedin\.com/company/([a-zA-Z0-9_\-]+)", html, re.I)
            if m:
                slug = [s for s in m if s.lower() not in ["company", "jobs"]][0]
                # fetch slug
                c_url = f"https://www.linkedin.com/company/{slug}/"
                c_req = urllib.request.Request(c_url, headers={"User-Agent": "Mozilla/5.0"})
                try:
                    with urllib.request.urlopen(c_req, timeout=5) as c_r:
                        c_html = c_r.read().decode("utf-8", errors="ignore")
                        m_id = re.search(r"organization/(\d+)", c_html) or re.search(r"urn:li:organization:(\d+)", c_html) or re.search(r"\"id\":\"?(\d+)\"?", c_html)
                        print(f"  {name:20s} ({domain}) -> slug='{slug}' | ID: {m_id.group(1) if m_id else 'None'}")
                except Exception as e2:
                    print(f"  {name:20s} ({domain}) -> slug='{slug}' (ID fetch failed: {e2})")
            else:
                print(f"  {name:20s} ({domain}) -> No LinkedIn link on homepage")
    except Exception as e:
        print(f"  {name:20s} ({domain}) -> Site error: {e}")
