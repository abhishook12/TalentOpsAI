import json
import re

from sqlalchemy.orm import Session
from sqlalchemy import update, text
from datetime import datetime
import io

from ..database import SessionLocal
from ..models.models import SmartImportJob, SmartImportRow, Recruiter, Company
from ..services.job_tracker import mark_progress, utc_now
from ..utils.state_mapper import extract_state_detailed
from ..utils.state_recovery import build_company_domain_state_index, infer_state_from_sources
from ..utils.phone_normalizer import format_us_phone

# Normalization Dictionaries
STATE_MAP = {
    "texas": "TX", "tx": "TX", "austin": "TX", "dallas": "TX", "houston": "TX",
    "michigan": "MI", "mi": "MI", "detroit": "MI",
    "california": "CA", "ca": "CA", "bay area": "CA", "san francisco": "CA", "los angeles": "CA",
    "new york": "NY", "ny": "NY", "nyc": "NY",
    "north carolina": "NC", "nc": "NC", "wilmington": "NC",
    "florida": "FL", "fl": "FL", "miami": "FL",
    # Add more as needed
}

def normalize_state(raw_val: str) -> str:
    if not raw_val: return None
    val = raw_val.lower().strip()
    for key, state_code in STATE_MAP.items():
        if key in val:
            return state_code
    return raw_val.strip().title()

def clean_phone(phone: str) -> str:
    if not phone:
        return None
    return format_us_phone(phone)

# Detect Smart Columns (Heuristics)
def detect_smart_columns(headers, sample_data):
    mapping = {}
    
    # Common variations
    regex_map = {
        "name": re.compile(r'(name|contact|full.*name)', re.I),
        "email": re.compile(r'(email|mail|e-mail)', re.I),
        "phone": re.compile(r'(phone|mobile|cell|contact.*no)', re.I),
        "company": re.compile(r'(company|firm|client|organization)', re.I),
        "state": re.compile(r'(state|region)', re.I),
        "location": re.compile(r'(location|city)', re.I),
        "linkedin": re.compile(r'(linkedin|url|profile)', re.I),
        "title": re.compile(r'(title|role|position)', re.I),
    }

    for target_field, regex in regex_map.items():
        best_match = None
        best_score = 0
        
        for h in headers:
            # Check header text
            if regex.search(h):
                best_match = h
                best_score = 90
                break
                
            # If not found by header, check sample data if it's an email/phone field
            if target_field == "email" and not best_match:
                for row in sample_data:
                    val = str(row.get(h, ''))
                    if "@" in val and "." in val:
                        best_match = h
                        best_score = 80
                        break
                        
        if best_match:
            mapping[target_field] = {"column": best_match, "confidence": best_score}
            
    return mapping

