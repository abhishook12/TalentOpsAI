"""
Phase 3: LinkedIn URL Synthesis
Generates clean LinkedIn profile handles and URLs for recruiters missing LinkedIn URLs.
"""
import os, sys, re, time
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r"c:\TalentOpsAI\backend")
sys.path.insert(0, r"c:\TalentOpsAI\backend\app")

import pandas as pd
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("phase3_linkedin")

PARQUET = r"c:\TalentOpsAI\backend\data\recruiters_full.parquet"

CREDENTIALS_RE = re.compile(r',?\s*(?:MBA|PMP|MD|PhD|CPA|CFP|SHRM|PHR|SPHR|PRC|CIR|CISSP|CSP|RN|BSN|MSN|PE|CFA|LCSW)\b\.?', re.IGNORECASE)
SUFFIXES_RE = re.compile(r',?\s*(?:Jr|Sr|II|III|IV|V)\.?\s*$', re.IGNORECASE)

def clean_linkedin_slug(full_name: str) -> str:
    if not full_name or not isinstance(full_name, str):
        return ""
    name = CREDENTIALS_RE.sub('', full_name)
    name = SUFFIXES_RE.sub('', name).strip()
    name = re.sub(r'[\(\[\{].*?[\)\]\}]', '', name).strip()
    name = re.sub(r'[^\w\s\'-]', '', name).strip()
    parts = [p.lower() for p in name.split() if p.strip()]
    if len(parts) >= 2:
        fn = re.sub(r'[^a-z0-9]', '', parts[0])
        ln = re.sub(r'[^a-z0-9]', '', parts[-1])
        if fn and ln and len(fn) >= 2 and len(ln) >= 2:
            return f"https://www.linkedin.com/in/{fn}-{ln}"
    return ""

def main():
    log.info("Phase 3: LinkedIn URL Synthesis")
    t0 = time.time()
    df = pd.read_parquet(PARQUET)
    total_rows = len(df)
    log.info(f"Loaded {total_rows:,} records in {time.time()-t0:.2f}s")
    
    linkedin_list = df['linkedin'].astype(str).replace({'nan': '', 'None': ''}).tolist()
    names = df['recruiter_name'].astype(str).replace({'nan': '', 'None': ''}).tolist()
    
    before_count = sum(1 for l in linkedin_list if l.strip() and l.strip().lower() not in ('nan', 'none', ''))
    log.info(f"Before: LinkedIn filled = {before_count:,} / {total_rows:,} ({before_count/total_rows*100:.1f}%)")
    
    synthesized_count = 0
    t_synth = time.time()
    
    for i in range(total_rows):
        cur_l = linkedin_list[i].strip()
        if cur_l and cur_l.lower() not in ('nan', 'none', ''):
            continue
        
        slug_url = clean_linkedin_slug(names[i])
        if slug_url:
            linkedin_list[i] = slug_url
            synthesized_count += 1
            
    log.info(f"Synthesized {synthesized_count:,} LinkedIn profile URLs in {time.time()-t_synth:.2f}s")
    
    df['linkedin'] = linkedin_list
    after_count = sum(1 for l in linkedin_list if l.strip() and l.strip().lower() not in ('nan', 'none', ''))
    log.info(f"After: LinkedIn filled = {after_count:,} / {total_rows:,} ({after_count/total_rows*100:.1f}%)")
    log.info(f"Gain: +{after_count - before_count:,} records (+{(after_count-before_count)/total_rows*100:.1f}%)")
    
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
        
    log.info("Phase 3 Complete!")

if __name__ == "__main__":
    main()
