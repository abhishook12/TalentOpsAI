import sys
import os
import re
import json
import time
import shutil
import duckdb
import pyarrow as pa
import pyarrow.parquet as pq
from datetime import datetime, timezone

sys.path.insert(0, r"C:\TalentOpsAI\backend")
from app.database import SessionLocal
from app.models.models import Company, RepairLog
from sqlalchemy import text

print("=" * 80)
print("TALENTOPS ENTERPRISE DATA QUALITY ENGINE — 2.3M PROFILE PIPELINE")
print("=" * 80)

DATA_PATH = r"C:\TalentOpsAI\backend\data\recruiters_full.parquet"
BACKUP_PATH = r"C:\TalentOpsAI\backend\data\recruiters_full_pre_quality_backup.parquet"
OUTPUT_PATH = r"C:\TalentOpsAI\backend\data\recruiters_full_cleaned.parquet"

# 1. BACKUP DATASET
if not os.path.exists(BACKUP_PATH):
    print(f"[*] Creating safety backup: {BACKUP_PATH} ...")
    shutil.copy2(DATA_PATH, BACKUP_PATH)
    print("    Backup created successfully.")
else:
    print(f"[*] Safety backup already exists at {BACKUP_PATH}")

# 2. BUILD DOMAIN INTELLIGENCE MAP FROM POSTGRESQL & CACHE
print("\n[Step 1/8] Building Domain Intelligence Registry...")
CACHE_FILE = r"C:\TalentOpsAI\backend\data\companies_cache.json"
domain_to_company = {}
comp_id_to_meta = {}

companies_loaded = False
for attempt in range(3):
    try:
        db = SessionLocal()
        companies = db.query(Company.company_id, Company.company_name, Company.primary_domain, Company.logo_url).all()
        cache_data = []
        for cid, cname, pdom, logo in companies:
            cache_data.append({
                "company_id": cid,
                "company_name": cname,
                "primary_domain": pdom.lower().strip() if pdom else None,
                "logo_url": logo
            })
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache_data, f)
        db.close()
        companies_loaded = True
        break
    except Exception as e:
        print(f"    ! DB attempt {attempt+1} warning: {e}. Retrying in 2s...")
        time.sleep(2)

if not companies_loaded and os.path.exists(CACHE_FILE):
    print("    Loading companies from local cache file...")
    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        cache_data = json.load(f)
elif not companies_loaded:
    cache_data = []

for c in cache_data:
    cid = c["company_id"]
    pdom = c["primary_domain"]
    comp_id_to_meta[str(cid)] = c
    if pdom:
        domain_to_company[pdom] = c

print(f"    Loaded {len(comp_id_to_meta):,} companies and {len(domain_to_company):,} primary domains.")

# 3. INITIALIZE DUCKDB PIPELINE
print("\n[Step 2/8] Loading dataset into high-speed analytical engine...")
con = duckdb.connect(':memory:')
con.execute(f"CREATE TABLE raw_recruiters AS SELECT * FROM read_parquet('{DATA_PATH}')")
total_records = con.execute("SELECT COUNT(*) FROM raw_recruiters").fetchone()[0]
print(f"    Loaded {total_records:,} records into memory.")

# US State Postal Codes Set
US_STATES = {
    'AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA',
    'HI','ID','IL','IN','IA','KS','KY','LA','ME','MD',
    'MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ',
    'NM','NY','NC','ND','OH','OK','OR','PA','RI','SC',
    'SD','TN','TX','UT','VT','VA','WA','WV','WI','WY',
    'DC','PR','VI','GU'
}

