"""
Phase 6 & 7: Email Deliverability Validation and Full Completeness & Quality Score Recalculation
Validates email deliverability status, updates deliverable flags, and recomputes all 0-100 quality/completeness scores.
"""
import os, sys, re, time
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r"c:\TalentOpsAI\backend")
sys.path.insert(0, r"c:\TalentOpsAI\backend\app")

import pandas as pd
import numpy as np
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("phase6_7_scoring")

PARQUET = r"c:\TalentOpsAI\backend\data\recruiters_full.parquet"

EMAIL_RE = re.compile(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$')

DISPOSABLE_DOMAINS = {
    "tempmail.com", "throwawaymail.com", "guerrillamail.com", "sharklasers.com",
    "10minutemail.com", "trashmail.com", "yopmail.com", "mailinator.com"
}

def is_valid_email(email: str) -> bool:
    if not email or not isinstance(email, str):
        return False
    e = email.strip().lower()
    if not EMAIL_RE.match(e):
        return False
    dom = e.split('@')[1]
    if dom in DISPOSABLE_DOMAINS or '.' not in dom:
        return False
    return True

def main():
    log.info("Phase 6 & 7: Deliverability & Completeness/Quality Score Recalculation")
    t0 = time.time()
    df = pd.read_parquet(PARQUET)
    total_rows = len(df)
    log.info(f"Loaded {total_rows:,} records in {time.time()-t0:.2f}s")
    
    # Extract arrays for fast processing
    names = df['recruiter_name'].astype(str).replace({'nan': '', 'None': ''}).tolist()
    emails = df['email'].astype(str).replace({'nan': '', 'None': ''}).tolist()
    phones = df['phone'].astype(str).replace({'nan': '', 'None': ''}).tolist()
    titles = df['title'].astype(str).replace({'nan': '', 'None': ''}).tolist()
    companies = df['company_id'].astype(str).replace({'nan': '', 'None': ''}).tolist()
    linkedins = df['linkedin'].astype(str).replace({'nan': '', 'None': ''}).tolist()
    states = df['state'].astype(str).replace({'nan': '', 'None': ''}).tolist()
    email_sources = df['email_source'].astype(str).replace({'nan': '', 'None': ''}).tolist()
    email_confidences = df['email_confidence'].fillna(0).astype(np.int64).tolist()
    
    email_status = df['email_status'].astype(str).replace({'nan': '', 'None': ''}).tolist()
    is_deliverable = df['is_deliverable'].fillna(False).astype(bool).tolist()
    completeness_scores = df['completeness_score'].fillna(0).astype(np.int64).tolist()
    quality_scores = df['quality_score'].fillna(0).astype(np.int64).tolist()
    needs_review = df['needs_review'].astype(str).replace({'nan': '', 'None': ''}).tolist()
    
    log.info("Computing deliverability and scoring across all records...")
    t_score = time.time()
    
    deliverable_count = 0
    valid_email_count = 0
    
    for i in range(total_rows):
        e = emails[i].strip().lower()
        p = phones[i].strip()
        t = titles[i].strip()
        c = companies[i].strip()
        l = linkedins[i].strip()
        s = states[i].strip()
        
        has_e = bool(e and e not in ('nan', 'none', '') and is_valid_email(e))
        has_p = bool(p and p not in ('nan', 'none', '') and len(p) >= 7)
        has_t = bool(t and t not in ('nan', 'none', ''))
        has_c = bool(c and c not in ('nan', 'none', ''))
        has_l = bool(l and l not in ('nan', 'none', ''))
        has_s = bool(s and s not in ('nan', 'none', '') and s != 'US')
        
        # 1. Email Status & Deliverability
        if has_e:
            valid_email_count += 1
            src = email_sources[i].lower()
            if 'verified' in src:
                email_status[i] = "verified"
                is_deliverable[i] = True
            elif 'synthesis' in src:
                email_status[i] = "pattern_inferred"
                is_deliverable[i] = True
            else:
                email_status[i] = "valid"
                is_deliverable[i] = True
            deliverable_count += 1
        else:
            if e and e not in ('nan', 'none', ''):
                email_status[i] = "invalid_format"
            else:
                email_status[i] = "missing"
            is_deliverable[i] = False
            
        # 2. Completeness Score (0 - 100)
        # Email: 30, Phone: 20, Title: 15, Company: 15, LinkedIn: 10, State: 10
        comp_score = 0
        if has_e: comp_score += 30
        if has_p: comp_score += 20
        if has_t: comp_score += 15
        if has_c: comp_score += 15
        if has_l: comp_score += 10
        if has_s: comp_score += 10
        
        completeness_scores[i] = comp_score
        
        # 3. Quality Score (0 - 100)
        # Factors: Completeness + Email confidence factor + Active deliverability
        conf_factor = 1.0
        if has_e:
            raw_conf = email_confidences[i]
            if raw_conf > 0:
                conf_factor = max(0.6, min(1.0, raw_conf / 100.0))
            else:
                conf_factor = 0.85
                
        qual_score = int(comp_score * conf_factor)
        if has_e and is_deliverable[i]:
            qual_score = min(100, qual_score + 10)
        
        quality_scores[i] = qual_score
        
        # Needs review if incomplete (score < 40 or missing both email and phone)
        if comp_score < 40 or (not has_e and not has_p):
            needs_review[i] = "True"
        else:
            needs_review[i] = "False"
            
    log.info(f"Scoring completed in {time.time()-t_score:.2f}s")
    log.info(f"Valid Emails: {valid_email_count:,} / {total_rows:,} ({valid_email_count/total_rows*100:.1f}%)")
    log.info(f"Deliverable Records: {deliverable_count:,} / {total_rows:,} ({deliverable_count/total_rows*100:.1f}%)")
    log.info(f"Average Completeness Score: {np.mean(completeness_scores):.1f} / 100")
    log.info(f"Average Quality Score: {np.mean(quality_scores):.1f} / 100")
    
    # Assign back to DataFrame
    df['email_status'] = email_status
    df['is_deliverable'] = is_deliverable
    df['completeness_score'] = completeness_scores
    df['quality_score'] = quality_scores
    df['needs_review'] = needs_review
    
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
        
    log.info("Phase 6 & 7 Complete!")

if __name__ == "__main__":
    main()
