"""
Phase 9: Timezone Inference, Company Scale Classification & Seniority Alignment
1. Injects accurate US Timezones (ET, CT, MT, PT, AK, HT) based on resolved states.
2. Classifies Company Scale (Mega-Enterprise, Enterprise, Mid-Market, Boutique) dynamically based on total candidate/recruiter footprint.
3. Aligns Seniority Level tags directly with frontend UI dropdown keys (Executive, Lead, Senior, Specialist, Campus).
"""
import os, sys, re, time
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r"c:\TalentOpsAI\backend")
sys.path.insert(0, r"c:\TalentOpsAI\backend\app")

import pandas as pd
import numpy as np
import logging
from collections import Counter

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("phase9_tz_scale")

PARQUET = r"c:\TalentOpsAI\backend\data\recruiters_full.parquet"

# State to Timezone Code Mapping
STATE_TO_TZ = {
    # Pacific Time (PT)
    "CA": "PT", "WA": "PT", "OR": "PT", "NV": "PT",
    # Mountain Time (MT)
    "CO": "MT", "AZ": "MT", "UT": "MT", "ID": "MT", "NM": "MT", "MT": "MT", "WY": "MT",
    # Central Time (CT)
    "TX": "CT", "IL": "CT", "MN": "CT", "MO": "CT", "WI": "CT", "TN": "CT", "LA": "CT",
    "OK": "CT", "KS": "CT", "IA": "CT", "AL": "CT", "MS": "CT", "AR": "CT", "NE": "CT",
    "SD": "CT", "ND": "CT",
    # Eastern Time (ET)
    "NY": "ET", "FL": "ET", "GA": "ET", "NC": "ET", "PA": "ET", "OH": "ET", "VA": "ET",
    "MA": "ET", "NJ": "ET", "MI": "ET", "MD": "ET", "IN": "ET", "SC": "ET", "CT": "ET",
    "KY": "ET", "DC": "ET", "ME": "ET", "NH": "ET", "RI": "ET", "VT": "ET", "DE": "ET",
    "WV": "ET",
    # Alaska & Hawaii
    "AK": "AK", "HI": "HT"
}

TZ_NAMES = {
    "PT": "America/Los_Angeles (Pacific Time)",
    "MT": "America/Denver (Mountain Time)",
    "CT": "America/Chicago (Central Time)",
    "ET": "America/New_York (Eastern Time)",
    "AK": "America/Anchorage (Alaska Time)",
    "HT": "Pacific/Honolulu (Hawaii Time)"
}

def main():
    log.info("Phase 9: Timezone Inference, Company Scale Classification & Seniority Alignment")
    t0 = time.time()
    df = pd.read_parquet(PARQUET)
    total_rows = len(df)
    log.info(f"Loaded {total_rows:,} records in {time.time()-t0:.2f}s")
    
    states = df['state'].astype(str).replace({'nan': '', 'None': ''}).tolist()
    companies = df['company_id'].astype(str).replace({'nan': '', 'None': ''}).tolist()
    seniorities = df['seniority_level'].astype(str).replace({'nan': '', 'None': ''}).tolist()
    titles = df['title'].astype(str).replace({'nan': '', 'None': ''}).tolist()
    
    timezone_codes = df['timezone_code'].astype(str).replace({'nan': '', 'None': ''}).tolist()
    timezones = df['timezone'].astype(str).replace({'nan': '', 'None': ''}).tolist()
    company_scales = df['company_scale'].astype(str).replace({'nan': '', 'None': ''}).tolist()
    
    # ── 1. Infer Timezones ──
    log.info("Step 1: Inferring accurate US Timezones from state geography...")
    for i in range(total_rows):
        st = states[i].strip().upper()
        if st in STATE_TO_TZ:
            tz_code = STATE_TO_TZ[st]
            timezone_codes[i] = tz_code
            timezones[i] = TZ_NAMES.get(tz_code, tz_code)
        else:
            timezone_codes[i] = "ET"
            timezones[i] = "America/New_York (Eastern Time)"
            
    tz_dist = Counter(timezone_codes)
    log.info("Timezone Breakdown:")
    for code, cnt in tz_dist.most_common():
        log.info(f"  {code:5s}: {cnt:>10,} ({cnt/total_rows*100:5.1f}%)")
        
    # ── 2. Classify Company Scale ──
    log.info("\nStep 2: Calculating dynamic Company Scale from recruiter density...")
    comp_counts = Counter(comp.strip() for comp in companies if comp.strip())
    
    for i in range(total_rows):
        comp = companies[i].strip()
        cnt = comp_counts.get(comp, 0)
        
        if cnt >= 5000:
            company_scales[i] = "Mega Enterprise"
        elif cnt >= 500:
            company_scales[i] = "Enterprise"
        elif cnt >= 100:
            company_scales[i] = "Mid-Market"
        elif cnt >= 10:
            company_scales[i] = "Growth Agency"
        else:
            company_scales[i] = "Boutique / Niche"
            
    scale_dist = Counter(company_scales)
    log.info("Company Scale Breakdown:")
    for scale, cnt in scale_dist.most_common():
        log.info(f"  {scale:20s}: {cnt:>10,} ({cnt/total_rows*100:5.1f}%)")
        
    # ── 3. Align Seniority with Frontend Keys ──
    log.info("\nStep 3: Aligning Seniority keys to Frontend UI schema...")
    for i in range(total_rows):
        s = seniorities[i].strip()
        if s in ("Lead / Manager", "Lead"):
            seniorities[i] = "Lead"
        elif s == "Senior":
            seniorities[i] = "Senior"
        elif s == "Executive":
            seniorities[i] = "Executive"
        elif s in ("Associate / Entry", "Campus"):
            seniorities[i] = "Campus"
        else:
            seniorities[i] = "Specialist"
            
    sen_dist = Counter(seniorities)
    log.info("Aligned Seniority Breakdown (matching frontend dropdowns):")
    for lvl, cnt in sen_dist.most_common():
        log.info(f"  {lvl:15s}: {cnt:>10,} ({cnt/total_rows*100:5.1f}%)")
        
    # Assign back
    df['timezone_code'] = timezone_codes
    df['timezone'] = timezones
    df['company_scale'] = company_scales
    df['seniority_level'] = seniorities
    
    # Save back to Parquet
    log.info("\nSaving updated dataset to Parquet...")
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
        
    log.info("Phase 9 Complete!")

if __name__ == "__main__":
    main()
