from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from app.database import get_db
from app.models.models import Recruiter, Candidate, Submission, Company, Vendor

router = APIRouter()

@router.get("/dashboard")
def get_dashboard_kpis(db: Session = Depends(get_db)):
    total_recruiters    = db.query(Recruiter).count()
    active_recruiters   = db.query(Recruiter).filter(Recruiter.is_active == True).count()
    total_candidates    = db.query(Candidate).count()
    duplicate_candidates = db.query(Candidate).filter(Candidate.is_duplicate == True).count()
    total_submissions   = db.query(Submission).count()
    placed              = db.query(Submission).filter(Submission.status == "placed").count()
    interviews          = db.query(Submission).filter(Submission.status == "interview").count()
    offers              = db.query(Submission).filter(Submission.status == "offer").count()
    total_companies     = db.query(Company).count()
    total_vendors       = db.query(Vendor).count()

    placement_rate = round((placed / total_submissions * 100), 1) if total_submissions > 0 else 0
    duplicate_rate = round((duplicate_candidates / total_candidates * 100), 1) if total_candidates > 0 else 0

    return {
        "recruiters": {
            "total": total_recruiters,
            "active": active_recruiters,
            "inactive": total_recruiters - active_recruiters
        },
        "candidates": {
            "total": total_candidates,
            "duplicates": duplicate_candidates,
            "duplicate_rate_percent": duplicate_rate
        },
        "submissions": {
            "total": total_submissions,
            "placed": placed,
            "interviews": interviews,
            "offers": offers,
            "placement_rate_percent": placement_rate
        },
        "companies": {"total": total_companies},
        "vendors": {"total": total_vendors}
    }

@router.get("/submissions-by-status")
def submissions_by_status(db: Session = Depends(get_db)):
    results = db.query(
        Submission.status,
        func.count(Submission.submission_id).label("count")
    ).group_by(Submission.status).all()
    return [{"status": r.status, "count": r.count} for r in results]

@router.get("/candidates-by-visa")
def candidates_by_visa(db: Session = Depends(get_db)):
    results = db.query(
        Candidate.visa_status,
        func.count(Candidate.candidate_id).label("count")
    ).group_by(Candidate.visa_status).all()
    return [{"visa_status": r.visa_status, "count": r.count} for r in results]

@router.get("/recruiter-productivity")
def recruiter_productivity(db: Session = Depends(get_db)):
    results = db.query(
        Recruiter.recruiter_name,
        func.count(Submission.submission_id).label("total_submissions"),
        func.sum(case((Submission.status == "placed", 1), else_=0)).label("placements"),
        func.sum(case((Submission.status == "interview", 1), else_=0)).label("interviews")
    ).join(Submission, Submission.recruiter_id == Recruiter.recruiter_id, isouter=True)\
     .group_by(Recruiter.recruiter_id, Recruiter.recruiter_name).all()

    return [{
        "recruiter": r.recruiter_name,
        "total_submissions": r.total_submissions or 0,
        "placements": r.placements or 0,
        "interviews": r.interviews or 0
    } for r in results]

@router.get("/submissions-trend")
def submissions_trend(db: Session = Depends(get_db)):
    results = db.query(
        func.date_trunc("month", Submission.submission_date).label("month"),
        func.count(Submission.submission_id).label("count")
    ).group_by("month").order_by("month").all()
    return [{"month": str(r.month)[:7], "count": r.count} for r in results]
