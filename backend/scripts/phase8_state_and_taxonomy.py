"""
Phase 8: State Resolution & Taxonomy/Seniority Auto-Classification
1. Resolves US State from corporate headquarters & dominant company hubs.
2. Auto-classifies Seniority Level (Entry -> Executive) and Specialization Sector (Tech, Healthcare, Finance, etc.) across 933,821 titles.
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
log = logging.getLogger("state_and_taxonomy")

PARQUET = r"c:\TalentOpsAI\backend\data\recruiters_full.parquet"

# Corporate HQ & Primary Hub States for Major Staffing & Enterprise Firms
COMPANY_HQ_STATES = {
    "teksystems": "MD",
    "insight global": "GA",
    "apex systems": "VA",
    "aerotek": "MD",
    "actalent": "MD",
    "kforce": "FL",
    "cybercoders": "CA",
    "robert half": "CA",
    "manpower": "WI",
    "manpowergroup": "WI",
    "randstad": "GA",
    "kelly services": "MI",
    "beacon hill": "MA",
    "collabera": "NJ",
    "judge group": "PA",
    "the judge group": "PA",
    "system one": "PA",
    "modis": "FL",
    "disys": "VA",
    "prolink": "OH",
    "lucas group": "GA",
    "allegis": "MD",
    "allegis group": "MD",
    "hays": "FL",
    "adecco": "FL",
    "crossfire consulting": "NY",
    "swoon": "IL",
    "idr": "GA",
    "idr, inc.": "GA",
    "roth staffing": "CA",
    "innova solutions": "GA",
    "inspyr solutions": "FL",
    "eliassen group": "MA",
    "mondo": "NY",
    "vaco": "TN",
    "genesis10": "NY",
    "apex life sciences": "VA",
    "motion recruitment": "MA",
    "piper companies": "NC",
}

# Seniority Regex Patterns
RE_EXEC = re.compile(r'\b(?:vp|vice president|president|partner|founder|co-founder|ceo|coo|cto|cfo|chief|managing director|principal partner|owner)\b', re.IGNORECASE)
RE_DIR = re.compile(r'\b(?:director|head of|divisional head)\b', re.IGNORECASE)
RE_MGR = re.compile(r'\b(?:manager|lead|principal|supervisor|team lead|managing|practice lead)\b', re.IGNORECASE)
RE_SR = re.compile(r'\b(?:senior|sr\.?|level iii|level 3|experienced|advanced)\b', re.IGNORECASE)
RE_JR = re.compile(r'\b(?:junior|jr\.?|associate|intern|trainee|coordinator|assistant|level i|level 1)\b', re.IGNORECASE)

# Specialization Taxonomy Patterns
RE_TECH = re.compile(r'\b(?:tech|software|developer|engineer|engineering|it|cloud|devops|aws|azure|data|python|java|javascript|fullstack|frontend|backend|cyber|security|infrastructure|architect|qa|scrum|ai|ml|machine learning)\b', re.IGNORECASE)
RE_HEALTH = re.compile(r'\b(?:health|healthcare|nurse|nursing|clinical|physician|pharma|pharmaceutical|biotech|medical|therapist|allied)\b', re.IGNORECASE)
RE_FIN = re.compile(r'\b(?:finance|financial|accounting|accountant|tax|audit|banking|wealth|cpa|risk|analyst|treasury)\b', re.IGNORECASE)
RE_EXEC_SEARCH = re.compile(r'\b(?:executive search|c-suite|retained search|leadership hiring|talent advisory)\b', re.IGNORECASE)
RE_SALES = re.compile(r'\b(?:sales|account executive|business development|marketing|growth|bdr|sdr|client partner)\b', re.IGNORECASE)
RE_HR = re.compile(r'\b(?:human resources|hr|people ops|talent acquisition|talent partner|recruiting coordinator|staffing specialist)\b', re.IGNORECASE)

def classify_seniority(title: str) -> str:
    if not title or not isinstance(title, str):
        return "Mid-Level"
    t = title.lower().strip()
    if RE_EXEC.search(t):
        return "Executive"
    if RE_DIR.search(t):
        return "Director"
    if RE_MGR.search(t):
        return "Lead / Manager"
    if RE_SR.search(t):
        return "Senior"
    if RE_JR.search(t):
        return "Associate / Entry"
    return "Mid-Level"

def classify_sector(title: str, current_spec: str) -> str:
    combined = f"{title} {current_spec}".lower().strip()
    if RE_TECH.search(combined):
        return "Technology & Engineering"
    if RE_HEALTH.search(combined):
        return "Healthcare & Life Sciences"
    if RE_FIN.search(combined):
        return "Finance & Accounting"
    if RE_EXEC_SEARCH.search(combined):
        return "Executive Search"
    if RE_SALES.search(combined):
        return "Sales & Commercial"
    if RE_HR.search(combined):
        return "HR & Talent Operations"
    return "Professional Staffing"

def main():
    log.info("Phase 8: State Resolution & Taxonomy/Seniority Auto-Classification")
    t0 = time.time()
    df = pd.read_parquet(PARQUET)
    total_rows = len(df)
    log.info(f"Loaded {total_rows:,} records in {time.time()-t0:.2f}s")
    
    states = df['state'].astype(str).replace({'nan': '', 'None': ''}).tolist()
    companies = df['company_id'].astype(str).replace({'nan': '', 'None': ''}).tolist()
    titles = df['title'].astype(str).replace({'nan': '', 'None': ''}).tolist()
    specs = df['specialization'].astype(str).replace({'nan': '', 'None': ''}).tolist()
    state_sources = df['state_source'].astype(str).replace({'nan': '', 'None': ''}).tolist()
    state_confidences = df['state_confidence'].astype(str).replace({'nan': '', 'None': ''}).tolist()
    
    seniority_levels = df['seniority_level'].astype(str).replace({'nan': '', 'None': ''}).tolist()
    taxonomy_categories = df['taxonomy_category'].astype(str).replace({'nan': '', 'None': ''}).tolist()
    
    # ── 1. Map Dominant State Per Company ──
    log.info("Step 1: Calculating dominant regional hubs per company...")
    company_state_counts = defaultdict(lambda: Counter())
    
    for i in range(total_rows):
        st = states[i].strip().upper()
        comp = companies[i].strip()
        if comp and st and st != 'US' and len(st) == 2:
            company_state_counts[comp][st] += 1
            company_state_counts[comp.lower()][st] += 1
            
    dominant_company_states = {}
    for comp, counter in company_state_counts.items():
        if counter:
            best_st, count = counter.most_common(1)[0]
            if count >= 3 or (count >= 1 and len(counter) == 1):
                dominant_company_states[comp] = best_st
                
    log.info(f"Identified dominant state hubs for {len(dominant_company_states):,} company keys")
    
    # ── 2. Resolve Missing/Generic States ──
    log.info("Step 2: Resolving generic 'US' states to corporate hubs...")
    resolved_states = 0
    
    for i in range(total_rows):
        st = states[i].strip().upper()
        if st and st != 'US' and len(st) == 2:
            continue  # Already has a specific state
            
        comp = companies[i].strip()
        if not comp:
            continue
        c_low = comp.lower()
        
        target_state = None
        source_tag = None
        
        if c_low in COMPANY_HQ_STATES:
            target_state = COMPANY_HQ_STATES[c_low]
            source_tag = "company_hq_rule"
        else:
            for k, hq_st in COMPANY_HQ_STATES.items():
                if k in c_low:
                    target_state = hq_st
                    source_tag = "company_hq_rule"
                    break
                    
        if not target_state:
            if comp in dominant_company_states:
                target_state = dominant_company_states[comp]
                source_tag = "company_dominant_hub"
            elif c_low in dominant_company_states:
                target_state = dominant_company_states[c_low]
                source_tag = "company_dominant_hub"
                
        if target_state:
            states[i] = target_state
            state_sources[i] = source_tag
            state_confidences[i] = "85"
            resolved_states += 1
            
    log.info(f"Resolved specific US states for {resolved_states:,} recruiters!")
    
    # ── 3. Classify Seniority & Specialization Taxonomy ──
    log.info("Step 3: Classifying Seniority Levels and Specialization Taxonomies across all 933k records...")
    t_tax = time.time()
    
    for i in range(total_rows):
        t = titles[i]
        sp = specs[i]
        
        seniority = classify_seniority(t)
        sector = classify_sector(t, sp)
        
        seniority_levels[i] = seniority
        taxonomy_categories[i] = sector
        if not sp or sp.lower() in ('nan', 'none', 'general', ''):
            specs[i] = sector
            
    log.info(f"Seniority & Taxonomy classification complete in {time.time()-t_tax:.2f}s")
    
    # Seniority distribution
    sen_dist = Counter(seniority_levels)
    log.info("Seniority Breakdown:")
    for lvl, cnt in sen_dist.most_common():
        log.info(f"  {lvl:20s}: {cnt:>10,} ({cnt/total_rows*100:5.1f}%)")
        
    # Taxonomy distribution
    tax_dist = Counter(taxonomy_categories)
    log.info("\nTaxonomy Sector Breakdown:")
    for sec, cnt in tax_dist.most_common():
        log.info(f"  {sec:30s}: {cnt:>10,} ({cnt/total_rows*100:5.1f}%)")
        
    # Update DataFrame
    df['state'] = states
    df['state_source'] = state_sources
    df['state_confidence'] = state_confidences
    df['seniority_level'] = seniority_levels
    df['taxonomy_category'] = taxonomy_categories
    df['specialization'] = specs
    
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
        
    log.info("Phase 8 Complete!")

if __name__ == "__main__":
    main()
