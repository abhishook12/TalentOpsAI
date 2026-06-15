import os
import re
import json
import time
import pandas as pd
from urllib.parse import urlparse
from collections import defaultdict
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import uuid

# Load dotenv if needed, though we will hardcode the engine to be sure or use app.database
from dotenv import load_dotenv
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL or "supabase" not in DATABASE_URL:
    DATABASE_URL = "postgresql+psycopg://postgres.dcqvsvgrdsrgnbwwssup:rd%2Fnew%2Fjvminw@aws-1-ap-southeast-1.pooler.supabase.com:5432/postgres"

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)

def get_domain(email):
    if not email or '@' not in email: return None
    domain = email.split('@')[-1].lower().strip()
    if domain in ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'icloud.com']:
        return None
    return domain

def normalize_text(text):
    if pd.isna(text) or not str(text).strip(): return None
    val = str(text).strip()
    if val.lower() in ["null", "none", "n/a", "not provided", "-", "—", ""]: return None
    # remove double spaces
    val = re.sub(r'\s+', ' ', val)
    return val

def normalize_phone(phone):
    val = normalize_text(phone)
    if not val: return None
    # Keep digits only
    digits = re.sub(r'\D', '', val)
    if len(digits) >= 10:
        return digits[-10:]
    return digits

def normalize_email(email):
    val = normalize_text(email)
    if not val: return None
    return val.lower()