STATE_NAMES_MAP = {
    'alabama': 'AL', 'alaska': 'AK', 'arizona': 'AZ', 'arkansas': 'AR', 'california': 'CA',
    'colorado': 'CO', 'connecticut': 'CT', 'delaware': 'DE', 'florida': 'FL', 'georgia': 'GA',
    'hawaii': 'HI', 'idaho': 'ID', 'illinois': 'IL', 'indiana': 'IN', 'iowa': 'IA',
    'kansas': 'KS', 'kentucky': 'KY', 'louisiana': 'LA', 'maine': 'ME', 'maryland': 'MD',
    'massachusetts': 'MA', 'michigan': 'MI', 'minnesota': 'MN', 'mississippi': 'MS', 'missouri': 'MO',
    'montana': 'MT', 'nebraska': 'NE', 'nevada': 'NV', 'new hampshire': 'NH', 'new jersey': 'NJ',
    'new mexico': 'NM', 'new york': 'NY', 'north carolina': 'NC', 'north dakota': 'ND', 'ohio': 'OH',
    'oklahoma': 'OK', 'oregon': 'OR', 'pennsylvania': 'PA', 'rhode island': 'RI', 'south carolina': 'SC',
    'south dakota': 'SD', 'tennessee': 'TN', 'texas': 'TX', 'utah': 'UT', 'vermont': 'VT',
    'virginia': 'VA', 'washington': 'WA', 'west virginia': 'WV', 'wisconsin': 'WI', 'wyoming': 'WY',
    'district of columbia': 'DC', 'puerto rico': 'PR'
}

FREE_MAIL_DOMAINS = {
    'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'aol.com',
    'icloud.com', 'live.com', 'msn.com', 'comcast.net', 'att.net',
    'sbcglobal.net', 'verizon.net', 'me.com', 'mail.com', 'protonmail.com',
    'ymail.com', 'cox.net', 'charter.net', 'earthlink.net', 'talentops.ai'
}

# 4. PYTHON VECTORIZED QUALITY ENRICHMENT ENGINE
print("\n[Step 3/8] Executing multi-signal data quality normalization...")
start_time = time.time()

# Read as DataFrame for fast vectorized columnar manipulation
df = con.execute("SELECT * FROM raw_recruiters").fetchdf()

repaired_emails_cnt = 0
repaired_names_cnt = 0
repaired_locations_cnt = 0
repaired_phones_cnt = 0
repaired_titles_cnt = 0
repaired_companies_cnt = 0

print("    Applying algorithmic transformations across all 2.3M records...")

def clean_email(email_str):
    if not email_str or not isinstance(email_str, str):
        return None, "missing"
    e = email_str.strip().lower()
    if "@missing.local" in e or e in ("none", "null", "n/a", ""):
        return None, "missing"
    # Strip trailing punctuation
    e = re.sub(r'[.,;:"\'>]+$', '', e)
    e = re.sub(r'^[<\'"]+', '', e)
    if "@" in e and re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', e):
        dom = e.split("@")[-1]
        if dom in FREE_MAIL_DOMAINS:
            return e, "personal_valid"
        return e, "business_valid"
    return None, "malformed_quarantined"

def clean_name(name_str, email_str):
    has_email = isinstance(email_str, str) and "@" in email_str
    
    if not name_str or not isinstance(name_str, str) or name_str.strip().lower() in (
        "none", "null", "n/a", "unknown", "recruiter", "hr", "admin", "professional", "talent", "hiring manager"
    ):
        # Attempt high-confidence name reconstruction from email prefix if first.last
        if has_email:
            prefix = email_str.split("@")[0].lower()
            if "." in prefix:
                parts = prefix.split(".")
                if len(parts) == 2 and all(p.isalpha() and len(p) >= 2 for p in parts):
                    fn, ln = parts[0].capitalize(), parts[1].capitalize()
                    return f"{fn} {ln}", True
        return None, False
    
    n = name_str.strip()
    # Check synthetic initial patterns like "J. Osephs"
    m = re.match(r'^([A-Z])\.\s+([A-Z][a-z]+)$', n)
    if m and has_email:
        prefix = email_str.split("@")[0].lower()
        if "." in prefix:
            parts = prefix.split(".")
            if len(parts) == 2 and all(p.isalpha() and len(p) >= 2 for p in parts):
                return f"{parts[0].capitalize()} {parts[1].capitalize()}", True
    return n, False

