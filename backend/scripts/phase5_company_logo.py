"""
Phase 5: Company Canonicalization, Domain Resolution, and Logo Synthesis
Resolves canonical company names, brand domains, and attaches Clearbit logo URLs.
"""
import os, sys, re, time
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r"c:\TalentOpsAI\backend")
sys.path.insert(0, r"c:\TalentOpsAI\backend\app")

import pandas as pd
import logging
from collections import Counter, defaultdict

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("phase5_company_logo")

PARQUET = r"c:\TalentOpsAI\backend\data\recruiters_full.parquet"

FREE_DOMAINS = {
    "gmail.com","yahoo.com","hotmail.com","outlook.com","aol.com","icloud.com",
    "mail.com","protonmail.com","zoho.com","yandex.com","live.com","msn.com",
    "comcast.net","att.net","verizon.net","sbcglobal.net","me.com","mac.com",
    "cox.net","earthlink.net","charter.net","optonline.net","frontier.com",
    "missing.local","invalid.local","example.com","test.com","noemail.com"
}

KNOWN_COMPANY_MAP = {
    "teksystems": ("TEKsystems", "teksystems.com"),
    "insight global": ("Insight Global", "insightglobal.com"),
    "apex systems": ("Apex Systems", "apexsystems.com"),
    "aerotek": ("Aerotek", "aerotek.com"),
    "actalent": ("Actalent", "actalentservices.com"),
    "kforce": ("Kforce", "kforce.com"),
    "cybercoders": ("CyberCoders", "cybercoders.com"),
    "robert half": ("Robert Half", "roberthalf.com"),
    "manpower": ("ManpowerGroup", "manpowergroup.com"),
    "manpowergroup": ("ManpowerGroup", "manpowergroup.com"),
    "randstad": ("Randstad", "randstadusa.com"),
    "kelly services": ("Kelly Services", "kellyservices.com"),
    "beacon hill": ("Beacon Hill Staffing", "beaconhillstaffing.com"),
    "collabera": ("Collabera", "collabera.com"),
    "judge group": ("The Judge Group", "judge.com"),
    "the judge group": ("The Judge Group", "judge.com"),
    "system one": ("System One", "systemone.com"),
    "modis": ("Modis", "modis.com"),
    "disys": ("DISYS", "disys.com"),
    "prolink": ("Prolink Staffing", "prolinkstaff.com"),
    "lucas group": ("Lucas Group", "lucasgroup.com"),
    "allegis": ("Allegis Group", "allegisgroup.com"),
    "hays": ("Hays", "hays.com"),
    "adecco": ("Adecco", "adeccousa.com"),
}

def clean_company_name(raw: str) -> str:
    if not raw or not isinstance(raw, str):
        return ""
    c = raw.strip()
    if not c or c.lower() in ('nan', 'none', 'null', 'unknown', 'n/a'):
        return ""
    # Remove file extensions, parenthesis notes
    c = re.sub(r'\.xlsx?$|\.csv$', '', c, flags=re.IGNORECASE).strip()
    c = re.sub(r'[\(\[\{].*?[\)\]\}]', '', c).strip()
    c = re.sub(r'\s+', ' ', c).strip()
    return c

