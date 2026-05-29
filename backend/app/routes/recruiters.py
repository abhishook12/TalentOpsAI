import re
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session, joinedload, contains_eager
from sqlalchemy import text
from pydantic import BaseModel
from typing import List, Optional
from app.database import get_db
from app.routes.auth import verify_admin
from app.models.models import Recruiter, Company

from app.utils.state_mapper import normalize_state


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
        "state": r.state,
        "normalized_city": getattr(r, "normalized_city", None),
        "completeness_score": getattr(r, "completeness_score", 0),
        "needs_review": getattr(r, "needs_review", False),
        "location_confidence": getattr(r, "location_confidence", "high"),
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
        abbr = normalize_state(location)
        if abbr:
            base_sql += " AND COALESCE(r.state, c.state) = :location"
            params["location"] = abbr
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

@router.get("/")
def get_recruiters(
    response: Response,
    page: int = 1,
    limit: int = 100,
    search: Optional[str] = None,
    state: Optional[str] = None,
    city: Optional[str] = None,
    company: Optional[str] = None,
    title: Optional[str] = None,
    has_phone: Optional[bool] = None,
    missing_email: Optional[bool] = None,
    is_active: Optional[bool] = None,
    min_completeness: Optional[int] = None,
    needs_review: Optional[bool] = None,
    sort_by: Optional[str] = "created_at",
    sort_desc: Optional[bool] = True,
    db: Session = Depends(get_db)
):
    query = db.query(Recruiter).join(Recruiter.company, isouter=True).options(contains_eager(Recruiter.company))
    
    from app.utils.normalizer import normalize_text
    
    if search:
        clean_search = normalize_text(search)
        query = query.filter(
            Recruiter.normalized_recruiter_name.ilike(f"%{clean_search}%") |
            Recruiter.email.ilike(f"%{search}%") |
            Recruiter.specialization.ilike(f"%{search}%") |
            Company.normalized_company_name.ilike(f"%{clean_search}%")
        )
    
    if state:
        # State filter now perfectly uses normalized state
        query = query.filter(Recruiter.state == state)
        
    if city:
        query = query.filter(Recruiter.normalized_city.ilike(f"%{city}%"))
        
    if company:
        clean_company = normalize_text(company)
        query = query.filter(Company.normalized_company_name.ilike(f"%{clean_company}%"))
        
    if title:
        query = query.filter(Recruiter.specialization.ilike(f"%{title}%"))
        
    if has_phone is True:
        query = query.filter(Recruiter.phone.isnot(None), Recruiter.phone != "")
    elif has_phone is False:
        query = query.filter((Recruiter.phone.is_(None)) | (Recruiter.phone == ""))
        
    if missing_email is True:
        query = query.filter((Recruiter.email.is_(None)) | (Recruiter.email == ""))
    elif missing_email is False:
        query = query.filter(Recruiter.email.isnot(None), Recruiter.email != "")
        
    if is_active is not None:
        query = query.filter(Recruiter.is_active == is_active)
        
    if min_completeness is not None:
        query = query.filter(Recruiter.completeness_score >= min_completeness)
        
    if needs_review is not None:
        query = query.filter(Recruiter.needs_review == needs_review)
        
    total_count = query.count()
    response.headers["X-Total-Count"] = str(total_count)
    
    # Sorting
    if sort_by == "name":
        order_col = Recruiter.recruiter_name
    elif sort_by == "company":
        order_col = Company.company_name
    elif sort_by == "state":
        order_col = Recruiter.state
    elif sort_by == "completeness":
        order_col = Recruiter.completeness_score
    else:
        order_col = Recruiter.created_at
        
    if sort_desc:
        query = query.order_by(order_col.desc().nullslast())
    else:
        query = query.order_by(order_col.asc().nullslast())
    
    skip = (page - 1) * limit
    results = query.offset(skip).limit(limit).all()
    
    import math
    total_pages = math.ceil(total_count / limit) if limit else 1
    
    return {
        "total_count": total_count,
        "page": page,
        "total_pages": total_pages,
        "results": [serialize_recruiter(r) for r in results]
    }

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
        
    r_data = data.dict()
    state = normalize_state(r_data.get('location'))
    if not state and r_data.get('company_id'):
        company = db.query(Company).filter(Company.company_id == r_data['company_id']).first()
        if company and company.location:
            state = normalize_state(company.location)
            
    r = Recruiter(**r_data, state=state)
    db.add(r)
    db.commit()
    db.refresh(r)
    return serialize_recruiter(r)

@router.put("/{recruiter_id}")
def update_recruiter(recruiter_id: int, data: RecruiterUpdate, db: Session = Depends(get_db), _=Depends(verify_admin)):
    r = db.query(Recruiter).filter(Recruiter.recruiter_id == recruiter_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Recruiter not found")
        
    update_data = data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(r, key, value)
        
    # Re-evaluate state if location or company changed
    if 'location' in update_data or 'company_id' in update_data:
        loc = r.location
        if not loc and r.company_id:
            comp = db.query(Company).filter(Company.company_id == r.company_id).first()
            if comp:
                loc = comp.location
        r.state = normalize_state(loc) if loc else None
        
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
