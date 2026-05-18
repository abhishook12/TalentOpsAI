from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import date
from app.database import get_db
from app.models.models import Submission, Candidate, Recruiter, Company, Vendor

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

def serialize_submission(s):
    return {
        "submission_id": s.submission_id,
        "candidate_id": s.candidate_id,
        "candidate_name": s.candidate.candidate_name if s.candidate else None,
        "recruiter_id": s.recruiter_id,
        "recruiter_name": s.recruiter.recruiter_name if s.recruiter else None,
        "company_id": s.company_id,
        "company_name": s.company.company_name if s.company else None,
        "vendor_id": s.vendor_id,
        "vendor_name": s.vendor.vendor_name if s.vendor else None,
        "job_title": s.job_title,
        "status": s.status,
        "submission_date": str(s.submission_date) if s.submission_date else None,
        "interview_date": str(s.interview_date) if s.interview_date else None,
        "notes": s.notes,
        "created_at": str(s.created_at) if s.created_at else None,
    }

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
    results = query.offset(skip).limit(limit).all()
    return [serialize_submission(s) for s in results]

@router.get("/{submission_id}")
def get_submission(submission_id: int, db: Session = Depends(get_db)):
    s = db.query(Submission).filter(Submission.submission_id == submission_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Submission not found")
    return serialize_submission(s)

@router.post("/", status_code=201)
def create_submission(data: SubmissionCreate, db: Session = Depends(get_db)):
    if data.status and data.status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of {VALID_STATUSES}")
    s = Submission(**data.dict())
    db.add(s)
    db.commit()
    db.refresh(s)
    return serialize_submission(s)

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
    return serialize_submission(s)

@router.delete("/{submission_id}")
def delete_submission(submission_id: int, db: Session = Depends(get_db)):
    s = db.query(Submission).filter(Submission.submission_id == submission_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Submission not found")
    db.delete(s)
    db.commit()
    return {"message": "Submission deleted"}
