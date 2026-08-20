"""
Phase 1: Normalized City Extraction
Extracts city names from the 'location' field into 'normalized_city'.
"""
import os, sys, re, time
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r"c:\TalentOpsAI\backend")
sys.path.insert(0, r"c:\TalentOpsAI\backend\app")

import pandas as pd
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("phase1")

PARQUET = r"c:\TalentOpsAI\backend\data\recruiters_full.parquet"

STATE_ABBRS = {
    "AL","AK","AZ","AR","CA","CO","CT","DE","DC","FL","GA","HI","ID","IL","IN",
    "IA","KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH",
    "NJ","NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT",
    "VT","VA","WA","WV","WI","WY"
}

STATE_NAMES = {
    "alabama","alaska","arizona","arkansas","california","colorado","connecticut",
    "delaware","district of columbia","florida","georgia","hawaii","idaho","illinois",
    "indiana","iowa","kansas","kentucky","louisiana","maine","maryland","massachusetts",
    "michigan","minnesota","mississippi","missouri","montana","nebraska","nevada",
    "new hampshire","new jersey","new mexico","new york","north carolina","north dakota",
    "ohio","oklahoma","oregon","pennsylvania","rhode island","south carolina",
    "south dakota","tennessee","texas","utah","vermont","virginia","washington",
    "west virginia","wisconsin","wyoming"
}

ZIP_RE = re.compile(r'\b\d{5}(?:-\d{4})?\b')
COUNTRY_TOKENS = {"usa", "us", "united states", "united states of america", "america"}

def extract_city(location: str) -> str:
    if not location or not isinstance(location, str):
        return ""
    loc = location.strip()
    if not loc or loc.lower() in ("none", "nan", "null", "n/a", "unknown", ""):
        return ""
    loc = ZIP_RE.sub("", loc).strip()
    for ct in COUNTRY_TOKENS:
        if loc.lower().rstrip(" ,").endswith(ct):
            loc = loc[:loc.lower().rfind(ct)].rstrip(" ,")
    parts = [p.strip() for p in loc.split(",") if p.strip()]
    if not parts:
        return ""
    first_upper = parts[0].strip().upper()
    first_lower = parts[0].strip().lower()
    if first_upper in STATE_ABBRS or first_lower in STATE_NAMES:
        return ""
    city = parts[0].strip()
    if len(parts) == 1:
        tokens = city.split()
        if len(tokens) >= 2 and tokens[-1].upper() in STATE_ABBRS:
            city = " ".join(tokens[:-1])
        elif len(tokens) >= 3 and " ".join(tokens[-2:]).lower() in STATE_NAMES:
            city = " ".join(tokens[:-2])
    city = re.sub(r'[^\w\s\.\'-]', '', city).strip()
    city = re.sub(r'\s+', ' ', city)
    if not city or len(city) < 2:
        return ""
    city = city.title()
    city = city.replace("'S", "'s").replace(" Of ", " of ").replace(" The ", " the ")
    if re.match(r'^\d+$', city):
        return ""
    return city

def main():
    log.info("Phase 1: Normalized City Extraction")
    t0 = time.time()
    df = pd.read_parquet(PARQUET)
    log.info(f"Loaded {len(df):,} records in {time.time()-t0:.2f}s")
    before_filled = df['normalized_city'].notna() & (df['normalized_city'].astype(str).str.strip() != '') & (df['normalized_city'].astype(str).str.lower() != 'nan')
    before_count = before_filled.sum()
    log.info(f"Before: normalized_city filled = {before_count:,} / {len(df):,} ({before_count/len(df)*100:.1f}%)")
    needs_city = ~before_filled & df['location'].notna() & (df['location'].astype(str).str.strip() != '') & (df['location'].astype(str).str.lower() != 'nan')
    candidates = needs_city.sum()
    log.info(f"Candidates for city extraction: {candidates:,}")
    filled_count = 0
    t1 = time.time()
    for idx in df[needs_city].index:
        location = str(df.at[idx, 'location'])
        city = extract_city(location)
        if city:
            df.at[idx, 'normalized_city'] = city
            filled_count += 1
        if filled_count % 50000 == 0 and filled_count > 0:
            log.info(f"  Extracted {filled_count:,} cities so far...")
    log.info(f"Extracted {filled_count:,} cities in {time.time()-t1:.2f}s")
    after_filled = df['normalized_city'].notna() & (df['normalized_city'].astype(str).str.strip() != '') & (df['normalized_city'].astype(str).str.lower() != 'nan')
    after_count = after_filled.sum()
    log.info(f"After: normalized_city filled = {after_count:,} / {len(df):,} ({after_count/len(df)*100:.1f}%)")
    log.info(f"Improvement: +{after_count - before_count:,} records ({(after_count-before_count)/len(df)*100:.1f}%)")
    log.info("Writing back to parquet...")
    df.to_parquet(PARQUET, index=False, engine='pyarrow')
    log.info(f"Parquet updated ({os.path.getsize(PARQUET)/1024/1024:.2f} MB)")
    log.info("Reloading RecruiterStore...")
    try:
        from app.services.recruiter_store import recruiter_store
        recruiter_store.reload()
        log.info(f"RecruiterStore reloaded with {recruiter_store.total_count:,} records")
    except Exception as e:
        log.warning(f"RecruiterStore reload skipped: {e}")
    log.info("Sample extractions:")
    sample = df[after_filled & ~before_filled].head(10)
    for _, row in sample.iterrows():
        log.info(f"  '{row['location']}' -> '{row['normalized_city']}'")
    log.info("Phase 1 Complete!")

if __name__ == "__main__":
    main()
