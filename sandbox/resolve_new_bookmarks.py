import urllib.request
import urllib.parse
import re
import json
import time

NEW_TARGETS = [
    ("cullerton group", "cullertongroup.com"),
    ("talentfish", "talentfish.com"),
    ("complete staffing solutions", "completestaffingsolutions.com"),
    ("agility connect", "agilityconnect.io"),
    ("bct it solutions", "bct-corp.com"),
    ("bridgesource solutions", "bridgesourcesolutions.com"),
    ("blackstone talent group", "bstonetalent.com"),
    ("burnett specialists", "burnettspecialists.com"),
    ("calculated hire", "calculatedhire.com"),
    ("carex consulting group", "carexconsulting.com"),
    ("cornerstone technology talent", "cornerstonetechtalent.com"),
    ("corps team", "corpsteam.com"),
    ("doyle group", "doylegroup-it.com"),
    ("enterprise engineering inc", "joineei.com"),
    ("elevationhr", "elevationhr.com"),
    ("fuel talent", "fueltalent.com"),
    ("gforce life sciences", "gforcelifesciences.com"),
    ("henderson scott", "hendersonscott.com"),
    ("hightrail", "hightrail.com"),
    ("hka enterprises", "hkaa.com"),
    ("innovien", "innovien.com"),
    ("luna data solutions", "lunadatasolutions.com"),
    ("mmd services", "mmdtech.com"),
    ("peak performers", "peakperformers.org"),
    ("phaxis", "phaxis.com"),
    ("pmo partners", "pmopartners.com"),
    ("perennial resources", "perennialresources.com"),
    ("odyssey information services", "odysseyis.com"),
    ("stott and may", "stottandmay.com"),
    ("sand cherry associates", "sandcherry.com")
]

print(f"Resolving {len(NEW_TARGETS)} new staffing companies from user bookmarks...")

def resolve_linkedin_id_via_ddg(name, domain):
    query = f"site:linkedin.com/company {name}"
    url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
            # Look for linkedin.com/company/slug
            matches = re.findall(r"linkedin\.com/company/([a-zA-Z0-9_\-]+)", html)
            if matches:
                # filter out generic terms
                valid_slugs = [m for m in matches if m not in ["login", "signup", "jobs", "company"]]
                if valid_slugs:
                    slug = valid_slugs[0]
                    # Fetch company page to get numeric ID
                    c_url = f"https://www.linkedin.com/company/{slug}/"
                    c_req = urllib.request.Request(c_url, headers={"User-Agent": "Mozilla/5.0"})
                    try:
                        with urllib.request.urlopen(c_req, timeout=5) as c_resp:
                            c_html = c_resp.read().decode("utf-8", errors="ignore")
                            m_id = re.search(r"organization/(\d+)", c_html) or re.search(r"urn:li:organization:(\d+)", c_html) or re.search(r"\"id\":\"?(\d+)\"?", c_html)
                            return slug, m_id.group(1) if m_id else None
                    except Exception:
                        return slug, None
    except Exception as e:
        pass
    return None, None

results = {}
for name, domain in NEW_TARGETS:
    slug, cid = resolve_linkedin_id_via_ddg(name, domain)
    results[name] = {"domain": domain, "slug": slug, "id": cid}
    print(f"  {name:30s} -> slug='{slug}' | ID: {cid}")
    time.sleep(0.5)

with open(r"c:\TalentOpsAI\sandbox\resolved_new_companies.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2)
