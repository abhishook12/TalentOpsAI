import pandas as pd
import re
import datetime
from sqlalchemy import text
from app.database import SessionLocal
from app.utils.state_mapper import extract_state_detailed
import uuid
import json

def clean_phone(text):
    digits = re.sub(r'\D', '', str(text))
    if len(digits) >= 10:
        return digits[-10:]
    return None

def is_valid_name(text):
    if len(text) < 4 or len(text) > 40:
        return False
    # Names usually have spaces (first last) and no digits
    if ' ' not in text.strip():
        return False
    if any(char.isdigit() for char in text):
        return False
    if '@' in text or 'http' in text or '.com' in text:
        return False
    # Check if mostly titlecased or letters
    letters = sum(1 for c in text if c.isalpha() or c.isspace())
    if letters / len(text) < 0.8:
        return False
    return True

def run_chaotic_import():
    print("Loading final updated sheet (this may take a minute)...", flush=True)
    df = pd.read_excel('C:/Users/User/Desktop/final updated sheet.xlsx', header=None, dtype=str)
    
    print(f"Loaded {len(df)} rows. Parsing heuristically in memory...", flush=True)
    
    updates = []
    now = datetime.datetime.now(datetime.timezone.utc)
    
    for i, row in df.iterrows():
        if i % 10000 == 0:
            print(f"Processed {i} rows...", flush=True)
            
        vals = [str(x).strip() for x in row.values if pd.notna(x) and str(x).strip() not in ('nan', 'NaN', 'None', '')]
        if not vals:
            continue
            
        email = None
        phone = None
        linkedin = None
        name = None
        company = None
        location = None
        state_abbr = None
        
        remaining_vals = []
        
        for v in vals:
            v_lower = v.lower()
            if not email and '@' in v and '.' in v and ' ' not in v:
                email = v_lower
                continue
            if not linkedin and 'linkedin.com' in v_lower:
                linkedin = v
                continue
            if not phone:
                p = clean_phone(v)
                if p and '@' not in v and len(v) < 25:
                    phone = p
                    continue
            remaining_vals.append(v)
            
        if not email:
            continue
            
        for v in remaining_vals[:]:
            if not name and is_valid_name(v):
                name = v
                remaining_vals.remove(v)
                break
                
        for v in remaining_vals[:]:
            if not state_abbr:
                st, _ = extract_state_detailed(v, strict=True)
                if st:
                    state_abbr = st
                    location = v
                    remaining_vals.remove(v)
                    break
                    
        for v in remaining_vals:
            if len(v) > 1 and len(v) < 60:
                company = v
                break
                
        updates.append({
            'rn': name,
            'em': email,
            'ph': phone,
            'comp_str': company,
            'loc': location,
            'li': linkedin,
            'st': state_abbr,
            'now': now
        })
        
    print(f"Extracted {len(updates)} valid recruiters! Opening database connection...", flush=True)
    
    session = SessionLocal()
    comp_map = dict(session.execute(text("SELECT LOWER(company_name), company_id FROM companies")).fetchall())
    
    # 1. Bulk insert new companies
    new_companies_to_insert = set()
    for u in updates:
        if u['comp_str']:
            c_lower = u['comp_str'].lower()
            if c_lower not in comp_map:
                new_companies_to_insert.add(u['comp_str'])
                
    if new_companies_to_insert:
        print(f"Inserting {len(new_companies_to_insert)} new companies...", flush=True)
        comp_batch = [{'cn': c, 'now': now} for c in new_companies_to_insert]
        # Insert in chunks
        for i in range(0, len(comp_batch), 1000):
            session.execute(text("""
                INSERT INTO companies (company_name, metadata_json, created_at, updated_at)
                VALUES (:cn, '{}', :now, :now) ON CONFLICT DO NOTHING
            """), comp_batch[i:i+1000])
        session.commit()
        # Refresh map
        comp_map = dict(session.execute(text("SELECT LOWER(company_name), company_id FROM companies")).fetchall())
        
    print("Preparing recruiter upserts...", flush=True)
    existing_emails = set(r[0] for r in session.execute(text("SELECT email FROM recruiters")).fetchall())
    
    inserts = []
    upds = []
    
    for u in updates:
        cid = comp_map.get(u['comp_str'].lower()) if u['comp_str'] else None
        
        # Safely truncate to avoid VARCHAR limits
        rn = u.get('rn') or (u.get('em').split('@')[0] if u.get('em') else "Unknown Recruiter")
        em = u.get('em')
        
        u['rn'] = rn[:100] if rn else None
        u['em'] = em[:150] if em else None
        u['ph'] = u.get('ph')[:20] if u.get('ph') else None
        u['loc'] = u.get('loc')[:100] if u.get('loc') else None
        u['li'] = u.get('li')[:150] if u.get('li') else None
        u['st'] = u.get('st')[:5] if u.get('st') else None
        u['cid'] = cid
        
        if u['em'] in existing_emails:
            upds.append(u)
        else:
            inserts.append(u)
            existing_emails.add(u['em'])
            
    print(f"Inserting {len(inserts)} completely new recruiters...", flush=True)
    for i in range(0, len(inserts), 1000):
        batch = inserts[i:i+1000]
        session.execute(text("""
            INSERT INTO recruiters (
                recruiter_name, email, phone, company_id, location, linkedin, state, created_at, updated_at, metadata_json
            ) VALUES (
                :rn, :em, :ph, :cid, :loc, :li, :st, :now, :now, '{}'
            ) ON CONFLICT DO NOTHING
        """), batch)
    session.commit()
    
    print(f"Enriching {len(upds)} existing recruiters...", flush=True)
    for i in range(0, len(upds), 1000):
        session.execute(text("""
            UPDATE recruiters SET
                recruiter_name = COALESCE(recruiters.recruiter_name, b.rn),
                phone = COALESCE(recruiters.phone, b.ph),
                company_id = COALESCE(recruiters.company_id, b.cid),
                location = COALESCE(recruiters.location, b.loc),
                linkedin = COALESCE(recruiters.linkedin, b.li),
                state = COALESCE(recruiters.state, b.st)
            FROM (VALUES (:rn, :em, :ph, CAST(:cid AS INTEGER), :loc, :li, :st)) AS b(rn, em, ph, cid, loc, li, st)
            WHERE recruiters.email = b.em
        """), upds[i:i+1000])
    session.commit()
    
    print("Finished!", flush=True)
    session.close()

if __name__ == '__main__':
    run_chaotic_import()
