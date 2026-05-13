from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from app.models.models import Vendor

router = APIRouter()

class VendorCreate(BaseModel):
    vendor_name: str
    contact_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None

class VendorUpdate(BaseModel):
    vendor_name: Optional[str] = None
    contact_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None

@router.get("/")
def get_vendors(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(Vendor).offset(skip).limit(limit).all()

@router.get("/{vendor_id}")
def get_vendor(vendor_id: int, db: Session = Depends(get_db)):
    v = db.query(Vendor).filter(Vendor.vendor_id == vendor_id).first()
    if not v:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return v

@router.post("/", status_code=201)
def create_vendor(data: VendorCreate, db: Session = Depends(get_db)):
    v = Vendor(**data.dict())
    db.add(v)
    db.commit()
    db.refresh(v)
    return v

@router.put("/{vendor_id}")
def update_vendor(vendor_id: int, data: VendorUpdate, db: Session = Depends(get_db)):
    v = db.query(Vendor).filter(Vendor.vendor_id == vendor_id).first()
    if not v:
        raise HTTPException(status_code=404, detail="Vendor not found")
    for key, value in data.dict(exclude_unset=True).items():
        setattr(v, key, value)
    db.commit()
    db.refresh(v)
    return v

@router.delete("/{vendor_id}")
def delete_vendor(vendor_id: int, db: Session = Depends(get_db)):
    v = db.query(Vendor).filter(Vendor.vendor_id == vendor_id).first()
    if not v:
        raise HTTPException(status_code=404, detail="Vendor not found")
    db.delete(v)
    db.commit()
    return {"message": "Vendor deleted"}
