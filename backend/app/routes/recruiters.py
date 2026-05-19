from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload, contains_eager
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
    email2: Optional[str] = None
    phone2: Optional[str] = None
    linkedin: Optional[str] = None
    specialization: Optional[str] = None
    notes: Optional[str] = None
    company_id: Optional[int] = None
    location: Optional[str] = None
    is_active: Optional[bool] = True

class RecruiterUpdate(BaseModel):
    recruiter_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    email2: Optional[str] = None
    phone2: Optional[str] = None
    linkedin: Optional[str] = None
    specialization: Optional[str] = None
    notes: Optional[str] = None
    company_id: Optional[int] = None
    location: Optional[str] = None
    is_active: Optional[bool] = None

def serialize_recruiter(r):
    return {
        "recruiter_id": r.recruiter_id,
        "recruiter_name": r.recruiter_name,
        "email": r.email,
        "phone": r.phone,
        "email2": r.email2,
        "phone2": r.phone2,
        "linkedin": r.linkedin,
        "specialization": r.specialization,
        "notes": r.notes,
        "company_id": r.company_id,
        "company_name": r.company.company_name if r.company else None,
        "location": r.location if r.location else (r.company.location if r.company else None),
        "is_active": r.is_active,
        "created_at": str(r.created_at) if r.created_at else None,
    }

# --- Smart Ranked Search ---
@router.get("/search")
def search_recruiters(
    q: str = Query(..., min_length=1, description="Search query"),
    company: Optional[str] = Query(None, description="Filter by company"),
    location: Optional[str] = Query(None, description="Filter by location"),
    specialization: Optional[str] = Query(None, description="Filter by specialization"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """
    Smart weighted search using pg_trgm similarity + ILIKE scoring.
    Results are ranked by relevance_score descending.
    """
    try:
        db.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
        db.commit()
    except Exception:
        db.rollback()

    base_sql = """
        SELECT
            r.recruiter_id,
            r.recruiter_name,
            r.email,
            r.phone,
            r.email2,
            r.phone2,
            r.linkedin,
            r.specialization,
            r.notes,
            r.is_active,
            r.company_id,
            c.company_name,
            COALESCE(r.location, c.location) AS location,
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
                    WHEN LOWER(r.email) = LOWER(:q)
                        THEN 200
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
            (
                r.recruiter_name ILIKE '%' || :q || '%'
                OR r.email ILIKE '%' || :q || '%'
                OR COALESCE(c.company_name, '') ILIKE '%' || :q || '%'
                OR COALESCE(r.specialization, '') ILIKE '%' || :q || '%'
                OR similarity(r.recruiter_name, :q) > 0.3
                OR similarity(r.email, :q) > 0.3
            )
    """

    params = {"q": q, "limit": limit}

    if company:
        base_sql += " AND c.company_name ILIKE '%' || :company || '%'"
        params["company"] = company
    if location:
        base_sql += " AND c.location ILIKE '%' || :location || '%'"
        params["location"] = location
    if specialization:
        base_sql += " AND r.specialization ILIKE '%' || :specialization || '%'"
        params["specialization"] = specialization

    base_sql += " ORDER BY relevance_score DESC LIMIT :limit"

    rows = db.execute(text(base_sql), params).mappings().all()

    return [
        {
            "recruiter_id": row["recruiter_id"],
            "recruiter_name": row["recruiter_name"],
            "email": row["email"],
            "phone": row["phone"],
            "email2": row["email2"],
            "phone2": row["phone2"],
            "linkedin": row["linkedin"],
            "specialization": row["specialization"],
            "notes": row["notes"],
            "company_id": row["company_id"],
            "company_name": row["company_name"],
            "location": row.get("location"),
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
    location: Optional[str] = None,
    company: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Recruiter).join(Recruiter.company, isouter=True).options(contains_eager(Recruiter.company))
    if search:
        query = query.filter(
            Recruiter.recruiter_name.ilike(f"%{search}%") |
            Recruiter.email.ilike(f"%{search}%") |
            Recruiter.specialization.ilike(f"%{search}%")
        )
    if specialization:
        query = query.filter(Recruiter.specialization.ilike(f"%{specialization}%"))
    if location:
        query = query.filter(Recruiter.location.ilike(f"%{location}%") | Company.location.ilike(f"%{location}%"))
    if company:
        query = query.filter(Company.company_name.ilike(f"%{company}%"))
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
