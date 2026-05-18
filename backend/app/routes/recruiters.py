from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from typing import Optional, List
from app.database import get_db
from app.models.models import Recruiter, Company

router = APIRouter()

class RecruiterCreate(BaseModel):
    recruiter_name: str
    email: str
    phone: Optional[str] = None
    linkedin: Optional[str] = None
    specialization: Optional[str] = None
    company_id: Optional[int] = None
    is_active: Optional[bool] = True

class RecruiterUpdate(BaseModel):
    recruiter_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin: Optional[str] = None
    specialization: Optional[str] = None
    company_id: Optional[int] = None
    is_active: Optional[bool] = None

def serialize_recruiter(r):
    return {
        "recruiter_id": r.recruiter_id,
        "recruiter_name": r.recruiter_name,
        "email": r.email,
        "phone": r.phone,
        "linkedin": r.linkedin,
        "specialization": r.specialization,
        "company_id": r.company_id,
        "company_name": r.company.company_name if r.company else None,
        "is_active": r.is_active,
        "created_at": str(r.created_at) if r.created_at else None,
    }

# --- Smart Ranked Search ---
@router.get("/search")
def search_recruiters(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """
    Smart weighted search using pg_trgm similarity + ILIKE scoring.
    Results are ranked by relevance_score descending.

    Scoring breakdown:
      +200  exact name match
      +130  name starts with query
      +100  name contains query
      +80   email contains query
      +60   company contains query
      +40   specialization contains query
      +0-30 fuzzy name similarity (pg_trgm)
      +0-15 fuzzy email similarity (pg_trgm)
    """
    try:
        db.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
        db.commit()
    except Exception:
        db.rollback()

    sql = text("""
        SELECT
            r.recruiter_id,
            r.recruiter_name,
            r.email,
            r.phone,
            r.linkedin,
            r.specialization,
            r.is_active,
            r.company_id,
            c.company_name,
            (
                CASE
                    WHEN LOWER(r.recruiter_name) = LOWER(:q)
                        THEN 200
                    WHEN LOWER(r.recruiter_name) LIKE LOWER(:q) || '%'
                        THEN 130
                    WHEN LOWER(r.recruiter_name) LIKE '%' || LOWER(:q) || '%'
                        THEN 100
                    ELSE 0
                END
                +
                CASE
                    WHEN LOWER(r.email) LIKE '%' || LOWER(:q) || '%'
                        THEN 80
                    ELSE 0
                END
                +
                CASE
                    WHEN LOWER(COALESCE(c.company_name, '')) LIKE '%' || LOWER(:q) || '%'
                        THEN 60
                    ELSE 0
                END
                +
                CASE
                    WHEN LOWER(COALESCE(r.specialization, '')) LIKE '%' || LOWER(:q) || '%'
                        THEN 40
                    ELSE 0
                END
                + ROUND(similarity(r.recruiter_name, :q) * 30)::int
                + ROUND(similarity(r.email, :q) * 15)::int
            ) AS relevance_score
        FROM recruiters r
        LEFT JOIN companies c ON r.company_id = c.company_id
        WHERE
            r.recruiter_name ILIKE '%' || :q || '%'
            OR r.email ILIKE '%' || :q || '%'
            OR COALESCE(c.company_name, '') ILIKE '%' || :q || '%'
            OR COALESCE(r.specialization, '') ILIKE '%' || :q || '%'
            OR similarity(r.recruiter_name, :q) > 0.15
            OR similarity(r.email, :q) > 0.15
        ORDER BY relevance_score DESC
        LIMIT :limit
    """)

    rows = db.execute(sql, {"q": q, "limit": limit}).mappings().all()

    return [
        {
            "recruiter_id": row["recruiter_id"],
            "recruiter_name": row["recruiter_name"],
            "email": row["email"],
            "phone": row["phone"],
            "linkedin": row["linkedin"],
            "specialization": row["specialization"],
            "company_id": row["company_id"],
            "company_name": row["company_name"],
            "is_active": row["is_active"],
            "relevance_score": int(row["relevance_score"]),
        }
        for row in rows
    ]

# --- Standard CRUD ---
@router.get("/")
def get_recruiters(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    specialization: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Recruiter)
    if search:
        query = query.filter(
            Recruiter.recruiter_name.ilike(f"%{search}%") |
            Recruiter.email.ilike(f"%{search}%") |
            Recruiter.specialization.ilike(f"%{search}%")
        )
    if specialization:
        query = query.filter(Recruiter.specialization.ilike(f"%{specialization}%"))
    if is_active is not None:
        query = query.filter(Recruiter.is_active == is_active)
    results = query.offset(skip).limit(limit).all()
    return [serialize_recruiter(r) for r in results]

@router.get("/{recruiter_id}")
def get_recruiter(recruiter_id: int, db: Session = Depends(get_db)):
    r = db.query(Recruiter).filter(Recruiter.recruiter_id == recruiter_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Recruiter not found")
    return serialize_recruiter(r)

@router.post("/", status_code=201)
def create_recruiter(data: RecruiterCreate, db: Session = Depends(get_db)):
    existing = db.query(Recruiter).filter(Recruiter.email == data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already exists")
    r = Recruiter(**data.dict())
    db.add(r)
    db.commit()
    db.refresh(r)
    return serialize_recruiter(r)

@router.put("/{recruiter_id}")
def update_recruiter(recruiter_id: int, data: RecruiterUpdate, db: Session = Depends(get_db)):
    r = db.query(Recruiter).filter(Recruiter.recruiter_id == recruiter_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Recruiter not found")
    for key, value in data.dict(exclude_unset=True).items():
        setattr(r, key, value)
    db.commit()
    db.refresh(r)
    return serialize_recruiter(r)

@router.delete("/{recruiter_id}")
def delete_recruiter(recruiter_id: int, db: Session = Depends(get_db)):
    r = db.query(Recruiter).filter(Recruiter.recruiter_id == recruiter_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Recruiter not found")
    db.delete(r)
    db.commit()
    return {"message": "Recruiter deleted"}