def validate_and_save_rows(job_id: str, column_mapping: dict):
    db: Session = SessionLocal()
    db.expire_on_commit = False
    job = db.query(SmartImportJob).filter(SmartImportJob.job_id == job_id).first()
    if not job: 
        db.close()
        return

    rows = db.query(SmartImportRow).filter(SmartImportRow.job_id == job_id).all()
    mark_progress(
        job,
        status="validating",
        current_step="Validating rows",
        progress_percent=40,
    )
    db.commit()
    
    valid_count = 0
    error_count = 0
    dup_count = 0
    warning_count = 0
    enriched_count = 0
    possible_duplicate_count = 0
    processed_count = 0
    
    email_col = column_mapping.get("email")
    name_col = column_mapping.get("name")
    company_col = column_mapping.get("company")
    phone_col = column_mapping.get("phone")
    state_col = column_mapping.get("state")
    location_col = column_mapping.get("location")
    linkedin_col = column_mapping.get("linkedin")
    title_col = column_mapping.get("title")

    # 1. Gather all unique keys from the uploaded batch to batch-fetch existing records
    emails_to_check = set()
    phones_to_check = set()
    names_to_check = set()
    for r in rows:
        raw = json.loads(r.raw_json)
        e = str(raw.get(email_col, "")).strip().lower()
        if "](mailto:" in e:
            m = re.search(r'\]\(mailto:(.*?)\)', e)
            if m: e = m.group(1)
        if e: emails_to_check.add(e)
        
        p = clean_phone(str(raw.get(phone_col, "")))
        if p: phones_to_check.add(p)
        
        n = str(raw.get(name_col, "")).strip().title()
        if n: names_to_check.add(n)
        
    # 2. Fetch only matching records from DB in chunks to avoid query parser hangs
    existing_by_email = {}
    if emails_to_check:
        emails_list = list(emails_to_check)
        for i in range(0, len(emails_list), 1000):
            for er in db.query(Recruiter).filter(Recruiter.email.in_(emails_list[i:i+1000])).all():
                existing_by_email[er.email.lower()] = er
                
    existing_by_phone = {}
    if phones_to_check:
        phones_list = list(phones_to_check)
        for i in range(0, len(phones_list), 1000):
            for er in db.query(Recruiter).filter(Recruiter.phone.in_(phones_list[i:i+1000])).all():
                existing_by_phone[er.phone] = er
                
    existing_by_name_comp = {}
    if names_to_check:
        names_list = list(names_to_check)
        for i in range(0, len(names_list), 1000):
            matching_names = db.query(Recruiter).outerjoin(Company, Recruiter.company_id == Company.company_id).filter(Recruiter.recruiter_name.in_(names_list[i:i+1000])).all()
            for er in matching_names:
                if er.recruiter_name and er.company and er.company.company_name:
                    existing_by_name_comp[(er.recruiter_name.strip().title(), er.company.company_name.strip().title())] = er

    # If vertical format, group rows
    if job.detected_format == "vertical_multi_value":
        # Group by name + company
        headers = list(json.loads(rows[0].raw_json).keys()) if rows else []
        type_col = next((c for c in headers if 'type' in c.lower()), None)
        val_col = next((c for c in headers if 'value' in c.lower()), None)
        
        grouped = {}
        for r in rows:
            raw = json.loads(r.raw_json)
            n = str(raw.get(name_col, "")).strip().title() if name_col else ""
            c = str(raw.get(company_col, "")).strip() if company_col else ""
            key = (n, c)
            
            if key not in grouped:
                grouped[key] = {"primary_row": r, "merged_rows": [], "combined": raw.copy(), "all_emails": [], "all_phones": [], "unmapped": {}}
            else:
                grouped[key]["merged_rows"].append(r)
                r.status = "Merged"
            
            if type_col and val_col:
                f_type = str(raw.get(type_col, "")).lower().strip()
                f_val = str(raw.get(val_col, "")).strip()
                if not f_val: continue
                
                if 'email' in f_type:
                    grouped[key]["all_emails"].append(f_val)
                    if not email_col: email_col = "__extracted_email"
                elif 'phone' in f_type or 'mobile' in f_type:
                    grouped[key]["all_phones"].append(f_val)
                    if not phone_col: phone_col = "__extracted_phone"
                elif 'title' in f_type:
                    if not title_col: title_col = "__extracted_title"
                    grouped[key]["combined"][title_col] = f_val
                elif 'linkedin' in f_type:
                    if not linkedin_col: linkedin_col = "__extracted_linkedin"
                    grouped[key]["combined"][linkedin_col] = f_val
                else:
                    grouped[key]["unmapped"][f_type] = f_val
                    
        # Apply combined data back
        for key, data in grouped.items():
            if data["all_emails"]:
                data["combined"][email_col] = data["all_emails"][0]
                if len(data["all_emails"]) > 1:
                    data["combined"]["__email2"] = data["all_emails"][1]
            if data["all_phones"]:
                data["combined"][phone_col] = data["all_phones"][0]
                if len(data["all_phones"]) > 1:
                    data["combined"]["__phone2"] = data["all_phones"][1]
            data["combined"]["__unmapped_fields"] = data["unmapped"]
            data["primary_row"].raw_json = json.dumps(data["combined"])

    row_updates = []
    for r in rows:
        if r.status == "Merged":
            continue
        
        processed_count += 1
        raw = json.loads(r.raw_json)
        issues = []
        status = "Ready"
        
        # Extract based on mapping
        raw_email = str(raw.get(email_col, "")).strip().lower() if email_col else ""
        raw_name = str(raw.get(name_col, "")).strip().title() if name_col else ""
        raw_company = str(raw.get(company_col, "")).strip() if company_col else ""
        raw_phone = str(raw.get(phone_col, "")).strip() if phone_col else ""
        raw_state = str(raw.get(state_col, "")).strip() if state_col else ""
        raw_location = str(raw.get(location_col, "")).strip() if location_col else ""
        
        if "](mailto:" in raw_email:
            m = re.search(r'\]\(mailto:(.*?)\)', raw_email)
            if m: raw_email = m.group(1)
            
        row_update = {
            "row_id": r.row_id,
            "status": status,
            "validation_issues": json.dumps(issues),
            "email": raw_email if raw_email else None,
            "recruiter_name": r.recruiter_name if r.recruiter_name else (raw_name if raw_name else None),
            "company_name": r.company_name if hasattr(r, 'company_name') and r.company_name else (raw_company if raw_company else None),
            "phone": clean_phone(raw_phone),
            "state": normalize_state(raw_state) or (normalize_state(raw_location) if raw_location else None),
            "location": raw_location if raw_location else None,
            "linkedin": str(raw.get(linkedin_col, "")).strip() if linkedin_col else None,
            "title": str(raw.get(title_col, "")).strip() if title_col else None
        }
        
        if not row_update["recruiter_name"] and row_update["email"]:
            row_update["recruiter_name"] = row_update["email"].split("@")[0].replace(".", " ").title()
            issues.append("Name generated from email")
            if status == "Ready": status = "Warning"
            row_update["status"] = status
            row_update["validation_issues"] = json.dumps(issues)
            warning_count += 1
            
        if not row_update["company_name"] and row_update["email"]:
            domain = row_update["email"].split("@")[-1].split(".")[0].title()
            if domain not in ("Gmail", "Yahoo", "Hotmail", "Outlook", "Aol", "Icloud"):
                row_update["company_name"] = domain
                issues.append("Company inferred from email")
                if status == "Ready": status = "Warning"
                row_update["status"] = status
                row_update["validation_issues"] = json.dumps(issues)
                warning_count += 1

        # Check for duplicates
        email_to_check = row_update["email"]
        phone_to_check = row_update["phone"]
        name_comp_key = (row_update["recruiter_name"], row_update["company_name"])
        
        if email_to_check and email_to_check in existing_by_email:
            status = "Enrich"
            issues.append("Exact email match. Will enrich existing record.")
        elif phone_to_check and phone_to_check in existing_by_phone:
            status = "Possible Duplicate"
            issues.append("Phone number matches an existing recruiter.")
        elif row_update["recruiter_name"] and row_update["company_name"] and name_comp_key in existing_by_name_comp:
            status = "Possible Duplicate"
            issues.append("Name and Company match an existing recruiter.")
            
        row_update["status"] = status
        row_update["validation_issues"] = json.dumps(issues)

        row_updates.append(row_update)

        if status in ["Ready", "Warning", "Possible Duplicate"]:
            valid_count += 1
        elif status == "Enrich":
            dup_count += 1 # We count enrichments as duplicates in the overall tally
            enriched_count += 1
        elif status == "Error":
            error_count += 1

        if processed_count % 200 == 0:
            step_text = f"Validating rows ({processed_count}/{len(rows)})"
            prog_val = 40 + int(40 * (processed_count / max(len(rows), 1)))
            job.current_step = step_text
            job.progress_percent = prog_val
            # Direct SQL update in a separate session avoids expiring the ORM objects in the main session!
            progress_db = SessionLocal()
            try:
                progress_db.execute(
                    update(SmartImportJob).where(SmartImportJob.job_id == job_id).values(
                        current_step=step_text,
                        progress_percent=prog_val,
                        last_heartbeat_at=datetime.utcnow(),
                        updated_at=datetime.utcnow()
                    )
                )
                progress_db.commit()
            finally:
                progress_db.close()

    # Apply all updates in chunks for massive speedup without hitting Neon limits
    if row_updates:
        chunk_size = 200
        for i in range(0, len(row_updates), chunk_size):
            db.bulk_update_mappings(SmartImportRow, row_updates[i:i+chunk_size])

    job.valid_rows = valid_count
    job.error_rows = error_count
    job.duplicate_rows = dup_count
    job.warning_rows = warning_count
    job.possible_duplicate_rows = possible_duplicate_count
    job.enriched_rows = enriched_count
    job.failed_rows = error_count
    job.processed_rows = processed_count
    mark_progress(
        job,
        status="preview_ready",
        current_step="Validation complete",
        progress_percent=80,
        processed_rows=processed_count,
        valid_rows=valid_count,
        warning_rows=warning_count,
        error_rows=error_count,
        duplicate_rows=dup_count,
        possible_duplicate_rows=possible_duplicate_count,
        enriched_rows=enriched_count,
        failed_rows=error_count,
    )
    
    db.commit()
    db.close()


