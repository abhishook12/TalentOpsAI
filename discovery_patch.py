import os

with open("C:/TalentOpsAI/backend/app/routes/companies.py", "a", encoding="utf-8") as f:
    f.write("""
import re
import requests
from html import unescape
from urllib.parse import quote_plus
from sqlalchemy import func
from ..models.models import Recruiter

NAME_SPLIT_RE = re.compile(r"[-|—]+| at | - ")
LIKELY_NAME_RE = re.compile(r"^[A-Z][a-z]+(?:\\s+[A-Z][a-z]+)+$")
LINKEDIN_PROFILE_RE = re.compile(r"https://(?:[a-z]{2}\\.)?linkedin\\.com/in/[^/\"\\s]+/?")

def normalize_name(value: str) -> str:
    value = unescape(value or "")
    value = re.sub(r"\\s+", " ", value).strip()
    return value

def normalize_company(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (value or "").lower())

def extract_candidate_name(text: str, company_name: str) -> str:
    if not text: return None
    cleaned = re.sub(r"<[^>]+>", " ", unescape(text))
    cleaned = re.sub(r"\\s+", " ", cleaned).strip()
    if not cleaned: return None
    
    parts = NAME_SPLIT_RE.split(cleaned)
    blocked = {"linkedin", "profiles", "profile", "recruiter", "recruiting", "talent acquisition", "duckduckgo", "people", "search"}
    company_normalized = normalize_company(company_name)
    
    for part in parts:
        candidate = normalize_name(part)
        if not candidate or len(candidate) < 5 or len(candidate) > 60: continue
        lower = candidate.lower()
        if any(f in lower for f in blocked): continue
        if normalize_company(candidate) == company_normalized: continue
        words = candidate.split()
        if len(words) < 2 or len(words) > 4: continue
        if not LIKELY_NAME_RE.match(candidate): continue
        return candidate
    return None

@router.post("/{company_id}/discovery")
def run_discovery_scan(company_id: int, db: Session = Depends(get_db)):
    company = db.query(Company).filter(Company.company_id == company_id).first()
    if not company:
        raise HTTPException(404, "Company not found")
        
    query = f"site:linkedin.com/in \\"{company.company_name}\\" recruiter"
    url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
    
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        raise HTTPException(500, f"Search failed: {str(e)}")
        
    html = resp.text
    names = []
    seen = set()
    
    link_matches = LINKEDIN_PROFILE_RE.findall(html)
    for link in link_matches[:10]:
        slug = link.rstrip("/").split("/")[-1]
        slug = re.sub(r"[-_]+", " ", slug)
        slug = " ".join(w.capitalize() for w in slug.split() if w)
        candidate = extract_candidate_name(slug, company.company_name)
        if candidate and candidate.lower() not in seen:
            seen.add(candidate.lower())
            names.append(candidate)
            
    title_matches = re.findall(r'<a[^>]*class="[^"]*result__a[^"]*"[^>]*>(.*?)</a>', html, flags=re.I | re.S)
    for title in title_matches[:10]:
        candidate = extract_candidate_name(title, company.company_name)
        if candidate and candidate.lower() not in seen:
            seen.add(candidate.lower())
            names.append(candidate)
            
    # Deduplicate against DB
    new_names = []
    for name in names:
        exists = db.query(Recruiter).filter(
            func.lower(func.trim(Recruiter.recruiter_name)) == name.lower().strip(),
            func.lower(func.trim(Recruiter.company_name)) == company.company_name.lower().strip()
        ).first()
        if not exists:
            new_names.append(name)
            
    # Insert new ones
    for name in new_names:
        r = Recruiter(
            recruiter_name=name,
            company_name=company.company_name,
            company_id=company.company_id,
            source="ui_discovery"
        )
        db.add(r)
    
    db.commit()
    
    return {
        "scanned": True,
        "total_found": len(names),
        "new_names_found": new_names
    }
""")
