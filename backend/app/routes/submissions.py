from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import date
from app.database import get_db
from app.models.models import Submission

router = APIRouter()

VALID_STATUSES = ["submitted", "interview", "offer", "rejected", "placed", "withdrawn"]

class SubmissionCreate(BaseModel):
    candidate_id: int
    recruiter_id: Optional[int] = None
    company_id: Optional[int] = None
    vendor_id: Optional[int] = None
    job_title: Optional[str] = None
    status: Optional[str] = "submitted"
    submission_date: Optional[date] = None
    interview_date: Optional[date] = None
    notes: Optional[str] = None

class SubmissionUpdate(BaseModel):
    recruiter_id: Optional[int] = None
    company_id: Optional[int] = None
    vendor_id: Optional[int] = None
    job_title: Optional[str] = None
    status: Optional[str] = None
    interview_date: Optional[date] = None
    notes: Optional[str] = None

@router.get("/")
def get_submissions(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    recruiter_id: Optional[int] = None,
    company_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Submission)
    if status:
        query = query.filter(Submission.status == status)
    if recruiter_id:
        query = query.filter(Submission.recruiter_id == recruiter_id)
    if company_id:
        query = query.filter(Submission.company_id == company_id)
    return query.offset(skip).limit(limit).all()

@router.get("/{submission_id}")
def get_submission(submission_id: int, db: Session = Depends(get_db)):
    s = db.query(Submission).filter(Submission.submission_id == submission_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Submission not found")
    return s

@router.post("/", status_code=201)
def create_submission(data: SubmissionCreate, db: Session = Depends(get_db)):
    if data.status and data.status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of {VALID_STATUSES}")
    s = Submission(**data.dict())
    db.add(s)
    db.commit()
    db.refresh(s)
    return s

@router.put("/{submission_id}")
def update_submission(submission_id: int, data: SubmissionUpdate, db: Session = Depends(get_db)):
    s = db.query(Submission).filter(Submission.submission_id == submission_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Submission not found")
    if data.status and data.status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of {VALID_STATUSES}")
    for key, value in data.dict(exclude_unset=True).items():
        setattr(s, key, value)
    db.commit()
    db.refresh(s)
    return s

@router.delete("/{submission_id}")
def delete_submission(submission_id: int, db: Session = Depends(get_db)):
    s = db.query(Submission).filter(Submission.submission_id == submission_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Submission not found")
    db.delete(s)
    db.commit()
    return {"message": "Submission deleted"}