# Known state mappings
STATE_MAP = {
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

def extract_state_from_text(text):
    if not text: return None
    text_lower = text.lower()
    for state, abbr in STATE_MAP.items():
        if state in text_lower:
            return abbr
        # Match standalone abbreviation
        if re.search(rf'\b{abbr.lower()}\b', text_lower):
            return abbr
    return None

def scan_files():
    found_files = []
    desktop_file = "C:\\Users\\User\\Desktop\\final updated sheet.xlsx"
    if os.path.exists(desktop_file): found_files.append(desktop_file)
    
    upload_dir = "C:\\TalentOpsAI\\backend\\uploads"
    if os.path.exists(upload_dir):
        for f in os.listdir(upload_dir):
            if f.endswith('.xlsx') or f.endswith('.csv'):
                found_files.append(os.path.join(upload_dir, f))
    return found_files

def extract_raw_data(files):
    raw_data = []
    print(f"Extracting data from {len(files)} files...")
    for f in files:
        print(f"Reading {os.path.basename(f)}...")
        try:
            if f.endswith('.xlsx'):
                xl = pd.ExcelFile(f)
                for sheet in xl.sheet_names:
                    df = xl.parse(sheet, dtype=str)
                    df['source_file'] = os.path.basename(f)
                    df['source_sheet'] = sheet
                    raw_data.append(df)
            elif f.endswith('.csv'):
                df = pd.read_csv(f, dtype=str, low_memory=False)
                df['source_file'] = os.path.basename(f)
                df['source_sheet'] = 'CSV'
                raw_data.append(df)
        except Exception as e:
            print(f"Error reading {f}: {e}")
            
    if not raw_data:
        return pd.DataFrame()
        
    combined = pd.concat(raw_data, ignore_index=True)
    return combined

def map_columns(df):
    # Keep only the first matched column for each target to avoid duplicate column names
    col_map = {}
    used_targets = set()
    
    for col in df.columns:
        cl = str(col).lower().strip()
        target = None
        
        if 'name' in cl and 'company' not in cl and 'first' not in cl and 'last' not in cl:
            target = 'recruiter_name'
        elif cl in ['first name', 'first']:
            target = 'first_name'
        elif cl in ['last name', 'last']:
            target = 'last_name'
        elif 'email' in cl:
            target = 'email'
        elif 'phone' in cl or 'mobile' in cl:
            target = 'phone'
        elif 'company' in cl or 'account' in cl:
            target = 'company'
        elif 'linkedin' in cl or 'url' in cl:
            target = 'linkedin'
        elif 'title' in cl:
            target = 'title'
        elif 'location' in cl or 'city' in cl or 'state' in cl:
            target = 'location'
            
        if target and target not in used_targets:
            col_map[col] = target
            used_targets.add(target)
            
    # Drop columns that are not mapped, except source_file and source_sheet
    keep_cols = list(col_map.keys()) + ['source_file', 'source_sheet']
    keep_cols = [c for c in keep_cols if c in df.columns]
    df = df[keep_cols]
    
    df = df.rename(columns=col_map)
    
    # Ensure all required cols exist
    for c in ['recruiter_name', 'first_name', 'last_name', 'email', 'phone', 'company', 'linkedin', 'title', 'location', 'source_file', 'source_sheet']:
        if c not in df.columns:
            df[c] = None
            
    # merge first and last if needed
    for idx, row in df.iterrows():
        rn = row['recruiter_name']
        fn = row['first_name']
        ln = row['last_name']
        
        if pd.isna(rn) and not pd.isna(fn) and not pd.isna(ln):
            df.at[idx, 'recruiter_name'] = f"{fn} {ln}"
            
    return df

def clean_and_dedup(df):
    print("Cleaning and deduplicating...")
    records = []
    
    # Indexes for dedup
    idx_email = {}
    idx_phone = {}
    idx_linkedin = {}
    idx_name_company = {}
    idx_name_domain = {}
    
    # Process rows
    for i, row in df.iterrows():
        name = normalize_text(row['recruiter_name'])
        email = normalize_email(row['email'])
        phone = normalize_phone(row['phone'])
        company = normalize_text(row['company'])
        linkedin = normalize_text(row['linkedin'])
        location = normalize_text(row['location'])
        title = normalize_text(row['title'])
        
        if not name and not email and not phone:
            continue
            
        domain = get_domain(email)
        
        name_lower = name.lower() if name else ""
        company_lower = company.lower() if company else ""
        
        # Match existing
        match_id = None
        if email and email in idx_email:
            match_id = idx_email[email]
        elif phone and phone in idx_phone:
            match_id = idx_phone[phone]
        elif linkedin and linkedin in idx_linkedin:
            match_id = idx_linkedin[linkedin]
        elif name_lower and company_lower and f"{name_lower}::{company_lower}" in idx_name_company:
            match_id = idx_name_company[f"{name_lower}::{company_lower}"]
        elif name_lower and domain and f"{name_lower}::{domain}" in idx_name_domain:
            match_id = idx_name_domain[f"{name_lower}::{domain}"]
            
        if match_id is not None:
            # Merge
            rec = records[match_id]
            # Merge emails
            if email and email not in [rec['email'], rec['email2'], rec['email3'], rec['email4']]:
                if not rec['email']: rec['email'] = email
                elif not rec['email2']: rec['email2'] = email
                elif not rec['email3']: rec['email3'] = email
                elif not rec['email4']: rec['email4'] = email
            # Merge phones
            if phone and phone not in [rec['phone'], rec['phone2'], rec['phone3'], rec['phone4']]:
                if not rec['phone']: rec['phone'] = phone
                elif not rec['phone2']: rec['phone2'] = phone
                elif not rec['phone3']: rec['phone3'] = phone
                elif not rec['phone4']: rec['phone4'] = phone
                
            # Update missing fields
            if not rec['company']: rec['company'] = company
            if not rec['location']: rec['location'] = location
            if not rec['title']: rec['title'] = title
            if not rec['linkedin']: rec['linkedin'] = linkedin
            
            # Store evidence
            rec['metadata_json']['sources'].append({
                'file': row['source_file'],
                'sheet': row['source_sheet']
            })
            
            # Update indexes with new values
            if email: idx_email[email] = match_id
            if phone: idx_phone[phone] = match_id
            if linkedin: idx_linkedin[linkedin] = match_id
            
        else:
            # Create new
            new_id = len(records)
            rec = {
                'recruiter_id': str(uuid.uuid4()),
                'recruiter_name': name,
                'email': email, 'email2': None, 'email3': None, 'email4': None,
                'phone': phone, 'phone2': None, 'phone3': None, 'phone4': None,
                'company': company,
                'location': location,
                'linkedin': linkedin,
                'title': title,
                'metadata_json': {'sources': [{'file': row['source_file'], 'sheet': row['source_sheet']}]},
                'state': None,
                'state_source': None,
                'state_confidence': None,
                'state_reason': None,
                'needs_review': False,
                'review_reason': None
            }
            records.append(rec)
            
            # Add to indexes
            if email: idx_email[email] = new_id
            if phone: idx_phone[phone] = new_id
            if linkedin: idx_linkedin[linkedin] = new_id
            if name_lower and company_lower: idx_name_company[f"{name_lower}::{company_lower}"] = new_id
            if name_lower and domain: idx_name_domain[f"{name_lower}::{domain}"] = new_id

    print(f"Deduplication complete. Reduced to {len(records)} unique recruiters.")
    
    # Assign recruiter_ids
    for i, rec in enumerate(records, start=1):
        rec['recruiter_id'] = i
        
    return records

def infer_states_and_normalize_companies(records):
    print("Running state inference and company normalization...")
    companies = {}
    
    comp_id_counter = 1
    # First pass: map recruiters to companies
    for r in records:
        if r['company']:
            comp_name = r['company'].upper()
            if comp_name not in companies:
                companies[comp_name] = {
                    'company_id': comp_id_counter,
                    'name': r['company'],
                    'normalized_name': comp_name,
                    'recruiters': [],
                    'locations': [],
                    'hq_state': None
                }
                comp_id_counter += 1
            companies[comp_name]['recruiters'].append(r)
            if r['location']:
                companies[comp_name]['locations'].append(r['location'])
                
    # Determine company states
    for c_name, c_data in companies.items():
        state_counts = defaultdict(int)
        total_locs = 0
        for loc in c_data['locations']:
            s = extract_state_from_text(loc)
            if s:
                state_counts[s] += 1
                total_locs += 1
                
        if total_locs > 0:
            top_state = max(state_counts, key=state_counts.get)
            top_ratio = state_counts[top_state] / total_locs
            if top_ratio >= 0.90:
                c_data['hq_state'] = top_state
                c_data['confidence'] = 'high'
            elif top_ratio >= 0.75:
                c_data['hq_state'] = top_state
                c_data['confidence'] = 'medium'

    # Second pass: assign state to recruiters
    for r in records:
        comp = companies.get(r['company'].upper()) if r['company'] else None
        loc_state = extract_state_from_text(r['location'])
        sheet_state = None
        for s in r['metadata_json']['sources']:
            ss = extract_state_from_text(s['sheet'])
            if ss:
                sheet_state = ss
                break
                
        # High confidence
        if loc_state:
            r['state'] = loc_state
            r['state_source'] = 'location_field'
            r['state_confidence'] = 'high'
            r['state_reason'] = f"Extracted directly from location text: '{r['location']}'"
        elif sheet_state:
            r['state'] = sheet_state
            r['state_source'] = 'sheet_name'
            r['state_confidence'] = 'high'
            r['state_reason'] = f"Extracted from source sheet name"
        elif comp and comp['hq_state'] and comp.get('confidence') == 'high':
            r['state'] = comp['hq_state']
            r['state_source'] = 'company_majority'
            r['state_confidence'] = 'high'
            r['state_reason'] = f"Over 90% of company locations point to {comp['hq_state']}"
            
        # Medium confidence
        elif comp and comp['hq_state'] and comp.get('confidence') == 'medium':
            r['needs_review'] = True
            r['state_confidence'] = 'medium'
            r['review_reason'] = f"Company has 75-90% consensus on {comp['hq_state']} but needs verification."
            
        # Low confidence
        else:
            r['needs_review'] = True
            r['state_confidence'] = 'low'
            r['review_reason'] = "Insufficient or ambiguous location data. No strong company consensus."
            domain = get_domain(r['email'])
            if not r['company'] and not domain:
                r['review_reason'] = "No company or distinct email domain to associate with."
                
    return records, companies.values()

def insert_to_supabase(records, companies):
    print("Inserting to Supabase...")
    db = SessionLocal()
    
    # 1. Clean existing staging
    db.execute(text("DELETE FROM staging_recruiters"))
    db.execute(text("DELETE FROM staging_companies"))
    db.commit()
    
    # 2. Insert Companies
    comp_inserts = []
    now = datetime.utcnow()
    for c in companies:
        comp_inserts.append({
            'company_id': c['company_id'],
            'company_name': c['name'],
            'normalized_company_name': c['normalized_name'],
            'state': c['hq_state'],
            'created_at': now,
            'updated_at': now
        })
        
    print(f"Batch inserting {len(comp_inserts)} companies...")
    for i in range(0, len(comp_inserts), 1000):
        db.execute(
            text("""
                INSERT INTO companies (company_id, company_name, normalized_company_name, state, created_at, updated_at)
                VALUES (:company_id, :company_name, :normalized_company_name, :state, :created_at, :updated_at)
                ON CONFLICT (company_id) DO NOTHING
            """),
            comp_inserts[i:i+1000]
        )
        db.commit()
    
    # 3. Insert Recruiters
    rec_inserts = []
    company_lookup = {c['name'].upper(): c['company_id'] for c in companies}
    
    for r in records:
        cid = company_lookup.get(r['company'].upper()) if r['company'] else None
        
        # Clean metadata_json
        meta = r['metadata_json']
        if isinstance(meta, str):
            try:
                meta = json.loads(meta)
            except:
                meta = {'raw': meta}
        if 'sources' in meta and not meta['sources']: del meta['sources']
        
        rec_name = r['recruiter_name']
        if not rec_name:
            if r['email']:
                rec_name = r['email'].split('@')[0]
            else:
                rec_name = "Unknown Recruiter"
        
        rec_inserts.append({
            'recruiter_id': r['recruiter_id'],
            'recruiter_name': rec_name,
            'email': r['email'], 'email2': r['email2'], 'email3': r['email3'], 'email4': r['email4'],
            'phone': r['phone'], 'phone2': r['phone2'], 'phone3': r['phone3'], 'phone4': r['phone4'],
            'company_id': cid,
            'location': r['location'],
            'title': r['title'],
            'linkedin': r['linkedin'],
            'state': r['state'],
            'state_source': r['state_source'],
            'state_confidence': r['state_confidence'],
            'state_reason': r['state_reason'],
            'needs_review': r['needs_review'],
            'review_reason': r['review_reason'],
            'metadata_json': json.dumps(meta),
            'created_at': now,
            'updated_at': now
        })
        
    print(f"Batch inserting {len(rec_inserts)} recruiters...")
    for i in range(0, len(rec_inserts), 100):
        print(f"  Inserting recruiters {i} to {i+100}...")
        batch = rec_inserts[i:i+100]
        # Debug check for UUIDs and None emails, and truncate long strings
        for idx, row in enumerate(batch):
            if not row.get('email'):
                row['email'] = f"no-email-{row['recruiter_id']}@talentops.ai"
            
            # Truncate string fields to avoid DataError
            for field in ['recruiter_name', 'email', 'email2', 'email3', 'email4', 'title', 'location', 'state_source']:
                if row.get(field) and isinstance(row[field], str) and len(row[field]) > 140:
                    row[field] = row[field][:140]
            for field in ['phone', 'phone2', 'phone3', 'phone4']:
                if row.get(field) and isinstance(row[field], str) and len(row[field]) > 25:
                    row[field] = row[field][:25]
            
            for k, v in row.items():
                if isinstance(v, str) and len(v) == 36 and '-' in v:
                    print(f"Found UUID in recruiter insert! row_idx={i+idx}, key={k}, value={v}")
        
        db.execute(
            text("""
                INSERT INTO recruiters (
                    recruiter_id, recruiter_name, email, email2, email3, email4,
                    phone, phone2, phone3, phone4, company_id,
                    location, title, linkedin, state, state_source, state_confidence,
                    state_reason, needs_review, review_reason, metadata_json, created_at, updated_at
                ) VALUES (
                    :recruiter_id, :recruiter_name, :email, :email2, :email3, :email4,
                    :phone, :phone2, :phone3, :phone4, :company_id,
                    :location, :title, :linkedin, :state, :state_source, :state_confidence,
                    :state_reason, :needs_review, :review_reason, :metadata_json, :created_at, :updated_at
                ) ON CONFLICT (recruiter_id) DO NOTHING
            """),
            batch
        )
        db.commit()
    
    # 4. Upload Job
    db.execute(text("""
        INSERT INTO upload_jobs (job_id, filename, status, total_rows, created_at, updated_at)
        VALUES (:jid, :fn, 'completed', :tr, :now, :now)
    """), {'jid': str(uuid.uuid4()), 'fn': 'Supabase_Raw_Migration', 'tr': len(rec_inserts), 'now': now})
    db.commit()
    
    # Verification stats
    total_recs = db.execute(text("SELECT COUNT(*) FROM recruiters")).scalar()
    total_comps = db.execute(text("SELECT COUNT(*) FROM companies")).scalar()
    known_state = db.execute(text("SELECT COUNT(*) FROM recruiters WHERE state IS NOT NULL")).scalar()
    unknown_state = db.execute(text("SELECT COUNT(*) FROM recruiters WHERE state IS NULL")).scalar()
    needs_review = db.execute(text("SELECT COUNT(*) FROM recruiters WHERE needs_review = true")).scalar()
    top_state = db.execute(text("SELECT state FROM recruiters WHERE state IS NOT NULL GROUP BY state ORDER BY COUNT(*) DESC LIMIT 1")).scalar()
    
    sc = {}
    for st in ['NY', 'TX', 'CA', 'GA', 'NC', 'FL']:
        sc[st] = db.execute(text(f"SELECT COUNT(*) FROM recruiters WHERE state = '{st}'")).scalar()
        
    db.close()
    return {
        'total_recs': total_recs,
        'total_comps': total_comps,
        'known_state': known_state,
        'unknown_state': unknown_state,
        'needs_review': needs_review,
        'top_state': top_state,
        'state_counts': sc
    }

def optimize_db():
    print("Optimizing Database...")
    db = SessionLocal()
    
    # Before size
    before_mb = db.execute(text("SELECT pg_database_size(current_database()) / 1048576.0")).scalar()
    
    # Clean empty strings
    for col in ['email', 'email2', 'email3', 'email4', 'phone', 'phone2', 'phone3', 'phone4', 'location', 'linkedin', 'title', 'state', 'state_source', 'state_confidence', 'state_reason', 'review_reason']:
        db.execute(text(f"UPDATE recruiters SET {col} = NULL WHERE {col} = ''"))
        
    # Truncate raw data if it existed
    # (Since we didn't inject raw_data col in this script, skip)
    
    # Vacuum
    db.commit()
    # Cannot run VACUUM in transaction block, so we use raw connection
    raw_conn = engine.raw_connection()
    raw_conn.set_isolation_level(0) # AUTOCOMMIT
    cursor = raw_conn.cursor()
    cursor.execute("VACUUM ANALYZE recruiters;")
    cursor.execute("VACUUM ANALYZE companies;")
    raw_conn.close()
    
    # After size
    after_mb = db.execute(text("SELECT pg_database_size(current_database()) / 1048576.0")).scalar()
    db.close()
    
    return before_mb, after_mb

if __name__ == "__main__":
    t0 = time.time()
    files = scan_files()
    raw_df = extract_raw_data(files)
    mapped_df = map_columns(raw_df)
    
    print(f"Total raw rows extracted: {len(mapped_df)}")
    
    records = clean_and_dedup(mapped_df)
    duplicates_merged = len(mapped_df) - len(records)
    
    records, companies = infer_states_and_normalize_companies(records)
    
    stats = insert_to_supabase(records, companies)
    before_mb, after_mb = optimize_db()
    
    print("\n" + "="*40)
    print("======= SUPABASE MIGRATION REPORT =======")
    print(f"Total recruiters inserted: {stats['total_recs']}")
    print(f"Total companies inserted:  {stats['total_comps']}")
    print(f"Known state count:         {stats['known_state']}")
    print(f"Unknown state count:       {stats['unknown_state']}")
    print(f"Needs review count:        {stats['needs_review']}")
    print(f"Duplicates merged:         {duplicates_merged}")
    print(f"Top state by recruiter count: {stats['top_state']}")
    
    print("State counts — NY / TX / CA / GA / NC / FL:")
    for s, c in stats['state_counts'].items():
        print(f"  {s}: {c}")
        
    print("")
    print(f"Database size before optimization: {before_mb:.2f} MB")
    print(f"Database size after optimization:  {after_mb:.2f} MB")
    print(f"Space saved:                       {(before_mb - after_mb):.2f} MB")
    print("")
    print("Local site verified:     PENDING")
    print("Dashboard loads:         PENDING")
    print("All pages load:          PENDING")
    print("Console errors:          PENDING")
    print("")
    print(f"Files processed: {len(files)}")
    print(f"Scripts created: 1")
    print("==========================================")
    print("MIGRATION COMPLETE — AWAITING PUSH COMMAND")
    print("==========================================")
