import pandas as pd
import json
import traceback
from datetime import datetime
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.models import UploadJob, RawUpload, StagingRecruiter, StagingCompany
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
        company_col = column_map.get('company')
        location_col = column_map.get('location')
        state_col = column_map.get('state')

        inserted = 0
        skipped = 0
        errors = 0
        processed = 0
        error_log = []

        batch_size = 500
        new_raw = []
        new_staging_recs = []
        new_staging_comps = []

        for idx, row in df.iterrows():
            processed += 1
            try:
                raw_json = json.dumps(row.to_dict(), default=str)
                raw_obj = RawUpload(
                    job_id=job_id,
                    raw_data=raw_json,
                    source_filename=job.filename
                )
                db.add(raw_obj)
                db.flush() # To get raw_obj.id

                email = clean_email(clean_val(row.get(email_col, '')))
                if not email or '@' not in email:
                    skipped += 1
                    continue

                raw_name = clean_val(row.get(name_col, '')) if name_col else None
                fallback_name = email.split('@')[0].title()
                company_name = clean_val(row.get(company_col, '')) if company_col else None
                loc_val = clean_val(row.get(location_col, '')) if location_col else None

                staging_rec = StagingRecruiter(
                    job_id=job_id,
                    raw_upload_id=raw_obj.id,
                    recruiter_name=raw_name or fallback_name,
                    email=email,
                    phone=clean_phone(clean_val(row.get(phone_col, ''))) if phone_col else None,
                    company_name=company_name,
                    location=loc_val,
                    status="pending",
                    confidence_score=0
                )
                db.add(staging_rec)

                if company_name:
                    staging_comp = StagingCompany(
                        job_id=job_id,
                        company_name=company_name,
                        location=loc_val,
                        status="pending"
                    )
                    db.add(staging_comp)

                inserted += 1

                if inserted % batch_size == 0:
                    db.commit()
                    job.processed_rows = processed
                    job.inserted_rows = inserted
                    job.skipped_rows = skipped
                    job.error_count = errors
                    db.commit()

            except Exception as e:
                errors += 1
                error_log.append({"row": processed, "reason": str(e)})

        db.commit()

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