def main():
    log.info("Phase 5: Company Domain, Canonical ID, and Logo Synthesis")
    t0 = time.time()
    df = pd.read_parquet(PARQUET)
    total_rows = len(df)
    log.info(f"Loaded {total_rows:,} records in {time.time()-t0:.2f}s")
    
    company_ids = df['company_id'].astype(str).replace({'nan': '', 'None': ''}).tolist()
    emails = df['email'].astype(str).replace({'nan': '', 'None': ''}).tolist()
    canonical_company_ids = df['canonical_company_id'].astype(str).replace({'nan': '', 'None': ''}).tolist()
    logo_urls = df['logo_url'].astype(str).replace({'nan': '', 'None': ''}).tolist()
    
    before_logos = sum(1 for l in logo_urls if l.strip() and l.strip().lower() not in ('nan', 'none', ''))
    log.info(f"Before: Logos filled = {before_logos:,} / {total_rows:,} ({before_logos/total_rows*100:.1f}%)")
    
    # ── Step 1: Aggregate dominant domain per company ──
    log.info("Step 1: Mapping dominant domain per company...")
    company_domains = defaultdict(lambda: Counter())
    
    for i in range(total_rows):
        comp = company_ids[i].strip()
        e = emails[i].strip().lower()
        if comp and '@' in e:
            dom = e.split('@')[1].strip()
            if dom not in FREE_DOMAINS and '.' in dom:
                company_domains[comp][dom] += 1
                company_domains[comp.lower()][dom] += 1
    
    resolved_domains = {}
    for comp, counter in company_domains.items():
        if counter:
            best_dom, _ = counter.most_common(1)[0]
            resolved_domains[comp] = best_dom
            
    log.info(f"Resolved dominant domains for {len(resolved_domains):,} company keys")
    
    # ── Step 2: Canonicalize companies and attach Logos ──
    log.info("Step 2: Canonicalizing companies and generating logo URLs...")
    updated_canonical = 0
    updated_logos = 0
    
    for i in range(total_rows):
        comp = company_ids[i].strip()
        if not comp:
            continue
        
        c_low = comp.lower()
        
        # 1. Canonical Company Name
        canonical_name = None
        brand_domain = None
        
        if c_low in KNOWN_COMPANY_MAP:
            canonical_name, brand_domain = KNOWN_COMPANY_MAP[c_low]
        else:
            for k, (name, dom) in KNOWN_COMPANY_MAP.items():
                if k in c_low:
                    canonical_name, brand_domain = name, dom
                    break
        
        if not canonical_name:
            canonical_name = clean_company_name(comp)
            if canonical_name and (not canonical_company_ids[i] or canonical_company_ids[i].lower() in ('nan', 'none', '')):
                canonical_company_ids[i] = canonical_name
                updated_canonical += 1
        else:
            canonical_company_ids[i] = canonical_name
            updated_canonical += 1
        
        # 2. Domain & Logo
        dom = brand_domain or resolved_domains.get(comp) or resolved_domains.get(c_low)
        if dom and '.' in dom and dom not in FREE_DOMAINS:
            logo_urls[i] = f"https://logo.clearbit.com/{dom}?size=128"
            updated_logos += 1
            
    log.info(f"Updated/Standardized canonical names: {updated_canonical:,}")
    log.info(f"Generated/Attached logo URLs: {updated_logos:,}")
    
    df['canonical_company_id'] = canonical_company_ids
    df['logo_url'] = logo_urls
    
    after_logos = sum(1 for l in logo_urls if l.strip() and l.strip().lower() not in ('nan', 'none', ''))
    log.info(f"After: Logos filled = {after_logos:,} / {total_rows:,} ({after_logos/total_rows*100:.1f}%)")
    log.info(f"Logo Gain: +{after_logos - before_logos:,} records (+{(after_logos-before_logos)/total_rows*100:.1f}%)")
    
    log.info("Saving updated dataset to Parquet...")
    t_save = time.time()
    df.to_parquet(PARQUET, index=False, engine='pyarrow')
    log.info(f"Saved to {PARQUET} ({os.path.getsize(PARQUET)/1024/1024:.2f} MB) in {time.time()-t_save:.2f}s")
    
    # Reload RecruiterStore
    log.info("Reloading RecruiterStore...")
    try:
        from app.services.recruiter_store import recruiter_store
        recruiter_store.reload()
        log.info(f"RecruiterStore reloaded with {recruiter_store.total_count:,} records")
    except Exception as e:
        log.warning(f"RecruiterStore reload skipped: {e}")
        
    log.info("Phase 5 Complete!")

if __name__ == "__main__":
    main()