def process_commit(job_id: str):
    db: Session = SessionLocal()
    db.expire_on_commit = False
    job = db.query(SmartImportJob).filter(SmartImportJob.job_id == job_id).first()
    if not job: 
        db.close()
        return
        
    rows = db.query(SmartImportRow).filter(SmartImportRow.job_id == job_id).all()
    column_mapping = json.loads(job.column_mapping) if job.column_mapping else {}
    
    # ---------------------------------------------------------
    # NEW ARCHITECTURE: ROUTE TO BUCKET ONLY, BYPASS POSTGRES
    # ---------------------------------------------------------
    import uuid
    import gzip
    import os
    
    bucket_data = []
    processed = 0
    
    for i, r in enumerate(rows):
        processed += 1
        if r.status in ["Ready", "Warning", "Possible Duplicate", "Enrich"]:
            raw_dict = json.loads(r.raw_json)
            # Compile the raw payload for the bucket archive
            bucket_row = {
                "recruiter_name": r.recruiter_name,
                "email": r.email,
                "phone": r.phone,
                "company": r.company_name,
                "location": r.location,
                "state": r.state,
                "linkedin": r.linkedin,
                "title": r.title,
                "import_status": r.status,
                "validation_issues": json.loads(r.validation_issues) if r.validation_issues else [],
                "raw_metadata": raw_dict
            }
            bucket_data.append(bucket_row)
            
        if processed % 200 == 0:
            step_text = f"Packaging rows for bucket ({processed}/{len(rows)})"
            prog_val = 80 if not len(rows) else min(98, 80 + int((processed / max(len(rows), 1)) * 18))
            db.execute(
                update(SmartImportJob).where(SmartImportJob.job_id == job_id).values(
                    status="importing",
                    current_step=step_text,
                    progress_percent=prog_val,
                    processed_rows=processed,
                    last_heartbeat_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
            )
            db.commit()

    # Create the Archive File
    archive_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "archives")
    os.makedirs(archive_dir, exist_ok=True)
    file_id = uuid.uuid4().hex[:8]
    archive_path = os.path.join(archive_dir, f"import_{job_id}_{file_id}.json.gz")
    
    with gzip.open(archive_path, 'wt', encoding='utf-8') as f:
        json.dump(bucket_data, f)
        
    file_size_bytes = os.path.getsize(archive_path)
    
    # Register in Supabase Storage Bucket
    path_name = f"archives/import_{job_id}_{file_id}.json.gz"
    metadata = json.dumps({
        "size": file_size_bytes,
        "mimetype": "application/gzip",
        "job_id": job_id,
        "total_rows": len(bucket_data)
    })
    
    db.execute(text("""
        INSERT INTO storage.objects (id, bucket_id, name, owner, created_at, updated_at, last_accessed_at, metadata, version)
        VALUES (:id, 'recruiter-data', :name, NULL, NOW(), NOW(), NOW(), :metadata, :version)
    """), {
        "id": str(uuid.uuid4()),
        "name": path_name,
        "metadata": metadata,
        "version": str(uuid.uuid4())
    })
    
    job.inserted_rows = len(bucket_data) # We count bucket saves as "inserted" to clear the UI
    job.skipped_rows = len(rows) - len(bucket_data)
    job.processed_rows = processed
    mark_progress(
        job,
        status="completed",
        current_step="Routed directly to Bucket Storage",
        progress_percent=100,
        processed_rows=processed,
        inserted_rows=len(bucket_data),
        skipped_rows=job.skipped_rows,
    )
    job.completed_at = utc_now()
    db.commit()
    db.close()


def generate_excel_from_rows(rows):
    import pandas as pd
    data = []
    for r in rows:
        data.append({
            "Name": r.recruiter_name,
            "Email": r.email,
            "Phone": r.phone,
            "Company": r.company_name,
            "State": r.state,
            "Location": r.location,
            "Status": r.status,
            "Issues": ", ".join(json.loads(r.validation_issues)) if r.validation_issues else ""
        })
    df = pd.DataFrame(data)
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    
    return output.getvalue()
