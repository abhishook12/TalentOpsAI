import urllib.request
import re
import json

url = "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/4482995428"
req = urllib.request.Request(
    url,
    headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }
)

with urllib.request.urlopen(req, timeout=10) as resp:
    html = resp.read().decode("utf-8", errors="ignore")

# Extract details
title = re.search(r"<h2[^>]*topcard__title[^>]*>(.*?)</h2>", html, re.S)
company = re.search(r"<a[^>]*topcard__org-name-link[^>]*>(.*?)</a>", html, re.S)
company_url = re.search(r"href=\"(https://[^\"]*linkedin.com/company/[^\"]*)\"", html)
location = re.search(r"<span[^>]*topcard__flavor--bullet[^>]*>(.*?)</span>", html, re.S)
criteria = re.findall(r"<li[^>]*description__job-criteria-item[^>]*>.*?<h3[^>]*>(.*?)</h3>.*?<span[^>]*>(.*?)</span>", html, re.S)
posted_time = re.search(r"<span[^>]*posted-time-ago__text[^>]*>(.*?)</span>", html, re.S)
num_applicants = re.search(r"<span[^>]*num-applicants__caption[^>]*>(.*?)</span>", html, re.S)

desc_match = re.search(r"<div[^>]*show-more-less-html__markup[^>]*>(.*?)</div>", html, re.S)
desc_text = ""
if desc_match:
    desc_clean = re.sub(r"<br\s*/?>", "\n", desc_match.group(1))
    desc_clean = re.sub(r"</p>", "\n\n", desc_clean)
    desc_clean = re.sub(r"<li[^>]*>", "• ", desc_clean)
    desc_clean = re.sub(r"</li>", "\n", desc_clean)
    desc_clean = re.sub(r"<[^>]+>", "", desc_clean)
    desc_text = desc_clean.strip()

report = {
    "job_id": "4482995428",
    "title": title.group(1).strip() if title else "",
    "company": company.group(1).strip() if company else "",
    "company_url": company_url.group(1).strip() if company_url else "",
    "location": location.group(1).strip() if location else "",
    "posted_time": posted_time.group(1).strip() if posted_time else "",
    "num_applicants": num_applicants.group(1).strip() if num_applicants else "",
    "criteria": {c[0].strip(): c[1].strip() for c in criteria},
    "description": desc_text
}

with open(r"c:\TalentOpsAI\sandbox\job_4482995428_details.json", "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2, ensure_ascii=False)

print(f"Title: {report['title']}")
print(f"Company: {report['company']}")
print(f"Location: {report['location']}")
print(f"Posted: {report['posted_time']} | Applicants: {report['num_applicants']}")
print(f"Criteria: {report['criteria']}")
print(f"\nDescription Snippet (first 500 chars):\n{report['description'][:500]}")
