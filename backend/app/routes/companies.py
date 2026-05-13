from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from app.models.models import Company

router = APIRouter()

class CompanyCreate(BaseModel):
    company_name: str
    industry: Optional[str] = None
    location: Optional[str] = None
    website: Optional[str] = None

class CompanyUpdate(BaseModel):
    company_name: Optional[str] = None
    industry: Optional[str] = None
    location: Optional[str] = None
    website: Optional[str] = None

@router.get("/")
def get_companies(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(Company).offset(skip).limit(limit).all()

@router.get("/{company_id}")
def get_company(company_id: int, db: Session = Depends(get_db)):
    c = db.query(Company).filter(Company.company_id == company_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Company not found")
    return c

@router.post("/", status_code=201)
def create_company(data: CompanyCreate, db: Session = Depends(get_db)):
    c = Company(**data.dict())
    db.add(c)
    db.commit()
    db.refresh(c)
    return c

@router.put("/{company_id}")
def update_company(company_id: int, data: CompanyUpdate, db: Session = Depends(get_db)):
    c = db.query(Company).filter(Company.company_id == company_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Company not found")
    for key, value in data.dict(exclude_unset=True).items():
        setattr(c, key, value)
    db.commit()
    db.refresh(c)
    return c

@router.delete("/{company_id}")
def delete_company(company_id: int, db: Session = Depends(get_db)):
    c = db.query(Company).filter(Company.company_id == company_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Company not found")
    db.delete(c)
    db.commit()
    return {"message": "Company deleted"}
