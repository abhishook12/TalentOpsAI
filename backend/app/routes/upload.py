from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import pandas as pd
import io, csv, uuid, re
from openpyxl import load_workbook
from app.database import get_db
from app.models.models import Candidate, Recruiter
from app.utils.column_mapper import detect_columns
from app.schemas.upload import AnalyzeResponse

router = APIRouter()

# ─── Helpers ───────────────────────────────────────────────────────────────────
def clean_email(email): return str(email).lower().strip()
def clean_phone(phone): return str(phone).replace("-","").replace(" ","").replace("(","").replace(")","").strip()
def clean_name(name): return str(name).strip().title()

def read_file(contents, filename):
    if filename.endswith(".csv"):
        text = contents.decode("utf-8")
        reader = csv.DictReader(io.StringIO(text))
        return [row for row in reader]
    else:
        wb = load_workbook(io.BytesIO(contents))
        ws = wb.active
        headers = [cell.value for cell in ws[1]]
        return [dict(zip(headers, [cell.value for cell in row])) for row in ws.iter_rows(min_row=2)]

# ─── Original Legacy Endpoints (keep working) ─────────────────────────────────

@router.post("/candidates")
async def upload_candidates(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.endswith((".csv", ".xlsx")):
        raise HTTPException(status_code=400, detail="Only CSV and Excel files are supported")
    contents = await file.read()
    rows = read_file(contents, file.filename)
    if not rows or "candidate_name" not in rows[0] or "email" not in rows[0]:
        raise HTTPException(status_code=400, detail="Missing required columns: candidate_name, email")
    inserted = duplicates = 0
    for row in rows:
        email = clean_email(row.get("email",""))
        if not email: continue
        if db.query(Candidate).filter(Candidate.email == email).first():
            duplicates += 1; continue
        candidate = Candidate(
            candidate_name=clean_name(row.get("candidate_name","")),
            email=email,
            phone=clean_phone(row.get("phone","")) or None,
            visa_status=str(row["visa_status"]).strip() if row.get("visa_status") else None,
            skills=str(row["skills"]) if row.get("skills") else None,
            experience_years=float(row["experience_years"]) if row.get("experience_years") else None,
            location=str(row["location"]).strip() if row.get("location") else None,
            rate_per_hour=float(row["rate_per_hour"]) if row.get("rate_per_hour") else None,
            availability=str(row["availability"]).strip() if row.get("availability") else None,
        )
        db.add(candidate); inserted += 1
    db.commit()
    return {"message": "Upload complete", "inserted": inserted, "duplicates_skipped": duplicates, "total_rows": len(rows)}

@router.post("/recruiters")
async def upload_recruiters(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.endswith((".csv", ".xlsx")):
        raise HTTPException(status_code=400, detail="Only CSV and Excel files are supported")
    contents = await file.read()
    rows = read_file(contents, file.filename)
    if not rows or "recruiter_name" not in rows[0] or "email" not in rows[0]:
        raise HTTPException(status_code=400, detail="Missing required columns: recruiter_name, email")
    inserted = duplicates = 0
    for row in rows:
        email = clean_email(row.get("email",""))
        if not email: continue
        if db.query(Recruiter).filter(Recruiter.email == email).first():
            duplicates += 1; continue
        recruiter = Recruiter(
            recruiter_name=clean_name(row.get("recruiter_name","")),
            email=email,
            phone=clean_phone(row.get("phone","")) or None,
            email2=str(row["email2"]).lower().strip() if row.get("email2") else None,
            phone2=clean_phone(row.get("phone2","")) or None,
            linkedin=str(row["linkedin"]).strip() if row.get("linkedin") else None,
            specialization=str(row["specialization"]).strip() if row.get("specialization") else None,
            notes=str(row["notes"]).strip() if row.get("notes") else None,
            is_active=True,
        )
        db.add(recruiter); inserted += 1
    db.commit()
    return {"message": "Upload complete", "inserted": inserted, "duplicates_skipped": duplicates, "total_rows": len(rows)}


# ─── NEW: Smart Analyze Endpoint ──────────────────────────────────────────────

@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_file(file: UploadFile = File(...)):
    """Parse the uploaded CSV/Excel, automatically detect column mapping,
    run basic validation, and return a preview with statistics."""
    if not file.filename.lower().endswith((".csv", ".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Unsupported file type. Use CSV or Excel.")
    try:
        contents = await file.read()
        if file.filename.lower().endswith('.csv'):
            df = pd.read_csv(io.BytesIO(contents), dtype=str, keep_default_na=False)
        else:
            df = pd.read_excel(io.BytesIO(contents), dtype=str, keep_default_na=False)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse file: {e}")

    # Detect column mapping using heuristic matcher
    column_map = detect_columns(list(df.columns))

    total_rows = len(df)
    email_col = column_map.get('email')
    duplicates = missing = invalid_emails = invalid_phones = 0

    if email_col:
        duplicates = int(df[email_col].duplicated().sum())
        missing = int((df[email_col] == '').sum() + df[email_col].isna().sum())
        email_re = re.compile(r'^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$')
        valid_mask = df[email_col].astype(str).apply(lambda x: bool(email_re.match(x)))
        invalid_emails = int((~valid_mask).sum())

    phone_re = re.compile(r'^(?:\+?1[\s.\-]?)?\(?\d{3}\)?[\s.\-]?\d{3}[\s.\-]?\d{4}$')
    phone_cols = [c for k, c in column_map.items() if k.startswith('phone')]
    for pc in phone_cols:
        valid_mask = df[pc].astype(str).apply(lambda x: bool(phone_re.match(x)) if x.strip() else True)
        invalid_phones += int((~valid_mask).sum())

    # Empty columns
    empty_cols = [c for c in df.columns if (df[c] == '').all() or df[c].isna().all()]

    # Corrupted rows (all empty)
    corrupted = int((df.apply(lambda row: all(str(v).strip() == '' for v in row), axis=1)).sum())

    # Prepare preview (first 10 rows) with original headers
    preview: List[Dict[str, Any]] = []
    for _, row in df.head(10).iterrows():
        preview.append({col: row[col] for col in df.columns})

    analysis_id = str(uuid.uuid4())
    return AnalyzeResponse(
        analysis_id=analysis_id,
        total_rows=total_rows,
        duplicates=duplicates,
        missing_fields=missing,
        invalid_emails=invalid_emails,
        invalid_phones=invalid_phones,
        empty_columns=empty_cols,
        corrupted_rows=corrupted,
        column_map=column_map,
        original_headers=list(df.columns),
        preview=preview,
    )


# ─── NEW: Smart Import Endpoint ───────────────────────────────────────────────

@router.post("/smart-import")
async def smart_import(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Accept a file + column mapping (as query params or JSON body) and import
    using the smart mapping. For now the mapping is auto‑detected.
    """
    if not file.filename.lower().endswith((".csv", ".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Unsupported file type. Use CSV or Excel.")
    try:
        contents = await file.read()
        if file.filename.lower().endswith('.csv'):
            df = pd.read_csv(io.BytesIO(contents), dtype=str, keep_default_na=False)
        else:
            df = pd.read_excel(io.BytesIO(contents), dtype=str, keep_default_na=False)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse file: {e}")

    column_map = detect_columns(list(df.columns))
    email_col = column_map.get('email')
    if not email_col:
        raise HTTPException(status_code=400, detail="Could not detect an email column in this file.")

    name_col = column_map.get('name')
    phone_col = column_map.get('phone')
    phone2_col = column_map.get('phone2')
    email2_col = column_map.get('email2')
    linkedin_col = column_map.get('linkedin')
    spec_col = column_map.get('specialization')
    notes_col = column_map.get('notes')

    inserted = duplicates = errors = 0
    for _, row in df.iterrows():
        try:
            email = clean_email(str(row.get(email_col, '')))
            if not email or email == 'nan' or '@' not in email:
                errors += 1
                continue
            if db.query(Recruiter).filter(Recruiter.email == email).first():
                duplicates += 1
                continue
            recruiter = Recruiter(
                recruiter_name=clean_name(str(row.get(name_col, ''))) if name_col else email.split('@')[0].title(),
                email=email,
                phone=clean_phone(str(row.get(phone_col, ''))) or None if phone_col else None,
                email2=clean_email(str(row.get(email2_col, ''))) or None if email2_col else None,
                phone2=clean_phone(str(row.get(phone2_col, ''))) or None if phone2_col else None,
                linkedin=str(row.get(linkedin_col, '')).strip() or None if linkedin_col else None,
                specialization=str(row.get(spec_col, '')).strip() or None if spec_col else None,
                notes=str(row.get(notes_col, '')).strip() or None if notes_col else None,
                is_active=True,
            )
            db.add(recruiter)
            inserted += 1
            # Batch commit every 2000 rows
            if inserted % 2000 == 0:
                db.commit()
        except Exception:
            errors += 1
            continue
    db.commit()
    return {
        "message": "Smart import complete",
        "inserted": inserted,
        "duplicates_skipped": duplicates,
        "errors": errors,
        "total_rows": len(df),
        "column_map_used": column_map,
    }