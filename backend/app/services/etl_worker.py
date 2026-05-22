import pandas as pd
import json
import traceback
from datetime import datetime
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.models import UploadJob, Recruiter, Company
from app.utils.state_mapper import normalize_state

def clean_val(v):
    if pd.isna(v): return None
    s = str(v).strip()
    return s if s and s.lower() not in ('none', 'n/a', 'nan', 'null', '') else None

def clean_email(email): 
    return str(email).lower().strip() if email else None

def clean_phone(phone): 
    if not phone: return None
    return str(phone).replace("-","").replace(" ","").replace("(","").replace(")","").strip()

def process_smart_import(job_id: str, filepath: str, column_map: dict):
    db: Session = SessionLocal()
    job = db.query(UploadJob).filter(UploadJob.job_id == job_id).first()
    
    if not job:
        db.close()
        return

    job.status = "processing"
    db.commit()

    try:
        if filepath.lower().endswith('.csv'):
            df = pd.read_csv(filepath, dtype=str, keep_default_na=False)
        else:
            df = pd.read_excel(filepath, dtype=str, keep_default_na=False)

        job.total_rows = len(df)
        db.commit()

        email_col = column_map.get('email')
        name_col = column_map.get('name')
        phone_col = column_map.get('phone')
        phone2_col = column_map.get('phone2')
        email2_col = column_map.get('email2')
        linkedin_col = column_map.get('linkedin')
        spec_col = column_map.get('specialization')
        notes_col = column_map.get('notes')
        company_col = column_map.get('company')
        location_col = column_map.get('location')
        state_col = column_map.get('state')

        inserted = 0
        skipped = 0
        errors = 0
        processed = 0
        error_log = []

        # Cache existing companies
        companies = db.query(Company.company_id, Company.company_name).all()
        company_cache = {c.company_name.lower(): c.company_id for c in companies if c.company_name}
        
        # Cache existing emails
        existing_emails = {row[0] for row in db.query(Recruiter.email).all()}

        new_companies = {}
        batch_size = 2000
        new_recruiters = []

        for idx, row in df.iterrows():
            processed += 1
            try:
                raw_email = clean_val(row.get(email_col, ''))
                email = clean_email(raw_email)
                
                if not email or '@' not in email:
                    skipped += 1
                    continue

                if email in existing_emails:
                    skipped += 1
                    continue

                # Handle Company
                company_name = clean_val(row.get(company_col, '')) if company_col else None
                company_id = None
                if company_name:
                    c_key = company_name.lower()
                    if c_key in company_cache:
                        company_id = company_cache[c_key]
                    else:
                        if c_key not in new_companies:
                            new_comp = Company(company_name=company_name)
                            db.add(new_comp)
                            db.commit()
                            db.refresh(new_comp)
                            new_companies[c_key] = new_comp.company_id
                            company_cache[c_key] = new_comp.company_id
                        company_id = new_companies[c_key]

                # State handling
                loc_val = clean_val(row.get(location_col, '')) if location_col else None
                state_val = clean_val(row.get(state_col, '')) if state_col else None
                
                state_abbr = None
                if state_val:
                    state_abbr = normalize_state(state_val)
                if not state_abbr and loc_val:
                    state_abbr = normalize_state(loc_val)

                raw_name = clean_val(row.get(name_col, '')) if name_col else None
                fallback_name = email.split('@')[0].title()
                
                new_recruiters.append({
                    "recruiter_name": raw_name or fallback_name,
                    "email": email,
                    "phone": clean_phone(clean_val(row.get(phone_col, ''))) if phone_col else None,
                    "email2": clean_email(clean_val(row.get(email2_col, ''))) if email2_col else None,
                    "phone2": clean_phone(clean_val(row.get(phone2_col, ''))) if phone2_col else None,
                    "linkedin": clean_val(row.get(linkedin_col, '')) if linkedin_col else None,
                    "specialization": clean_val(row.get(spec_col, '')) if spec_col else None,
                    "notes": clean_val(row.get(notes_col, '')) if notes_col else None,
                    "company_id": company_id,
                    "location": loc_val,
                    "state": state_abbr,
                    "is_active": True,
                })
                
                existing_emails.add(email) # Prevent duplicates within the same batch

                if len(new_recruiters) >= batch_size:
                    db.bulk_insert_mappings(Recruiter, new_recruiters)
                    db.commit()
                    inserted += len(new_recruiters)
                    new_recruiters = []
                    
                    job.processed_rows = processed
                    job.inserted_rows = inserted
                    job.skipped_rows = skipped
                    job.error_count = errors
                    db.commit()

            except Exception as e:
                errors += 1
                error_log.append({"row": processed, "reason": str(e)})

        # Insert remaining records
        if new_recruiters:
            try:
                db.bulk_insert_mappings(Recruiter, new_recruiters)
                db.commit()
                inserted += len(new_recruiters)
            except Exception as e:
                db.rollback()
                errors += len(new_recruiters)
                error_log.append({"row": "batch", "reason": f"Final batch commit failed: {e}"})

        job.status = "completed"
        job.processed_rows = processed
        job.inserted_rows = inserted
        job.skipped_rows = skipped
        job.error_count = errors
        job.errors = json.dumps(error_log)
        job.completed_at = datetime.utcnow()
        db.commit()

    except Exception as e:
        db.rollback()
        job.status = "failed"
        job.errors = json.dumps([{"row": 0, "reason": f"Fatal pipeline error: {traceback.format_exc()}"}])
        job.completed_at = datetime.utcnow()
        db.commit()
    finally:
        db.close()
