from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.auth_models import User
from app.services.auth_service import get_current_user_from_request
from app.models.sentinel_state import SentinelPhase4State

router = APIRouter()

@router.get("/dashboard")
def get_sentinel_dashboard(db: Session = Depends(get_db), current_user: User = Depends(get_current_user_from_request)):
    if not current_user.role or current_user.role.name.lower() not in ('admin', 'superadmin'):
        return {"error": "Unauthorized"}
    
    from sqlalchemy import func
    from app.models.models import Recruiter
    
    state = db.query(SentinelPhase4State).first()
    
    # Calculate perfectly synced LIVE counts from Postgres / Parquet
    from app.services.recruiter_store import RecruiterStore
    store = RecruiterStore.get_instance()
    
    total_recruiters = store._record_count if store._loaded else (db.query(func.count(Recruiter.recruiter_id)).scalar() or 0)
    total_comps = (store._conn.execute("SELECT COUNT(*) FROM company_summary").fetchone()[0] if store._loaded else db.query(func.count(func.distinct(Recruiter.company_id))).scalar() or 0)
    
    missing_emails = db.query(func.count(Recruiter.recruiter_id)).filter((Recruiter.email == None) | (Recruiter.email == '') | (Recruiter.email.ilike('%missing.local%'))).scalar() or 0
    missing_phones = db.query(func.count(Recruiter.recruiter_id)).filter((Recruiter.phone == None) | (Recruiter.phone == '')).scalar() or 0
    missing_li = db.query(func.count(Recruiter.recruiter_id)).filter((Recruiter.linkedin == None) | (Recruiter.linkedin == '')).scalar() or 0
    unknown_comps = db.query(func.count(Recruiter.recruiter_id)).filter(Recruiter.company_id == None).scalar() or 0
    
    below_50 = db.query(func.count(Recruiter.recruiter_id)).filter(Recruiter.completeness_score < 50).scalar() or 0
    above_90 = db.query(func.count(Recruiter.recruiter_id)).filter(Recruiter.completeness_score > 90).scalar() or 0
    avg_comp = db.query(func.avg(Recruiter.completeness_score)).scalar() or 0
    
    return {
        "status": state.status if state else "Offline",
        "total_recruiters": total_recruiters,
        "total_companies": total_comps,
        "unknown_companies": unknown_comps,
        "missing_emails": missing_emails,
        "missing_phones": missing_phones,
        "missing_linkedin": missing_li,
        "missing_logos": state.missing_logos if state else 0, # Assuming logo requires company join, we can keep cached for speed
        "profiles_below_50": below_50,
        "profiles_above_90": above_90,
        "avg_confidence": state.avg_confidence if state else 0,
        "avg_completeness": int(avg_comp),
        "companies_completed": state.companies_completed if state else 0,
        "recruiters_completed": state.recruiters_completed if state else 0,
        "current_company_name": state.current_company_name if state else "-",
        "current_state": state.current_state if state else "-",
        "estimated_completion_hours": state.estimated_completion_hours if state else 0
    }
