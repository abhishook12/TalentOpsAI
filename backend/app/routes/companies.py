from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from ..database import get_db
from ..models.models import Company

router = APIRouter()

class CompanyCreate(BaseModel):
    company_name: str
    industry: Optional[str] = None
    location: Optional[str] = None
    website: Optional[str] = None
    email_pattern: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = True

class CompanyUpdate(BaseModel):
    company_name: Optional[str] = None
    industry: Optional[str] = None
    location: Optional[str] = None
    website: Optional[str] = None
    email_pattern: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None

@router.get("/")
def get_companies(
    skip: int = 0, 
    limit: int = 100, 
    state: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Company)
    if state:
        abbr = normalize_state(state)
        if abbr:
            query = query.filter(Company.state == abbr)
    return query.offset(skip).limit(limit).all()

@router.get("/{company_id}")
def get_company(company_id: int, db: Session = Depends(get_db)):
    c = db.query(Company).filter(Company.company_id == company_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Company not found")
    return c

from ..utils.state_mapper import normalize_state

from .auth import verify_admin

@router.post("/", status_code=201)
def create_company(data: CompanyCreate, db: Session = Depends(get_db), _=Depends(verify_admin)):
    c_data = data.dict()
    state = normalize_state(c_data.get('location'))
    c = Company(**c_data, state=state)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c

@router.put("/{company_id}")
def update_company(company_id: int, data: CompanyUpdate, db: Session = Depends(get_db), _=Depends(verify_admin)):
    c = db.query(Company).filter(Company.company_id == company_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Company not found")
        
    update_data = data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(c, key, value)
        
    if 'location' in update_data:
        c.state = normalize_state(c.location) if c.location else None
        
    db.commit()
    db.refresh(c)
    return c

@router.delete("/{company_id}")
def delete_company(company_id: int, db: Session = Depends(get_db), _=Depends(verify_admin)):
    c = db.query(Company).filter(Company.company_id == company_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Company not found")
    db.delete(c)
    db.commit()
    return {"message": "Company deleted"}
