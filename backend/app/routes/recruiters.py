from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from app.database import get_db
from app.models.models import Recruiter

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

@router.get("/")
def get_recruiters(
    skip: int = 0,
    limit: int = 100,
    specialization: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Recruiter)
    if specialization:
        query = query.filter(Recruiter.specialization.ilike(f"%{specialization}%"))
    if is_active is not None:
        query = query.filter(Recruiter.is_active == is_active)
    return query.offset(skip).limit(limit).all()

@router.get("/{recruiter_id}")
def get_recruiter(recruiter_id: int, db: Session = Depends(get_db)):
    r = db.query(Recruiter).filter(Recruiter.recruiter_id == recruiter_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Recruiter not found")
    return r

@router.post("/", status_code=201)
def create_recruiter(data: RecruiterCreate, db: Session = Depends(get_db)):
    existing = db.query(Recruiter).filter(Recruiter.email == data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already exists")
    r = Recruiter(**data.dict())
    db.add(r)
    db.commit()
    db.refresh(r)
    return r

@router.put("/{recruiter_id}")
def update_recruiter(recruiter_id: int, data: RecruiterUpdate, db: Session = Depends(get_db)):
    r = db.query(Recruiter).filter(Recruiter.recruiter_id == recruiter_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Recruiter not found")
    for key, value in data.dict(exclude_unset=True).items():
        setattr(r, key, value)
    db.commit()
    db.refresh(r)
    return r

@router.delete("/{recruiter_id}")
def delete_recruiter(recruiter_id: int, db: Session = Depends(get_db)):
    r = db.query(Recruiter).filter(Recruiter.recruiter_id == recruiter_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Recruiter not found")
    db.delete(r)
    db.commit()
    return {"message": "Recruiter deleted"}
