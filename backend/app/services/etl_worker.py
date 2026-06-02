import pandas as pd
import json
import traceback
from datetime import datetime
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.models import UploadJob, RawUpload, Recruiter, Company
from app.utils.normalizer import normalize_text, extract_domain
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

def clean_name(name):
    if not name:
        return None
    value = str(name).strip()
    return value if value else None

def build_company_name(company_name: str | None) -> str | None:
    if not company_name:
        return None
    value = str(company_name).strip()
    return value if value else None

def get_or_create_company(db: Session, company_name: str | None, location: str | None, state: str | None, email: str | None):
    company_name = build_company_name(company_name)
    if not company_name:
        return None

    normalized_name = normalize_text(company_name)
    if not normalized_name:
        return None

    company = db.query(Company).filter(Company.normalized_company_name == normalized_name).first()
    if company:
        return company

    domain = extract_domain(email) if email else ""
    if domain and domain not in {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "aol.com"}:
        company = db.query(Company).filter(
            (Company.website.ilike(f"%{domain}%")) |
            (Company.email_pattern.ilike(f"%{domain}%"))
        ).first()
        if company:
            return company

    company = Company(
        company_name=company_name,
        normalized_company_name=normalized_name,
        location=location,
        state=state,
        data_source="etl",
        trust_score=80,
        is_active=True,
    )
    db.add(company)
    db.flush()
    return company

def calculate_completeness(name: str | None, email: str | None, phone: str | None, company_id: int | None, location: str | None, state: str | None) -> int:
    score = 0
    if name: score += 25
    if email: score += 25
    if phone: score += 15
    if company_id: score += 15
    if location: score += 10
    if state: score += 10
    return min(score, 100)

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
        existing_emails = set(
            email for (email,) in db.query(Recruiter.email).all() if email
        )

        batch_size = 500
        new_raw = []

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

                if email in existing_emails:
                    skipped += 1
                    continue

                raw_name = clean_name(clean_val(row.get(name_col, ''))) if name_col else None
                fallback_name = email.split('@')[0].replace('.', ' ').replace('_', ' ').title()
                company_name = clean_val(row.get(company_col, '')) if company_col else None
                loc_val = clean_val(row.get(location_col, '')) if location_col else None
                state_val = clean_val(row.get(state_col, '')) if state_col else None
                normalized_state = normalize_state(state_val or loc_val) if (state_val or loc_val) else None

                company = get_or_create_company(db, company_name, loc_val, normalized_state, email)
                company_id = company.company_id if company else None

                recruiter_name = raw_name or fallback_name
                if not recruiter_name:
                    skipped += 1
                    continue

                phone_val = clean_phone(clean_val(row.get(phone_col, ''))) if phone_col else None
                recruiter = Recruiter(
                    recruiter_name=recruiter_name,
                    normalized_recruiter_name=normalize_text(recruiter_name),
                    email=email,
                    phone=phone_val,
                    company_id=company_id,
                    location=loc_val,
                    state=normalized_state,
                    normalized_city=normalize_text(loc_val) if loc_val else None,
                    location_confidence="high" if normalized_state or loc_val else "low",
                    completeness_score=calculate_completeness(recruiter_name, email, phone_val, company_id, loc_val, normalized_state),
                    needs_review=not bool(company_id and normalized_state),
                    data_source="etl",
                    trust_score=80 if company_id else 65,
                    is_active=True,
                )
                db.add(recruiter)
                existing_emails.add(email)

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

