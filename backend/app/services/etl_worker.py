import csv
import json
import os
import traceback
from datetime import datetime

import pandas as pd
from openpyxl import load_workbook
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.models import Company, RawUpload, Recruiter, UploadJob
from app.utils.normalizer import extract_domain, normalize_text
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

def iter_file_batches(filepath: str, batch_size: int = 2000):
    if filepath.lower().endswith(".csv"):
        for chunk in pd.read_csv(filepath, dtype=str, keep_default_na=False, chunksize=batch_size):
            yield chunk.fillna("").to_dict(orient="records")
        return

    workbook = load_workbook(filepath, read_only=True, data_only=True)
    worksheet = workbook.active
    rows = worksheet.iter_rows(values_only=True)
    headers = [str(header).strip() if header is not None else "" for header in next(rows, [])]
    batch: list[dict] = []
    for values in rows:
        row = {}
        for index, header in enumerate(headers):
            if not header:
                continue
            row[header] = values[index] if index < len(values) else None
        batch.append(row)
        if len(batch) >= batch_size:
            yield batch
            batch = []
    if batch:
        yield batch
    workbook.close()

def get_or_create_company(
    db: Session,
    company_name: str | None,
    location: str | None,
    state: str | None,
    email: str | None,
    company_cache: dict[str, int],
):
    company_name = build_company_name(company_name)
    if not company_name:
        return None

    normalized_name = normalize_text(company_name)
    if not normalized_name:
        return None

    if normalized_name in company_cache:
        return company_cache[normalized_name]

    company = db.query(Company).filter(Company.normalized_company_name == normalized_name).first()
    if company:
        company_cache[normalized_name] = company.company_id
        return company.company_id

    domain = extract_domain(email) if email else ""
    if domain and domain not in {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "aol.com"}:
        company = db.query(Company).filter(
            (Company.website.ilike(f"%{domain}%")) |
            (Company.email_pattern.ilike(f"%{domain}%"))
        ).first()
        if company:
            company_cache[normalized_name] = company.company_id
            return company.company_id

    company = Company(
        company_name=company_name,
        normalized_company_name=normalized_name,
        location=location,
        state=state,
        data_source="etl",
        trust_score=80,
        is_active=True,
        source_job_id=job_id,
    )
    db.add(company)
    db.flush()
    company_cache[normalized_name] = company.company_id
    return company.company_id

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
        existing_emails = {
            email for (email,) in db.query(Recruiter.email).yield_per(5000) if email
        }
        company_cache: dict[str, int] = {
            normalized: company_id
            for company_id, normalized in db.query(Company.company_id, Company.normalized_company_name).all()
            if normalized
        }

        batch_size = 2000
        job.total_rows = 0
        db.commit()

        for batch in iter_file_batches(filepath, batch_size=batch_size):
            job.total_rows += len(batch)
            raw_rows = []
            recruiter_rows = []

            for row in batch:
                processed += 1
                try:
                    email = clean_email(clean_val(row.get(email_col, '')))
                    if not email or '@' not in email:
                        skipped += 1
                        continue

                    if email in existing_emails:
                        skipped += 1
                        continue

                    raw_name = clean_name(clean_val(row.get(name_col, ''))) if name_col else None
                    fallback_name = email.split('@')[0].replace('.', ' ').replace('_', ' ').title()
                    recruiter_name = raw_name or fallback_name
                    if not recruiter_name:
                        skipped += 1
                        continue

                    company_name = clean_val(row.get(company_col, '')) if company_col else None
                    loc_val = clean_val(row.get(location_col, '')) if location_col else None
                    state_val = clean_val(row.get(state_col, '')) if state_col else None
                    normalized_state = normalize_state(state_val or loc_val) if (state_val or loc_val) else None
                    phone_val = clean_phone(clean_val(row.get(phone_col, ''))) if phone_col else None
                    company_id = get_or_create_company(
                        db,
                        company_name,
                        loc_val,
                        normalized_state,
                        email,
                        company_cache,
                    )

                    raw_rows.append({
                        "job_id": job_id,
                        "raw_data": json.dumps(row, default=str),
                        "source_filename": job.filename,
                    })

                    recruiter_rows.append({
                        "recruiter_name": recruiter_name,
                        "normalized_recruiter_name": normalize_text(recruiter_name),
                        "email": email,
                        "phone": phone_val,
                        "company_id": company_id,
                        "location": loc_val,
                        "state": normalized_state,
                        "normalized_city": normalize_text(loc_val) if loc_val else None,
                        "location_confidence": "high" if normalized_state or loc_val else "low",
                        "completeness_score": calculate_completeness(
                            recruiter_name,
                            email,
                            phone_val,
                            company_id,
                            loc_val,
                            normalized_state,
                        ),
                        "needs_review": not bool(company_id and normalized_state),
                        "data_source": "etl",
                        "trust_score": 80 if company_id else 65,
                        "is_active": True,
                        "source_job_id": job_id,
                    })
                    existing_emails.add(email)
                    inserted += 1
                except Exception as e:
                    errors += 1
                    error_log.append({"row": processed, "reason": str(e)})

            try:
                if raw_rows:
                    db.bulk_insert_mappings(RawUpload, raw_rows)
                if recruiter_rows:
                    db.bulk_insert_mappings(Recruiter, recruiter_rows)
                db.commit()
            except Exception as batch_error:
                db.rollback()
                errors += len(recruiter_rows) or 1
                error_log.append({"row": processed, "reason": str(batch_error)})

            job.processed_rows = processed
            job.inserted_rows = inserted
            job.skipped_rows = skipped
            job.error_count = errors
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

