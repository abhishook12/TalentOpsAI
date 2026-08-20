"""
Phase 2: High-Performance Email Pattern Discovery & Synthesis
Extracts naming patterns from existing emails and synthesizes valid emails for missing records.
"""
import os, sys, re, time
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r"c:\TalentOpsAI\backend")
sys.path.insert(0, r"c:\TalentOpsAI\backend\app")

import pandas as pd
import numpy as np
import logging
from collections import Counter, defaultdict

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("phase2_fast")

PARQUET = r"c:\TalentOpsAI\backend\data\recruiters_full.parquet"

FREE_DOMAINS = {
    "gmail.com","yahoo.com","hotmail.com","outlook.com","aol.com","icloud.com",
    "mail.com","protonmail.com","zoho.com","yandex.com","live.com","msn.com",
    "comcast.net","att.net","verizon.net","sbcglobal.net","me.com","mac.com",
    "cox.net","earthlink.net","charter.net","optonline.net","frontier.com",
    "missing.local","invalid.local","example.com","test.com","noemail.com"
}

KNOWN_COMPANY_PATTERNS = {
    "teksystems": ("teksystems.com", "{f1}{last}"),
    "insight global": ("insightglobal.com", "{first}.{last}"),
    "apex systems": ("apexsystems.com", "{f1}{last}"),
    "aerotek": ("aerotek.com", "{first}.{last}"),
    "actalent": ("actalentservices.com", "{first}.{last}"),
    "kforce": ("kforce.com", "{first}.{last}"),
    "cybercoders": ("cybercoders.com", "{first}.{last}"),
    "robert half": ("roberthalf.com", "{first}.{last}"),
    "manpower": ("manpower.com", "{first}.{last}"),
    "manpowergroup": ("manpowergroup.com", "{first}.{last}"),
    "randstad": ("randstadusa.com", "{first}.{last}"),
    "kelly services": ("kellyservices.com", "{first}.{last}"),
    "beacon hill": ("beaconhillstaffing.com", "{first}.{last}"),
    "collabera": ("collabera.com", "{first}.{last}"),
    "judge group": ("judge.com", "{first}.{last}"),
    "the judge group": ("judge.com", "{first}.{last}"),
}

