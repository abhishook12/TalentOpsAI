import os
import sys
import uuid
import datetime
from sqlalchemy import text
from run_supabase_migration import (
    extract_raw_data,
    map_columns,
    clean_and_dedup,
    infer_states_and_normalize_companies,
    SessionLocal
)

import json

def run_import(file_path):
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return
        
    print(f"Processing new file: {file_path}")
    raw_df = extract_raw_data([file_path])
    mapped_df = map_columns(raw_df)
    records = clean_and_dedup(mapped_df)
    records, companies = infer_states_and_normalize_companies(records)
    
    db = SessionLocal()
    now = datetime.datetime.now(datetime.timezone.utc)
    
    # Build mapping for existing companies
    comp_map = dict(db.execute(text("SELECT company_name, company_id FROM companies")).fetchall())
    
    # Insert new companies
    for comp in companies:
        cname = comp['name']
        if cname not in comp_map:
            db.execute(text("""
                INSERT INTO companies (company_name, metadata_json, created_at, updated_at)
                VALUES (:cn, '{}', :now, :now)
            """), {'cn': cname, 'now': now})
    db.commit()
    
    # Re-fetch mapping to get the new company IDs
    comp_map = dict(db.execute(text("SELECT company_name, company_id FROM companies")).fetchall())
    
    # Insert recruiters
    success = 0
    
    for row in records:
        comp_id = comp_map.get(row.get('company_name'))
        
        email = row.get('email')
        if not email:
            email = f"no-email-{uuid.uuid4()}@talentops.ai"
            
        try:
            mj_str = json.dumps(row.get('metadata_json', {})) if isinstance(row.get('metadata_json'), dict) else '{}'
            db.execute(text("""
                INSERT INTO recruiters (
                    recruiter_name, email,
                    phone, company_id,
                    location, title, linkedin, state, state_source, state_confidence,
                    state_reason, needs_review, review_reason, metadata_json, created_at, updated_at
                ) VALUES (
                    :rn, :em,
                    :ph, :cid,
                    :loc, :ttl, :li, :st, :ss, :sc,
                    :sr, :nr, :rr, :mj, :now, :now
                ) ON CONFLICT (email) DO NOTHING
            """), {
                'rn': str(row.get('recruiter_name', ''))[:140] if row.get('recruiter_name') else None,
                'em': str(email)[:140],
                'ph': str(row.get('phone', ''))[:25] if row.get('phone') else None,
                'cid': comp_id,
                'loc': str(row.get('location', ''))[:140] if row.get('location') else None,
                'ttl': str(row.get('title', ''))[:140] if row.get('title') else None,
                'li': str(row.get('linkedin', ''))[:140] if row.get('linkedin') else None,
                'st': row.get('state'),
                'ss': str(row.get('state_source', ''))[:140] if row.get('state_source') else None,
                'sc': row.get('state_confidence'),
                'sr': row.get('state_reason'),
                'nr': row.get('needs_review', False),
                'rr': row.get('review_reason'),
                'mj': mj_str,
                'now': now
            })
            success += 1
            if success % 500 == 0:
                db.commit()
                print(f"Inserted {success} recruiters...")
        except Exception as e:
            db.rollback()
            print(f"Error on row: {e}")
            
    db.commit()
    db.close()
    print(f"Successfully processed and inserted new records for {file_path}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        run_import(sys.argv[1])
    else:
        print("Please provide a file path")

