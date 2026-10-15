"""
corporate_intel_enricher.py — Autonomous Recruiter & Corporate Intelligence Ingestion Service.

Permanent Systemic Implementation of User Directives:
1. When emails are entered/staged/sent, parse whole name (First & Last name) when complete.
2. If name is incomplete (e.g. single name, initials, truncated prefix), strictly ignore it (store None, no hallucination).
3. Associate every recipient with their corporate entity in the 'companies' table derived from email domains.
4. Autonomous Web Scraping: Scrape the corporate website to extract title, description, phone numbers,
   industry tags, and location to perpetually enrich the master database.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import httpx
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..models.models import Company, Recruiter

logger = logging.getLogger("talentops.corporate_intel")

PUBLIC_EMAIL_DOMAINS = {
    "gmail.com", "googlemail.com", "yahoo.com", "ymail.com", "hotmail.com",
    "outlook.com", "live.com", "msn.com", "icloud.com", "me.com", "aol.com",
    "protonmail.com", "proton.me", "zoho.com", "mail.com", "gmx.com",
    "noemail.talentops", "unknown.com", "noemail.com", "test.com", "example.com"
}

GENERIC_EMAIL_PREFIXES = {
    "info", "support", "contact", "careers", "jobs", "team", "sales",
    "admin", "help", "billing", "office", "hr", "recruiting", "inquiries",
    "press", "media", "general", "service", "hello", "mail", "webmaster", "postmaster"
}

KNOWN_DOMAIN_MAP = {
    "entegee.com": "Entegee",
    "elitetechnical.com": "Elite Technical",
    "refactortalent.com": "Refactor Talent",
    "connection.com": "Connection",
    "cullertongroup.com": "Cullerton Group",
    "gotoagile.com": "GoToAgile",
    "hirenetworks.com": "HireNetworks",
    "technovion.com": "Technovion",
    "roberthalf.com": "Robert Half",
    "teksystems.com": "TEKsystems",
    "insightglobal.com": "Insight Global",
    "randstadusa.com": "Randstad",
    "kforce.com": "Kforce",
    "aerotek.com": "Aerotek",
    "apexsystems.com": "Apex Systems",
}

COMMON_COMPANY_SUFFIX_WORDS = [
    "group", "technical", "talent", "staffing", "solutions", "technologies",
    "consulting", "recruiting", "partners", "media", "digital", "services",
    "capital", "global", "labs", "networks", "systems", "associates",
    "resources", "personnel", "search", "advisors", "international"
]


def format_domain_to_company_name(domain: Optional[str]) -> Optional[str]:
    """Converts a raw domain string into an enterprise-formatted company name."""
    if not domain:
        return None
    d = domain.strip().lower()
    if d in KNOWN_DOMAIN_MAP:
        return KNOWN_DOMAIN_MAP[d]
    if d in PUBLIC_EMAIL_DOMAINS:
        return None

    base = re.sub(r"\.(com|net|org|io|co|ai|us|ca|tech|info|biz|global|llc|co\.uk)$", "", d)
    base = re.sub(r"^(mail|corp|web|app)\.", "", base)

    if not re.search(r"[-_.]", base) and len(base) > 7:
        for suffix in COMMON_COMPANY_SUFFIX_WORDS:
            if base.endswith(suffix) and len(base) > len(suffix):
                prefix = base[:-len(suffix)]
                base = f"{prefix} {suffix}"
                break

    parts = [p for p in re.split(r"[-_.\s]+", base) if p]
    if not parts:
        return None
    cleaned_words = []
    for p in parts:
        if p.lower() in {"sg", "it", "llc", "inc", "corp", "hr", "ai", "us", "uk", "ca"}:
            cleaned_words.append(p.upper())
        else:
            cleaned_words.append(p.capitalize())
    return " ".join(cleaned_words)


def extract_clean_person_name(email: str, raw_name: Optional[str] = None) -> Optional[str]:
    """
    Extracts a validated whole name (First and Last name) for a person.
    Strictly adheres to user instruction:
    - If email/raw_name has both first & last name -> returns properly capitalized full name.
    - If the name is incomplete (e.g. single token, initial only, truncated prefix) -> returns None.
    """
    # 1. Inspect explicit raw_name if passed
    if raw_name:
        clean = str(raw_name).strip()
        if "@" in clean:
            clean = clean.split("@")[0]
        clean = re.sub(r"[<>\'\"()]", "", clean).strip()
        clean = re.sub(r"[._-]+", " ", clean)
        parts = clean.split()
        if len(parts) >= 2:
            # Must all be alphabetical and length >= 2 (rejects "J Keller" or "Debby W")
            if all(p.isalpha() and len(p) >= 2 for p in parts):
                return " ".join(p.capitalize() for p in parts)

    # 2. Extract from email local part
    if not email or "@" not in email:
        return None
    local = email.split("@")[0].strip().lower()
    if local in GENERIC_EMAIL_PREFIXES:
        return None

    # Check for separator (. or _ or -) indicating distinct first and last name
    if re.search(r"[._-]", local):
        parts = [p for p in re.split(r"[._-]+", local) if p]
        if len(parts) >= 2:
            # Each token must be pure letters with at least 2 characters (rejects initial formats like 'c.sullivan')
            if all(p.isalpha() and len(p) >= 2 for p in parts):
                return " ".join(p.capitalize() for p in parts)

    # Incomplete name (e.g. 'nm', 'jkeller', 'anna', 'richard', 'debby.w') -> ignore as instructed
    return None


def resolve_or_create_company(
    db: Session,
    domain: str,
    explicit_name: Optional[str] = None,
    user_id: Optional[int] = None
) -> Optional[Company]:
    """
    Finds or creates a Company record for a corporate domain.
    Returns None if the domain is a consumer/public webmail.
    """
    if not domain or domain.lower() in PUBLIC_EMAIL_DOMAINS:
        return None

    clean_dom = domain.strip().lower()
    comp_name = explicit_name or KNOWN_DOMAIN_MAP.get(clean_dom) or format_domain_to_company_name(clean_dom)
    if not comp_name:
        return None

    # Check if company exists by primary domain or normalized name
    company = db.query(Company).filter(
        (func.lower(Company.primary_domain) == clean_dom) |
        (func.lower(Company.company_name) == comp_name.lower())
    ).first()

    if company:
        if not company.primary_domain:
            company.primary_domain = clean_dom
        if not company.website:
            company.website = f"https://{clean_dom}"
        return company

    # Create new company
    now = datetime.now(timezone.utc)
    company = Company(
        user_id=user_id,
        company_name=comp_name,
        normalized_company_name=comp_name.lower(),
        primary_domain=clean_dom,
        website=f"https://{clean_dom}",
        data_source="campaign_intelligence",
        trust_score=95,
        is_active=True,
        created_at=now,
        updated_at=now
    )
    db.add(company)
    db.flush()
    return company


def scrape_and_enrich_company_site(db: Session, company_id: int) -> Dict[str, Any]:
    """
    Autonomously visits the company website to scrape site title, meta description,
    phone numbers, and favicon/logo, enriching the company record in PostgreSQL.
    """
    company = db.query(Company).filter(Company.company_id == company_id).first()
    if not company or not company.primary_domain:
        return {"status": "SKIPPED", "reason": "No company or domain"}

    domain = company.primary_domain.strip().lower()
    target_urls = [f"https://{domain}", f"http://{domain}"]

    scraped_info = {
        "title": None,
        "description": None,
        "phone": None,
        "logo_url": f"https://{domain}/favicon.ico",
        "industry_hints": []
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9"
    }

    html_content = ""
    with httpx.Client(timeout=5.0, follow_redirects=True, headers=headers, verify=False) as client:
        for url in target_urls:
            try:
                resp = client.get(url)
                if resp.status_code == 200 and resp.text:
                    html_content = resp.text
                    break
            except Exception as e:
                logger.debug("Failed probing %s: %s", url, e)

    if html_content:
        # 1. Extract title
        title_match = re.search(r"<title[^>]*>(.*?)</title>", html_content, re.IGNORECASE | re.DOTALL)
        if title_match:
            clean_title = re.sub(r"\s+", " ", title_match.group(1)).strip()
            # Remove generic boilerplate
            clean_title = re.sub(r"^Home\s*[-|:]\s*", "", clean_title, flags=re.IGNORECASE).strip()
            scraped_info["title"] = clean_title[:250] if clean_title else None

        # 2. Extract description from meta tags
        desc_match = re.search(r'<meta[^>]+(?:name|property)=["\'](?:description|og:description)["\'][^>]+content=["\'](.*?)["\']', html_content, re.IGNORECASE)
        if not desc_match:
            desc_match = re.search(r'<meta[^>]+content=["\'](.*?)["\'][^>]+(?:name|property)=["\'](?:description|og:description)["\']', html_content, re.IGNORECASE)
        if desc_match:
            clean_desc = re.sub(r"\s+", " ", desc_match.group(1)).strip()
            scraped_info["description"] = clean_desc[:500] if clean_desc else None

        # 3. Extract phone numbers
        phones = re.findall(r"(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", html_content)
        if phones:
            scraped_info["phone"] = phones[0]

        # 4. Check for staffing / tech industry keywords
        lower_html = html_content.lower()
        if "staffing" in lower_html or "recruiting" in lower_html or "talent" in lower_html:
            scraped_info["industry_hints"].append("Staffing & Recruiting")
        if "engineering" in lower_html or "technical" in lower_html:
            scraped_info["industry_hints"].append("Engineering Services")
        if "information technology" in lower_html or "software" in lower_html or "cloud" in lower_html:
            scraped_info["industry_hints"].append("Information Technology")

        # 5. Apply enrichment to Company record
        meta = json.loads(company.metadata_json) if company.metadata_json else {}
        meta["site_scrape"] = {
            "title": scraped_info["title"],
            "description": scraped_info["description"],
            "scraped_at": datetime.now(timezone.utc).isoformat()
        }
        company.metadata_json = json.dumps(meta)

        if not company.notes and scraped_info["description"]:
            company.notes = scraped_info["description"]
        if not company.industry and scraped_info["industry_hints"]:
            company.industry = " / ".join(scraped_info["industry_hints"])
        if not company.logo_url:
            company.logo_url = scraped_info["logo_url"]
            company.logo_source = "domain_favicon"

        company.last_verified_at = datetime.now(timezone.utc)
        company.verification_status = "verified"
        db.commit()
        return {"status": "SUCCESS", "company_id": company.company_id, "data": scraped_info}

    return {"status": "UNREACHABLE", "domain": domain}


def ingest_campaign_recipients_to_db(
    db: Session,
    recipients: List[Any],
    user_id: Optional[int] = None,
    enrich_sites: bool = True
) -> Dict[str, Any]:
    """
    Ingests and reconciles candidate emails directly into the master PostgreSQL database:
    - Resolves and attaches corporate Company records derived from email domains.
    - Extracts full name (First & Last) when present; ignores incomplete names.
    - Scrapes the corporate site to enrich company metadata, notes, and industry tags.
    """
    stats = {
        "total_processed": len(recipients),
        "names_extracted": 0,
        "names_incomplete_ignored": 0,
        "companies_linked": 0,
        "companies_created": 0,
        "sites_enriched": 0
    }

    companies_to_scrape = set()

    for r in recipients:
        raw_email = getattr(r, "email", None) or (r.get("email") if isinstance(r, dict) else str(r))
        if not raw_email or "@" not in str(raw_email):
            continue
        clean_email = str(raw_email).strip().lower()
        domain = clean_email.split("@")[-1].strip().lower()

        raw_name = getattr(r, "name", None) or (r.get("name") if isinstance(r, dict) else None)
        explicit_company = getattr(r, "company", None) or (r.get("company") if isinstance(r, dict) else None)

        # 1. Whole name extraction
        whole_name = extract_clean_person_name(clean_email, raw_name)
        if whole_name:
            stats["names_extracted"] += 1
        else:
            stats["names_incomplete_ignored"] += 1

        # 2. Company association
        company = None
        if domain not in PUBLIC_EMAIL_DOMAINS:
            company = resolve_or_create_company(db, domain, explicit_name=explicit_company, user_id=user_id)
            if company:
                stats["companies_linked"] += 1
                companies_to_scrape.add(company.company_id)

        # 3. Upsert Recruiter record
        recruiter = db.query(Recruiter).filter(func.lower(Recruiter.email) == clean_email).first()
        if recruiter:
            if company and not recruiter.company_id:
                recruiter.company_id = company.company_id
            if whole_name:
                # Update if current name is missing or raw local-part
                curr = str(recruiter.recruiter_name or "").strip()
                if not curr or curr == clean_email.split("@")[0] or curr.lower() == clean_email:
                    recruiter.recruiter_name = whole_name
                    recruiter.normalized_recruiter_name = whole_name.lower()
            elif not recruiter.recruiter_name:
                recruiter.recruiter_name = "Recruiter"
                recruiter.normalized_recruiter_name = None
        else:
            recruiter = Recruiter(
                user_id=user_id,
                email=clean_email,
                recruiter_name=whole_name or "Recruiter",
                normalized_recruiter_name=whole_name.lower() if whole_name else None,
                company_id=company.company_id if company else None,
                data_source="campaign_intelligence",
                trust_score=95
            )
            db.add(recruiter)

    db.commit()

    # 4. Scrape company sites if enabled
    if enrich_sites and companies_to_scrape:
        for cid in companies_to_scrape:
            try:
                res = scrape_and_enrich_company_site(db, cid)
                if res.get("status") == "SUCCESS":
                    stats["sites_enriched"] += 1
            except Exception as e:
                logger.debug("Site enrichment failed for company ID %s: %s", cid, e)

    return stats


def detect_dominant_company_from_recipients(recipients: list, db: Optional[Session] = None) -> Optional[str]:
    """
    Analyzes a list of recipients / emails and identifies if a single dominant company exists.
    Returns the company name if plurality >= 50% or sole corporate company; otherwise None.
    """
    if not recipients:
        return None
        
    counts = {}
    corporate_total = 0
    domains_to_lookup = set()

    for r in recipients:
        raw_email = getattr(r, "email", None) or (r.get("email") if isinstance(r, dict) else str(r))
        if not raw_email or "@" not in str(raw_email):
            continue
        email_clean = str(raw_email).strip().lower()
        domain = email_clean.split("@")[-1].strip().lower()
        if domain in PUBLIC_EMAIL_DOMAINS or not domain:
            continue
            
        explicit_company = getattr(r, "company", None) or (r.get("company") if isinstance(r, dict) else None)
        if explicit_company and str(explicit_company).strip() and str(explicit_company).strip() not in {"Unknown", "Independent", "N/A", "None"}:
            comp_name = str(explicit_company).strip()
        else:
            comp_name = KNOWN_DOMAIN_MAP.get(domain)
            if not comp_name and db:
                domains_to_lookup.add(domain)
            if not comp_name:
                comp_name = format_domain_to_company_name(domain)
                
        if comp_name:
            corporate_total += 1
            counts[comp_name] = counts.get(comp_name, 0) + 1

    if db and domains_to_lookup:
        try:
            from ..models.models import Company
            comps = db.query(Company).filter(Company.primary_domain.in_(list(domains_to_lookup))).all()
            domain_comp_map = {c.primary_domain.lower(): c.company_name for c in comps if c.company_name and c.primary_domain}
            if domain_comp_map:
                for domain, db_name in domain_comp_map.items():
                    for r in recipients:
                        em = (getattr(r, "email", None) or (r.get("email") if isinstance(r, dict) else "")).strip().lower()
                        if em.endswith(f"@{domain}"):
                            counts[db_name] = counts.get(db_name, 0) + 1
        except Exception:
            pass

    if not counts or corporate_total == 0:
        return None

    top_company, top_count = max(counts.items(), key=lambda x: x[1])
    percentage = (top_count / corporate_total) * 100

    if len(counts) == 1 or percentage >= 50 or (top_count >= 3 and percentage >= 40):
        return top_company

    return None


def auto_name_unnamed_campaigns(db: Session) -> int:
    """
    Exhaustively scans all campaigns in the database and automatically names any
    unnamed or generically-named campaigns (e.g. 'New Campaign', 'Draft', 'Untitled', etc.)
    by analyzing the recipient emails and logs to resolve the dominant company name.
    """
    from ..models.campaigns import Campaign, CampaignRecruiter, EmailLog

    camps = db.query(Campaign).all()
    renamed_count = 0

    for c in camps:
        curr_name = (c.name or "").strip()
        is_generic = (
            not curr_name
            or curr_name.lower() in {"new campaign", "draft", "campaign", "untitled", "new campaign template"}
            or curr_name.lower().startswith("new campaign")
            or curr_name.lower().startswith("instant speed campaign")
            or curr_name.lower().startswith("ab test campaign")
        )

        if not is_generic:
            continue

        crs = db.query(CampaignRecruiter).filter(CampaignRecruiter.campaign_id == c.campaign_id).all()
        logs = db.query(EmailLog).filter(EmailLog.campaign_id == c.campaign_id).all()

        emails = []
        if crs:
            r_ids = [cr.recruiter_id for cr in crs]
            recs = db.query(Recruiter).filter(Recruiter.recruiter_id.in_(r_ids)).all()
            for r in recs:
                if r.email:
                    emails.append({"email": r.email, "company": r.company.company_name if r.company else None})

        if logs:
            for l in logs:
                if l.recipient_email:
                    emails.append({"email": l.recipient_email})

        if not emails:
            continue

        dominant = detect_dominant_company_from_recipients(emails, db)
        if dominant and dominant.lower() != "company":
            c.name = dominant
            renamed_count += 1
            logger.info("[AUTO_NAME] Renamed Campaign #%s from '%s' to '%s'", c.campaign_id, curr_name, dominant)

    if renamed_count > 0:
        db.commit()
    return renamed_count