def clean_location(state_str, city_str):
    st = state_str.strip().upper() if isinstance(state_str, str) and state_str.strip() else None
    ct = city_str.strip() if isinstance(city_str, str) and city_str.strip() else None
    
    # Clean city if placeholder
    if ct and ct.lower() in ("n/a", "none", "null", "unknown", "0"):
        ct = None
        
    # Check if city contains comma e.g. "New York, NY"
    if ct and "," in ct:
        parts = [p.strip() for p in ct.split(",")]
        ct = parts[0].title()
        if len(parts) > 1 and len(parts[1]) == 2 and parts[1].upper() in US_STATES:
            st = parts[1].upper()
            
    # Check if city equals state name or abbreviation
    if ct:
        ct_lower = ct.lower()
        if st and ct_lower == st.lower():
            ct = None
        elif ct_lower in STATE_NAMES_MAP:
            if not st:
                st = STATE_NAMES_MAP[ct_lower]
            ct = None
        elif len(ct) == 2 and ct.upper() in US_STATES:
            if not st:
                st = ct.upper()
            ct = None
        else:
            ct = ct.title()
            
    if st and st not in US_STATES:
        # Check if state string was a full state name
        if st.lower() in STATE_NAMES_MAP:
            st = STATE_NAMES_MAP[st.lower()]
            
    return st, ct

def clean_phone(phone_str):
    if not phone_str or not isinstance(phone_str, str):
        return None
    p = phone_str.strip()
    if p.lower() in ("n/a", "none", "null", "unknown", "0", "0000000000", ""):
        return None
    digits = re.sub(r'\D', '', p)
    if len(digits) == 10:
        return f"+1{digits}"
    elif len(digits) == 11 and digits.startswith('1'):
        return f"+{digits}"
    elif 10 <= len(digits) <= 15:
        return f"+{digits}"
    return None

def clean_title(title_str):
    if not title_str or not isinstance(title_str, str):
        return None
    t = title_str.strip()
    if t.lower() in ("professional", "n/a", "none", "null", "unknown", "recruiter", "talent", ""):
        return None
    return t

# Vectorized batch processing
print("    Processing emails...")
cleaned_emails_and_status = [clean_email(e) for e in df['email']]
df['email'] = [x[0] for x in cleaned_emails_and_status]
df['email_status'] = [x[1] for x in cleaned_emails_and_status]

print("    Processing names...")
cleaned_names = [clean_name(n, e) for n, e in zip(df['recruiter_name'], df['email'])]
df['recruiter_name'] = [x[0] for x in cleaned_names]
df['normalized_recruiter_name'] = df['recruiter_name']

print("    Processing locations...")
cleaned_locs = [clean_location(s, c) for s, c in zip(df['state'], df['normalized_city'])]
df['state'] = [x[0] for x in cleaned_locs]
df['normalized_city'] = [x[1] for x in cleaned_locs]

print("    Processing phones...")
df['phone'] = [clean_phone(p) for p in df['phone']]

print("    Processing titles...")
df['title'] = [clean_title(t) for t in df['title']]

print("    Resolving unmapped companies via domain intelligence...")
new_comp_ids = []
for cid, email, status in zip(df['company_id'], df['email'], df['email_status']):
    cid_str = str(cid).strip() if cid is not None else ""
    if cid_str and cid_str not in ("None", "nan", "unknown", "0", "null", "need to fill data", "N/A"):
        new_comp_ids.append(cid_str)
    elif status == "business_valid" and isinstance(email, str) and "@" in email:
        dom = email.split("@")[-1].lower()
        if dom in domain_to_company:
            new_comp_ids.append(str(domain_to_company[dom]["company_id"]))
            repaired_companies_cnt += 1
        else:
            new_comp_ids.append(cid_str if cid_str else None)
    else:
        new_comp_ids.append(None)

df['company_id'] = new_comp_ids

# 5. DEDUPLICATION
print("\n[Step 4/8] Executing deduplication and canonical entity selection...")
# Find duplicate emails (where email is not None)
valid_emails = df[df['email'].notnull()]
dup_mask = valid_emails.duplicated(subset=['email'], keep=False)
dup_emails = valid_emails[dup_mask]['email'].unique()
print(f"    Found {len(dup_emails):,} unique emails involved in duplication.")

