import json
import re
import pandas as pd
from sqlalchemy.orm import Session
from datetime import datetime
import io

from app.database import SessionLocal
from app.models.models import SmartImportJob, SmartImportRow, Recruiter, Company
from app.services.job_tracker import mark_progress, utc_now

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
    if not phone: return None
    p = str(phone).replace("-","").replace(" ","").replace("(","").replace(")","").replace("+","").strip()
    if len(p) == 11 and p.startswith("1"):
        p = p[1:]
    return p if p else None

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
        
    # 2. Fetch only matching records from DB
    existing_by_email = {er.email.lower(): er for er in db.query(Recruiter).filter(Recruiter.email.in_(emails_to_check)).all()} if emails_to_check else {}
    existing_by_phone = {er.phone: er for er in db.query(Recruiter).filter(Recruiter.phone.in_(phones_to_check)).all()} if phones_to_check else {}
    
    existing_by_name_comp = {}
    if names_to_check:
        matching_names = db.query(Recruiter).outerjoin(Company, Recruiter.company_id == Company.company_id).filter(Recruiter.recruiter_name.in_(names_to_check)).all()
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

        row_updates.append(row_update)

        if status in ["Ready", "Warning", "Possible Duplicate"]:
            valid_count += 1
        elif status == "Enrich":
            dup_count += 1 # We count enrichments as duplicates in the overall tally
            enriched_count += 1
        elif status == "Error":
            error_count += 1

        if processed_count % 200 == 0:
            # We don't commit here because we haven't flushed row_updates yet!
            job.current_step = f"Validating rows ({processed_count}/{len(rows)})"
            job.progress_percent = 40 + int(40 * (processed_count / max(len(rows), 1)))

    # Apply all updates in chunks for massive speedup without hitting Neon limits
    if row_updates:
        chunk_size = 2000
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
    job = db.query(SmartImportJob).filter(SmartImportJob.job_id == job_id).first()
    if not job: 
        db.close()
        return
        
    rows = db.query(SmartImportRow).filter(SmartImportRow.job_id == job_id).all()
    column_mapping = json.loads(job.column_mapping) if job.column_mapping else {}
    
    # We want the values (mapped column names from the file)
    mapped_keys = [k for k in column_mapping.values() if k and isinstance(k, str)]
    
    from app.utils.normalizer import normalize_text
    
    # Cache companies to avoid n+1 selects
    company_cache = {normalize_text(c.company_name): c for c in db.query(Company).all() if c.company_name}
    
    inserted = 0
    skipped = 0
    processed = 0
    
    for i, r in enumerate(rows):
        processed += 1
        if r.status in ["Ready", "Warning", "Possible Duplicate", "Enrich"]:
            # Process Company
            company_id = None
            if r.company_name:
                norm_comp = normalize_text(r.company_name)
                if norm_comp in company_cache:
                    company_id = company_cache[norm_comp].company_id
                else:
                    new_comp = Company(
                        company_name=r.company_name,
                        normalized_company_name=norm_comp,
                        location=r.location,
                        state=r.state,
                        is_active=True,
                        data_source="smart_import",
                        source_job_id=job_id
                    )
                    db.add(new_comp)
                    db.commit()
                    db.refresh(new_comp)
                    company_cache[norm_comp] = new_comp
                    company_id = new_comp.company_id

            # Preserve metadata (unknown columns)
            raw_dict = json.loads(r.raw_json)
            metadata = {k: v for k, v in raw_dict.items() if k not in mapped_keys and not k.startswith("__") and v is not None and str(v).strip() != ""}
            if "__unmapped_fields" in raw_dict:
                metadata.update(raw_dict["__unmapped_fields"])
            
            # Extract alternative emails/phones from metadata
            email2 = raw_dict.get("__email2")
            phone2 = raw_dict.get("__phone2")
            for k, v in metadata.items():
                key_lower = k.lower()
                if "email" in key_lower and not email2 and str(v).strip().lower() != (r.email or "").lower():
                    email2 = str(v).strip()
                elif ("phone" in key_lower or "mobile" in key_lower or "cell" in key_lower) and not phone2:
                    cp = clean_phone(str(v))
                    if cp and cp != r.phone:
                        phone2 = cp
                        
            metadata_json = json.dumps(metadata) if metadata else None
            
            if r.status == "Enrich":
                # Find existing recruiter and merge data
                existing = None
                if r.email:
                    existing = db.query(Recruiter).filter(Recruiter.email == r.email).first()
                if not existing and r.phone:
                    existing = db.query(Recruiter).filter(Recruiter.phone == r.phone).first()
                
                if existing:
                    # Enrich missing core fields
                    if not existing.phone and r.phone: existing.phone = r.phone
                    if not existing.title and r.title:
                        existing.title = r.title
                        existing.specialization = r.title
                    if not existing.location and r.location: existing.location = r.location
                    if not existing.state and r.state: existing.state = r.state
                    if not existing.linkedin and r.linkedin: existing.linkedin = r.linkedin
                    if not existing.company_id and company_id: existing.company_id = company_id
                    
                    if email2 and not existing.email2: existing.email2 = email2
                    if phone2 and not existing.phone2: existing.phone2 = phone2
                    
                    # Merge metadata
                    if metadata:
                        existing_meta = json.loads(existing.metadata_json) if existing.metadata_json else {}
                        existing_meta.update(metadata)
                        existing.metadata_json = json.dumps(existing_meta)
                        
                    inserted += 1 # Count as successful import/update
            else:
                # Insert new recruiter (Ready, Warning, Possible Duplicate)
                needs_review = (r.status == "Possible Duplicate")
                notes = "[Possible Duplicate] Uploaded with matching details to an existing profile." if needs_review else None
                
                rec = Recruiter(
                    recruiter_name=r.recruiter_name,
                    normalized_recruiter_name=normalize_text(r.recruiter_name) if r.recruiter_name else None,
                    email=r.email,
                    phone=r.phone,
                    email2=email2,
                    phone2=phone2,
                    linkedin=r.linkedin,
                    specialization=r.title,
                    title=r.title,
                    company_id=company_id,
                    location=r.location,
                    state=r.state,
                    is_active=True,
                    data_source="smart_import",
                    source_job_id=job_id,
                    raw_data=r.raw_json,
                    metadata_json=metadata_json,
                    needs_review=needs_review,
                    notes=notes
                )
                db.add(rec)
                inserted += 1
                
            # Chunked commits
            if inserted % 500 == 0:
                db.commit()
        else:
            skipped += 1

        if processed % 200 == 0:
            mark_progress(
                job,
                status="importing",
                current_step=f"Importing rows {processed}/{len(rows)}",
                progress_percent=80 if not len(rows) else min(98, 80 + int((processed / max(len(rows), 1)) * 18)),
                processed_rows=processed,
                inserted_rows=inserted,
                skipped_rows=skipped,
            )
            db.commit()
            
    db.commit()
    
    job.inserted_rows = inserted
    job.skipped_rows = skipped
    job.processed_rows = processed
    mark_progress(
        job,
        status="completed",
        current_step="Import completed",
        progress_percent=100,
        processed_rows=processed,
        inserted_rows=inserted,
        skipped_rows=skipped,
    )
    job.completed_at = utc_now()
    
    db.commit()
    db.close()


def generate_excel_from_rows(rows):
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
