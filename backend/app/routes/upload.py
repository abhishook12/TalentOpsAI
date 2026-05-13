from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
import pandas as pd
import io
from app.database import get_db
from app.models.models import Candidate, Recruiter

router = APIRouter()

def clean_email(email: str) -> str:
    return str(email).lower().strip()

def clean_phone(phone: str) -> str:
    return str(phone).replace("-", "").replace(" ", "").replace("(", "").replace(")", "").strip()

def clean_name(name: str) -> str:
    return str(name).strip().title()

@router.post("/candidates")
async def upload_candidates(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.endswith((".csv", ".xlsx")):
        raise HTTPException(status_code=400, detail="Only CSV and Excel files are supported")

    contents = await file.read()

    if file.filename.endswith(".csv"):
        df = pd.read_csv(io.StringIO(contents.decode("utf-8")))
    else:
        df = pd.read_excel(io.BytesIO(contents))

    required_cols = ["candidate_name", "email"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing required columns: {missing}")

    inserted = 0
    skipped = 0
    duplicates = 0

    for _, row in df.iterrows():
        email = clean_email(row["email"])
        name  = clean_name(row["candidate_name"])

        existing = db.query(Candidate).filter(Candidate.email == email).first()
        if existing:
            duplicates += 1
            continue

        skills = []
        if "skills" in row and pd.notna(row["skills"]):
            skills = [s.strip() for s in str(row["skills"]).split(",")]

        candidate = Candidate(
            candidate_name   = name,
            email            = email,
            phone            = clean_phone(row.get("phone", "")) if pd.notna(row.get("phone", "")) else None,
            visa_status      = str(row["visa_status"]).strip() if "visa_status" in row and pd.notna(row.get("visa_status")) else None,
            skills           = skills,
            experience_years = float(row["experience_years"]) if "experience_years" in row and pd.notna(row.get("experience_years")) else None,
            location         = str(row["location"]).strip() if "location" in row and pd.notna(row.get("location")) else None,
            rate_per_hour    = float(row["rate_per_hour"]) if "rate_per_hour" in row and pd.notna(row.get("rate_per_hour")) else None,
            availability     = str(row["availability"]).strip() if "availability" in row and pd.notna(row.get("availability")) else None,
        )
        db.add(candidate)
        inserted += 1

    db.commit()

    return {
        "message": "Upload complete",
        "inserted": inserted,
        "duplicates_skipped": duplicates,
        "total_rows": len(df)
    }

@router.post("/recruiters")
async def upload_recruiters(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.endswith((".csv", ".xlsx")):
        raise HTTPException(status_code=400, detail="Only CSV and Excel files are supported")

    contents = await file.read()
    if file.filename.endswith(".csv"):
        df = pd.read_csv(io.StringIO(contents.decode("utf-8")))
    else:
        df = pd.read_excel(io.BytesIO(contents))

    required_cols = ["recruiter_name", "email"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing required columns: {missing}")

    inserted = 0
    duplicates = 0

    for _, row in df.iterrows():
        email = clean_email(row["email"])
        existing = db.query(Recruiter).filter(Recruiter.email == email).first()
        if existing:
            duplicates += 1
            continue

        recruiter = Recruiter(
            recruiter_name = clean_name(row["recruiter_name"]),
            email          = email,
            phone          = clean_phone(row.get("phone", "")) if pd.notna(row.get("phone", "")) else None,
            specialization = str(row["specialization"]).strip() if "specialization" in row and pd.notna(row.get("specialization")) else None,
        )
        db.add(recruiter)
        inserted += 1

    db.commit()
    return {"message": "Upload complete", "inserted": inserted, "duplicates_skipped": duplicates, "total_rows": len(df)}
