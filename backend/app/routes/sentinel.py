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
    
    state = db.query(SentinelPhase4State).first()
    if not state:
        return {
            "status": "Offline",
            "total_recruiters": 0,
            "total_companies": 0,
            "unknown_companies": 0,
            "missing_emails": 0,
            "missing_phones": 0,
            "missing_linkedin": 0,
            "missing_logos": 0,
            "profiles_below_50": 0,
            "profiles_above_90": 0,
            "avg_confidence": 0,
            "avg_completeness": 0,
            "companies_completed": 0,
            "recruiters_completed": 0,
            "current_company_name": "-",
            "current_state": "-",
            "estimated_completion_hours": 0
        }
    
    return {
        "status": state.status,
        "total_recruiters": state.total_recruiters,
        "total_companies": state.total_companies,
        "unknown_companies": state.unknown_companies,
        "missing_emails": state.missing_emails,
        "missing_phones": state.missing_phones,
        "missing_linkedin": state.missing_linkedin,
        "missing_logos": state.missing_logos,
        "profiles_below_50": state.profiles_below_50,
        "profiles_above_90": state.profiles_above_90,
        "avg_confidence": state.avg_confidence,
        "avg_completeness": state.avg_completeness,
        "companies_completed": state.companies_completed,
        "recruiters_completed": state.recruiters_completed,
        "current_company_name": state.current_company_name,
        "current_state": state.current_state,
        "estimated_completion_hours": state.estimated_completion_hours
    }
