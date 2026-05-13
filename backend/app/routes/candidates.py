from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_
from pydantic import BaseModel
from typing import Optional, List
from app.database import get_db
from app.models.models import Candidate

router = APIRouter()

class CandidateCreate(BaseModel):
    candidate_name: str
    email: str
    phone: Optional[str] = None
    linkedin: Optional[str] = None
    visa_status: Optional[str] = None
    skills: Optional[List[str]] = []
    experience_years: Optional[float] = None
    location: Optional[str] = None
    rate_per_hour: Optional[float] = None
    availability: Optional[str] = None
    recruiter_id: Optional[int] = None

class CandidateUpdate(BaseModel):
    candidate_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin: Optional[str] = None
    visa_status: Optional[str] = None
    skills: Optional[List[str]] = None
    experience_years: Optional[float] = None
    location: Optional[str] = None
    rate_per_hour: Optional[float] = None
    availability: Optional[str] = None
    is_duplicate: Optional[bool] = None
    recruiter_id: Optional[int] = None

@router.get("/")
def get_candidates(
    skip: int = 0,
    limit: int = 100,
    visa_status: Optional[str] = None,
    location: Optional[str] = None,
    skill: Optional[str] = None,
    availability: Optional[str] = None,
    is_duplicate: Optional[bool] = None,
    min_experience: Optional[float] = None,
    max_rate: Optional[float] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Candidate)
    if visa_status:
        query = query.filter(Candidate.visa_status == visa_status)
    if location:
        query = query.filter(Candidate.location.ilike(f"%{location}%"))
    if skill:
        query = query.filter(Candidate.skills.any(skill))
    if availability:
        query = query.filter(Candidate.availability == availability)
    if is_duplicate is not None:
        query = query.filter(Candidate.is_duplicate == is_duplicate)
    if min_experience is not None:
        query = query.filter(Candidate.experience_years >= min_experience)
    if max_rate is not None:
        query = query.filter(Candidate.rate_per_hour <= max_rate)
    return query.offset(skip).limit(limit).all()

@router.get("/{candidate_id}")
def get_candidate(candidate_id: int, db: Session = Depends(get_db)):
    c = db.query(Candidate).filter(Candidate.candidate_id == candidate_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return c

@router.post("/", status_code=201)
def create_candidate(data: CandidateCreate, db: Session = Depends(get_db)):
    existing = db.query(Candidate).filter(Candidate.email == data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Candidate with this email already exists")
    c = Candidate(**data.dict())
    db.add(c)
    db.commit()
    db.refresh(c)
    return c

@router.put("/{candidate_id}")
def update_candidate(candidate_id: int, data: CandidateUpdate, db: Session = Depends(get_db)):
    c = db.query(Candidate).filter(Candidate.candidate_id == candidate_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Candidate not found")
    for key, value in data.dict(exclude_unset=True).items():
        setattr(c, key, value)
    db.commit()
    db.refresh(c)
    return c

@router.delete("/{candidate_id}")
def delete_candidate(candidate_id: int, db: Session = Depends(get_db)):
    c = db.query(Candidate).filter(Candidate.candidate_id == candidate_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Candidate not found")
    db.delete(c)
    db.commit()
    return {"message": "Candidate deleted"}

@router.get("/{candidate_id}/duplicates")
def find_duplicates(candidate_id: int, db: Session = Depends(get_db)):
    c = db.query(Candidate).filter(Candidate.candidate_id == candidate_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Candidate not found")
    dupes = db.query(Candidate).filter(
        Candidate.candidate_id != candidate_id,
        or_(
            Candidate.email == c.email,
            Candidate.phone == c.phone
        )
    ).all()
    return {"candidate_id": candidate_id, "duplicates_found": len(dupes), "duplicates": dupes}
