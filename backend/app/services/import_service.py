import json
import re
import pandas as pd
from sqlalchemy.orm import Session
from datetime import datetime
import io

from app.database import SessionLocal
from app.models.models import SmartImportJob, SmartImportRow, Recruiter, Company

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
    
    valid_count = 0
    error_count = 0
    dup_count = 0
    
    # Caches for advanced deduplication
    existing_emails = {e[0].lower() for e in db.query(Recruiter.email).filter(Recruiter.email.isnot(None)).all() if e[0]}
    existing_phones = {clean_phone(p[0]) for p in db.query(Recruiter.phone).filter(Recruiter.phone.isnot(None)).all() if p[0] and clean_phone(p[0])}
    existing_linkedin = {l[0].lower().strip() for l in db.query(Recruiter.linkedin).filter(Recruiter.linkedin.isnot(None)).all() if l[0]}
    
    # Pre-fetch companies for name+company dedupe
    existing_rec_comps = db.query(Recruiter.recruiter_name, Company.company_name).outerjoin(Company, Recruiter.company_id == Company.company_id).all()
    existing_name_company = set()
    for name, comp in existing_rec_comps:
        if name and comp:
            existing_name_company.add((name.strip().title(), comp.strip().title()))
    
    email_col = column_mapping.get("email")
    name_col = column_mapping.get("name")
    company_col = column_mapping.get("company")
    phone_col = column_mapping.get("phone")
    state_col = column_mapping.get("state")
    location_col = column_mapping.get("location")
    linkedin_col = column_mapping.get("linkedin")
    title_col = column_mapping.get("title")

    for r in rows:
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
        
        # Remove Markdown Links from email e.g. [a@b.com](mailto:a@b.com)
        if "](mailto:" in raw_email:
            m = re.search(r'\]\(mailto:(.*?)\)', raw_email)
            if m: raw_email = m.group(1)
            
        r.email = raw_email if raw_email else None
        r.recruiter_name = raw_name if raw_name else None
        r.company_name = raw_company if raw_company else None
        r.phone = clean_phone(raw_phone)
        r.state = normalize_state(raw_state)
        if not r.state and raw_location: # fallback location->state
            r.state = normalize_state(raw_location)
            
        r.location = raw_location if raw_location else None
        r.linkedin = str(raw.get(linkedin_col, "")).strip() if linkedin_col else None
        r.title = str(raw.get(title_col, "")).strip() if title_col else None
        
        # Validation Logic
        if not r.email:
            issues.append("Missing email")
            status = "Error"
        elif "@" not in r.email or "." not in r.email:
            issues.append("Invalid email format")
            status = "Error"
        elif r.email.lower() in existing_emails:
            issues.append("Duplicate email in database")
            status = "Duplicate"
        elif r.phone and r.phone in existing_phones:
            issues.append("Duplicate phone in database")
            status = "Duplicate"
        elif r.linkedin and r.linkedin.lower().strip() in existing_linkedin:
            issues.append("Duplicate LinkedIn in database")
            status = "Duplicate"
        elif r.recruiter_name and r.company_name and (r.recruiter_name.title(), r.company_name.title()) in existing_name_company:
            issues.append("Duplicate Name+Company in database")
            status = "Duplicate"
            
        if not r.recruiter_name and r.email:
            # Auto-generate name from email
            r.recruiter_name = r.email.split("@")[0].replace(".", " ").title()
            issues.append("Name generated from email")
            if status == "Ready": status = "Warning"
            
        if not r.company_name and r.email:
            # Auto-generate company from email domain
            domain = r.email.split("@")[-1].split(".")[0].title()
            if domain not in ("Gmail", "Yahoo", "Hotmail", "Outlook", "Aol", "Icloud"):
                r.company_name = domain
                issues.append("Company inferred from email")
                if status == "Ready": status = "Warning"

        r.status = status
        r.validation_issues = json.dumps(issues)
        
        if status == "Ready" or status == "Warning":
            valid_count += 1
        elif status == "Error":
            error_count += 1
        elif status == "Duplicate":
            dup_count += 1

    job.valid_rows = valid_count
    job.error_rows = error_count
    job.duplicate_rows = dup_count
    job.status = "preview"
    
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
    
    for i, r in enumerate(rows):
        if r.status in ["Ready", "Warning"]:
            # Check duplicate again just in case (e.g. against rows just inserted in this loop)
            if not db.query(Recruiter).filter(Recruiter.email == r.email).first():
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
                metadata = {k: v for k, v in raw_dict.items() if k not in mapped_keys and v is not None and str(v).strip() != ""}
                metadata_json = json.dumps(metadata) if metadata else None
                
                # Extract alternative emails/phones from metadata
                email2 = None
                phone2 = None
                for k, v in metadata.items():
                    key_lower = k.lower()
                    if "email" in key_lower and not email2 and str(v).strip().lower() != (r.email or "").lower():
                        email2 = str(v).strip()
                    elif ("phone" in key_lower or "mobile" in key_lower or "cell" in key_lower) and not phone2:
                        cp = clean_phone(str(v))
                        if cp and cp != r.phone:
                            phone2 = cp

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
                    metadata_json=metadata_json
                )
                db.add(rec)
                inserted += 1
                
                # Chunked commits
                if inserted % 500 == 0:
                    db.commit()
            else:
                skipped += 1
                r.status = "Duplicate"
        else:
            skipped += 1
            
    db.commit()
    
    job.inserted_rows = inserted
    job.skipped_rows = skipped
    job.status = "completed"
    job.completed_at = datetime.utcnow()
    
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
