from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
import io, csv
from openpyxl import load_workbook
from app.database import get_db
from app.models.models import Candidate, Recruiter

router = APIRouter()

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
            specialization=str(row["specialization"]).strip() if row.get("specialization") else None,
            is_active=True,
        )
        db.add(recruiter); inserted += 1
    db.commit()
    return {"message": "Upload complete", "inserted": inserted, "duplicates_skipped": duplicates, "total_rows": len(rows)}