CREDENTIALS_RE = re.compile(r',?\s*(?:MBA|PMP|MD|PhD|CPA|CFP|SHRM|PHR|SPHR|PRC|CIR|CISSP|CSP|RN|BSN|MSN|PE|CFA|LCSW)\b\.?', re.IGNORECASE)
SUFFIXES_RE = re.compile(r',?\s*(?:Jr|Sr|II|III|IV|V)\.?\s*$', re.IGNORECASE)
EMAIL_RE = re.compile(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$')

def extract_names(full_name: str):
    if not full_name or not isinstance(full_name, str):
        return "", ""
    name = CREDENTIALS_RE.sub('', full_name)
    name = SUFFIXES_RE.sub('', name).strip()
    # Remove parens / brackets
    name = re.sub(r'[\(\[\{].*?[\)\]\}]', '', name).strip()
    # Remove weird non-ascii or numbers
    name = re.sub(r'[^\w\s\.\'-]', '', name).strip()
    parts = name.split()
    if len(parts) >= 2:
        return parts[0].strip(), parts[-1].strip()
    return "", ""

def get_email_pattern(first_name: str, last_name: str, email: str, domain: str) -> str:
    local_part = email.split('@')[0].lower()
    f = re.sub(r'[^a-z0-9]', '', first_name.lower())
    l = re.sub(r'[^a-z0-9]', '', last_name.lower())
    f1 = f[0] if f else ""
    l1 = l[0] if l else ""
    if f and l:
        if local_part == f"{f}.{l}": return "{first}.{last}"
        if local_part == f"{f}{l}": return "{first}{last}"
        if local_part == f"{f}_{l}": return "{first}_{last}"
        if local_part == f"{f}-{l}": return "{first}-{last}"
        if local_part == f"{f1}{l}": return "{f1}{last}"
        if local_part == f"{f}{l1}": return "{first}{l1}"
        if local_part == f"{l}.{f}": return "{last}.{first}"
        if local_part == f"{l}{f1}": return "{last}{f1}"
        if local_part == f: return "{first}"
        if local_part == l: return "{last}"
    return "unknown"

def generate_email(first_name: str, last_name: str, domain: str, pattern: str) -> str:
    f = re.sub(r'[^a-z0-9]', '', first_name.lower())
    l = re.sub(r'[^a-z0-9]', '', last_name.lower())
    f1 = f[0] if f else ""
    l1 = l[0] if l else ""
    local = pattern.replace("{first}", f).replace("{last}", l).replace("{f1}", f1).replace("{l1}", l1)
    local = re.sub(r'[^a-z0-9._-]', '', local)
    local = re.sub(r'\.{2,}', '.', local)
    local = local.strip('._-')
    if not local:
        return ""
    return f"{local}@{domain.lower().strip()}"

def is_valid_email(email: str) -> bool:
    if not email or not isinstance(email, str):
        return False
    return bool(EMAIL_RE.match(email.strip()))

def main():
    log.info("Phase 2: High-Performance Email Pattern Discovery & Synthesis")
    t0 = time.time()
    df = pd.read_parquet(PARQUET)
    total_rows = len(df)
    log.info(f"Loaded {total_rows:,} records in {time.time()-t0:.2f}s")
    
    # Pre-extract lists to avoid pandas indexing overhead
    emails = df['email'].astype(str).replace({'nan': '', 'None': '', 'None': ''}).tolist()
    names = df['recruiter_name'].astype(str).replace({'nan': '', 'None': ''}).tolist()
    companies = df['company_id'].astype(str).replace({'nan': '', 'None': ''}).tolist()
    
    email_generated = df['email_generated'].astype(str).replace({'nan': '', 'None': ''}).tolist()
    email_source = df['email_source'].astype(str).replace({'nan': '', 'None': ''}).tolist()
    email_confidence = df['email_confidence'].fillna(0).astype(np.int64).tolist()
    email_pattern_id = df['email_pattern_id'].astype(str).replace({'nan': '', 'None': ''}).tolist()
    raw_email_value = df['raw_email_value'].astype(str).replace({'nan': '', 'None': ''}).tolist()
    
    has_email_count = sum(1 for e in emails if e.strip() and e.strip().lower() not in ('nan', 'none', ''))
    log.info(f"Before: Email filled = {has_email_count:,} / {total_rows:,} ({has_email_count/total_rows*100:.1f}%)")
    
    # ── Step 1: Discover Patterns Per Company ──
    log.info("Step 1: Discovering company email patterns from existing emails...")
    t_start_disc = time.time()
    
    company_pattern_counts = defaultdict(lambda: Counter())
    company_domain_counts = defaultdict(lambda: Counter())
    
    for i in range(total_rows):
        e = emails[i].strip().lower()
        if not e or '@' not in e:
            continue
        domain = e.split('@')[1].strip()
        if domain in FREE_DOMAINS or '.' not in domain:
            continue
        comp = companies[i].strip()
        if not comp:
            continue
        
        fn, ln = extract_names(names[i])
        if not fn or not ln or len(fn) < 2 or len(ln) < 2:
            continue
        
        pat = get_email_pattern(fn, ln, e, domain)
        if pat != "unknown":
            company_pattern_counts[comp][pat] += 1
            company_domain_counts[comp][domain] += 1
            # Also register for lowercase company key
            comp_lower = comp.lower()
            if comp_lower != comp:
                company_pattern_counts[comp_lower][pat] += 1
                company_domain_counts[comp_lower][domain] += 1
    
    company_rules = {}
    for comp, pat_counter in company_pattern_counts.items():
        if not pat_counter:
            continue
        dom_counter = company_domain_counts[comp]
        if not dom_counter:
            continue
        best_pat, pat_cnt = pat_counter.most_common(1)[0]
        best_dom, dom_cnt = dom_counter.most_common(1)[0]
        total_pats = sum(pat_counter.values())
        
        ratio = pat_cnt / total_pats
        if pat_cnt >= 3 and ratio >= 0.85:
            conf = 90
        elif pat_cnt >= 2 and ratio >= 0.70:
            conf = 75
        elif pat_cnt >= 1:
            conf = 60
        else:
            continue
        
        company_rules[comp] = (best_dom, best_pat, conf)
    
    log.info(f"Discovered pattern rules for {len(company_rules):,} distinct company keys in {time.time()-t_start_disc:.2f}s")
    
    # ── Step 2: Synthesize Missing Emails ──
    log.info("Step 2: Synthesizing missing emails...")
    t_start_syn = time.time()
    synthesized_count = 0
    
    for i in range(total_rows):
        e = emails[i].strip()
        if e and e.lower() not in ('nan', 'none', ''):
            continue # Already has email
        
        comp = companies[i].strip()
        if not comp:
            continue
        
        fn, ln = extract_names(names[i])
        if not fn or not ln or len(fn) < 2 or len(ln) < 2:
            continue
        
        rule = None
        if comp in company_rules:
            rule = company_rules[comp]
        elif comp.lower() in company_rules:
            rule = company_rules[comp.lower()]
        elif comp.lower() in KNOWN_COMPANY_PATTERNS:
            dom, pat = KNOWN_COMPANY_PATTERNS[comp.lower()]
            rule = (dom, pat, 85)
        else:
            # Check for partial match in known company patterns
            c_low = comp.lower()
            for k, v in KNOWN_COMPANY_PATTERNS.items():
                if k in c_low:
                    rule = (v[0], v[1], 80)
                    break
        
        if not rule:
            continue
        
        domain, pattern, conf = rule
        gen_email = generate_email(fn, ln, domain, pattern)
        if not is_valid_email(gen_email):
            continue
        
        emails[i] = gen_email
        email_generated[i] = "True"
        email_source[i] = "pattern_synthesis"
        email_confidence[i] = int(conf)
        email_pattern_id[i] = pattern
        raw_email_value[i] = gen_email
        synthesized_count += 1
    
    log.info(f"Synthesized {synthesized_count:,} new emails in {time.time()-t_start_syn:.2f}s")
    
    # Put arrays back into DataFrame
    log.info("Updating DataFrame columns...")
    df['email'] = emails
    df['email_generated'] = email_generated
    df['email_source'] = email_source
    df['email_confidence'] = email_confidence
    df['email_pattern_id'] = email_pattern_id
    df['raw_email_value'] = raw_email_value
    
    after_count = sum(1 for e in emails if e.strip() and e.strip().lower() not in ('nan', 'none', ''))
    log.info(f"After: Email filled = {after_count:,} / {total_rows:,} ({after_count/total_rows*100:.1f}%)")
    log.info(f"Total Gain: +{after_count - has_email_count:,} records (+{(after_count-has_email_count)/total_rows*100:.1f}%)")
    
    # Save back to Parquet
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
    
    log.info("Phase 2 Complete!")

if __name__ == "__main__":
    main()