# Keep first occurrence as active canonical, mark duplicates
df['is_active'] = True
df['merged_into_id'] = None

dup_indices = df[df['email'].notnull() & df.duplicated(subset=['email'], keep='first')].index
df.loc[dup_indices, 'is_active'] = False
print(f"    De-duplicated {len(dup_indices):,} duplicate rows marked as inactive/merged.")

# 6. QUALITY & TRUST SCORING
print("\n[Step 5/8] Calculating precision Completeness and Trust Scores...")
emails = df['email'].values
email_statuses = df['email_status'].values
names = df['recruiter_name'].values
comp_ids = df['company_id'].values
states = df['state'].values
cities = df['normalized_city'].values
phones = df['phone'].values
titles = df['title'].values

n_records = len(df)
comp_scores = [0] * n_records
trust_scores = [100] * n_records

for i in range(n_records):
    c = 0
    t = 100
    
    # Email (30%)
    estat = email_statuses[i]
    if estat == 'business_valid':
        c += 30
    elif estat == 'personal_valid':
        c += 20
        t -= 10
    else:
        t -= 30
        
    # Name (25%)
    nm = names[i]
    if isinstance(nm, str) and len(nm.strip()) >= 3:
        c += 25
    else:
        t -= 20
        
    # Company (20%)
    cid = comp_ids[i]
    if isinstance(cid, str) and cid.strip() not in ("None", "nan", ""):
        c += 20
    else:
        t -= 20
        
    # Location (15%)
    if isinstance(states[i], str) and states[i].strip():
        c += 10
    if isinstance(cities[i], str) and cities[i].strip():
        c += 5
        
    # Phone (5%)
    if isinstance(phones[i], str) and phones[i].strip():
        c += 5
        
    # Title (5%)
    if isinstance(titles[i], str) and titles[i].strip():
        c += 5
        
    comp_scores[i] = c
    trust_scores[i] = max(0, min(100, t))

df['completeness_score'] = comp_scores
df['quality_score'] = comp_scores
df['trust_score'] = trust_scores

# 7. PARQUET RE-SERIALIZATION
print("\n[Step 6/8] Writing pristine, enriched Parquet dataset to disk...")
cleaned_table = pa.Table.from_pandas(df)
pq.write_table(cleaned_table, OUTPUT_PATH, compression='snappy')
file_size_mb = os.path.getsize(OUTPUT_PATH) / (1024 * 1024)
print(f"    Successfully wrote {len(df):,} records to {OUTPUT_PATH} ({file_size_mb:.2f} MB)")

# Replace active file with cleaned file
shutil.copy2(OUTPUT_PATH, DATA_PATH)
print(f"    Overwrote active dataset at {DATA_PATH}")

# 8. AUDIT LOGGING IN POSTGRESQL
print("\n[Step 7/8] Recording execution audit in PostgreSQL...")
try:
    db = SessionLocal()
    audit_entry = RepairLog(
        entity_type="RecruiterStore",
        entity_id=0,
        field_name="FullDatasetQualityPipeline",
        old_value="Baseline 67.49% Quality",
        new_value=f"Post-Pipeline Cleaned {len(df):,} Records",
        confidence=98,
        evidence=json.dumps({
            "total_records": len(df),
            "valid_emails": int((df['email_status'] == 'business_valid').sum() + (df['email_status'] == 'personal_valid').sum()),
            "valid_names": int(df['recruiter_name'].notnull().sum()),
            "mapped_companies": int(df['company_id'].notnull().sum()),
            "deduplicated_rows": int(len(dup_indices)),
            "duration_seconds": round(time.time() - start_time, 2)
        }),
        source="EnterpriseDataQualityEngine"
    )
    db.add(audit_entry)
    db.commit()
    print("    Audit log written to PostgreSQL repair_logs.")
    db.close()
except Exception as e:
    print(f"    ! Audit log warning: {e}")

print(f"\n[Step 8/8] Pipeline Complete in {time.time() - start_time:.2f}s!")
print("=" * 80)
